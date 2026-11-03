"""Optional provider metadata must preserve curated rows and receiver identities."""
import json
import unittest
from unittest.mock import patch
from laut_radio import Station, download, station_key, stations, MAX_RESPONSE
from update_world_radio import build, parse, supplement_laut
from test_world_radio import OWN, SOURCE, marker, stream


def row(name, **changes):
    value = {'name': name, 'display_name': name.title(), 'active': True,
             'stream_url': 'https://' + name + '.stream.laut.fm/' + name,
             'location': 'Neon City', 'lat': 14.3608, 'lng': 120.933}
    value.update(changes)
    return value


class Response:
    def __init__(self, value, url='https://api.laut.fm/stations'):
        self.raw = json.dumps(value).encode(); self.url = url
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self, limit): return self.raw[:limit]


class LautTests(unittest.TestCase):
    def source(self):
        return SOURCE.replace(marker('Germany'), marker('Germany') +
            stream('Existing name', 'http://stream.laut.fm/known', '4097:0:2:99:88:ED:0:0:0:0'))

    def test_provider_aliases_deduplicate_without_accepting_other_hosts_or_injection(self):
        for url in ('http://stream.laut.fm/known', 'https://known.stream.laut.fm/known?ref=old',
                    'https://alias-host.stream.laut.fm/known'):
            self.assertEqual(station_key(url), 'known')
        self.assertEqual(station_key('https://antenneb.stream.laut.fm/antenne_b'),'antenne_b')
        for url in ('https://api.laut.fm/station/known', 'https://laut.fm/known',
                    'https://a.b.stream.laut.fm/known', 'https://stream.laut.fm.evil/known',
                    'https://user:pass@stream.laut.fm/known', 'https://stream.laut.fm/known?x=\nINJECT',
                    'file:///tmp/known', None):
            self.assertIsNone(station_key(url))

    def test_known_metadata_and_bounded_discovery_accept_real_api_shapes(self):
        calls = []
        def opener(request, timeout):
            calls.append(request.full_url)
            self.assertGreater(timeout, 0); self.assertLessEqual(timeout, 15)
            if '?' in request.full_url:
                return Response({'total':16908,'offset':0,'limit':3,'next_offset':3,
                                 'items':[row('new'),row('known'),row('inactive',active=False)]})
            return Response([row('known',display_name='Official name')])
        result, report = download({'known'},3,opener=opener)
        self.assertEqual(set(result), {'known','new'})
        self.assertEqual(result['known'].display_name, 'Official name')
        self.assertEqual(len(calls),2)
        self.assertEqual(report['discovery_candidates'],1)
        self.assertFalse(report['country_filter'])

    def test_requested_batches_do_not_accept_unrequested_station_substitution(self):
        with self.assertRaises(ValueError):
            download({'known'},0,opener=lambda *a,**k:Response([row('other')]))
        with self.assertRaises(ValueError):
            stations([row('known',stream_url='https://other.stream.laut.fm/other')])

    def test_invalid_pages_overlarge_responses_and_https_downgrades_fail_closed(self):
        for value in ([], {'total':1000,'offset':1,'items':[row('one')]},
                      {'total':0,'offset':0,'items':[row('one')]}):
            with self.assertRaises(ValueError):
                download(set(),1,opener=lambda *a,**k:Response(value))
        class Large(Response):
            def read(self, limit):
                self.asserted = limit
                return b'x'*limit
        with self.assertRaises(ValueError):
            download(set(),1,opener=lambda *a,**k:Large(None))
        with self.assertRaises(ValueError):
            download({'known'},0,opener=lambda *a,**k:Response([row('known')],url='http://api.laut.fm/stations'))

    def test_bad_labels_conflicts_and_inactive_rows_do_not_leak_into_output(self):
        self.assertEqual(stations([row('inactive',active=False)]),{})
        for rows in ([row('one',display_name='bad\nlabel')],
                     [row('one'),row('one',display_name='Conflicting')], [None]):
            with self.assertRaises(ValueError):stations(rows)

    def test_owned_rows_and_existing_country_references_are_unchanged(self):
        owned = OWN.replace('https%3a//sk.test/live','http%3a//stream.laut.fm/ownedsk')
        base,_=build(self.source(),owned,'')
        result, report = supplement_laut(base,owned,'',stations([row('ownedsk'),row('known')]))
        self.assertTrue(result.split('\n',1)[1].startswith(owned.split('\n',1)[1]))
        parsed=parse(result)
        existing=next(e for e in parsed if e.name=='Existing name')
        before=next(e for e in parse(base) if e.name=='Existing name')
        self.assertEqual(existing.reference,before.reference)
        self.assertEqual(existing.url,'https://known.stream.laut.fm/known')
        self.assertEqual(report['streams_updated'],1)
        self.assertEqual(sum(e.url is None and e.name=='Germany' for e in parsed),1)

    def test_new_stations_have_neutral_provider_group_without_country_guesses(self):
        base,_=build(self.source(),OWN,'')
        result,report=supplement_laut(base,OWN,'',stations([row('known'),row('new',location='Germany')]))
        self.assertEqual(report['new_stations'],1)
        self.assertIn('#DESCRIPTION laut.fm\n',result)
        self.assertIn('#DESCRIPTION laut.fm - New\n',result)
        self.assertEqual(sum(e.url is None and e.name=='Germany' for e in parse(result)),1)
        self.assertEqual(sum(station_key(e.url)=='known' for e in parse(result) if e.url),1)

    def test_repeated_primary_merge_and_api_outage_keep_added_ids_and_last_good_urls(self):
        base,_=build(self.source(),OWN,'')
        first,_=supplement_laut(base,OWN,'',stations([row('known'),row('new')]))
        rebuilt,_=build(self.source(),OWN,first)
        second,_=supplement_laut(rebuilt,OWN,first,stations([row('known'),row('new')]))
        self.assertEqual(first,second)
        fallback,_=supplement_laut(rebuilt,OWN,first,{})
        self.assertEqual(first,fallback)

    def test_removed_owned_station_is_not_reimported_from_provider(self):
        previous=OWN.replace('https%3a//sk.test/live','https%3a//stream.laut.fm/former-owned')
        base,_=build(SOURCE,OWN,'')
        result,_=supplement_laut(base,OWN,previous,stations([row('former-owned')]))
        self.assertNotIn('former-owned',result)

    def test_file_limit_prevents_publishing_a_catalogue_receivers_cannot_read(self):
        base,_=build(SOURCE,OWN,'')
        with patch('update_world_radio.MAX_BYTES',100),self.assertRaises(ValueError):
            supplement_laut(base,OWN,'',stations([row('new')]))


if __name__=='__main__':unittest.main()
