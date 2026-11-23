"""Offline tests for one-pass GioppyGio source watch; never contact or download ZIPs."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
from gioppygio_source_watch import CATALOG_URL, find_archives, scan_source


NAMES = [
    "gioppygio-ful-trs-220x132-%s.zip" % item
    for item in ("1.9-est", "4.8-est", "7.0-est", "9.0-est", "13-est",
                 "16-est", "19.2-est", "23-est", "28-est", "34W-70E-motor")
]
HTML = ("<html>" + "".join(
    '<a href="https://gioppygio.it/picons/220x132/%s">%s</a>' % (name, name)
    for name in NAMES
) + '<a href="https://evil.example/picons/220x132/gioppygio-ful-trs-220x132-26-est.zip">evil</a>'
    + '<a href="https://gioppygio.it/picons/417x250/gioppygio-ful-trs-417x250-13-est.zip">wrong size</a>'
    + '<a href="/picons/220x132/gioppygio-silver-220x132-13-est.zip">decorative</a>'
    + "</html>").encode("utf-8")


def response(name):
    return {"etag": '"rev-' + name + '"', "last_modified": "Mon, 23 Nov 2026 06:00:00 GMT",
            "content_length": "162530"}


class TestGioppyGioSourceWatch(unittest.TestCase):
    source = {"id": "gioppygio-sat-snp", "url": CATALOG_URL,
              "source_group": "gioppygio-snp", "role": "satellite-snp-artwork-review"}
    baseline = {"url": CATALOG_URL, "index_sha256": None, "snapshot": None}

    def test_only_canonical_sat_archives(self):
        items = find_archives(HTML)
        self.assertEqual(set(items), set(NAMES))
        self.assertEqual(len(items), 10)

    def test_initial_state_does_not_claim_existing_picons_processed(self):
        row = scan_source(self.source, self.baseline, lambda: HTML, response)
        self.assertEqual(row["status"], "INITIAL_BASELINE_REVIEW_REQUIRED")
        self.assertEqual(row["archive_count"], 10)
        self.assertTrue(row["no_binary_download"])
        self.assertEqual(row["metadata_head_requests"], 10)

    def test_unchanged_head_does_not_recheck_picons(self):
        old = scan_source(self.source, self.baseline, lambda: HTML, response)
        baseline = {"url": CATALOG_URL, "index_sha256": old["current_sha"],
                    "snapshot": old["snapshot"]}
        new = scan_source(self.source, baseline, lambda: HTML, response)
        self.assertEqual(new["status"], "UNCHANGED_SKIP")
        self.assertEqual(new["changed_path_count"], 0)

    def test_same_name_changed_etag_is_detected(self):
        old = scan_source(self.source, self.baseline, lambda: HTML, response)
        baseline = {"url": CATALOG_URL, "index_sha256": old["current_sha"],
                    "snapshot": old["snapshot"]}
        def modified(name):
            meta = response(name)
            if "13-est" in name:
                meta["etag"] = '"new-revision"'
            return meta
        new = scan_source(self.source, baseline, lambda: HTML, modified)
        self.assertEqual(new["status"], "CHANGED_REVIEW_REQUIRED")
        self.assertTrue(any(x.get("reason") == "archive metadata changed" for x in new["candidates"]))

    def test_fail_closed_on_sparse_or_wrong_source(self):
        with self.assertRaises(ValueError):
            find_archives(b"<html>no picons</html>")
        with self.assertRaises(ValueError):
            scan_source(self.source, {"url": "https://example.org", "index_sha256": None},
                        lambda: HTML, response)


if __name__ == "__main__":
    unittest.main()
