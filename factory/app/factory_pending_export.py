"""Safe, bounded export of pending Factory reviews to one ZIP on D:."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import zipfile

from review_queue import load_review_queue
from review_ui import latest_review
from review_gallery import evidence_digests

MAX_FILES = 300000

def export_pending(report_dir, output_dir, destination, *, ledger_path=None):
    report_dir, output_dir, destination = map(Path, (report_dir, output_dir, destination))
    review_path = latest_review(report_dir)
    if not review_path:
        raise FileNotFoundError('No review queue exists')
    queue = load_review_queue(review_path)
    pending = [item for item in queue['items'] if item.get('decision', 'PENDING') == 'PENDING']
    if ledger_path and Path(ledger_path).is_file():
        from review_decisions import evidence_hash
        decisions = json.loads(Path(ledger_path).read_text(encoding='utf-8')).get('decisions', {})
        pending = [item for item in pending if not (
            item['review_id'] in decisions and
            decisions[item['review_id']].get('evidence_hash') == evidence_hash(item))]
    if destination.exists():
        raise FileExistsError('Export already exists: ' + str(destination))
    if not destination.parent.is_dir():
        raise FileNotFoundError('Destination disk is not available: ' + str(destination.parent))
    manifest = {'schema': 1, 'review_source': review_path.name,
                'pending_tasks': len(pending), 'items': pending, 'files': [], 'missing': []}
    # Export only existing referenced originals and derivatives; never guess paths.
    candidates = {}
    for item in pending:
        sources = [item.get('original')] + item.get('source_evidence', []) + item.get('variants', [])
        for entry in sources:
            source = entry if isinstance(entry, str) else entry.get('source') if isinstance(entry, dict) else None
            if source:
                p = Path(source)
                if p.is_file() and p.suffix.lower() == '.png' and not p.is_symlink():
                    candidates[str(p.resolve())] = p
                else:
                    manifest['missing'].append({'review_id': item['review_id'], 'source': str(source)})
        for sha in evidence_digests(item):
            for variant in ('transparent', 'black', 'white'):
                p = output_dir / sha[:2] / sha / (variant + '.png')
                if p.is_file() and not p.is_symlink():
                    candidates[str(p.resolve())] = p
                else:
                    manifest['missing'].append({'review_id': item['review_id'], 'variant': variant, 'sha256': sha})
    if len(candidates) > MAX_FILES:
        raise ValueError('Too many PNGs for one export')
    fd, temp_name = tempfile.mkstemp(prefix='.warder-pending-', suffix='.zip.tmp', dir=destination.parent)
    os.close(fd)
    try:
        with zipfile.ZipFile(temp_name, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=4, allowZip64=True) as archive:
            for index, p in enumerate(candidates.values()):
                digest = hashlib.sha256()
                with p.open('rb') as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                        digest.update(chunk)
                name = 'png/%06d-%s.png' % (index, digest.hexdigest())
                archive.write(p, name)
                manifest['files'].append({'archive_path': name, 'sha256': digest.hexdigest(), 'source': str(p)})
            archive.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))
        with zipfile.ZipFile(temp_name) as check:
            if check.testzip() is not None:
                raise ValueError('ZIP integrity verification failed')
        os.replace(temp_name, destination)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    return {'path': str(destination), 'tasks': len(pending), 'png': len(candidates),
            'missing': len(manifest['missing'])}
