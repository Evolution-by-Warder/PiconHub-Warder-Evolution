"""Read offline notes for the installed release without fetching a newer feed."""
import json
from pathlib import Path


def load_notes(path, version, language):
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(document, dict) or document.get("version") != version:
            return ""
        notes = document.get("notes", {})
        if not isinstance(notes, dict):
            return ""
        code = str(language).replace("-", "_").split("_")[0].lower()
        value = notes.get(code) or notes.get("en", "")
        return value.strip() if isinstance(value, str) else ""
    except (OSError, ValueError, UnicodeError):
        return ""
