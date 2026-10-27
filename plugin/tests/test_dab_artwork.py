"""Inspect committed artwork bytes without graphics libraries on receivers/CI."""
import csv,hashlib,json,pathlib,struct,unittest,zlib
ROOT=pathlib.Path(__file__).parents[2]
DAB=ROOT/'picons/DAB'

class AuthenticArtworkTests(unittest.TestCase):
    def setUp(self):
        self.catalog=json.loads((DAB/'catalog/authentic-preview.json').read_text())
        self.mapping=list(csv.DictReader((DAB/'catalog/DAB_radio_picon_mapping.csv').open(encoding='utf-8-sig')))
    def test_exact_receiver_identities_and_regional_labels_are_retained(self):
        names={r['picon_filename']:r['station'] for r in self.mapping}
        self.assertEqual(len(names),82);self.assertEqual(len(set(names.values())),52)
        self.assertEqual(self.catalog['reference_count'],80)
        for r in self.catalog['records']:self.assertEqual(names[r['picon_filename']],r['station'])
        self.assertEqual({names[n] for n in set(names)-{r['picon_filename'] for r in self.catalog['records']}},{'ASA DE'})
    def test_all_png_hashes_crc_dimensions_and_decoded_sizes_are_valid(self):
        checked=set()
        for row in self.catalog['records']:
            self.assertFalse(row['approved_master_v9'])
            for style,digest in row['sha256'].items():
                p=DAB/'preview/authentic'/style/row['picon_filename'];raw=p.read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),digest)
                if digest in checked:continue
                checked.add(digest);self.assertEqual(raw[:8],b'\x89PNG\r\n\x1a\n');offset=8;pixels=b'';end=False
                while offset<len(raw):
                    size=struct.unpack('>I',raw[offset:offset+4])[0];tag=raw[offset+4:offset+8];data=raw[offset+8:offset+8+size];crc=struct.unpack('>I',raw[offset+8+size:offset+12+size])[0];self.assertEqual(zlib.crc32(tag+data)&0xffffffff,crc)
                    if tag==b'IHDR':self.assertEqual(struct.unpack('>IIBBBBB',data),(220,132,8,6,0,0,0))
                    if tag==b'IDAT':pixels+=data
                    if tag==b'IEND':end=True
                    offset+=12+size
                self.assertTrue(end);self.assertEqual(offset,len(raw));self.assertEqual(len(zlib.decompress(pixels)),132*(1+220*4))
    def test_templates_and_all_selected_source_files_match_pinned_hashes(self):
        config=json.loads((DAB/'catalog/artwork.json').read_text())
        for style,digest in config['master_sha256'].items():self.assertEqual(hashlib.sha256((ROOT/'plugin/artwork/templates/picons'/(style+'-sablona.png')).read_bytes()).hexdigest(),digest)
        for spec in config['stations'].values():
            for style,path in spec['variants'].items():self.assertEqual(hashlib.sha256((DAB/path).read_bytes()).hexdigest(),spec['source_sha256'][style])
    def test_review_assets_are_not_in_verified_distribution(self):
        self.assertFalse(list((DAB/'verified').glob('*.png')))
        self.assertNotEqual(self.catalog['status'],'verified')
