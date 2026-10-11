"""PNG evidence delivery independent of the 10-item manual review gallery."""
import base64
import hashlib
import json
import os
import tempfile
from pathlib import Path
import re
import urllib.error
import urllib.request

REPO = 'Evolution-by-Warder/PiconHub-Warder-Evolution'
BRANCH = 'factory-warder-development'
MAX_PNG = 2 * 1024 * 1024
PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'

def upload_png_evidence(report_dir, *, opener=None, state_path=None, max_attempts=None):
    """Send every eligible distinct referenced PNG; only successful responses count."""
    from review_ui import latest_review
    from review_queue import load_review_queue
    token = os.environ.get('WARDER_DIAGNOSTICS_TOKEN', '').strip()
    if not token:
        return {'status': 'not_configured', 'sent': 0, 'attempted': 0}
    review_path = latest_review(Path(report_dir))
    if not review_path:
        return {'status': 'no_review', 'sent': 0, 'attempted': 0}
    queue = load_review_queue(review_path)
    sent = attempted = skipped = 0
    state_path = Path(state_path) if state_path is not None else Path(report_dir) / 'png-evidence-delivered.json'
    try:
        ledger = json.loads(state_path.read_text(encoding='utf-8'))
        delivered = set(ledger['sha256']) if ledger.get('schema') == 1 and isinstance(ledger.get('sha256'), list) else set()
        delivered = {value for value in delivered if isinstance(value, str) and re.fullmatch(r'[a-f0-9]{64}', value)}
    except (OSError, ValueError, KeyError, TypeError):
        delivered = set()
    seen = set()
    errors = []
    stop_upload = False
    cooldown_path = state_path.with_name('png-evidence-cooldown.json')
    import time
    try:
        cooldown = json.loads(cooldown_path.read_text(encoding='utf-8'))
        if float(cooldown.get('until', 0)) > time.time():
            return {'status': 'cooldown', 'sent': 0, 'attempted': 0, 'errors': [str(cooldown.get('reason', 'HTTP limit'))]}
    except (OSError, ValueError, TypeError):
        pass
    for item in queue.get('items', []):
        if stop_upload or (max_attempts is not None and attempted >= max_attempts):
            break
        sources = [item.get('original')]
        for field in ('source_evidence', 'variants'):
            value = item.get(field) or []
            sources.extend(value if isinstance(value, (list, tuple)) else [value])
        paths = []
        for entry in sources:
            if isinstance(entry, str):
                paths.append(entry)
            elif isinstance(entry, dict):
                paths.append(entry.get('source'))
                nested = entry.get('sources') or []
                if isinstance(nested, (list, tuple)):
                    paths.extend(nested)
        for source in paths:
            if stop_upload or (max_attempts is not None and attempted >= max_attempts):
                break
            if not isinstance(source, str) or not source:
                continue
            path = Path(source)
            if path.suffix.lower() != '.png' or path.is_symlink() or not path.is_file():
                continue
            try:
                if path.stat().st_size > MAX_PNG or path.stat().st_size < 8:
                    continue
                content = path.read_bytes()
                if len(content) > MAX_PNG or not content.startswith(PNG_SIGNATURE):
                    continue
                sha = hashlib.sha256(content).hexdigest()
                if sha in seen:
                    continue
                seen.add(sha)
                if sha in delivered:
                    skipped += 1
                    continue
                attempted += 1
                run = review_path.stem.removeprefix('review-queue-')
                if not re.fullmatch(r'[0-9]{8}-[0-9]{6}-[0-9]+', run):
                    return {'status': 'invalid_run', 'sent': sent, 'attempted': attempted}
                # Content-addressed location avoids duplicate GitHub objects across runs.
                remote = 'factory/temp/evidence/sha256/' + sha[:2] + '/' + sha + '.png'
                url = 'https://api.github.com/repos/' + REPO + '/contents/' + remote
                body = json.dumps({'message': 'factory: diagnostic PNG evidence ' + sha[:12],
                                   'branch': BRANCH,
                                   'content': base64.b64encode(content).decode('ascii')}).encode('utf-8')
                request = urllib.request.Request(url, data=body, method='PUT', headers={
                    'Authorization': 'Bearer ' + token,
                    'Accept': 'application/vnd.github+json',
                    'Content-Type': 'application/json',
                    'User-Agent': 'Warder-Picon-Factory'})
                try:
                    with (opener or urllib.request.urlopen)(request, timeout=20) as response:
                        if response.status in (200, 201):
                            sent += 1
                            delivered.add(sha)
                            state_path.parent.mkdir(parents=True, exist_ok=True)
                            fd, temp = tempfile.mkstemp(prefix='.png-evidence-', suffix='.tmp', dir=state_path.parent)
                            try:
                                with os.fdopen(fd, 'w', encoding='utf-8') as output:
                                    json.dump({'schema': 1, 'sha256': sorted(delivered)}, output)
                                os.replace(temp, state_path)
                            finally:
                                if os.path.exists(temp):
                                    os.unlink(temp)
                        else:
                            errors.append('HTTP ' + str(response.status))
                except urllib.error.HTTPError as exc:
                    if exc.code == 422:
                        # A pre-existing file is accepted only if GitHub returns the same bytes.
                        try:
                            check = urllib.request.Request(url, headers={
                                'Authorization': 'Bearer ' + token,
                                'Accept': 'application/vnd.github+json',
                                'User-Agent': 'Warder-Picon-Factory'})
                            with (opener or urllib.request.urlopen)(check, timeout=20) as response:
                                remote_data = json.load(response)
                            # GitHub Contents API may omit base64 content for larger PNGs.
                            # Its blob SHA is a verifiable digest of the exact file bytes.
                            blob_sha = hashlib.sha1(b'blob ' + str(len(content)).encode('ascii') + b'\\0' + content).hexdigest()
                            if remote_data.get('sha') == blob_sha:
                                sent += 1
                                delivered.add(sha)
                                state_path.parent.mkdir(parents=True, exist_ok=True)
                                fd, temp = tempfile.mkstemp(prefix='.png-evidence-', suffix='.tmp', dir=state_path.parent)
                                try:
                                    with os.fdopen(fd, 'w', encoding='utf-8') as output:
                                        json.dump({'schema': 1, 'sha256': sorted(delivered)}, output)
                                    os.replace(temp, state_path)
                                finally:
                                    if os.path.exists(temp):
                                        os.unlink(temp)
                                continue
                        except (OSError, ValueError, KeyError, TypeError, urllib.error.HTTPError):
                            pass
                    errors.append('HTTP ' + str(exc.code))
                    if exc.code == 422:
                        stop_upload = True
                    # GitHub abuse/secondary limits and authentication failures
                    # must not trigger 20 identical write attempts each minute.
                    if exc.code in (401, 403, 429):
                        stop_upload = True
                        try:
                            cooldown_path.write_text(json.dumps({'until': time.time() + (3600 if exc.code in (403, 429) else 86400), 'reason': 'HTTP ' + str(exc.code)}), encoding='utf-8')
                        except OSError:
                            pass
            except (OSError, ValueError) as exc:
                errors.append(type(exc).__name__)
    return {'status': 'rate_limited_or_forbidden' if stop_upload else 'sent' if sent == attempted and attempted else 'partial' if sent else 'failed' if attempted else 'already_delivered' if skipped else 'no_evidence',
            'sent': sent, 'attempted': attempted, 'skipped': skipped, 'errors': errors[:5]}
