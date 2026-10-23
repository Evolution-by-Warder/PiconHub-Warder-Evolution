"""Warder ZIP adapter: original profile modes, skin plans and staged installs."""
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
    if not sync.trusted_publication_url(url, "production"):
        raise PiconError("Nedôveryhodný zdroj balíka.")
    return urlopen(Request(url, headers={"User-Agent": "PiconHub-Warder-Evolution", "Cache-Control": "no-cache"}),
                   timeout=15, context=ssl.create_default_context())


def fetch_manifest(opener=network_open):
    with opener(sync.RUNTIME_MANIFEST_URL) as response:
        raw = response.read(8*1024*1024+1)
    if len(raw) > 8*1024*1024:
        raise PiconError("Katalóg prekročil povolenú veľkosť.")
    try:
        document = json.loads(raw)
    except (ValueError, UnicodeError) as exc:
        raise PiconError("Neplatný katalóg piconov.") from exc
    errors = sync.validate_publication_manifest(document, sync.RUNTIME_MANIFEST_URL)
    if errors:
        raise PiconError("Neplatný katalóg: " + "; ".join(map(str, errors[:3])))
    return document


class Stage:
    def __init__(self, queue):
        self.queue = queue
        self.target = pathlib.Path(queue["destination"])
        if not sync.destination_storage_available(str(self.target)):
            raise PiconError("Cieľový priečinok alebo úložisko nie je dostupné.")
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
            raise PiconError("Obnova potrebuje zásah; záloha zostáva v %s: %s" % (self.backup, errors[0]))
        self.moved, self.written = [], []

    def apply(self):
        if sync.validate_destination(str(self.target)) != str(self.target):
            raise PiconError("Cieľový priečinok sa zmenil.")
        existing = set()
        for path in self.target.iterdir():
            stem = sync.normalize_service_reference(path.stem)
            if path.suffix == ".png" and stem and path.name == stem+".png" and path.is_file() and not path.is_symlink():
                existing.add(path.name)
        writes = []
        for name, checksum in self.hashes.items():
            path = self.target/name
            if path.is_symlink() or (path.exists() and not path.is_file()):
                raise PiconError("Cieľ piconu nie je bežný súbor: " + name)
            if not path.exists() or digest(path) != checksum:
                writes.append(name)
        wanted = sync.wanted_picon_names(self.queue)
        if self.queue["mode"] == sync.UPDATE_MODE_INCREMENTAL:
            stale = []
        else:
            keep = wanted if wanted is not None else self.upstream
            stale = sync.plan_stale_position_picons(existing, self.queue["positions"], keep)
        touched = set(writes) | set(stale)
        # Preserve a readable journal and backup if rollback cannot finish.
        (self.work/"journal.json").write_text(json.dumps({"destination": str(self.target), "writes": writes,
                                                        "old": sorted(touched & existing)}, indent=2))
        try:
            for name in sorted(touched):
                path = self.target/name
                if path.exists():
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
            raise Cancelled("Aktualizácia bola zrušená pred zápisom.")

    def download(self, job, path):
        total = hashlib.sha256()
        count = 0
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
                            raise PiconError("Stiahnutý balík prekročil veľkosť.")
                        checksum.update(data)
                        total.update(data)
                        target.write(data)
                        self.event("download", job["selector_id"], count, job["bytes"])
                if size != part["bytes"] or checksum.hexdigest() != part["sha256"]:
                    raise PiconError("Nesúhlasí časť balíka " + job["selector_id"])
        if count != job["bytes"] or total.hexdigest() != job["sha256"]:
            raise PiconError("Nesúhlasí SHA256 balíka " + job["selector_id"])

    def unpack(self, stage, archive_path, job):
        wanted = sync.wanted_picon_names(stage.queue)
        native_count = 0
        with zipfile.ZipFile(archive_path) as archive:
            members = archive.infolist()
            if sum(info.file_size for info in members) > job["bytes"]*20 + 8*1024*1024:
                raise PiconError("Neprimeraná veľkosť rozbaleného balíka.")
            for info in members:
                self.check_cancel()
                if not sync.safe_archive_member(info.filename) or stat.S_ISLNK(info.external_attr >> 16):
                    raise PiconError("Nebezpečná položka v ZIP archíve.")
                if info.is_dir():
                    continue
                filename = info.filename.replace("\\", "/").rsplit("/",1)[-1]
                if not filename.lower().endswith(".png"):
                    continue
                stem = sync.normalize_service_reference(filename[:-4])
                if not stem:
                    continue
                name = stem + ".png"
                native_count += 1
                stage.upstream.add(name)
                if wanted is not None and name not in wanted:
                    continue
                if info.file_size > 5*1024*1024:
                    raise PiconError("Picon prekročil povolenú veľkosť.")
                data = archive.read(info)
                if (len(data)<24 or not data.startswith(b"\x89PNG\r\n\x1a\n")
                        or data[12:16]!=b"IHDR"
                        or struct.unpack(">II",data[16:24])!=tuple(map(int,job["resolution"].split("x")))):
                    raise PiconError("Neplatný PNG súbor v balíku.")
                checksum = hashlib.sha256(data).hexdigest()
                if name in stage.hashes and stage.hashes[name] != checksum:
                    raise PiconError("Vybrané balíky obsahujú rozdielny picon: " + name)
                stage.hashes[name] = checksum
                (stage.ready/name).write_bytes(data)
        if not native_count:
            raise PiconError("Balík neobsahuje žiadne kanálové picony.")

    def run(self, preferences):
        if not preferences:
            raise PiconError("Nie je zapnutý žiadny profil.")
        stages, applied = [], []
        with open(self.lock_path, "a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise PiconError("Aktualizácia piconov už prebieha.") from exc
            try:
                self.event("stage", "Načítavam katalóg")
                document = fetch_manifest(self.opener)
                for number,prefs in enumerate(preferences,1):
                    self.check_cancel()
                    queue = sync.build_runtime_queue(prefs, self.enigma2_dir, sync.runtime_publication())
                    if queue["mode"] in (sync.UPDATE_MODE_SYNC_TV, sync.UPDATE_MODE_SYNC_TV_RADIO) and not queue["services"]:
                        raise PiconError("Vo vybraných TV/rádio bouquetoch nie sú služby vybraných pozícií.")
                    plan = sync.plan_runtime_packages(document, queue)
                    if plan["state"] != "ready":
                        raise PiconError("Nie sú dostupné všetky vybrané balíky: " + ", ".join(plan.get("missing_selectors", [])))
                    jobs = sync.build_download_jobs(document, plan)
                    if jobs["state"] != "ready" or not jobs["jobs"]:
                        raise PiconError("Nie je pripravený platný plán sťahovania.")
                    stage = Stage(queue)
                    stages.append(stage)
                    if shutil.disk_usage(stage.target).free < sum(job["bytes"] for job in jobs["jobs"])*3 + 8*1024*1024:
                        raise PiconError("Na cieľovom úložisku nie je dosť voľného miesta.")
                    for index,job in enumerate(jobs["jobs"],1):
                        self.event("stage", "Profil %d • balík %d/%d • %s" % (number,index,len(jobs["jobs"]),job["selector_id"]))
                        archive = stage.work/"package.zip"
                        self.download(job, archive)
                        self.event("stage", "Overujem a rozbaľujem " + job["selector_id"])
                        self.unpack(stage, archive, job)
                        archive.unlink()
                self.check_cancel()
                self.event("stage", "Zapisujem overené picony; dokončenie už neprerušujte")
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
