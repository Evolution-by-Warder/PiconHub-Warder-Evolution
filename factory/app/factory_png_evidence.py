"""PNG evidence delivery independent of the 10-item manual review gallery."""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request

REPO = 'Evolution-by-Warder/PiconHub-Warder-Evolution'
BRANCH = 'factory-warder-development'
MAX_PNG = 2 * 1024 * 1024
PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'

def upload_png_evidence(report_dir, *, opener=None):
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
    sent = attempted = 0
    seen = set()
    errors = []
    for item in queue.get('items', []):
        sources = [item.get('original')] + (item.get('source_evidence') or []) + (item.get('variants') or [])
        for entry in sources:
            source = entry if isinstance(entry, str) else entry.get('source') if isinstance(entry, dict) else None
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
                attempted += 1
                run = review_path.stem.removeprefix('review-queue-')
                if not re.fullmatch(r'[0-9]{8}-[0-9]{6}-[0-9]+', run):
                    return {'status': 'invalid_run', 'sent': sent, 'attempted': attempted}
                remote = 'factory/temp/evidence/' + run + '/' + sha + '.png'
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
                        else:
                            errors.append('HTTP ' + str(response.status))
                except urllib.error.HTTPError as exc:
                    errors.append('HTTP ' + str(exc.code))
            except (OSError, ValueError) as exc:
                errors.append(type(exc).__name__)
    return {'status': 'sent' if sent == attempted and attempted else 'partial' if sent else 'failed' if attempted else 'no_evidence',
            'sent': sent, 'attempted': attempted, 'errors': errors[:5]}
