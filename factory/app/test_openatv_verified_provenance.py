import hashlib
import tempfile
import unittest
from pathlib import Path

from openatv_feed import verified_package_style, verified_package_styles


class VerifiedOpenATVPackageProvenanceTests(unittest.TestCase):
    def _package(self, family, style, payload=b"verified package bytes"):
        name=f'enigma2-plugin-picons-{family}-full.220x132-190x102.{style}.on.transparent'
        filename=name+'_2026-10-11--12-56-43_all.ipk'
        digest=hashlib.sha256(payload).hexdigest()
        return {'name':name,'filename':filename,'sha256':digest},payload

    def test_feed_metadata_requires_exact_consistent_package_name(self):
        package,_=self._package('srp','dark')
        self.assertEqual(verified_package_style(package),('srp','dark'))
        mismatch=dict(package,filename=package['filename'].replace('srp-','utf8snp-'))
        self.assertIsNone(verified_package_style(mismatch))
        ambiguous=dict(package,name=package['name']+'.light.on.transparent')
        self.assertIsNone(verified_package_style(ambiguous))

    def test_provenance_map_requires_archive_sha256_match(self):
        package,payload=self._package('utf8snp','light')
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/(package['sha256']+'.ipk')).write_bytes(payload)
            self.assertEqual(verified_package_styles([package],root),
                             {package['sha256']:('utf8snp','light')})
            (root/(package['sha256']+'.ipk')).write_bytes(b'changed bytes')
            self.assertEqual(verified_package_styles([package],root),{})


if __name__ == '__main__':
    unittest.main()
