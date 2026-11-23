"""Offline regression tests for SatDigitalne source monitoring (never access network)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
from satdigitalne_source_watch import (CATALOG_URL, catalog_names, requested_archives, scan_source)


GROUPS = ["CanalPlus", "AntikSAT", "FreeSAT", "DigiSK_TellyCz", "Hotbird_13e",
          "Astra_19_2e", "Eutelsat_16e", "Turksat_42e", "Multi_13-16-19-23-28E"]
FILES = [
    "srp.%s_%s.005jon.tar.xz" % (style, group)
    for group in GROUPS
    for style in ("220x132-220x132.light.on.transparent",
                  "400x240-400x240.light.on.transparent")
]
HTML = ("<html><body>" + "".join(
    '<a href="%s">%s</a>' % (f, f) for f in FILES
) + '<a href="https://evil.example/picon/srp.220x132-220x132.light.on.transparent_Outside.005jon.tar.xz">evil</a>'
  + '<a href="snp.400x240-400x240.light.on.transparent_DvB-T_Cz.005jon.tar.xz">DVB</a>'
  + '<a href="enigma2-plugin-extensions-piconczsk_3.1.6_all.ipk">Plugin</a>'
  + "</body></html>").encode()


def head(filename):
    return {"etag": '"sha-' + filename + '"', "last_modified": "Mon, 23 Nov 2026 04:00:00 GMT",
            "content_length": "10000"}


class SatDigitalneOfflineTests(unittest.TestCase):
    source = {
        "id": "satdigitalne-sat-picons", "url": CATALOG_URL,
        "role": "provider-srp-artwork-review", "source_group": "satdigitalne-005jon",
    }
    unscanned = {"url": CATALOG_URL, "index_sha256": None, "snapshot": None}

    def test_only_approved_sat_archive_links(self):
        names = catalog_names(HTML)
        self.assertEqual(len(names), 18)
        self.assertEqual(len(requested_archives(names)), 18)
        self.assertNotIn("DvB-T_Cz", "".join(names))
        self.assertNotIn("Outside", "".join(names))

    def test_initial_baseline_never_faked(self):
        row = scan_source(self.source, self.unscanned, lambda: HTML, head)
        self.assertEqual(row["status"], "INITIAL_BASELINE_REVIEW_REQUIRED")
        self.assertEqual(row["previous_sha"], None)
        self.assertEqual(len(row["current_sha"]), 64)
        self.assertTrue(row["no_binary_download"])
        self.assertEqual(row["representative_head_requests"], 18)

    def test_unchanged_metadata_skips(self):
        initial = scan_source(self.source, self.unscanned, lambda: HTML, head)
        baseline = {"url": CATALOG_URL, "index_sha256": initial["current_sha"],
                    "snapshot": initial["snapshot"]}
        row = scan_source(self.source, baseline, lambda: HTML, head)
        self.assertEqual(row["status"], "UNCHANGED_SKIP")
        self.assertEqual(row["changed_path_count"], 0)

    def test_same_filename_new_etag_is_reviewed(self):
        initial = scan_source(self.source, self.unscanned, lambda: HTML, head)
        baseline = {"url": CATALOG_URL, "index_sha256": initial["current_sha"],
                    "snapshot": initial["snapshot"]}
        def changed(filename):
            metadata = head(filename)
            if "_CanalPlus." in filename:
                metadata["etag"] = '"new-canaplus"'
            return metadata
        row = scan_source(self.source, baseline, lambda: HTML, changed)
        self.assertEqual(row["status"], "CHANGED_REVIEW_REQUIRED")
        self.assertTrue(any(c.get("reason") == "metadata changed" for c in row["candidates"]))

    def test_too_small_index_fail_closed(self):
        with self.assertRaises(ValueError):
            catalog_names(b"<a href='srp.220x132-220x132.light.on.transparent_One.005jon.tar.xz'>a</a>")

    def test_untrusted_catalogue_origin_refused(self):
        with self.assertRaises(ValueError):
            scan_source(self.source, {"url": "https://evil.example/picon/", "index_sha256": None},
                        lambda: HTML, head)


if __name__ == "__main__":
    unittest.main()
