"""Build/runtime identity shown in the GUI and used by diagnostics."""
from __future__ import annotations

import json
from pathlib import Path
import sys


def build_commit() -> str:
    try:
        path = Path(__file__).with_name(".factory-build.json")
        data = json.loads(path.read_text(encoding="utf-8"))
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
