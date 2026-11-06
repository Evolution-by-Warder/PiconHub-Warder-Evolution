"""Read-only recovery audit. Never render PNGs, publish, or rewrite batch 33."""
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import time
import zipfile

HERE = Path(__file__).resolve().parent
OUT = Path('_history33_audit')
OUT.mkdir(exist_ok=True)
RECOVERED = OUT / 'verified-pngs'
RECOVERED.mkdir(exist_ok=True)
REPO = 'Evolution-by-Warder/PiconHub-Warder-Evolution'
data = json.loads((HERE / 'expected-payloads.json').read_text())
wanted = data['payloads']
git_ids = {v[0]: h for h, v in wanted.items()}
found = {}
errors = []
budget = 3 * 1024 ** 3
deadline = time.monotonic() + 850
report = {'schema': 1, 'mode': 'read-only-no-production-publication',
          'input_commit': os.environ.get('GITHUB_SHA'), 'repository': REPO,
          'original_archives': data['archives'], 'expected_png_memberships': 5400,
          'unique_expected_pngs': len(wanted), 'errors': errors,
          'branches': [], 'release_assets': [], 'git_archives': [], 'artifacts': []}


def cmd(args, **kw):
    return subprocess.run(args, check=True, capture_output=True, timeout=180, **kw).stdout


def api(path):
    return json.loads(cmd(['gh', 'api', path]))


def pages(path, field=None):
    result = []
    for page in range(1, 101):
        value = api(path + ('&' if '?' in path else '?') + f'per_page=100&page={page}')
        items = value[field] if field else value
        result.extend(items)
        if len(items) < 100:
            return result
    raise RuntimeError('Pagination exceeded 100 pages; audit must be marked incomplete')


def accept(body, source):
    h = hashlib.sha256(body).hexdigest()
    if h in wanted:
        assert len(body) == wanted[h][1]
        found.setdefault(h, source)
        path = RECOVERED / (h + '.png')
        if not path.exists():
            path.write_bytes(body)


def scan_zip(raw, source, depth=0):
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        for entry in z.infolist():
            if entry.file_size > 150 * 1024 ** 2:
                errors.append({'source': source, 'entry': entry.filename, 'reason': 'entry over safety limit'})
                continue
            if entry.filename.lower().endswith('.png'):
                accept(z.read(entry), source + '!' + entry.filename)
            elif depth < 2 and entry.filename.lower().endswith('.zip'):
                scan_zip(z.read(entry), source + '!' + entry.filename, depth + 1)


def within_budget(size, source):
    global budget
    if size > budget or time.monotonic() > deadline:
        errors.append({'source': source, 'reason': 'bounded scan budget exceeded; not claimed absent'})
        return False
    budget -= size
    return True


def save():
    missing = {h: {'bytes': wanted[h][1], 'uses': wanted[h][2]} for h in wanted if h not in found}
    report.update(status=('all-png-inputs-recovered-exact-zip-rebuild-still-required' if not missing else
                          'missing-approved-png-inputs'),
                  scan_complete=not errors, verified_unique_pngs=len(found),
                  verified_png_memberships=sum(len(wanted[h][2]) for h in found),
                  missing_unique_pngs=len(missing),
                  missing_png_memberships=sum(len(v['uses']) for v in missing.values()),
                  sources=found, original_zip_reproduction_verified=False,
                  original_zip_upload_verified=False, png_rendering_performed=False,
                  production_changed=False)
    (OUT / 'remote-audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    (OUT / 'missing-inputs.json').write_text(json.dumps(missing, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ['status', 'scan_complete', 'verified_unique_pngs',
          'verified_png_memberships', 'missing_unique_pngs', 'missing_png_memberships']}))


try:
    branches = pages(f'repos/{REPO}/branches')
    selected = [b for b in branches if b['name'] == 'main' or 'radio' in b['name'].lower()]
    report['branches'] = [{'name': b['name'], 'sha': b['commit']['sha']} for b in selected]
    specs = [b['commit']['sha'] + ':refs/remotes/history-audit/' + str(i) for i, b in enumerate(selected)]
    cmd(['git', 'fetch', '--quiet', '--filter=blob:none', '--depth=1', 'origin'] + specs)
    refs = ['refs/remotes/history-audit/' + str(i) for i in range(len(selected))]
    blobs = {}
    archives = {}
    for ref in refs:
        for line in cmd(['git', 'ls-tree', '-r', ref]).decode().splitlines():
            meta, path = line.split('\t', 1)
            oid = meta.split()[2]
            if oid in git_ids:
                blobs[oid] = path
            # Read radio archives only. No skin/satellite/Vhannibal payloads.
            lower = path.lower()
            if lower.endswith('.zip') and ('radio' in lower or re.search(r'(^|/)iptv-[a-z]{2}(/|-)', lower)):
                if 'vhannibal' not in lower and 'satellite' not in lower:
                    archives[oid] = path
    report['matching_git_blob_ids'] = len(blobs)
    for oid, path in blobs.items():
        accept(cmd(['git', 'cat-file', 'blob', oid]), 'git:' + oid + ':' + path)
    print('Read radio branch object inventories:', len(selected), 'matching loose PNGs:', len(blobs), flush=True)
    for oid, path in archives.items():
        if time.monotonic() > deadline:
            errors.append({'source': 'git:' + oid + ':' + path, 'reason': 'scan deadline; not claimed absent'})
            continue
        try:
            # Git lazily obtains only these approved-scope ZIP objects.
            raw = cmd(['git', 'cat-file', 'blob', oid])
            if not within_budget(len(raw), 'git:' + oid):
                continue
            record = {'blob': oid, 'path': path, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
            report['git_archives'].append(record)
            scan_zip(raw, 'git:' + oid + ':' + path)
        except Exception as exc:
            errors.append({'source': 'git:' + oid + ':' + path, 'error': type(exc).__name__})
    for release in pages(f'repos/{REPO}/releases'):
        for asset in release['assets']:
            report['release_assets'].append({k: asset.get(k) for k in ['id', 'name', 'size', 'digest']})
            name = asset['name'].lower()
            if name.endswith('.zip') and ('radio' in name or any(a['name'] == asset['name'] for a in data['archives'])):
                if within_budget(asset['size'], 'release-asset:' + str(asset['id'])):
                    try:
                        raw = cmd(['gh', 'api', '-H', 'Accept: application/octet-stream',
                                   f'repos/{REPO}/releases/assets/{asset["id"]}'])
                        scan_zip(raw, 'release-asset:' + str(asset['id']))
                    except Exception as exc:
                        errors.append({'source': 'release-asset:' + str(asset['id']), 'error': type(exc).__name__})
    for artifact in pages(f'repos/{REPO}/actions/artifacts', 'artifacts'):
        branch = artifact.get('workflow_run', {}).get('head_branch', '')
        if 'radio' not in (artifact['name'] + ' ' + branch).lower():
            continue
        item = {k: artifact.get(k) for k in ['id', 'name', 'size_in_bytes', 'expired', 'digest', 'workflow_run']}
        report['artifacts'].append(item)
        if artifact['expired']:
            item['status'] = 'expired-unavailable'
            continue
        if not within_budget(artifact['size_in_bytes'], 'artifact:' + str(artifact['id'])):
            item['status'] = 'budget-skipped'
            continue
        try:
            raw = cmd(['gh', 'api', f'repos/{REPO}/actions/artifacts/{artifact["id"]}/zip'])
            digest = artifact.get('digest')
            if digest:
                assert digest == 'sha256:' + hashlib.sha256(raw).hexdigest()
            scan_zip(raw, 'artifact:' + str(artifact['id']))
            item['status'] = 'downloaded-sha256-checked-and-scanned'
        except Exception as exc:
            item['status'] = 'unreadable'
            errors.append({'source': 'artifact:' + str(artifact['id']), 'error': type(exc).__name__})
finally:
    save()
