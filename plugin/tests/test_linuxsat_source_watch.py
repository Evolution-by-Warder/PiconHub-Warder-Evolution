"""Offline tests for public LinuxSat Picons forum RSS. No Internet or attachments."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
from linuxsat_source_watch import RSS_URL, parse_rss, scan_source


ITEMS = [
    ("Transparent Picons by stefanbenno6", "12345", "Mon, 23 Nov 2026 08:15:00 GMT"),
    ("Nephilim Enigma2 Picons 220x132", "12346", "Mon, 23 Nov 2026 07:59:00 GMT"),
    ("Picons 13 Est by GioppyGio", "12347", "Mon, 23 Nov 2026 07:40:00 GMT"),
    ("Picons DTT ITALIA by Azzurra", "12348", "Mon, 23 Nov 2026 07:30:00 GMT"),
    ("Rakuten IPTV picons", "12349", "Mon, 23 Nov 2026 07:28:00 GMT"),
]


def xml(items=ITEMS):
    return (
        '<?xml version="1.0"?><rss version="2.0"><channel><title>LinuxSat Picons</title>'
        + "".join(
            '<item><title>%s</title><link>https://www.linuxsat-support.com/thread/%s-topic/</link>'
            '<pubDate>%s</pubDate></item>' % (name, ident, date)
            for name, ident, date in items
        )
        + "</channel></rss>"
    ).encode("utf-8")


class LinuxSatForumFeedTest(unittest.TestCase):
    source = {"id": "linuxsat-e2-picons-forum", "url": RSS_URL,
              "role": "forum-updates-discovery-only", "source_group": "linuxsat-community"}
    new = {"url": RSS_URL, "index_sha256": None, "snapshot": None}

    def test_parse_public_feed_with_thread_identity_and_filters(self):
        parsed = parse_rss(xml())
        self.assertEqual(len(parsed), 5)
        by_id = {x["thread_id"]: x for x in parsed}
        self.assertEqual(by_id["12347"]["duplicate_of"], "gioppygio-sat-snp")
        self.assertEqual(by_id["12349"]["category"], "NOT_SAT_IGNORE")
        self.assertEqual(by_id["12348"]["category"], "NOT_SAT_IGNORE")
        self.assertEqual(by_id["12345"]["category"], "UNVERIFIED_FORUM_TOPIC")

    def test_no_fabricated_initial_snapshot(self):
        row = scan_source(self.source, self.new, lambda: xml())
        self.assertEqual(row["status"], "INITIAL_BASELINE_REVIEW_REQUIRED")
        self.assertEqual(row["rss_items_seen"], 5)
        self.assertEqual(row["changed_path_count"], 3)
        self.assertTrue(row["no_attachment_download"])

    def test_unchanged_feed_skipped(self):
        first = scan_source(self.source, self.new, lambda: xml())
        prior = {"url": RSS_URL, "index_sha256": first["current_sha"],
                 "snapshot": first["snapshot"]}
        again = scan_source(self.source, prior, lambda: xml())
        self.assertEqual(again["status"], "UNCHANGED_SKIP")
        self.assertEqual(again["changed_path_count"], 0)

    def test_new_forum_reply_updates_one_thread_only(self):
        first = scan_source(self.source, self.new, lambda: xml())
        prior = {"url": RSS_URL, "index_sha256": first["current_sha"],
                 "snapshot": first["snapshot"]}
        revised = list(ITEMS)
        revised[1] = (revised[1][0], revised[1][1], "Tue, 24 Nov 2026 09:00:00 GMT")
        result = scan_source(self.source, prior, lambda: xml(revised))
        self.assertEqual(result["status"], "CHANGED_REVIEW_REQUIRED")
        self.assertEqual(result["changed_path_count"], 1)
        self.assertEqual(result["candidates"][0]["thread_id"], "12346")

    def test_rejects_other_domain_and_nonthread_urls(self):
        text = xml().replace(b"www.linuxsat-support.com", b"malicious.invalid")
        with self.assertRaises(ValueError):
            parse_rss(text)
        text = xml().replace(b"/thread/12345-topic/", b"/attachment/12345/")
        with self.assertRaises(ValueError):
            parse_rss(text)

    def test_rejects_invalid_rss_and_entity_declarations(self):
        for payload in (
            b"<html><title>Login required</title></html>",
            b'<!DOCTYPE rss [<!ENTITY data "x">]><rss><channel><item/></channel></rss>',
            b"",
        ):
            with self.subTest(payload=payload[:30]):
                with self.assertRaises(ValueError):
                    parse_rss(payload)

    def test_fail_closed_on_unapproved_rss_location(self):
        with self.assertRaises(ValueError):
            scan_source(self.source, {"url": "https://evil.invalid/rss", "index_sha256": None},
                        lambda: xml())


if __name__ == "__main__":
    unittest.main()
