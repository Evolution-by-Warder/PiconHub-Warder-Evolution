"""Optional automatic GitHub diagnostics upload; never uploads PNG or credentials.

Uploads only allowlisted numerical summaries to factory/temp on the existing
factory-warder-development branch. Requires WARDER_DIAGNOSTICS_TOKEN on the PC.
Git deletion does not erase historical commits.
"""
import json
import os
import re
import hashlib
import base64
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

_ALLOWED = re.compile(r'^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$')
_ALLOWED_KEYS = ('scanned', 'changed', 'duplicates', 'exceptions', 'created',
                 'review_queue_items', 'review_workstreams', 'qa_blocking',
                 'qa_repaired', 'qa_pending_by_workstream', 'integrity_issues',
                 'installed_factory_version', 'source_errors',
                 'run_duration_seconds', 'processing_failure')

def sanitized_summary(report):
    """Whitelist counters only: no file paths, PNG, service names or tokens."""
    stats = report.get('stats', {})
    if not isinstance(stats, dict):
        raise ValueError('Invalid stats')
    summary = {}
    for key in _ALLOWED_KEYS:
        value = stats.get(key)
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            summary[key] = value
        elif key in ('review_workstreams', 'qa_pending_by_workstream') and isinstance(value, dict):
            summary[key] = {str(k)[:60]: v for k, v in value.items()
                            if isinstance(k, str) and isinstance(v, int) and v >= 0}
        elif key == 'installed_factory_version' and isinstance(value, str):
            summary[key] = value[:60]
    # Preserve aggregate decision evidence, never raw filenames, paths, PNG or tokens.
    for key in ('qa_backlog_causes', 'openatv_identity_triage', 'artwork_evidence_counts',
                'pixel_evidence_counts', 'normalized_evidence_counts', 'scaled_evidence_counts',
                'review_queue_groups', 'final_picons_on_disk',
                'new_candidate_finalization', 'qa_grouping_savings'):
        value = stats.get(key)
        if isinstance(value, dict):
            safe = {k: v for k, v in value.items()
                    if isinstance(k, str) and re.fullmatch(r'[A-Za-z0-9_ -]{1,60}', k)
                    and isinstance(v, int) and not isinstance(v, bool) and v >= 0}
            if safe:
                summary[key] = safe
    run = str(report.get('run', ''))[:64]
    created = report.get('created_utc')
    if not isinstance(created, str):
        try:
            created = datetime.strptime(run, '%Y%m%d-%H%M%S-%f').replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            created = datetime.now(timezone.utc).isoformat()
    return {'schema': 1, 'run': run, 'created_utc': created[:64], 'summary': summary}


def _existing_report_matches(remote, expected, blob_sha):
    if not isinstance(remote, dict):
        return False
    if remote.get('sha') == blob_sha:
        return True
    # Earlier Factory builds generated created_utc at send time, so a retry
    # can have different bytes even though the run ID and allowlisted facts
    # are identical. Accept only that exact semantic match; never overwrite.
    try:
        encoded = remote.get('content', '').replace('\n', '')
        if remote.get('encoding') != 'base64' or not encoded:
            return False
        stored = json.loads(base64.b64decode(encoded, validate=True))
        return all(stored.get(key) == expected.get(key)
                   for key in ('schema', 'run', 'summary'))
    except (ValueError, TypeError, json.JSONDecodeError):
        return False


def upload_report(report_path, *, opener=None):
    repo = 'Evolution-by-Warder/PiconHub-Warder-Evolution'
    token = os.environ.get('WARDER_DIAGNOSTICS_TOKEN', '').strip()
    if not token:
        return {'status': 'not_configured'}
    if not _ALLOWED.fullmatch(repo):
        return {'status': 'invalid_configuration'}
    report = json.loads(Path(report_path).read_text(encoding='utf-8'))
    payload = sanitized_summary(report)
    run = payload['run']
    if not re.fullmatch(r'\d{8}-\d{6}-\d+', run):
        return {'status': 'invalid_run'}
    content = json.dumps(payload, ensure_ascii=False, indent=2).encode('utf-8') + b'\n'
    blob_sha = hashlib.sha1(b'blob ' + str(len(content)).encode('ascii') + b'\0' + content).hexdigest()
    url = 'https://api.github.com/repos/' + repo + '/contents/factory/temp/' + run + '.json'
    headers = {'Authorization': 'Bearer ' + token,
               'Accept': 'application/vnd.github+json',
               'User-Agent': 'Warder-Picon-Factory'}
    # A lost response after a successful PUT must be safe to retry. GitHub's
    # Contents API rejects a create-only PUT for an existing path with 422.
    try:
        check = urllib.request.Request(url + '?ref=factory-warder-development', headers=headers)
        try:
            with (opener or urllib.request.urlopen)(check, timeout=15) as response:
                remote = json.load(response)
            if _existing_report_matches(remote, payload, blob_sha):
                return {'status': 'sent', 'run': run, 'already_present': True, 'verified': True}
            return {'status': 'http_error', 'code': 422, 'detail': 'existing_report_sha_mismatch'}
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                return {'status': 'http_error', 'code': exc.code}
        body = json.dumps({'message': 'diagnostics: ' + run,
                           'branch': 'factory-warder-development',
                           'content': base64.b64encode(content).decode('ascii')}).encode('utf-8')
        req = urllib.request.Request(url, data=body, method='PUT', headers={**headers,
                 'Content-Type': 'application/json'})
        with (opener or urllib.request.urlopen)(req, timeout=15) as response:
            if response.status not in (200, 201):
                return {'status': 'http_error', 'code': response.status}
        # A successful PUT is not enough: read the exact branch/path back before
        # allowing the local copy to be removed.
        with (opener or urllib.request.urlopen)(check, timeout=15) as response:
            confirmed = json.load(response)
        if not _existing_report_matches(confirmed, payload, blob_sha):
            return {'status': 'verification_failed', 'run': run}
        return {'status': 'sent', 'run': run, 'verified': True}
    except urllib.error.HTTPError as exc:
        # Resolve an upload/response race only when the remote bytes match.
        if exc.code == 422:
            try:
                check = urllib.request.Request(url + '?ref=factory-warder-development', headers=headers)
                with (opener or urllib.request.urlopen)(check, timeout=15) as response:
                    remote = json.load(response)
                if _existing_report_matches(remote, payload, blob_sha):
                    return {'status': 'sent', 'run': run, 'already_present': True}
                return {'status': 'http_error', 'code': 422, 'detail': 'existing_report_sha_mismatch'}
            except (OSError, ValueError, TypeError, urllib.error.HTTPError):
                pass
        return {'status': 'http_error', 'code': exc.code}
    except (OSError, ValueError):
        return {'status': 'offline_or_failed'}
