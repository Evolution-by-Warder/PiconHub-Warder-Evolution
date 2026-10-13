"""Deprecated raw-PNG uploader; private review evidence stays local.

The public ``factory/temp`` branch accepts anonymized JSON summaries only.
This compatibility entry point deliberately performs no file reads or network
requests so older installations cannot upload PNGs or source paths.
"""

def upload_png_evidence(report_dir, *, opener=None, state_path=None, max_attempts=None, legacy_report_dir=None):
    return {
        'status': 'disabled_by_privacy_policy',
        'sent': 0,
        'attempted': 0,
        'skipped': 0,
    }
