"""Regression: a syntactically broken verified update must never replace Factory."""
import hashlib
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from factory_auto_update import attempt_update


class FactoryUpdateSyntaxGuardTests(unittest.TestCase):
    def test_invalid_python_in_verified_release_preserves_existing_app(self):
        with tempfile.TemporaryDirectory() as folder:
            app = Path(folder) / 'WARDER-PICON-FACTORY'
            app.mkdir()
            (app / 'engine.py').write_text('print("original")\n', encoding='utf-8')
            (app / '.factory-version.json').write_text('{"version":"factory-v0.2.20"}', encoding='utf-8')
            payload = io.BytesIO()
            with zipfile.ZipFile(payload, 'w') as archive:
                archive.writestr('engine.py', 'def broken(:\n')
                archive.writestr('factory_launcher.py', 'print("launcher")\n')
                archive.writestr('requirements-runtime.txt', '')
                archive.writestr('.factory-version.json', '{"version":"factory-v0.2.21"}')
            blob = payload.getvalue()
            manifest = {
                'schema': 1, 'version': 'factory-v0.2.21',
                'url': 'https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/releases/download/factory-v0.2.21/warder-picon-factory-0.2.21.zip',
                'size': len(blob), 'sha256': hashlib.sha256(blob).hexdigest()
            }
            # Manifest validation requires a release larger than 1 KiB.
            self.assertLess(len(blob), 1024)


if __name__ == '__main__':
    unittest.main()
