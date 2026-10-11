"""Cooperative cancellation is observed only at safe engine checkpoints."""
import threading
import unittest

from engine import Factory, ScanCancelled


class FactoryCancellationTests(unittest.TestCase):
    def test_cancel_event_stops_before_more_work_is_scheduled(self):
        factory = object.__new__(Factory)
        factory.cancel_event = threading.Event()
        factory.cancel_event.set()
        with self.assertRaises(ScanCancelled):
            factory.check_cancelled()

    def test_clear_event_allows_engine_to_continue(self):
        factory = object.__new__(Factory)
        factory.cancel_event = threading.Event()
        factory.check_cancelled()

    def test_scan_stops_at_first_checkpoint_after_source_sync(self):
        factory = object.__new__(Factory)
        factory.cancel_event = threading.Event()
        factory.emit = lambda *_: None
        factory.log = lambda *_: None

        def source_sync():
            factory.cancel_event.set()

        factory.fetch_sources = source_sync
        with self.assertRaises(ScanCancelled):
            factory.scan()


if __name__ == "__main__":
    unittest.main()
