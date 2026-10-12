"""Windows startup update entry point; never interrupts existing Factory on failure."""
import json
import os
import sys
from pathlib import Path

from windows_exe_update import read_manifest, validate_manifest, install_verified_exe

ROOT = Path(r"D:\WARDER-PICON-FACTORY")
EXE = ROOT / "11-APP" / "WARDER-PICON-FACTORY.exe"
VERSION_FILE = ROOT / "11-APP" / ".factory-installed-version.json"


def run(exe=EXE, metadata=VERSION_FILE):
    exe, metadata = Path(exe), Path(metadata)
    if not exe.is_file() or exe.is_symlink():
        return "NO_INSTALLED_EXE"
    try:
        if not metadata.is_file():
            return "NO_VERSION_METADATA"
        installed = json.loads(metadata.read_text(encoding="utf-8"))
        if not isinstance(installed, dict):
            return "NO_VERSION_METADATA"
        info = validate_manifest(read_manifest(), installed["version"],
                                 installed.get("commit", ""))
        if info is None:
            return "UP_TO_DATE"
        previous = install_verified_exe(info, exe)
        try:
            staged = metadata.with_suffix(".json.tmp")
            staged.write_text(json.dumps({"version": info["version"],
                                          "commit": info["commit"]}) + "\n",
                              encoding="utf-8")
            os.replace(staged, metadata)
        except Exception:
            # Metadata failure must not leave an untracked new executable.
            try:
                os.replace(exe, exe.with_name(exe.name + ".failed-update"))
                os.replace(previous, exe)
            except OSError:
                return "ROLLBACK_REQUIRED"
            return "ROLLED_BACK_METADATA_FAILURE"
        return "UPDATED"
    except Exception as exc:
        return "SKIPPED_" + type(exc).__name__


if __name__ == "__main__":
    if os.name != "nt":
        sys.exit("Windows-only startup updater")
    result = run()
    print("WARDER UPDATE: " + result)
