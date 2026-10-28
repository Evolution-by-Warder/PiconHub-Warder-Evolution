"""Warder ZIP adapter: original profile modes, skin plans and staged installs."""
from .warder_i18n import _
import fcntl
import hashlib
import json
import os
import pathlib
import shutil
import ssl
import stat
import struct
import tempfile
import threading
import zipfile
from urllib.request import Request, urlopen

from . import warder_skin_sync as sync
from .warder_model import selector_display_label
from . import warder_dab as dab
from . import warder_iptv as iptv


class PiconError(ValueError):
    pass


class Cancelled(PiconError):
    pass


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as source:
        for data in iter(lambda: source.read(128*1024), b""):
            result.update(data)
    return result.hexdigest()


def network_open(url):
    if not (sync.trusted_publication_url(url, "production") or dab.trusted_url(url) or iptv.trusted_url(url)):
        raise PiconError(_("Nedôveryhodný zdroj balíka."))
    response = urlopen(Request(url, headers={"User-Agent": "PiconHub-Warder-Evolution", "Cache-Control": "no-cache"}),
                       timeout=15, context=ssl.create_default_context())
    if (dab.trusted_url(url) or iptv.trusted_url(url)) and response.geturl() != url:
        response.close()
        raise PiconError(_("Nedôveryhodný zdroj balíka."))
    return response


def fetch_manifest(opener=network_open):
    with opener(sync.RUNTIME_MANIFEST_URL) as response:
        raw = response.read(8*1024*1024+1)
    if len(raw) > 8*1024*1024:
        raise PiconError(_("Katalóg prekročil povolenú veľkosť."))
    try:
        document = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise PiconError(_("Neplatný katalóg piconov.")) from exc
    errors = sync.validate_publication_manifest(document, sync.RUNTIME_MANIFEST_URL)
    if errors:
        raise PiconError(_("Neplatný katalóg: ") + "; ".join(map(str, errors[:3])))
    return document


class Stage:
    def __init__(self, queue):
        self.queue = queue
        self.target = pathlib.Path(queue["destination"])
        if not sync.destination_storage_available(str(self.target)):
            raise PiconError(_("Cieľový priečinok alebo úložisko nie je dostupné."))
        self.target.mkdir(parents=True, exist_ok=True)
        self.work = pathlib.Path(tempfile.mkdtemp(prefix=".piconhub-stage-", dir=str(self.target)))
        self.ready, self.backup = self.work/"ready", self.work/"backup"
        self.ready.mkdir()
        self.backup.mkdir()
        self.upstream, self.hashes = set(), {}
        self.moved, self.written = [], []
        self.keep = False

    def rollback(self):
        errors = []
        for name in reversed(self.written):
            try:
                (self.target/name).unlink(missing_ok=True)
            except OSError as exc:
                errors.append(str(exc))
        for name in reversed(self.moved):
            try:
                os.replace(self.backup/name, self.target/name)
            except OSError as exc:
                errors.append(str(exc))
        if errors:
            self.keep = True
            raise PiconError(_("Obnova potrebuje zásah; záloha zostáva v %s: %s") % (self.backup, errors[0]))
        self.moved, self.written = [], []

    def apply(self):
        if sync.validate_destination(str(self.target)) != str(self.target):
            raise PiconError(_("Cieľový priečinok sa zmenil."))
        existing = set()
        for path in self.target.iterdir():
            stem = sync.normalize_service_reference(path.stem)
            if path.suffix == ".png" and stem and path.name == stem+".png" and (path.is_file() or path.is_symlink()):
                existing.add(path.name)
        writes = []
        for name, checksum in self.hashes.items():
            path = self.target/name
            if not path.is_symlink() and path.exists() and not path.is_file():
                raise PiconError(_("Cieľ piconu nie je bežný súbor: ") + name)
            if path.is_symlink() or not path.exists() or digest(path) != checksum:
                writes.append(name)
        wanted = sync.wanted_picon_names(self.queue)
        if self.queue["mode"] == sync.UPDATE_MODE_INCREMENTAL:
            stale = []
        else:
            keep = wanted if wanted is not None else self.upstream
            stale = sync.plan_stale_position_picons(existing, self.queue["positions"], keep)
        # A satellite package cannot authorize deletion of another transport's picons.
        stale = [name for name in stale if name.startswith("1_")]
        if self.queue["mode"] == sync.UPDATE_MODE_SYNC_TV_RADIO:
            stale = []  # Preserve radio identities absent from current upstream coverage.
        touched = set(writes) | set(stale)
        # Preserve a readable journal and backup if rollback cannot finish.
        (self.work/"journal.json").write_text(json.dumps({"destination": str(self.target), "writes": writes,
                                                        "old": sorted(touched & existing)}, indent=2))
        try:
            for name in sorted(touched):
                path = self.target/name
                if path.is_symlink() or path.exists():
                    os.replace(path, self.backup/name)
                    self.moved.append(name)
            for name in writes:
                os.replace(self.ready/name, self.target/name)
                self.written.append(name)
        except Exception:
            self.rollback()
            raise
        return {"added": len(set(writes)-existing), "changed": len(set(writes)&existing), "removed": len(stale)}

    def cleanup(self):
        if not self.keep:
            shutil.rmtree(self.work)


class PiconRunner:
    def __init__(self, opener=network_open, event=None, cancel=None, enigma2_dir="/etc/enigma2", lock_path="/tmp/piconhub-picons.lock"):
        self.opener, self.event = opener, event or (lambda *args: None)
        self.cancel = cancel or threading.Event()
        self.enigma2_dir, self.lock_path = enigma2_dir, lock_path

    def check_cancel(self):
        if self.cancel.is_set():
            raise Cancelled(_("Aktualizácia bola zrušená pred zápisom."))

    def download(self, job, path):
        total = hashlib.sha256()
        count = 0
        self.event("download", selector_display_label(job["selector_id"]), 0, job["bytes"])
        with path.open("wb") as target:
            for part in job["parts"]:
                self.check_cancel()
                checksum, size = hashlib.sha256(), 0
                with self.opener(part["url"]) as source:
                    while True:
                        self.check_cancel()
                        data = source.read(128*1024)
                        if not data:
                            break
                        count += len(data)
                        size += len(data)
                        if size > part["bytes"] or count > job["bytes"]:
                            raise PiconError(_("Stiahnutý balík prekročil veľkosť."))
                        checksum.update(data)
                        total.update(data)
                        target.write(data)
                        self.event("download", selector_display_label(job["selector_id"]), count, job["bytes"])
                if size != part["bytes"] or checksum.hexdigest() != part["sha256"]:
                    raise PiconError(_("Nesúhlasí časť balíka ") + selector_display_label(job["selector_id"]))
        if count != job["bytes"] or total.hexdigest() != job["sha256"]:
            raise PiconError(_("Nesúhlasí SHA256 balíka ") + selector_display_label(job["selector_id"]))

    def unpack(self, stage, archive_path, job):
        wanted = sync.wanted_picon_names(stage.queue)
        native_count = 0
        foreign_count = 0
        expected_position = sync.canonical_position_for_selector(job["selector_id"])
        with zipfile.ZipFile(archive_path) as archive:
            members = archive.infolist()
            if sum(info.file_size for info in members) > job["bytes"]*20 + 8*1024*1024:
                raise PiconError(_("Neprimeraná veľkosť rozbaleného balíka."))
            for info in members:
                self.check_cancel()
                if not sync.safe_archive_member(info.filename) or stat.S_ISLNK(info.external_attr >> 16):
                    raise PiconError(_("Nebezpečná položka v ZIP archíve."))
                if info.is_dir():
                    continue
                filename = info.filename.replace("\\", "/").rsplit("/",1)[-1]
                if not filename.lower().endswith(".png"):
                    continue
                stem = sync.normalize_service_reference(filename[:-4])
                if not stem:
                    continue
                name = stem + ".png"
                # Appended source archives may include service-reference aliases
                # from other orbital positions. Only the owning position's
                # package may supply its channel image to this staged install.
                # Check before duplicate detection, so an unrelated alias in
                # 13.0E cannot conflict with the real 19.2E package.
                if expected_position and expected_position != "dtt" and sync.service_orbital_position(stem) != expected_position:
                    foreign_count += 1
                    continue
                native_count += 1
                stage.upstream.add(name)
                if wanted is not None and name not in wanted:
                    continue
                if info.file_size > 5*1024*1024:
                    raise PiconError(_("Picon prekročil povolenú veľkosť."))
                data = archive.read(info)
                if (len(data)<24 or not data.startswith(b"\x89PNG\r\n\x1a\n")
                        or data[12:16]!=b"IHDR"
                        or struct.unpack(">II",data[16:24])!=tuple(map(int,job["resolution"].split("x")))):
                    raise PiconError(_("Neplatný PNG súbor v balíku."))
                checksum = hashlib.sha256(data).hexdigest()
                if name in stage.hashes and stage.hashes[name] != checksum:
                    raise PiconError(_("Vybrané balíky obsahujú rozdielny picon: ") + name)
                stage.hashes[name] = checksum
                (stage.ready/name).write_bytes(data)
        if foreign_count:
            self.event("package-filter", {"selector_id":job["selector_id"],
                       "position":expected_position,"foreign_picons_ignored":foreign_count})
        if not native_count:
            raise PiconError(_("Balík neobsahuje žiadne kanálové picony."))

    def stage_dab(self, prefs, stages):
        self.check_cancel()
        self.event("stage", _("Načítavam katalóg") + " DAB / DAB+")
        try:
            document = dab.read_manifest(self.opener)
        except (ValueError, TypeError) as exc:
            raise PiconError(_("Neplatný katalóg: ") + "DAB / DAB+") from exc
        dab_preferences = dict(prefs)
        if prefs.get("radio_only") and not prefs.get("positions"):
            dab_preferences["dab_only"] = True
        planned = dab.plan(document, dab_preferences, self.enigma2_dir)
        if planned is None:
            if prefs.get("dab_only"):
                raise PiconError("DAB / DAB+" + _(" • zatiaľ nedostupné"))
            self.event("stage", "DAB / DAB+" + _(" • zatiaľ nedostupné"))
            return
        queue, job = planned
        stage = Stage(queue)
        stages.append(stage)
        if shutil.disk_usage(stage.target).free < job["bytes"]*3 + 8*1024*1024:
            raise PiconError(_("Na cieľovom úložisku nie je dosť voľného miesta."))
        archive = stage.work/"dab.zip"
        self.download(job, archive)
        self.event("stage", _("Overujem a rozbaľujem ") + "DAB / DAB+")
        try:
            dab.unpack(stage, archive, job, self.check_cancel)
        except (ValueError, TypeError, zipfile.BadZipFile) as exc:
            raise PiconError(_("Neplatný katalóg: ") + "DAB / DAB+") from exc
        if prefs["update_mode"] == sync.UPDATE_MODE_SYNC_TV_RADIO:
            covered=set(job["files"])
            missing={name for name in dab.bouquet_names(self.enigma2_dir) if name.startswith("4115_")}-covered
            if missing:self.event("stage", "DAB / DAB+: " + str(len(missing)) + _(" • zatiaľ nedostupné"))
        self.event("processed", "DAB / DAB+")
        archive.unlink()

    def stage_iptv(self, prefs, stages):
        self.check_cancel()
        label = _(iptv.LABEL)
        self.event("stage", _("Načítavam katalóg") + " " + label)
        try:
            document = iptv.read_manifest(self.opener)
            planned = iptv.plan(document, prefs, self.enigma2_dir)
        except (ValueError, TypeError) as exc:
            raise PiconError(_("Neplatný katalóg: ") + label) from exc
        if planned is None:
            if prefs.get("iptv_only"):
                raise PiconError(label + _(" • zatiaľ nedostupné"))
            self.event("stage", label + _(" • zatiaľ nedostupné"))
            return
        queue, job = planned
        stage = Stage(queue)
        stages.append(stage)
        if shutil.disk_usage(stage.target).free < job["bytes"] * 3 + 8 * 1024 * 1024:
            raise PiconError(_("Na cieľovom úložisku nie je dosť voľného miesta."))
        archive = stage.work / "iptv-sk-cz.zip"
        self.download(job, archive)
        self.event("stage", _("Overujem a rozbaľujem ") + label)
        try:
            iptv.unpack(stage, archive, job, self.check_cancel)
        except (ValueError, TypeError, zipfile.BadZipFile) as exc:
            raise PiconError(_("Neplatný katalóg: ") + label) from exc
        self.event("processed", label)
        archive.unlink()

    def run(self, preferences):
        if not preferences:
            raise PiconError(_("Nie je zapnutý žiadny profil."))
        stages, applied = [], []
        with open(self.lock_path, "a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise PiconError(_("Aktualizácia piconov už prebieha.")) from exc
            try:
                self.event("stage", _("Načítavam katalóg"))
                document = None if all(p.get("dab_only") or p.get("iptv_only") or p.get("radio_only") for p in preferences) else fetch_manifest(self.opener)
                for number,prefs in enumerate(preferences,1):
                    self.check_cancel()
                    if prefs.get("radio_only"):
                        if prefs.get("include_dab"):
                            self.stage_dab(prefs, stages)
                        if prefs.get("include_iptv"):
                            self.stage_iptv(prefs, stages)
                        continue
                    if prefs.get("iptv_only"):
                        self.stage_iptv(prefs, stages)
                        continue
                    if prefs.get("dab_only"):
                        self.stage_dab(prefs, stages)
                        continue
                    queue = sync.build_runtime_queue(prefs, self.enigma2_dir, sync.runtime_publication())
                    if queue["mode"] in (sync.UPDATE_MODE_SYNC_TV, sync.UPDATE_MODE_SYNC_TV_RADIO) and not queue["services"]:
                        raise PiconError(_("Vo vybraných TV/rádio bouquetoch nie sú služby vybraných pozícií."))
                    plan = sync.plan_runtime_packages(document, queue)
                    if plan["state"] != "ready":
                        raise PiconError(_("Nie sú dostupné všetky vybrané balíky: ") + ", ".join(selector_display_label(s) for s in plan.get("missing_selectors", [])))
                    jobs = sync.build_download_jobs(document, plan)
                    if jobs["state"] != "ready" or not jobs["jobs"]:
                        raise PiconError(_("Nie je pripravený platný plán sťahovania."))
                    stage = Stage(queue)
                    stages.append(stage)
                    if shutil.disk_usage(stage.target).free < sum(job["bytes"] for job in jobs["jobs"])*3 + 8*1024*1024:
                        raise PiconError(_("Na cieľovom úložisku nie je dosť voľného miesta."))
                    for index,job in enumerate(jobs["jobs"],1):
                        archive = stage.work/"package.zip"
                        self.download(job, archive)
                        self.event("stage", _("Overujem a rozbaľujem ") + selector_display_label(job["selector_id"]))
                        self.unpack(stage, archive, job)
                        self.event("processed", selector_display_label(job["selector_id"]))
                        archive.unlink()
                    if prefs.get("include_dab"):
                        self.stage_dab(prefs, stages)
                    if prefs.get("include_iptv"):
                        self.stage_iptv(prefs, stages)
                self.check_cancel()
                self.event("stage", _("Zapisujem overené picony; dokončenie už neprerušujte"))
                total = {"added":0,"changed":0,"removed":0}
                for stage in stages:
                    result = stage.apply()
                    applied.append(stage)
                    for key in total:
                        total[key] += result[key]
                self.event("done", total)
                return total
            except Exception as original:
                recovery_errors = []
                for stage in reversed(applied):
                    try:
                        stage.rollback()
                    except Exception as exc:
                        stage.keep = True
                        recovery_errors.append(str(exc))
                if recovery_errors:
                    raise PiconError("; ".join(recovery_errors)) from original
                raise
            finally:
                for stage in stages:
                    stage.cleanup()

