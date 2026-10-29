"""Keep the progress log usable without creating receiver log files."""
import pathlib
import tempfile
import unittest
from unittest.mock import patch
import test_native_ui as native_ui


class CleanupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        native_ui.NativeControllerTests.setUpClass();cls.gui=native_ui.NativeControllerTests.gui

    def job(self):
        job=self.gui.PiconJobController();job.setup_job([]);return job

    def test_success_history_stays_in_memory_and_is_bounded(self):
        job=self.job()
        class Runner:
            def __init__(self,event,cancel):self.event=event
            def run(self,preferences):
                for number in range(500):self.event('stage','item '+str(number))
                return {'added':1,'changed':0,'removed':0}
        with patch.object(self.gui,'PiconRunner',Runner),patch('builtins.open',side_effect=AssertionError('Unexpected log write')):
            job.work()
        self.assertEqual(len(job._log_rows),160)
        self.assertIn('item 499',job.log_text());self.assertNotIn('item 0\'',job.log_text())
        self.assertEqual(job.events.qsize(),501)

    def test_error_reaches_ui_queue_and_memory_log_without_a_file(self):
        job=self.job()
        with patch.object(self.gui,'PiconRunner',side_effect=OSError('network unavailable')),patch('builtins.open',side_effect=AssertionError('Unexpected log write')):
            job.work()
        self.assertEqual(job.events.get_nowait(),('error','network unavailable'))
        self.assertIn('network unavailable',job.log_text())

    def test_stage_constructor_failure_cleans_its_new_directory(self):
        import types
        engine=types.SimpleNamespace(**self.gui.PiconRunner.run.__globals__)
        mkdir=pathlib.Path.mkdir
        def fail_backup(path,*args,**kwargs):
            if path.name=='backup':raise OSError('disk full')
            return mkdir(path,*args,**kwargs)
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(engine.sync,'destination_storage_available',return_value=True),patch.object(pathlib.Path,'mkdir',fail_backup):
                with self.assertRaises(OSError):engine.Stage({'destination':tmp})
            self.assertEqual(list(pathlib.Path(tmp).iterdir()),[])
