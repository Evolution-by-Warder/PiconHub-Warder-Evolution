"""Deliver diagnostic reports and remove local copies only after GitHub readback.

Only report-*.json files are eligible. Failed or unverified uploads remain on disk.
"""
import json
from pathlib import Path
from factory_diagnostics import upload_report


def retry_reports(report_dir, state_file, limit=5):
    folder, state_file = Path(report_dir), Path(state_file)
    if limit < 1:
        raise ValueError('limit must be positive')
    results = []
    if not folder.is_dir():
        return results
    # Newest first; no deletion based solely on an old local delivered marker.
    for path in sorted(folder.glob('report-*.json'), reverse=True):
        if len(results) >= limit:
            break
        if path.is_symlink() or not path.is_file():
            continue
        try:
            result = upload_report(path)
        except (OSError, ValueError, KeyError, TypeError):
            result = {'status': 'local_error'}
        status = result.get('status', 'local_error')
        if status == 'sent' and result.get('verified') is True:
            try:
                path.unlink()
            except OSError:
                status = 'verified_cleanup_failed'
        elif status == 'sent':
            status = 'verification_missing'
        results.append({'report': path.name, 'status': status})
        if status in ('not_configured', 'invalid_configuration'):
            break
    # No ever-growing delivery ledger: remote readback is the authority.
    # Keep the old state file untouched for compatibility with existing installs.
    return results
