"""Pure-Python install migration; runnable without importing Enigma2."""
import json
import os
from pathlib import Path
import shutil
import uuid

PRODUCT = "PiconHub Warder Evolution"
OLD_NAME = "ChocholousekPicons"
NEW_NAME = "WarderPiconHub"
MARKER = ".warder-runtime-transition.json"
DEFAULT_EXTENSIONS = Path("/usr/lib/enigma2/python/Plugins/Extensions")
DEFAULT_STATE = Path("/var/lib/warder-piconhub")


def running_gui_pid():
    try:
        for path in Path("/proc").iterdir():
            if not path.name.isdecimal():
                continue
            try:
                if (path/"comm").read_text().strip() == "enigma2":
                    return int(path.name)
            except OSError:
                continue
    except OSError:
        pass
    return None


def compatibility_record(legacy):
    if legacy.is_symlink() or not legacy.is_dir():
        return None
    marker, version = legacy / MARKER, legacy / "version.txt"
    if marker.is_symlink() or version.is_symlink():
        return None
    try:
        record = json.loads(marker.read_text())
        if (record.get("product") == PRODUCT and record.get("compatibility") == 1
                and version.read_text().strip() == record.get("version")
                and {p.name for p in legacy.iterdir()} == {MARKER, "version.txt"}):
            return record
    except (OSError, ValueError, AttributeError):
        pass
    return None


def migrate(extensions=DEFAULT_EXTENSIONS, state=DEFAULT_STATE):
    extensions, state = Path(extensions), Path(state)
    current, legacy = extensions / NEW_NAME, extensions / OLD_NAME
    version = (current / "version.txt").read_text().strip()
    # Clear only compiled code; configuration stays in /etc/enigma2/settings.
    for path in current.rglob("*.py[co]"):
        if path.is_file() and not path.is_symlink():
            path.unlink()
    requested = state / "legacy-transition-needed"
    present = legacy.exists() or legacy.is_symlink()
    if not present and not requested.is_file():
        return None
    record = compatibility_record(legacy)
    backup = record.get("archived_to") if record else None
    if present and record is None:
        backups = state / "previous-runtime"
        backups.mkdir(parents=True, exist_ok=True)
        destination = backups / (OLD_NAME + "-" + uuid.uuid4().hex)
        # Preserve unowned user files and caches outside plugin discovery.
        shutil.move(str(legacy), str(destination))
        backup = str(destination)
    legacy.mkdir(parents=True, exist_ok=True)
    # The already-running old main screen still reads its version every second.
    # No Python launcher remains here, so Enigma2 cannot list a second plugin.
    (legacy / "version.txt").write_text(version + "\n")
    (legacy / MARKER).write_text(json.dumps({"product":PRODUCT,"compatibility":1,
                                           "version":version,"archived_to":backup,"gui_pid":running_gui_pid()}) + "\n")
    requested.unlink(missing_ok=True)
    return backup


def cleanup_compatibility(extensions=DEFAULT_EXTENSIONS):
    """Called only when the new package is imported after the GUI restart."""
    legacy = Path(extensions) / OLD_NAME
    record = compatibility_record(legacy)
    if record is None or record.get("gui_pid") == os.getpid():
        return False
    try:
        (legacy / "version.txt").unlink()
        (legacy / MARKER).unlink()
        legacy.rmdir()
        return True
    except OSError:
        return False


if __name__ == "__main__":
    migrate()
