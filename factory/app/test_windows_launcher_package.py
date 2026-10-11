"""Validate the generated single-file Windows launcher structure."""
import hashlib
import base64
import json
import re
import tempfile
import unittest
import zipfile
from pathlib import Path

from package_windows_cmd import build_launcher


class WindowsLauncherPackageTests(unittest.TestCase):
    def test_launcher_contains_verified_executable_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            executable = root / 'factory.exe'
            binary = b'MZ' + b'example PE payload'
            executable.write_bytes(binary)
            launcher = root / 'SPUSTI-WARDER.cmd'
            result = build_launcher(executable, launcher, 'factory-v1.2.3')
            image = launcher.read_bytes()
            offset = result['payload_offset']
            self.assertEqual(image[offset:offset + 4], b'PK\x03\x04')
            self.assertEqual(result['executable_sha256'], hashlib.sha256(binary).hexdigest())
            self.assertIn(b'set "WARDER_VERSION=factory-v1.2.3"', image[:offset])
            encoded = re.search(rb'-EncodedCommand ([A-Za-z0-9+/=]+)', image[:offset]).group(1)
            powershell = base64.b64decode(encoded).decode('utf-16le')
            self.assertIn('$env:WARDER_PAYLOAD_OFFSET', powershell)
            self.assertIn('Expand-Archive', powershell)
            self.assertIn('Factory executable SHA-256 mismatch', powershell)
            self.assertIn('[Security.Cryptography.SHA256]', powershell)
            self.assertNotIn('Get-FileHash', powershell)
            payload_path = root / 'payload.zip'
            payload_path.write_bytes(image[offset:])
            with zipfile.ZipFile(payload_path) as payload:
                self.assertIsNone(payload.testzip())
                self.assertEqual(payload.read('WARDER-PICON-FACTORY.exe'), binary)
                metadata = json.loads(payload.read('factory-payload.json'))
                self.assertEqual(metadata['sha256'], result['executable_sha256'])

    def test_non_pe_input_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'bad.exe'
            source.write_bytes(b'not an executable')
            with self.assertRaises(ValueError):
                build_launcher(source, root / 'launch.cmd', 'factory-v1.2.3')

    def test_unsafe_version_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'factory.exe'
            source.write_bytes(b'MZpayload')
            with self.assertRaises(ValueError):
                build_launcher(source, root / 'launch.cmd', 'factory-v1.2.3&start calc')


if __name__ == '__main__':
    unittest.main()
