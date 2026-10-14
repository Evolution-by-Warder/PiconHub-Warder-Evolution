"""Optional exception-only review. Does not write or publish production assets."""
import json
from pathlib import Path


def latest_review(report_dir, *fallback_dirs):
    files = []
    for folder in (report_dir, *fallback_dirs):
        try:
            files.extend(Path(folder).glob('review-queue-*.json'))
        except OSError:
            continue
    eligible = []
    from source_cycle import is_cancelled_legacy_review_queue
    for path in files:
        try:
            if path.is_symlink() or not path.is_file():
                continue
            payload = json.loads(path.read_text(encoding='utf-8'))
            if is_cancelled_legacy_review_queue(payload):
                continue
            eligible.append(path)
        except (OSError, ValueError, TypeError):
            # Preserve malformed reports for the workspace's explicit error
            # state instead of silently reporting that no queue exists.
            if not path.is_symlink() and path.is_file():
                eligible.append(path)
    files = sorted(eligible, key=lambda p: (p.stat().st_mtime_ns, p.name), reverse=True)
    return files[0] if files else None
