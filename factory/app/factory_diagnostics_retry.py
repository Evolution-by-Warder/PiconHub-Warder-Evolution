"""Retry pending local run summaries without deleting source reports."""
import json
from pathlib import Path
from factory_diagnostics import upload_report

def retry_reports(report_dir, state_file, limit=5):
    folder, state_file = Path(report_dir), Path(state_file)
    if limit < 1:
        raise ValueError('limit must be positive')
    try:
        state = json.loads(state_file.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        state = {}
    if state.get('schema') != 2:
        state = {}
    delivered = set(state.get('delivered', []))
    results = []
    if not folder.is_dir():
        return results
    for path in sorted(folder.glob('report-*.json'), reverse=True):
        if len(results) >= limit:
            break
        if path.is_symlink() or not path.is_file() or path.name in delivered:
            continue
        result = upload_report(path)
        results.append({'report': path.name, 'status': result['status']})
        if result['status'] == 'sent':
            delivered.add(path.name)
        elif result['status'] in ('not_configured', 'invalid_configuration'):
            break
    if results:
        state_file.parent.mkdir(parents=True, exist_ok=True)
        temp = state_file.with_suffix('.json.tmp')
        temp.write_text(json.dumps({'schema': 2, 'delivered': sorted(delivered)}, indent=2), encoding='utf-8')
        temp.replace(state_file)
    return results
