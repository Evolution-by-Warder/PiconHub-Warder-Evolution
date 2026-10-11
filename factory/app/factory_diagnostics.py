"""Optional automatic GitHub diagnostics upload; never uploads PNG or credentials.

Uploads only allowlisted numerical summaries to factory/temp on the existing
factory-warder-development branch. Requires WARDER_DIAGNOSTICS_TOKEN on the PC.
Git deletion does not erase historical commits.
"""
import json
import os
import re
import urllib.request
import urllib.error
import base64
from datetime import datetime, timezone
from pathlib import Path

_ALLOWED = re.compile(r'^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$')
_ALLOWED_KEYS = ('scanned', 'changed', 'duplicates', 'exceptions', 'created',
                 'review_queue_items', 'review_workstreams', 'qa_blocking',
                 'qa_repaired', 'qa_pending_by_workstream', 'integrity_issues',
                 'installed_factory_version', 'source_errors')

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
    return {'schema': 1, 'run': str(report.get('run', ''))[:64],
            'created_utc': datetime.now(timezone.utc).isoformat(), 'summary': summary}

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
    body = json.dumps({'message': 'diagnostics: ' + run,
                       'branch': 'factory-warder-development',
                       'content': base64.b64encode(json.dumps(payload, ensure_ascii=False).encode('utf-8')).decode('ascii')}).encode('utf-8')
    req = urllib.request.Request(
        'https://api.github.com/repos/' + repo + '/contents/factory/temp/' + run + '.json',
        data=body, method='PUT',
        headers={'Authorization': 'Bearer ' + token,
                 'Accept': 'application/vnd.github+json',
                 'Content-Type': 'application/json',
                 'User-Agent': 'Warder-Picon-Factory'})
    try:
        with (opener or urllib.request.urlopen)(req, timeout=15) as response:
            if response.status not in (200, 201):
                return {'status': 'http_error', 'code': response.status}
        return {'status': 'sent', 'run': run}
    except urllib.error.HTTPError as exc:
        if exc.code == 422:
            return {'status': 'already_present_or_conflict', 'code': exc.code}
        return {'status': 'http_error', 'code': exc.code}
    except (OSError, ValueError):
        return {'status': 'offline_or_failed'}
