"""DAB installer smoke tests (no Enigma2 receiver required)."""
import importlib.util
import struct
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'picons' / 'DAB' / 'install_verified.py'
spec = importlib.util.spec_from_file_location('dab_install_verified', str(SCRIPT))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class DABInstallerTests(unittest.TestCase):
    def test_valid_png_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            png = Path(tmp) / '4115_0_2_A_1_1_0_0_0_0.png'
            png.write_bytes(b'\x89PNG\r\n\x1a\n' + struct.pack('>I', 13) +
                            b'IHDR' + struct.pack('>II', 220, 132) + b'\x00' * 5)
            module.validate_png(png)
            result = module.plan(Path(tmp), Path(tmp) / 'destination')
            self.assertEqual(len(result), 1)

    def test_wrong_size_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            png = Path(tmp) / '4115_0_2_A_1_1_0_0_0_0.png'
            png.write_bytes(b'\x89PNG\r\n\x1a\n' + struct.pack('>I', 13) +
                            b'IHDR' + struct.pack('>II', 64, 64) + b'\x00' * 5)
            with self.assertRaises(ValueError):
                module.validate_png(png)

    def test_invalid_basename_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            png = Path(tmp) / 'not-a-reference.png'
            png.write_bytes(b'\x89PNG\r\n\x1a\n' + struct.pack('>I', 13) +
                            b'IHDR' + struct.pack('>II', 220, 132) + b'\x00' * 5)
            with self.assertRaises(ValueError):
                module.plan(Path(tmp), Path(tmp) / 'destination')


if __name__ == '__main__':
    unittest.main()
