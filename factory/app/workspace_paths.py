"""Authoritative Factory workspace layout and read-only Windows preflight."""
from __future__ import annotations

from dataclasses import dataclass, asdict
import os
from pathlib import Path
import stat

WINDOWS_ROOT = Path(r"D:\WARDER-PICON-FACTORY")
DIRECTORIES = (
    ("00-STATE", "Checkpoints a história behov"),
    ("01-SOURCES", "Vstupné zdroje a stiahnuté archívy"),
    ("02-ORIGINALS", "Nedotknuteľné pôvodné PNG"),
    ("03-REGISTRY", "Warder Master Registry a mapovania"),
    ("04-WORK", "Pracovné obrázky a spracovanie"),
    ("05-QA", "Kontroly, výnimky a manuálne rozhodnutia"),
    ("06-OUTPUT", "Finálne schválené výsledky"),
    ("07-PUBLISH-STAGING", "Príprava publikovania"),
    ("08-REPORTS", "Reporty a štatistiky"),
    ("09-LOGS", "Diagnostické logy"),
    ("10-TOOLS", "Servisné nástroje"),
    ("11-APP", "Engine, GUI, lokálne závislosti, updater a aplikačné dáta"),
    ("12-ARCHIVE", "Historické archivované dáta"),
)


@dataclass(frozen=True)
class PreflightResult:
    root: str
    ok: bool
    checked: int
    missing: tuple[str, ...]
    unreadable: tuple[str, ...]
    inventory: dict[str, dict[str, int]]
    findings: tuple[str, ...]

    def as_dict(self):
        value = asdict(self)
        value["missing"] = list(self.missing)
        value["unreadable"] = list(self.unreadable)
        value["findings"] = list(self.findings)
        return value


def resolve_root(*, env=None, home=None, platform=None) -> Path:
    """Return the single production root; Windows environment overrides are ignored."""
    env = os.environ if env is None else env
    platform = os.name if platform is None else platform
    if platform == "nt":
        return WINDOWS_ROOT
    # Development/test runs on non-Windows hosts never claim to be user data.
    return Path(env.get("WARDER_PICON_FACTORY_ROOT") or Path(home or Path.home()) / ".warder-picon-factory-dev").expanduser()


def workspace_paths(root: Path) -> dict[str, Path]:
    """Map every operational role to the exact authorized top-level category."""
    root = Path(root).expanduser()
    state = root / "00-STATE"
    sources = root / "01-SOURCES"
    originals = root / "02-ORIGINALS"
    registry = root / "03-REGISTRY"
    work = root / "04-WORK"
    qa = root / "05-QA"
    output = root / "06-OUTPUT"
    app_root = root / "11-APP"
    app = app_root / "WARDER-PICON-FACTORY"
    # This is the existing Factory app-data location from the installed
    # application; reusing it preserves source selections and private state.
    app_data = app_root / ".factory-data"
    return {
        "root": root,
        "state": state,
        "sources": sources,
        "inbox": sources / "LOCAL-INBOX",
        "originals": originals,
        "registry": registry,
        "master_root": registry / "MASTER-SNAPSHOTS",
        "work": work,
        "output": work / "PICONS",
        "qa": qa,
        "exceptions": qa / "EXCEPTIONS",
        "legacy_exception_reports": root / "08-REPORTS",
        "ledger": qa / "review-decisions.json",
        "legacy_ledger": app_data / "review-decisions.json",
        "final_root": output,
        "final": output / "PICONS",
        "publish": root / "07-PUBLISH-STAGING",
        "reports": root / "08-REPORTS",
        "logs": root / "09-LOGS",
        "tools": root / "10-TOOLS",
        "app_root": app_root,
        "app": app,
        "app_data": app_data,
        "archive": root / "12-ARCHIVE",
        "data": state,
        "db": state / "factory.sqlite3",
        "source_state": state / "sources.json",
        "source_manifest": sources / "source-manifest.json",
        "ingest": sources / "source-ingest",
        "master_paths": state / "master-current-paths.json",
        "master_cache": state / "master-registry-cache.json",
        "output_cache": state / "output-cache.json",
        "ledger_path": qa / "review-decisions.json",
        "chocho_positions": app_data / "chocholousek-positions.json",
        "diagnostics_cache": app_data / "diagnostics-delivered.json",
        "github_credentials": app_data / "github-upload.dpapi",
        "startup_log": root / "09-LOGS" / "factory-startup-error.log",
    }


def _is_reparse_point(path: Path) -> bool:
    """Detect symlinks and Windows junction/reparse points without following them."""
    try:
        if path.is_symlink():
            return True
        is_junction = getattr(path, "is_junction", None)
        if callable(is_junction) and is_junction():
            return True
        return bool(path.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    except (AttributeError, OSError):
        return False


def _category_counts(folder: Path):
    counts = {"files": 0, "bytes": 0, "png": 0, "archives": 0, "json": 0, "sqlite": 0}
    errors = []
    archive_suffixes = {".zip", ".7z", ".tar", ".gz", ".bz2", ".xz", ".ipk"}
    try:
        def walk_error(exc):
            errors.append(f"{getattr(exc, 'filename', folder)}: {type(exc).__name__}")
        for current, directories, filenames in os.walk(folder, followlinks=False, onerror=walk_error):
            current_path = Path(current)
            # A link can point outside the workspace. Do not traverse it.
            for name in directories:
                if _is_reparse_point(current_path / name):
                    errors.append(f"UNSAFE_REPARSE: {current_path / name}")
            directories[:] = [name for name in directories if not _is_reparse_point(current_path / name)]
            for name in filenames:
                path = current_path / name
                try:
                    if _is_reparse_point(path):
                        errors.append(f"UNSAFE_REPARSE: {path}")
                        continue
                    if not stat.S_ISREG(path.lstat().st_mode):
                        continue
                    size = path.stat().st_size
                except OSError as exc:
                    errors.append(f"{path}: {type(exc).__name__}")
                    continue
                counts["files"] += 1
                counts["bytes"] += size
                suffix = path.suffix.casefold()
                if suffix == ".png": counts["png"] += 1
                if suffix in archive_suffixes: counts["archives"] += 1
                if suffix == ".json": counts["json"] += 1
                if suffix in (".sqlite", ".sqlite3", ".db"): counts["sqlite"] += 1
    except OSError as exc:
        errors.append(f"{folder}: {type(exc).__name__}: {exc}")
    return counts, errors


def verify_required_directories(root: Path):
    """Cheap, read-only structure recheck immediately before an operation writes."""
    root = Path(root)
    if not root.is_dir() or _is_reparse_point(root):
        return False, (f"Dátový koreň nie je dostupný alebo je nebezpečný: {root}",)
    missing = []
    for name, _purpose in DIRECTORIES:
        folder = root / name
        if not folder.is_dir() or _is_reparse_point(folder):
            missing.append(name)
            continue
        try:
            with os.scandir(folder):
                pass
        except OSError as exc:
            missing.append(f"{name} ({type(exc).__name__})")
    if missing:
        return False, ("Chýbajú alebo nie sú čitateľné povinné kategórie: " + ", ".join(missing),)
    return True, ()


def read_only_preflight(root: Path | None = None) -> PreflightResult:
    """Audit the 13 required directories without creating or changing anything."""
    root = Path(root) if root is not None else resolve_root()
    missing, unreadable, findings = [], [], []
    inventory = {}
    checked = 0
    if not root.is_dir():
        return PreflightResult(str(root), False, 0, tuple(name for name, _ in DIRECTORIES),
                               (str(root),), {}, ("Dátový koreň nie je dostupný; zápis je zablokovaný.",))
    if _is_reparse_point(root):
        return PreflightResult(str(root), False, 0, tuple(name for name, _ in DIRECTORIES),
                               (str(root),), {}, ("Dátový koreň je symbolický odkaz; zápis je zablokovaný.",))
    structure_ok, structure_findings = verify_required_directories(root)
    if not structure_ok:
        findings.extend(structure_findings)
    for name, purpose in DIRECTORIES:
        folder = root / name
        checked += 1
        if not folder.is_dir() or _is_reparse_point(folder):
            missing.append(name)
            inventory[name] = {"files": 0, "bytes": 0, "png": 0, "archives": 0, "json": 0, "sqlite": 0}
            continue
        counts, errors = _category_counts(folder)
        inventory[name] = counts
        if errors:
            unreadable.extend(errors[:20])
        findings.append(f"{name}: {counts['files']} súborov, {counts['bytes']} B · {purpose}")
    if missing:
        findings.append("Chýbajú povinné kategórie: " + ", ".join(missing))
    if unreadable:
        findings.append(f"Čítanie niektorých položiek zlyhalo ({len(unreadable)}).")
    return PreflightResult(str(root), structure_ok and not missing and not unreadable, checked,
                           tuple(missing), tuple(unreadable), inventory, tuple(findings))


def workspace_available(root: Path) -> bool:
    return read_only_preflight(root).ok
