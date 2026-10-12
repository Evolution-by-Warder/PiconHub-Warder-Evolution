"""Windows startup update entry point; never interrupts existing Factory on failure."""
import json
import os
import sys
from pathlib import Path

from windows_exe_update import read_manifest, validate_bundle_manifest, install_verified_bundle

ROOT = Path(r"D:\WARDER-PICON-FACTORY")
EXE = ROOT / "11-APP" / "WARDER-PICON-FACTORY" / "WARDER-PICON-FACTORY.exe"
VERSION_FILE = EXE.parent / ".factory-installed-version.json"


def run(exe=EXE, metadata=VERSION_FILE):
    exe, metadata = Path(exe), Path(metadata)
    if not exe.is_file() or exe.is_symlink():
        return "NO_INSTALLED_EXE"
    try:
        if metadata.is_file():
            installed = json.loads(metadata.read_text(encoding="utf-8-sig"))
        else:
            identity = exe.parent / "BUILD-IDENTITY.json"
            if not identity.is_file() or identity.is_symlink():
                return "NO_VERSION_METADATA"
            build = json.loads(identity.read_text(encoding="utf-8-sig"))
            if (build.get("filename") != exe.name or
                    build.get("bytes") != exe.stat().st_size or
                    build.get("smoke_test") != "passed"):
                return "NO_VERSION_METADATA"
            import hashlib
            digest = hashlib.sha256()
            with exe.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            if digest.hexdigest() != build.get("sha256"):
                return "NO_VERSION_METADATA"
            installed = {"version": build["version"], "commit": build["commit"]}
        if not isinstance(installed, dict):
            return "NO_VERSION_METADATA"
        info = validate_bundle_manifest(read_manifest(), installed["version"])
        if info is None:
            return "UP_TO_DATE"
        backups = install_verified_bundle(info, exe.parent)
        try:
            staged = metadata.with_suffix(".json.tmp")
            staged.write_text(json.dumps({"version": info["version"],
                                          "commit": info["commit"]}) + "\n",
                              encoding="utf-8")
            os.replace(staged, metadata)
        except Exception:
            return "UPDATED_METADATA_PENDING"
        return "UPDATED"
    except Exception as exc:
        return "SKIPPED_" + type(exc).__name__


if __name__ == "__main__":
    if os.name != "nt":
        sys.exit("Windows-only startup updater")
    import ctypes
    import subprocess

    def dialog(message, flags=0x40):
        return ctypes.windll.user32.MessageBoxW(
            None, message, "WARDER PICON FACTORY - aktualizácia", flags)

    if not EXE.is_file():
        dialog("Aplikácia nebola nájdená:\n" + str(EXE) +
               "\n\nNič nebolo zmenené.", 0x10)
        sys.exit(1)

    running = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq WARDER-PICON-FACTORY.exe", "/FO", "CSV", "/NH"],
        capture_output=True, text=True, creationflags=0x08000000)
    if running.returncode != 0 or '"WARDER-PICON-FACTORY.exe"' in running.stdout:
        dialog("Najprv zatvorte WARDER PICON FACTORY a spustite aktualizátor znova.\n"
               "Nič nebolo zmenené.", 0x30)
        sys.exit(1)

    if dialog("Aktualizovať WARDER PICON FACTORY?\n\n"
              "Umiestnenie: " + str(EXE.parent) +
              "\n\nDáta, registry a picony zostanú nedotknuté.",
              0x24) != 6:
        sys.exit(0)

    result = run()
    messages = {
        "UPDATED": "Aktualizácia bola úspešne dokončená.",
        "UP_TO_DATE": "Aplikácia už má najnovšiu verziu.",
        "UPDATED_METADATA_PENDING": "Súbory boli aktualizované, ale zápis verzie sa nepodaril."
    }
    if result == "NO_VERSION_METADATA":
        dialog("Chýba identifikácia existujúcej inštalácie.\n"
               "Automatická výmena bez overenia pôvodnej verzie bola odmietnutá.\n"
               "Nič nebolo zmenené.", 0x10)
        sys.exit(1)
    dialog(messages.get(result, "Aktualizácia sa nevykonala: " + result),
           0x40 if result in ("UPDATED", "UP_TO_DATE") else 0x10)
    sys.exit(0 if result in ("UPDATED", "UP_TO_DATE") else 1)

