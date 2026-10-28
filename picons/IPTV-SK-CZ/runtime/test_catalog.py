"""Identity regressions found while reconciling real SK/CZ station sources."""
import json
from pathlib import Path
import unittest
from urllib.parse import urlsplit,parse_qs

ROOT=Path(__file__).resolve().parent.parent
class CatalogTests(unittest.TestCase):
 def setUp(self):
  self.rows=json.loads((ROOT/'catalog/refreshed-stations.json').read_text())['stations']
 def test_service_ids_and_legacy_aliases_do_not_collide_between_programmes(self):
  refs=[r['service_reference'] for r in self.rows]
  aliases=[a for r in self.rows for a in r['reference_aliases']]
  self.assertEqual(len(refs),len(set(refs)));self.assertEqual(len(aliases),len(set(aliases)))
  self.assertFalse(set(refs)&set(aliases))
  for r in self.rows:
   parts=r['service_reference'].split(':');self.assertEqual(parts[:3],['4097','0','2'])
   self.assertTrue(any(int(x,16) for x in parts[3:]))
 def test_dvojka_cannot_be_replaced_with_radio_praha_or_prague_international(self):
  r=next(r for r in self.rows if r['country']=='CZ' and r['identity_key']=='dvojka')
  self.assertTrue('cro2' in r['stream_url'] or 'dvojka' in r['stream_url'])
  self.assertNotIn('cro7',r['stream_url'])
 def test_confirmed_retired_or_wrong_country_programmes_stay_excluded(self):
  names={r['name'] for r in self.rows}
  for name in ('N-Radio','Radio Yes','SRo 7 - Radio Pyramida','LA RADIO PLUS ANNECY','RadioParty.pl'):
   self.assertNotIn(name,names)
 def test_selected_streams_contain_no_login_or_expiring_radiojar_token(self):
  for r in self.rows:
   p=urlsplit(r['stream_url']);self.assertIn(p.scheme,('http','https'))
   self.assertIsNone(p.username)
   self.assertFalse({'rj-tok','rj-ttl'} & set(parse_qs(p.query)),r['name'])
if __name__=='__main__':unittest.main()
