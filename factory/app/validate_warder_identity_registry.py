"""CI validator for identity, approvals, immutable assets, and Git transitions."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

from warder_identity_registry import (
    empty_approval_ledger, empty_registry, validate_master_store,
)
from warder_master_store import validate_store_transition


def _load_base(commit, relative_path, empty_value):
    if not re.fullmatch(r"[0-9a-fA-F]{40}", commit or ""):
        raise ValueError("A full base commit SHA is required")
    exists = subprocess.run(["git", "cat-file", "-e", f"{commit}^{{commit}}"],
                            capture_output=True).returncode == 0
    if not exists:
        raise ValueError("Base commit is not present in the checked-out Git history")
    result = subprocess.run(["git", "show", f"{commit}:{relative_path}"],
                            capture_output=True, text=True, encoding="utf-8")
    if result.returncode:
        path_exists = subprocess.run(["git", "cat-file", "-e", f"{commit}:{relative_path}"],
                                     capture_output=True).returncode == 0
        if path_exists:
            raise ValueError("Could not read the base Master file from Git: " + relative_path)
        return empty_value
    return json.loads(result.stdout)


def _read_worktree_asset(path):
    parsed = PurePosixPath(path)
    if parsed.is_absolute() or ".." in parsed.parts or not path.startswith("factory/approved-picons/"):
        raise ValueError("Unsafe approved artwork path")
    return Path(*parsed.parts).read_bytes()


def validate_files(registry_path, ledger_path, base_commit, progress_path="factory/registry/project-progress.json"):
    registry_path, ledger_path = Path(registry_path), Path(ledger_path)
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    base_registry = _load_base(base_commit, registry_path.as_posix(), empty_registry())
    base_ledger = _load_base(base_commit, ledger_path.as_posix(), empty_approval_ledger())
    transition = validate_store_transition(base_registry, base_ledger, registry, ledger)
    store = validate_master_store(registry, ledger, read_asset=_read_worktree_asset)
    progress = None
    if progress_path:
        from warder_review_store import validate_progress
        progress = json.loads(Path(progress_path).read_text(encoding="utf-8"))
        progress_check = validate_progress(registry, ledger, progress)
    else:
        progress_check = {"status": "SKIPPED", "issues": []}
    issues = [{"scope": "transition", **item} for item in transition["issues"]]
    issues.extend({"scope": "current_store", **item} for item in store["issues"])
    issues.extend({"scope": "progress", **item} for item in progress_check["issues"])
    return {"status": "VALID" if not issues else "INVALID",
            "identity_count": store["identity"]["record_count"],
            "approval_event_count": store["approval_ledger"]["event_count"],
            "transition": transition, "store": store, "progress": progress_check,
            "issues": issues}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", default="factory/registry/warder-identity-registry.json")
    parser.add_argument("--ledger", default="factory/registry/master-approval-ledger.json")
    parser.add_argument("--base-commit", required=True)
    parser.add_argument("--progress", default="factory/registry/project-progress.json")
    args = parser.parse_args(argv)
    try:
        result = validate_files(args.registry, args.ledger, args.base_commit, args.progress)
    except (OSError, ValueError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "INVALID", "issues": [{"code": type(exc).__name__,
                                                               "detail": str(exc)}]}, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "VALID" else 1


if __name__ == "__main__":
    sys.exit(main())
