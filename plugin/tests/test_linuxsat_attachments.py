import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import linuxsat_attachment_fetch as fetch
from linuxsat_login import BASE, SourceError, THREAD, trusted
from vhannibal_dtt_settings import BOUQUETS, settings_index

SR = "1_0_19_53_8800_217C_DDE0000_0_0_0"
NAME = SR + ".png"
DIGEST = hashlib.sha256(b"historic content").hexdigest()


def post(aid, name=NAME, author=fetch.AUTHOR, quoted=False):
    link = f'<a data-caption="{name}" href="/cms/file-download/{aid}/"></a>'
    if quoted:
        link = "<blockquote>" + link + "</blockquote>"
    return f'<article class="wbbPost message" data-post-id="790931" data-user-id="{author}">{link}</article>'


def page(posts, number=1, last=True):
    return (f'<li id="userMenu"></li><ul class="wbbThreadPostList" data-page-no="{number}" '
            f'data-is-last-page="{str(last).lower()}">{posts}</ul>').encode()


class Forum:
    def __init__(self, html):
        self.pages = {THREAD: html}
        self.etags = {}
        self.bodies = {}
        self.downloads = []

    def request(self, url, stage, method="GET", **kwargs):
        if url in self.pages:
            return url, {}, self.pages[url]
        aid = url.rstrip("/").rsplit("/", 1)[1]
        headers = {"etag": self.etags[aid]}
        if method == "HEAD":
            return url, headers, b""
        self.downloads.append(aid)
        return url, headers, self.bodies[aid]


class AttachmentsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name)
        self.baseline = {"1": {"filename": NAME, "sha256": DIGEST}}
        self.forum = Forum(page(post("1")))
        self.forum.etags["1"] = f'"1-{DIGEST[:8]}"'
        self.settings = {SR: "Italia"}

    def scan(self):
        return fetch.collect(self.forum, self.baseline, self.output, "a"*64, self.settings)

    def test_existing_files_never_download(self):
        self.assertEqual(self.scan()["downloads"], 0)
        checkpoint = (self.output / "checkpoint.json").read_bytes()
        self.assertEqual(self.scan()["updated"], 0)
        self.assertEqual((self.output / "checkpoint.json").read_bytes(), checkpoint)
        self.assertFalse(self.forum.downloads)

    def test_foreign_authors_quoted_files_and_other_domains(self):
        foreign = '<a href="https://example.org/cms/file-download/99/"></a>'
        self.forum.pages[THREAD] = page(post("1") + post("3", author="5") + post("4", quoted=True) + foreign)
        self.assertEqual(set(fetch.discover(self.forum)[1]), {"1"})
        for url in ("http://www.linuxsat-support.com", "https://www.linuxsat-support.com@other.org"):
            with self.assertRaises(SourceError):
                trusted(url)

    def test_pagination_must_be_complete(self):
        self.forum.pages[THREAD] = page(post("1"), last=False)
        with self.assertRaisesRegex(SourceError, "pagination"):
            self.scan()
        self.forum.pages[THREAD] += b'<a href="?pageNo=2">2</a>'
        self.forum.pages[THREAD + "?pageNo=2"] = page(post("5"), number=2)
        self.assertEqual(fetch.discover(self.forum)[0], 2)

    def test_new_alias_reuses_original_hash_and_refreshes_settings(self):
        self.forum.pages[THREAD] = page(post("1") + post("2"))
        self.forum.bodies["2"] = b"historic content"
        self.forum.etags["2"] = f'"2-{DIGEST[:8]}"'
        self.assertEqual(self.scan()["updated"], 1)
        self.assertEqual(list((self.output / "objects").iterdir()), [])
        self.assertEqual(self.scan()["downloads"], 0)
        fetch.collect(self.forum, self.baseline, self.output, "b"*64, {})
        entry = json.loads((self.output / "checkpoint.json").read_text())["changes"]["2"]
        self.assertEqual(entry["members"][0]["status"], "REVIEW_REFERENCE")
        self.assertEqual(self.forum.downloads, ["2"])

    def test_renamed_file_rechecked_without_get(self):
        self.forum.pages[THREAD] = page(post("1", "new name.png"))
        self.scan()
        record = json.loads((self.output / "checkpoint.json").read_text())["changes"]["1"]
        self.assertEqual(record["members"][0]["status"], "REVIEW_NAME")
        self.assertFalse(self.forum.downloads)

    def test_changed_bytes_verified_and_saved_once(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Image decoding is covered in the LinuxSat regression job")
        source = io.BytesIO()
        Image.new("RGBA", (20, 10)).save(source, format="PNG")
        raw = self.forum.bodies["1"] = source.getvalue()
        digest = hashlib.sha256(raw).hexdigest()
        self.forum.etags["1"] = f'"1-{digest[:8]}"'
        self.assertEqual(self.scan()["downloads"], 1)
        self.assertEqual((self.output / "objects" / digest).read_bytes(), raw)
        self.assertEqual(self.scan()["downloads"], 0)
        (self.output / "objects" / digest).unlink()
        with self.assertRaisesRegex(SourceError, "stored_object_missing"):
            self.scan()
        packed = io.BytesIO()
        with ZipFile(packed, "w") as z:
            z.writestr("picons/" + NAME, raw)
        self.assertEqual(fetch.inspect_content(packed.getvalue(), "picons.zip")[0]["sha256"], digest)

    def test_validator_or_guest_error_cannot_advance_checkpoint(self):
        self.scan()
        old = (self.output / "checkpoint.json").read_bytes()
        for etag in ("", '"1-00000000"'):
            self.forum.etags["1"] = etag
            self.forum.bodies["1"] = b"login page"
            with self.assertRaises(SourceError):
                self.scan()
            self.assertEqual((self.output / "checkpoint.json").read_bytes(), old)
        self.forum.pages[THREAD] = self.forum.pages[THREAD].replace(b'userMenu', b'userLogin')
        with self.assertRaises(SourceError):
            self.scan()

    def test_lamedb_and_exact_orbital_namespace_must_agree(self):
        data = io.BytesIO()
        folder = "Vhannibal Motor Dtt Italia test/"
        services = set()
        with ZipFile(data, "w") as archive:
            for n, (title, orbital) in BOUQUETS.items():
                ns = orbital << 16 | 0x272
                services.add(f"0001:{ns:08x}:0002:0003:25:0\nStation\np:Network")
                archive.writestr(folder + "userbouquet.dbe" + n + ".tv",
                                 f"#NAME {title}\n#SERVICE 1:0:19:1:2:3:{ns:x}:0:0:0:\n")
            archive.writestr(folder + "lamedb", "eDVB services /4/\nservices\n" +
                             "\n".join(sorted(services)) + "\nend\n")
        _, refs = settings_index(data.getvalue())
        self.assertIn("1_0_19_1_2_3_EEEE0272_0_0_0", refs)
        self.assertEqual(len(refs), 3)
