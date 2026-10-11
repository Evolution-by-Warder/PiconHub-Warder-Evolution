"""Regression coverage for the live Chocholousek download-directory format."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import hashlib
import importlib.util
import json

from PIL import Image

from chocholousek_source import INDEX_URL, parse_archive_index, sync_chocholousek


CURRENT_PAGE = '''<!doctype html><html><body>
<a class="download-link" title="Build 260107" href="https://picon.cz/download/3330/" rel="nofollow">
 piconblack-220x132-13.0E_by_chocholousek.7z\t(staženo 102451× )
</a>
<a class="download-link" href="https://picon.cz/download/3348/">
 piconblack-220x132-23.5E_by_chocholousek.7z (staženo 96738× )
</a></body></html>'''


class Response:
    def __init__(self, url, body):
        self.url = url
        self.body = body

    def geturl(self):
        return self.url

    def read(self, limit=-1):
        return self.body[:limit]

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class ChocholousekSourceTests(unittest.TestCase):
    def test_public_220x132_page_annotations_are_stripped_from_archive_names(self):
        entries = parse_archive_index(CURRENT_PAGE)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0], {
            'permalink': '3330',
            'filename': 'piconblack-220x132-13.0E_by_chocholousek.7z',
        })

    def test_empty_selection_does_not_contact_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = sync_chocholousek(tmp, selected_positions=[])
        self.assertEqual(result['status'], 'selection_required')
        self.assertFalse(Path(tmp, 'chocholousek-state.json').exists())

    def test_only_explicitly_selected_positions_are_downloaded(self):
        calls = []
        payload = CURRENT_PAGE.encode('utf-8')

        def opener(request, timeout):
            self.assertEqual(request.full_url, INDEX_URL)
            return Response(INDEX_URL, payload)

        def download(permalink, target, opener=None):
            calls.append((permalink, Path(target).name))
            return 'a' * 64

        with tempfile.TemporaryDirectory() as tmp, \
                patch('chocholousek_source._download_7z', side_effect=download), \
                patch('chocholousek_source._import_7z', return_value={
                    'imported': 4, 'skipped': 0, 'sha256': 'a' * 64}):
            result = sync_chocholousek(tmp, opener=opener, now=1_800_000_000,
                                       selected_positions=['13.0E'])

        self.assertEqual([call[0] for call in calls], ['3330'])
        self.assertEqual(result['downloaded'], 1)
        self.assertEqual(result['imported_png'], 4)
        self.assertEqual(result['archive_count'], 1)

    def test_newly_selected_position_imports_even_when_index_hash_is_unchanged(self):
        calls = []
        payload = CURRENT_PAGE.encode('utf-8')
        digest = hashlib.sha256(payload).hexdigest()

        def opener(request, timeout):
            return Response(INDEX_URL, payload)

        def download(permalink, target, opener=None):
            calls.append(permalink)
            return 'b' * 64

        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / 'chocholousek-state.json'
            state.write_text(json.dumps({
                'schema': 1, 'index_sha256': digest, 'checked_unix': 1,
                'archives': {'piconblack-220x132-13.0E_by_chocholousek.7z': {
                    'permalink': '3330', 'sha256': 'a' * 64}},
            }), encoding='utf-8')
            with patch('chocholousek_source._download_7z', side_effect=download), \
                    patch('chocholousek_source._import_7z', return_value={
                        'imported': 2, 'skipped': 0, 'sha256': 'b' * 64}):
                result = sync_chocholousek(tmp, opener=opener, now=604802,
                                           selected_positions=['13.0E', '23.5E'])

        self.assertEqual(calls, ['3348'])
        self.assertEqual(result['downloaded'], 1)

    def test_invalid_position_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(ValueError):
            sync_chocholousek(tmp, selected_positions=['invented-orbit'])

    @unittest.skipUnless(importlib.util.find_spec('py7zr'), 'py7zr runtime dependency is not installed')
    def test_real_selected_7z_archive_download_and_import(self):
        import py7zr
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source.png'
            Image.new('RGBA', (220, 132), (20, 100, 180, 255)).save(source)
            source_bytes = source.read_bytes()
            archive = root / '13.0E.7z'
            with py7zr.SevenZipFile(archive, 'w') as seven:
                seven.write(source, 'picons/13.0E/service.png')
            contents = archive.read_bytes()
            page = CURRENT_PAGE.encode('utf-8')

            def opener(request, timeout):
                payload = page if request.full_url == INDEX_URL else contents
                return Response(request.full_url, payload)

            result = sync_chocholousek(root / 'workspace', opener=opener, now=1_800_000_000,
                                       selected_positions=['13.0E'])
            imported = list((root / 'workspace' / 'originals' / 'chocholousek').rglob('*.png'))
            imported_bytes = imported[0].read_bytes() if imported else None

        self.assertEqual(result['downloaded'], 1)
        self.assertEqual(result['imported_png'], 1)
        self.assertEqual(len(imported), 1)
        self.assertEqual(imported_bytes, source_bytes)


if __name__ == '__main__':
    unittest.main()
