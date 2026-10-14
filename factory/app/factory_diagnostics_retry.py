"""Bounded, verified delivery of diagnostic JSON reports.

Failed reports remain local. Automatic attempts are persisted by file SHA so
the GUI scheduler cannot retry a broken/offline upload forever.
"""
import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from factory_diagnostics import upload_report


def _retryable(result):
    status = result.get('status')
    if status in ('offline_or_failed', 'verification_failed'):
        return True
    if status == 'http_error':
        code = result.get('code')
        return isinstance(code, int) and (code in (408, 429) or code >= 500)
    return False


def _read_state(path):
    if not path.exists():
        return {'schema': 1, 'attempts': {}}
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    if not isinstance(value, dict) or value.get('schema') != 1:
        return None
    attempts = value.get('attempts')
    if not isinstance(attempts, dict) or any(
            not isinstance(k, str) or not isinstance(v, int) or v < 0
            for k, v in attempts.items()):
        return None
    return value


def _write_state(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent,
                                         prefix=path.name + '.', suffix='.tmp',
                                         delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(state, stream, ensure_ascii=False, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except OSError:
        if temporary is not None:
            try:
                temporary.unlink()
            except OSError:
                pass
        raise


def retry_reports(report_dir, state_file, limit=5, *, max_attempts=3,
                  sleeper=time.sleep, force_retry=False):
    folder, state_file = Path(report_dir), Path(state_file)
    if limit < 1 or max_attempts < 1:
        raise ValueError('limit and max_attempts must be positive')
    if not folder.is_dir():
        return []
    paths = [p for p in sorted(folder.glob('report-*.json'), reverse=True)
             if not p.is_symlink() and p.is_file()]
    state = _read_state(state_file)
    if state is None:
        return [{'report': p.name, 'status': 'retry_state_invalid'} for p in paths[:limit]]
    attempts = state['attempts']
    results = []
    for path in paths:
        if len(results) >= limit:
            break
        try:
            before = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            results.append({'report': path.name, 'status': 'local_read_error'})
            continue
        key = path.name + ':' + before
        if force_retry:
            attempts.pop(key, None)
        count = attempts.get(key, 0)
        if count >= max_attempts:
            results.append({'report': path.name, 'status': 'retry_limit_reached',
                            'attempts': count})
            continue
        result = {'status': 'local_error'}
        for attempt in range(count, max_attempts):
            attempts[key] = attempt + 1
            try:
                _write_state(state_file, state)
            except OSError:
                result = {'status': 'retry_state_write_failed'}
                break
            try:
                result = upload_report(path)
            except (OSError, ValueError, KeyError, TypeError):
                result = {'status': 'local_error'}
            if result.get('status') == 'sent' and result.get('verified') is True:
                try:
                    after = hashlib.sha256(path.read_bytes()).hexdigest()
                except OSError:
                    result = {'status': 'local_read_error'}
                    break
                if after != before:
                    result = {'status': 'changed_during_delivery'}
                    attempts.pop(key, None)
                    _write_state(state_file, state)
                    break
                try:
                    path.unlink()
                    attempts.pop(key, None)
                    _write_state(state_file, state)
                except OSError:
                    result = {'status': 'verified_cleanup_failed'}
                    _write_state(state_file, state)
                break
            if result.get('status') == 'sent':
                result = {'status': 'verification_missing'}
            if attempt + 1 >= max_attempts or not _retryable(result):
                break
            sleeper(min(2 ** attempt, 5))
        results.append({'report': path.name, 'status': result.get('status', 'local_error'),
                        'attempts': attempts.get(key, 0)})
    return results
