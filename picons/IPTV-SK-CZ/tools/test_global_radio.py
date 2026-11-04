import unittest
from global_radio import url_key, source_rows, compile_catalogue, baseline_rows, UNKNOWN
from update_world_radio import parse

OWNED='''#NAME Owned
#SERVICE 1:64:2:0:0:0:0:0:0:0:
#DESCRIPTION Slovensko
#SERVICE 4097:0:2:1:1:1:0:0:0:0:https%3a//owned.test/sk
#DESCRIPTION Owned SK
#SERVICE 1:64:2:0:0:0:0:0:0:0:
#DESCRIPTION Čechy
#SERVICE 4097:0:2:2:2:2:0:0:0:0:https%3a//owned.test/cz
#DESCRIPTION Owned CZ
'''
NAMES={'SK':'Slovensko','CZ':'Čechy','DE':'Germany','US':'United States','FR':'France'}


def record(key,url,country='DE',healthy=True,aliases=None,**extra):
    return dict(source_id=key,name=key,url=url,aliases=aliases or [url],countrycode=country,
                healthy=healthy,genres=[],languages=[],bitrate=128,codec='MP3',**extra)


def sources(*rows):
    return {'warder':{'rows':baseline_rows(OWNED,OWNED,NAMES)},'extra':{'rows':list(rows)}}

class GlobalRadioTests(unittest.TestCase):
    def test_owner_removed_station_is_not_revived_from_a_cached_master(self):
        dead=record('warder:removed','http://sc.ipip.cz:8004/;',country='CZ',
                    reference='4097:0:2:B929:9DC5:EC:0:0:0:0')
        dead['name']='Star The Mix'
        reused=record('rb:reused','http://sc.ipip.cz:8004/;',country='CZ')
        reused['name']='Radio Diana'
        rows,bouquet,_=compile_catalogue(sources(dead,reused),NAMES,OWNED)
        self.assertNotIn('Star The Mix',bouquet)
        self.assertTrue(any(r['name']=='Radio Diana' for r in rows))
        incoming={'stationuuid':'removed','name':'Star The Mix','url':'http://sc.ipip.cz:8004/;',
                  'countrycode':'CZ','lastcheckok':1}
        imported,counts=source_rows('radio-browser',[incoming],NAMES)
        self.assertEqual(imported,[])
        self.assertEqual(counts['owner_removed_stations'],1)

    def test_aliases_are_conservative(self):
        self.assertEqual(url_key('http://EXAMPLE.com:80'),url_key('http://example.com/'))
        self.assertNotEqual(url_key('http://a.test/128'),url_key('https://a.test/128'))
        self.assertNotEqual(url_key('https://a.test/a/'),url_key('https://a.test/a'))
        self.assertNotEqual(url_key('https://a.test/a?channel=1'),url_key('https://a.test/a?channel=2'))
        self.assertEqual(url_key('http://stream.laut.fm/antenne_b'),url_key('https://antenneb.stream.laut.fm/antenne_b'))
    def test_private_and_credential_urls_rejected(self):
        for url in ('http://127.0.0.1/a','http://192.168.1.1/a','http://[::1]/a','http://localhost/a','https://u:p@a.test/a','ftp://a.test/a','https://a.test/a b'):
            with self.subTest(url=url), self.assertRaises(ValueError):url_key(url)
    def test_owned_station_content_and_references_preserved(self):
        rows,bouquet,stats=compile_catalogue(sources(record('rb:a','https://new.test/a')),NAMES,OWNED)
        self.assertEqual(len([e for e in parse(bouquet) if e.url is None]),3)
        for owned in [e for e in parse(OWNED) if e.url]:
            self.assertEqual(next(r for r in rows if r['reference']==owned.reference)['url'],owned.url)
        self.assertEqual(len({r['reference'] for r in rows}),len(rows))
    def test_dedup_resolved_url_and_metadata_union(self):
        a=record('rb:a','https://play.test/a',aliases=['https://play.test/a','https://stream.test/a']);a['genres']=['rock']
        b=record('laut.fm:b','https://stream.test/a');b['languages']=['german']
        rows,_,stats=compile_catalogue(sources(a,b),NAMES,OWNED)
        self.assertEqual(len(rows),3)
        item=next(r for r in rows if not r['protected'])
        self.assertEqual(item['genres'],['rock']);self.assertEqual(item['languages'],['german'])
        self.assertEqual(len(item['source_ids']),2)
        self.assertEqual(stats['duplicate_observations_merged'],1)
    def test_same_name_different_streams_retained(self):
        a=record('rb:a','https://a.test/128');b=record('rb:b','https://a.test/320')
        a['name']=b['name']='Same station'
        rows,_,_=compile_catalogue(sources(a,b),NAMES,OWNED)
        self.assertEqual(len(rows),4)
    def test_conflicting_country_not_guessed(self):
        rows,_,stats=compile_catalogue(sources(record('rb:a','https://a.test/a','DE'),record('rb:b','https://a.test/a','FR')),NAMES,OWNED)
        item=next(r for r in rows if not r['protected'])
        self.assertIsNone(item['countrycode']);self.assertEqual(item['group'],UNKNOWN)
        self.assertEqual(stats['country_conflicts'],1)
    def test_owned_country_wins_over_conflict(self):
        rows,_,_=compile_catalogue(sources(record('rb:a','https://owned.test/sk','FR')),NAMES,OWNED)
        self.assertEqual(len(rows),2)
        self.assertEqual(next(r for r in rows if r['name']=='Owned SK')['countrycode'],'SK')
    def test_country_order_and_additional_sk_cz(self):
        rows,bouquet,_=compile_catalogue(sources(record('rb:f','https://f.test/a','FR'),record('rb:s','https://s.test/a','SK'),record('rb:n','https://n.test/a',None),record('rb:d','https://d.test/a','DE')),NAMES,OWNED)
        self.assertEqual(list(dict.fromkeys(r['group'] for r in rows)),['Slovensko','Čechy','France','Germany',UNKNOWN])
        self.assertEqual(len([e for e in parse(bouquet) if e.url]),len(rows))
    def test_identity_survives_changed_url_by_source_identity(self):
        before,_,_=compile_catalogue(sources(record('rb:a','https://old.test/a')),NAMES,OWNED)
        after,_,_=compile_catalogue(sources(record('rb:a','https://new.test/a')),NAMES,OWNED,before)
        self.assertEqual(next(r for r in before if not r['protected'])['id'],next(r for r in after if not r['protected'])['id'])
    def test_idempotent_output(self):
        src=sources(record('rb:a','https://a.test/a'),record('rb:b','https://b.test/a','US'))
        rows,bouquet,stats=compile_catalogue(src,NAMES,OWNED)
        again,bouquet2,stats2=compile_catalogue(src,NAMES,OWNED,rows)
        self.assertEqual(rows,again);self.assertEqual(bouquet,bouquet2)
    def test_unhealthy_new_excluded_existing_kept(self):
        src=sources(record('rb:a','https://a.test/a'))
        old,_,_=compile_catalogue(src,NAMES,OWNED)
        src['extra']['rows'][0]['healthy']=False
        fresh,_,_=compile_catalogue(src,NAMES,OWNED)
        retained,_,_=compile_catalogue(src,NAMES,OWNED,old)
        self.assertEqual(len(fresh),2);self.assertEqual(len(retained),3)
    def test_duplicate_baseline_references_collapsed_but_owned_protected(self):
        src=sources(record('warder:a','https://same.test/a',reference='4097:0:2:A:A:1:0:0:0:0'),record('warder:b','https://same.test/a',reference='4097:0:2:B:B:1:0:0:0:0'))
        rows,_,_=compile_catalogue(src,NAMES,OWNED)
        self.assertEqual(len(rows),3)
    def test_source_fields_retained_no_country_from_city(self):
        rows,rejected=source_rows('laut.fm',[{'name':'example','display_name':'Radio','stream_url':'https://example.stream.laut.fm/example','active':True,'genres':['Rock','POP'],'location':'Berlin'}],NAMES)
        self.assertEqual(rows[0]['genres'],['pop','rock']);self.assertIsNone(rows[0]['countrycode'])
        self.assertEqual(rows[0]['location'],'Berlin')
    def test_unhealthy_resolved_alias_not_trusted(self):
        rows,_=source_rows('radio-browser',[{'stationuuid':'a','name':'Radio','url':'https://a.test/a','url_resolved':'https://stale.test/a','countrycode':'DE','lastcheckok':0}],NAMES)
        self.assertEqual(rows[0]['aliases'],['https://a.test/a'])

if __name__=='__main__':unittest.main()
