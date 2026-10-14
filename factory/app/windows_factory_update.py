"""Single-file, rollback-capable updater for the installed WARDER Factory EXE."""
from __future__ import annotations

import csv
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

VERSION = re.compile(r"^factory-v(\d+)\.(\d+)\.(\d+)$")
VERSION_BYTES = re.compile(rb"factory-v\d+\.\d+\.\d+")
APP_EXE = "WARDER-PICON-FACTORY.exe"
VERSION_FILE = ".factory-installed-version.json"
REQUIRED_DIRS = (
    "00-STATE", "01-SOURCES", "02-ORIGINALS", "03-REGISTRY", "04-WORK",
    "05-QA", "06-OUTPUT", "07-PUBLISH-STAGING", "08-REPORTS", "09-LOGS",
    "10-TOOLS", "11-APP", "12-ARCHIVE",
)


class UpdateError(RuntimeError):
    pass


def version_tuple(value: str) -> tuple[int, int, int]:
    match = VERSION.fullmatch(value) if isinstance(value, str) else None
    if not match:
        raise UpdateError("Factory version is missing or invalid")
    return tuple(int(part) for part in match.groups())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_reparse(path: Path) -> bool:
    try:
        stat = path.lstat()
    except OSError:
        return False
    return path.is_symlink() or bool(getattr(stat, "st_file_attributes", 0) & 0x400)


def _metadata(payload: Path, build: dict) -> dict:
    if not isinstance(build, dict):
        raise UpdateError("Embedded update metadata is invalid")
    version = build.get("version")
    version_tuple(version)
    commit = build.get("commit")
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise UpdateError("Embedded build commit is invalid")
    digest = build.get("sha256")
    size = build.get("bytes")
    if (not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)
            or type(size) is not int or size < 1024):
        raise UpdateError("Embedded executable identity is invalid")
    if not payload.is_file() or _is_reparse(payload):
        raise UpdateError("Embedded Factory executable is missing or unsafe")
    if payload.stat().st_size != size or sha256_file(payload) != digest:
        raise UpdateError("Embedded Factory executable SHA-256 or size mismatch")
    with payload.open("rb") as stream:
        if stream.read(2) != b"MZ":
            raise UpdateError("Embedded payload is not a Windows executable")
    return {"version": version, "commit": commit, "sha256": digest, "bytes": size}


def installed_version(executable: Path, marker: Path) -> str:
    if marker.is_file() and not _is_reparse(marker):
        try:
            version = json.loads(marker.read_text(encoding="utf-8")).get("version")
            version_tuple(version)
            return version
        except (OSError, ValueError, TypeError, AttributeError):
            raise UpdateError("Installed version marker is invalid; no files were changed")
    # Older one-file installs may lack the adjacent marker. Read the embedded
    # version resource from their PyInstaller archive instead of guessing.
    try:
        from PyInstaller.archive.readers import CArchiveReader
        archive = CArchiveReader(str(executable))
        for name in (".factory-version.json", "_internal/.factory-version.json"):
            try:
                data = json.loads(archive.extract(name).decode("utf-8"))
                value = data.get("version")
                version_tuple(value)
                return value
            except KeyError:
                continue
            except (UnicodeDecodeError, ValueError, TypeError, AttributeError):
                break
    except Exception:
        pass
    # Also support builds that expose the resource as an uncompressed string.
    try:
        with executable.open("rb") as stream:
            raw = stream.read(64 * 1024 * 1024)
    except OSError as exc:
        raise UpdateError("Cannot read installed Factory version") from exc
    matches = sorted({item.decode("ascii") for item in VERSION_BYTES.findall(raw)})
    if len(matches) == 1:
        version_tuple(matches[0])
        return matches[0]
    raise UpdateError("Installed version cannot be verified; install marker is missing")


def validate_workspace(root: Path) -> tuple[Path, Path]:
    root = Path(root)
    if not root.is_dir() or _is_reparse(root):
        raise UpdateError("Existing D:\\WARDER-PICON-FACTORY workspace is missing or unsafe")
    for name in REQUIRED_DIRS:
        folder = root / name
        if not folder.is_dir() or _is_reparse(folder):
            raise UpdateError(f"Workspace category missing or unsafe: {name}")
        try:
            with os.scandir(folder):
                pass
        except OSError as exc:
            raise UpdateError(f"Workspace category is not readable: {name}") from exc
    app_dir = root / "11-APP" / "WARDER-PICON-FACTORY"
    if not app_dir.is_dir() or _is_reparse(app_dir):
        raise UpdateError("Existing Factory application directory is missing or unsafe")
    executable = app_dir / APP_EXE
    if not executable.is_file() or _is_reparse(executable):
        raise UpdateError("Existing Factory executable is missing or unsafe; updater will not install beside it")
    return app_dir, executable


def _running_factory(process_check=None) -> bool:
    if process_check is not None:
        return bool(process_check())
    result = subprocess.run(["tasklist", "/FI", "IMAGENAME eq " + APP_EXE, "/FO", "CSV", "/NH"],
                           capture_output=True, text=True, check=False, timeout=15)
    if result.returncode != 0:
        raise UpdateError("Cannot verify that the existing Factory is closed")
    rows = list(csv.reader(line for line in result.stdout.splitlines() if line.strip()))
    return any(row and row[0].casefold() == APP_EXE.casefold() for row in rows)


@contextmanager
def _exclusive_update_lock(app_dir: Path):
    """Serialize updater launches; OS locks are released automatically on crash."""
    lock_path = app_dir / ".factory-update.lock"
    stream = lock_path.open("a+b")
    try:
        if os.name == "nt":
            import msvcrt
            stream.seek(0)
            if lock_path.stat().st_size == 0:
                stream.write(b"0")
                stream.flush()
            stream.seek(0)
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise UpdateError("Another Factory update is already running") from exc
            unlock = lambda: msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise UpdateError("Another Factory update is already running") from exc
            unlock = lambda: fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        yield
        unlock()
    finally:
        stream.close()


def install_update(root: Path, payload: Path, build: dict, *, process_check=None,
                   launch_check=None, now=None) -> dict:
    """Verify version and payload, replace in place, and restore on failure."""
    root = Path(root)
    app_dir, _ = validate_workspace(root)
    with _exclusive_update_lock(app_dir):
        return _install_update_locked(root, payload, build, app_dir=app_dir,
                                      process_check=process_check,
                                      launch_check=launch_check, now=now)


def _install_update_locked(root: Path, payload: Path, build: dict, *, app_dir: Path,
                           process_check=None, launch_check=None, now=None) -> dict:
    app_dir, executable = validate_workspace(root)
    if _running_factory(process_check):
        raise UpdateError("Close WARDER PICON FACTORY before updating; installed files were not changed")
    marker = app_dir / VERSION_FILE
    new = _metadata(Path(payload), build)
    current = installed_version(executable, marker)
    if version_tuple(new["version"]) <= version_tuple(current):
        if new["version"] == current and new["sha256"] == sha256_file(executable):
            return {"status": "ALREADY_CURRENT", "version": current}
        raise UpdateError(f"Update {new['version']} is not newer than installed {current}")

    transaction = uuid.uuid4().hex
    stamp = str(int((now or time.time)()))
    previous_exe = app_dir / (APP_EXE + f".previous-{current}-{stamp}-{transaction[:8]}")
    previous_marker = app_dir / (VERSION_FILE + f".previous-{current}-{stamp}-{transaction[:8]}")
    staged_exe = app_dir / (".factory-update-" + transaction + ".exe")
    staged_marker = app_dir / (".factory-update-" + transaction + ".json")
    marker_existed = marker.exists()
    replaced = False
    try:
        shutil.copy2(executable, previous_exe)
        if marker_existed:
            shutil.copy2(marker, previous_marker)
        shutil.copyfile(payload, staged_exe)
        if sha256_file(staged_exe) != new["sha256"]:
            raise UpdateError("Staged Factory executable failed SHA-256 verification")
        staged_marker.write_text(json.dumps({"schema": 1, **new}, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(staged_exe, executable)
        replaced = True
        os.replace(staged_marker, marker)
        if sha256_file(executable) != new["sha256"]:
            raise UpdateError("Installed Factory executable failed read-back verification")
        if launch_check is not None and not launch_check(executable):
            raise UpdateError("Updated Factory did not pass startup verification")
        return {"status": "UPDATED", "version": new["version"], "commit": new["commit"],
                "sha256": new["sha256"], "previous_executable": str(previous_exe),
                "previous_marker": str(previous_marker) if marker_existed else None}
    except BaseException:
        if replaced:
            rollback = app_dir / (".factory-rollback-" + transaction + ".exe")
            if executable.exists():
                os.replace(executable, rollback)
            os.replace(previous_exe, executable)
            if marker_existed and previous_marker.exists():
                os.replace(previous_marker, marker)
            elif marker.exists():
                marker.unlink()
        raise
    finally:
        staged_exe.unlink(missing_ok=True)
        staged_marker.unlink(missing_ok=True)


def _bundle_path(name: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / name


def _launch_and_wait(executable: Path) -> bool:
    ready = Path(tempfile.gettempdir()) / ("warder-factory-ready-" + uuid.uuid4().hex + ".txt")
    ready.unlink(missing_ok=True)
    env = os.environ.copy()
    env["WARDER_FACTORY_GUI_READY_FILE"] = str(ready)
    process = subprocess.Popen([str(executable)], cwd=str(executable.parent), env=env)
    try:
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            if ready.is_file() and ready.read_text(encoding="utf-8").startswith("GUI_READY"):
                return True
            if process.poll() is not None:
                return False
            time.sleep(0.25)
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        return False
    finally:
        ready.unlink(missing_ok=True)


def main() -> int:
    root = Path(r"D:\WARDER-PICON-FACTORY")
    try:
        payload = _bundle_path("payload/WARDER-PICON-FACTORY.exe")
        build = json.loads(_bundle_path(".factory-update-build.json").read_text(encoding="utf-8"))
        result = install_update(root, payload, build, launch_check=_launch_and_wait)
        if result["status"] == "ALREADY_CURRENT":
            print(f"WARDER PICON FACTORY {result['version']} is already installed.")
        else:
            print(f"Updated Factory to {result['version']} ({result['commit'][:12]}), SHA-256 verified.")
            print("Previous executable retained at: " + result["previous_executable"])
        return 0
    except (OSError, ValueError, UpdateError, subprocess.SubprocessError) as exc:
        print("WARDER PICON FACTORY update failed; the existing installation was preserved or restored.")
        print(f"{type(exc).__name__}: {exc}")
        if sys.stdin.isatty() and os.environ.get("WARDER_TEST_NO_PAUSE") != "1":
            input("Press Enter to close.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
