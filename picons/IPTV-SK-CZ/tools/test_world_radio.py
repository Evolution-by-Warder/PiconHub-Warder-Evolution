"""Regression checks for the unattended world-radio merger."""
import unittest
from update_world_radio import build, parse


def marker(name):
    return '#SERVICE 1:64:D:0:0:0:0:0:0:0:\n#DESCRIPTION '+name+'\n'


def stream(name, url, ref='4097:0:2:0:0:0:0:0:0:0'):
    return '#SERVICE '+ref+':'+url.replace(':','%3a')+'\n#DESCRIPTION '+name+'\n'


OWN = ('#NAME Warder IPTV rádiá SK/CZ\n'+marker('Slovensko')+
       stream('Owned SK','https://sk.test/live','4097:0:2:1:2:EC:0:0:0:0')+
       marker('Čechy')+stream('Owned CZ','https://cz.test/live','4097:0:2:3:4:EC:0:0:0:0'))
SOURCE = ('#NAME HDF Radio Streams\n'+marker('Update by www.hdfreaks.cc')+
          marker('Germany')+stream('Foreign','https://de.test/live')+
          marker('Slowakei')+stream('Old SK','https://old-sk.test/live')+
          marker('Tschechien')+stream('Old CZ','https://old-cz.test/live'))


class MergerTests(unittest.TestCase):
    def test_owned_body_exactly_preserved_at_top(self):
        output, report = build(SOURCE,OWN,'')
        self.assertTrue(output.split('\n',1)[1].startswith(OWN.split('\n',1)[1]))
        self.assertEqual(report['owned_stations'],{'SK':1,'CZ':1})
        self.assertNotIn('Old SK',output)
        self.assertNotIn('Old CZ',output)
        self.assertNotIn('hdf',output.lower())

    def test_repeated_runs_are_identical(self):
        first,r1=build(SOURCE,OWN,'')
        second,r2=build(SOURCE,OWN,first)
        self.assertEqual(first,second)
        self.assertEqual(r1,r2)

    def test_existing_foreign_reference_survives_name_change(self):
        previous='#NAME Warder\n'+stream('Former name','https://de.test/live','4097:0:2:99:88:EC:0:0:0:0')
        result,_=build(SOURCE,OWN,previous)
        self.assertIn('4097:0:2:99:88:EC:0:0:0:0:',result)

    def test_source_audio_types_normalized(self):
        output,_=build(SOURCE.replace('4097:0:2:0:','4097:0:1:0:'),OWN,'')
        self.assertTrue(all(e.reference.split(':')[2]=='2' for e in parse(output) if e.url))

    def test_loopback_subheading_is_not_a_station(self):
        source=SOURCE.replace(marker('Germany'),marker('Germany')+stream('--- Group ---','https://127.0.0.1/hdfradio'))
        output,report=build(source,OWN,'')
        self.assertIn(marker('--- Group ---').replace('1:64:D:','1:64:2:'),output)
        self.assertNotIn('127.0.0.1',output)
        self.assertEqual(report['total_stations'],3)

    def test_missing_country_fails_closed(self):
        with self.assertRaises(ValueError):build(SOURCE.replace('Tschechien','Unexpected'),OWN,'')

    def test_truncated_source_fails_closed(self):
        with self.assertRaises(ValueError):build(SOURCE+'#SERVICE 4097:0:2:',OWN,'')

    def test_owned_url_excluded_in_foreign_section(self):
        source=SOURCE.replace(marker('Germany'),marker('Germany')+stream('Foreign label','https://sk.test/live'))
        result,report=build(source,OWN,'')
        self.assertNotIn('Foreign label',result)
        self.assertEqual(report['processing']['owned_url_duplicates_removed'],1)

    def test_duplicate_stream_removed(self):
        result,report=build(SOURCE.replace(marker('Germany'),marker('Germany')+stream('Foreign','https://de.test/live')),OWN,'')
        self.assertEqual(report['foreign_stations'],1)
        self.assertEqual(report['processing']['exact_duplicates_removed'],1)

    def test_distinct_queries_preserved(self):
        source=SOURCE.replace(marker('Germany'),marker('Germany')+stream('Other','https://de.test/live?station=2'))
        result,report=build(source,OWN,'')
        self.assertEqual(report['foreign_stations'],2)
        self.assertIn('?station=2',result)

    def test_source_code_is_never_interpreted(self):
        with self.assertRaises(ValueError):parse('#NAME Bad\n<script>alert(1)</script>')

    def test_removed_foreign_station_disappears(self):
        first,_=build(SOURCE.replace(marker('Germany'),marker('Germany')+stream('Gone','https://gone.test')),OWN,'')
        second,_=build(SOURCE,OWN,first)
        self.assertNotIn('https%3a//gone.test',second)

    def test_known_editorial_annotation_cleaned(self):
        output,_=build(SOURCE.replace('https%3a//de.test/live','https%3a//de.test/live : K.S.23102026'),OWN,'')
        self.assertNotIn('K.S.',output)


if __name__=='__main__':unittest.main()
