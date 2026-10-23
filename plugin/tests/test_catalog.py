import copy
import hashlib
import io
import unittest

from PiconHubWarderEvolution.catalog import Catalog, CatalogError, CATALOG_URL, verify_stream


def fixture():
    data = b"a test archive"
    sha = hashlib.sha256(data).hexdigest()
    name = "warder-235e-220x132-transparent-test.zip"
    return {"schema": 1, "delivery": "raw-github-parts",
            "parts": [{"filename": name + ".part00", "bytes": len(data), "sha256": sha}],
            "packages": [{"selector_id": "235E", "resolution": "220x132",
                          "family": "channel-transparent", "filename": name,
                          "bytes": len(data), "sha256": sha, "png_count": 1,
                          "parts": [CATALOG_URL.rsplit("/", 1)[0] + "/" + name + ".part00"]}]}


class CatalogTests(unittest.TestCase):
    def test_exact_selection_and_immutable_plan(self):
        catalog = Catalog(fixture())
        self.assertEqual(catalog.selectors, ("235E",))
        package = catalog.select("235E")
        self.assertEqual(package.bytes, sum(p.bytes for p in package.parts))
        with self.assertRaises(AttributeError):
            package.style = "black"

    def test_missing_selection_never_falls_back(self):
        with self.assertRaises(CatalogError):
            Catalog(fixture()).select("235E", style="black")

    def test_legacy_unknown_png_count_is_not_invented(self):
        doc = fixture()
        del doc["packages"][0]["png_count"]
        self.assertIsNone(Catalog(doc).select("235E").png_count)

    def test_provider_and_split_satellite_selectors(self):
        for selector in ("ANTIKSAT", "CANALPLUS_SK", "48E_A", "48E_B"):
            doc = fixture()
            doc["packages"][0]["selector_id"] = selector
            self.assertEqual(Catalog(doc).select(selector).selector_id, selector)

    def test_duplicate_selection_rejected(self):
        doc = fixture()
        doc["packages"].append(copy.deepcopy(doc["packages"][0]))
        with self.assertRaises(CatalogError):
            Catalog(doc)

    def test_untrusted_and_reordered_urls_rejected(self):
        for url in ("https://example.org/archive", fixture()["packages"][0]["parts"][0] + "?x=1",
                    fixture()["packages"][0]["parts"][0].replace("part00", "part01")):
            doc = fixture()
            doc["packages"][0]["parts"] = [url]
            with self.assertRaises(CatalogError):
                Catalog(doc)

    def test_missing_part_checksum_rejected(self):
        doc = fixture()
        doc["parts"] = []
        with self.assertRaises(CatalogError):
            Catalog(doc)

    def test_bad_metadata_rejected(self):
        for key, value in (("bytes", True), ("bytes", 999), ("sha256", "wrong"),
                           ("png_count", 0), ("filename", "../bad.zip")):
            doc = fixture()
            doc["packages"][0][key] = value
            with self.assertRaises(CatalogError):
                Catalog(doc)
        for payload in (b"{", "[]", "null", '{"schema": true}'):
            with self.assertRaises(CatalogError):
                Catalog.from_json(payload)

    def test_stream_integrity(self):
        data = b"correct bytes"
        sha = hashlib.sha256(data).hexdigest()
        self.assertTrue(verify_stream(io.BytesIO(data), len(data), sha))
        for bad in (data[:-1], data + b"x", b"X" + data[1:]):
            with self.assertRaises(CatalogError):
                verify_stream(io.BytesIO(bad), len(data), sha)


if __name__ == "__main__":
    unittest.main()
