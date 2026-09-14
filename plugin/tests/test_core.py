import os
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, ROOT)

from Plugins.Extensions.PiconHubWarderEvolution.core.engine import PiconHubEngine, validate_target
from Plugins.Extensions.PiconHubWarderEvolution.core.scanner import git_blob_sha1, service_line_to_picon
from Plugins.Extensions.PiconHubWarderEvolution.core.errors import UnsafePathError


class FakeCatalog(object):
    def __init__(self, rows):
        self.rows = rows
    def picons(self, satellite, provider, style):
        return list(self.rows)


class CoreTests(unittest.TestCase):
    def test_service_reference(self):
        line = '#SERVICE 1:0:19:5C8:4:1:E080000:0:0:0:'
        self.assertEqual(service_line_to_picon(line), '1_0_19_5C8_4_1_E080000_0_0_0.png')

    def test_safe_target(self):
        with self.assertRaises(UnsafePathError):
            validate_target('/etc')

    def test_git_blob_and_plan_unchanged(self):
        tmp = tempfile.mkdtemp(prefix='piconhub-test-')
        try:
            path = os.path.join(tmp, '1_0_1_A_1_1_0_0_0_0.png')
            with open(path, 'wb') as h:
                h.write(b'png-test')
            row = {'name': os.path.basename(path), 'size': os.path.getsize(path),
                   'sha': git_blob_sha1(path), 'download_url': 'https://example.invalid/a.png'}
            settings = {'target_dir': tmp, 'satellite': '23.5e', 'provider': 'x',
                        'style': 'transparent', 'mode': 'all', 'remove_orphans': False}
            plan = PiconHubEngine(settings, catalog=FakeCatalog([row])).plan()
            self.assertEqual(plan['download_count'], 0)
            self.assertEqual(plan['unchanged_count'], 1)
        finally:
            try:
                os.remove(path)
                os.rmdir(tmp)
            except Exception:
                pass


if __name__ == '__main__':
    unittest.main()
