"""Incremental Azzurra review inbox for one Warder SAT cycle."""
import argparse
import hashlib
import io
import json
import re
from email.message import Message
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlsplit
from zipfile import ZipFile

from linuxsat_login import BASE, FILE_LIMIT, THREAD, SourceError, authenticated, file_id
from vhannibal_dtt_settings import REF, current_settings, normalize

BASELINE_SHA = "2ee27e9cab46eab8467a3de9ce790c17d6dd08f385a904a2378a7a68aabdd456"
AUTHOR = "234347"
DIGEST = re.compile("[0-9a-f]{64}")
MAX_PAGES = 100


def load_baseline(path):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != BASELINE_SHA:
        raise SourceError("baseline_digest_mismatch")
    rows = json.loads(raw)
    index = {r["id"]: r for r in rows}
    if len(rows) != len(index) or len(index) != 483 or any(
            not k.isdigit() or not DIGEST.fullmatch(v["sha256"]) for k, v in index.items()):
        raise SourceError("invalid_baseline")
    return index


def filename(value):
    if len(value) > 255 or "/" in value or "\\" in value or any(ord(c) < 32 for c in value):
        raise SourceError("invalid_attachment_name")
    return value.strip()


def response_name(headers):
    message = Message()
    message["Content-Disposition"] = headers.get("content-disposition", "")
    return filename(message.get_filename() or "")


class ThreadPage(HTMLParser):
    def __init__(self, raw):
        super().__init__()
        self.page = self.last = self.post = None
        self.member = False
        self.quoted = 0
        self.pages = set()
        self.posts = set()
        self.attachments = {}
        self.feed(raw.decode("utf-8", "strict"))
        self.close()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "li" and a.get("id") == "userMenu":
            self.member = True
        if tag == "ul" and "wbbThreadPostList" in a.get("class", "").split():
            self.page = a.get("data-page-no")
            self.last = a.get("data-is-last-page")
        if tag == "article" and "wbbPost" in a.get("class", "").split():
            self.post = a.get("data-post-id") if a.get("data-user-id") == AUTHOR else None
            if self.post:
                if not self.post.isdigit():
                    raise SourceError("invalid_post_id")
                self.posts.add(self.post)
        if tag == "blockquote":
            self.quoted += 1
        if tag != "a" or not a.get("href"):
            return
        link = urlsplit(urljoin(THREAD, a["href"]))
        if (link.scheme, link.netloc) != ("https", "www.linuxsat-support.com"):
            return
        if link.path == urlsplit(THREAD).path:
            query = parse_qs(link.query)
            if set(query) == {"pageNo"} and len(query["pageNo"]) == 1 and query["pageNo"][0].isdigit():
                self.pages.add(int(query["pageNo"][0]))
        aid = file_id(link.geturl())
        if self.post and not self.quoted and aid:
            caption = filename(a.get("data-caption", ""))
            entry = self.attachments.setdefault(aid, {"filename": caption, "post": self.post})
            if entry["filename"] and caption and entry["filename"] != caption:
                raise SourceError("conflicting_file_identity")
            if caption:
                entry["filename"] = caption

    def handle_endtag(self, tag):
        if tag == "article":
            self.post = None
        if tag == "blockquote":
            self.quoted = max(0, self.quoted - 1)


def discover(session):
    attachments = {}
    for number in range(1, MAX_PAGES + 1):
        url = THREAD if number == 1 else THREAD + "?pageNo=" + str(number)
        _, _, raw = session.request(url, "thread")
        page = ThreadPage(raw)
        if not page.member or page.page != str(number) or page.last not in {"true", "false"}:
            raise SourceError("incomplete_authenticated_thread")
        for aid, row in page.attachments.items():
            if aid in attachments and attachments[aid]["filename"] != row["filename"]:
                raise SourceError("conflicting_file_identity")
            attachments.setdefault(aid, row)
        if page.last == "true":
            if not attachments:
                raise SourceError("empty_author_index")
            return number, attachments
        if number + 1 not in page.pages:
            raise SourceError("incomplete_pagination")
    raise SourceError("pagination_limit")


def reference(name, settings):
    stem = Path(name).stem
    if not REF.fullmatch(stem):
        return {"service_reference": None, "status": "REVIEW_NAME"}
    ref = normalize(stem)
    return {"service_reference": ref, "service": settings.get(ref),
            "status": "EXACT_VHANNIBAL" if ref in settings else "REVIEW_REFERENCE"}


def inspect_content(raw, name):
    from PIL import Image
    if raw.startswith(b"PK\x03\x04"):
        with ZipFile(io.BytesIO(raw)) as archive:
            files = archive.infolist()
            if len(files) > 2000 or sum(i.file_size for i in files) > 64 * 1024 * 1024:
                raise SourceError("archive_limit")
            result = []
            for info in files:
                if info.is_dir() or Path(info.filename).suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                    continue
                if info.file_size > FILE_LIMIT:
                    raise SourceError("image_limit")
                member = filename(Path(info.filename).name)
                data = archive.read(info)
                validate_image(data, Image)
                result.append({"filename": member, "sha256": hashlib.sha256(data).hexdigest()})
            if not result:
                raise SourceError("empty_picon_archive")
            return result
    validate_image(raw, Image)
    return [{"filename": name, "sha256": hashlib.sha256(raw).hexdigest()}]


def validate_image(raw, image):
    with image.open(io.BytesIO(raw)) as source:
        if source.format not in {"PNG", "JPEG", "WEBP"} or source.width * source.height > 16_000_000:
            raise SourceError("unsupported_image")
        source.verify()


def write_json(path, data):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def collect(session, baseline, output, settings_sha, settings):
    statefile = output / "checkpoint.json"
    state = json.loads(statefile.read_text()) if statefile.exists() else {
        "schema": 1, "baseline_sha256": BASELINE_SHA, "changes": {}}
    if state["schema"] != 1 or state["baseline_sha256"] != BASELINE_SHA:
        raise SourceError("checkpoint_identity_mismatch")
    pages, attachments = discover(session)
    changes = state["changes"]
    base_art = {r["sha256"] for r in baseline.values()}
    objects = output / "objects"
    objects.mkdir(parents=True, exist_ok=True)
    for row in changes.values():
        digest = row["sha256"]
        if not DIGEST.fullmatch(digest):
            raise SourceError("invalid_stored_digest")
        if row["content"] == "REVIEW_OBJECT" and not (objects / digest).is_file():
            raise SourceError("stored_object_missing")
    prior_art = {r["sha256"]: r["members"] for r in changes.values()}
    downloads = updated = 0
    for aid, meta in attachments.items():
        prior = changes.get(aid, baseline.get(aid))
        name = meta["filename"]
        url = BASE + "/cms/file-download/" + aid + "/"
        members = []
        size = prior.get("bytes") if prior else None
        if prior:
            _, headers, _ = session.request(url, "file_validator", method="HEAD")
            name = name or response_name(headers) or prior["filename"]
            etag = headers.get("etag", "")
            if not re.fullmatch(r'"' + aid + r'-[0-9a-f]{8}"', etag):
                raise SourceError("file_revision_validator_unavailable")
            length = headers.get("content-length", "")
            size_matches = size is None or not length.isdigit() or int(length) == size
            if size_matches and etag == f'"{aid}-{prior["sha256"][:8]}"':
                if prior["filename"] == name:
                    continue
                digest = prior["sha256"]
                members = prior.get("members", [{"filename": name, "sha256": digest}])
                if len(members) == 1 and members[0]["sha256"] == digest:
                    members = [{"filename": name, "sha256": digest}]
        if not members:
            _, headers, raw = session.request(url, "attachment", limit=FILE_LIMIT)
            name = name or response_name(headers)
            digest = hashlib.sha256(raw).hexdigest()
            if headers.get("etag") != f'"{aid}-{digest[:8]}"':
                raise SourceError("download_revision_mismatch")
            size = len(raw)
            downloads += 1
            dest = objects / digest
            if digest in base_art and not raw.startswith(b"PK\x03\x04"):
                members = [{"filename": name, "sha256": digest}]
            elif digest in prior_art:
                if raw.startswith(b"PK\x03\x04"):
                    members = [dict(m) for m in prior_art[digest]]
                else:
                    members = [{"filename": name, "sha256": digest}]
            else:
                members = inspect_content(raw, name)
                if not dest.exists():
                    dest.write_bytes(raw)
                elif hashlib.sha256(dest.read_bytes()).hexdigest() != digest:
                    raise SourceError("stored_object_digest_mismatch")
        prior_art[digest] = members
        changes[aid] = {"filename": name, "post": meta["post"], "sha256": digest, "members": members,
                        "bytes": size, "content": "BASELINE" if digest in base_art else "REVIEW_OBJECT"}
        updated += 1
    for aid, row in changes.items():
        row["listed"] = aid in attachments
        if state.get("vhannibal_sha256") != settings_sha or any("status" not in m for m in row["members"]):
            for member in row["members"]:
                member.update(reference(member["filename"], settings))
    state["vhannibal_sha256"] = settings_sha
    write_json(statefile, state)
    return {"pages": pages, "author_file_ids": len(attachments), "downloads": downloads, "updated": updated,
            "vhannibal_services": len(settings), "vhannibal_sha256": settings_sha}


def run(args):
    baseline = load_baseline(args.baseline)
    settings_sha, settings = current_settings()
    with authenticated() as session:
        if args.proof:
            session.proof()
        result = collect(session, baseline, args.output, settings_sha, settings)
    print(json.dumps(result, sort_keys=True))


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--proof", action="store_true")
    try:
        run(parser.parse_args(argv))
    except SourceError as error:
        print("SOURCE_ERROR_NO_ADVANCE", error)
        return 2
    except Exception as error:
        print("SOURCE_ERROR_NO_ADVANCE", type(error).__name__)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
