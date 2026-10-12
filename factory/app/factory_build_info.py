"""Build/runtime identity shown in the GUI and used by diagnostics."""
from __future__ import annotations

import json
from pathlib import Path
import sys


def bundled_metadata_path(filename: str) -> Path:
    """Locate PyInstaller one-file metadata in its extraction directory."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / filename
    return Path(__file__).resolve().with_name(filename)


def build_commit() -> str:
    try:
        data = json.loads(bundled_metadata_path(".factory-build.json").read_text(encoding="utf-8"))
        value = data.get("commit", "")
        return value if isinstance(value, str) and value else "nezistený"
    except (OSError, ValueError, TypeError):
        return "nezistený / lokálny build"


def executable_path() -> str:
    candidate = sys.executable if getattr(sys, "frozen", False) else __file__
    try:
        return str(Path(candidate).resolve())
    except OSError:
        return str(candidate)
