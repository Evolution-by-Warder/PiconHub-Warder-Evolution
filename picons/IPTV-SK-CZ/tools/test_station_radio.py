import copy
import tempfile
import threading
import time
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from pathlib import Path
from datetime import datetime,timezone
import unittest
from unittest.mock import patch
from station_identity import name_key, one_typo, select_stations, apply_stream_checks
from global_radio import original_source_list,SOURCE_GROUP,compile_catalogue
from stream_audit import probe, audio_signature, Redirects, audit, read_sample

NAMES = {'SK':'Slovensko', 'CZ':'Čechy', 'DE':'Germany', 'SI':'Slovenia'}


def row(name, url, reference, country='SK', home='https://station.example/', protected=False):
    return dict(name=name,url=url,reference=reference,id=reference,
                countrycode=country,group=NAMES.get(country,'Nezaradené'),
                homepages=[home] if home else [],aliases=[url],protected=protected,
                healthy=True,bitrate=128,codec='MP3',genres=[],languages=[],
                source_ids=[reference],favicons=[])


class StationIdentityTests(unittest.TestCase):
    def test_primary_reference_stays_with_its_profile_across_rebuilds(self):
        source=[]
        for key,name,url in [('a','Translated','https://stream.example/programme-128.mp3'),
                             ('b','Original','https://stream.example/programme-320.mp3')]:
            item=row(name,url,key,country='DE')
            item.update(source_id='radio-browser:'+key,homepage='https://station.example/')
            item.pop('reference')
            source.append(item)
        prior=row('Original',source[0]['url'],'old',country='DE')
        prior['aliases']=[r['url'] for r in source]
        prior['known_working']=True
        # A legacy unprotected baseline reference must not displace the
        # already-published programme reference after alternate recovery.
        source[0]['reference']='legacy'
        previous=[prior]
        for _ in range(3):
            rows,_,_=compile_catalogue({'test':{'rows':source}},NAMES,'#NAME Test\n',previous)
            selected,_,_=select_stations(rows,NAMES,{r['reference'] for r in previous})
            self.assertEqual([(r['name'],r['url'],r['reference']) for r in selected],
                             [('Original',source[1]['url'],'old')])
            previous=selected
    def test_translated_classic_praha_prague_share_the_same_stream(self):
        a=row('Classic Prague','https://icecast8.play.cz/classic128.mp3','a',country='CZ',home='https://www.classicpraha.cz/',protected=True)
        b=row('Classic Praha','http://icecast8.play.cz/classic128.mp3','b',country='CZ',home='http://www.classicpraha.cz/')
        out,review,_=select_stations([a,b],NAMES)
        self.assertEqual(len(out),1);self.assertFalse(review)
        self.assertEqual(set(out[0]['name_aliases']),{'Classic Prague','Classic Praha'})
    def test_foreign_praha_prague_merge_but_local_radio_praha_is_distinct(self):
        old=row('Český rozhlas Rádio Praha','http://icecast2.play.cz/cro7-128.mp3','old',country='CZ',home='http://www.radio.cz/en',protected=True)
        current=row('Radio Prague International','https://rozhlas.stream/cro7_mp3_128.mp3','new',country='CZ',home='https://english.radio.cz/',protected=True)
        current['aliases'].append('https://rozhlas.stream/radio_prague_int_high.aac')
        regional=row('Rádio Praha','https://rozhlas.stream/radio_dab_praha_high.aac','regional',country='CZ',home='https://praha.rozhlas.cz/')
        out,review,_=select_stations([old,current,regional],NAMES)
        self.assertEqual(len(out),2);self.assertFalse(review)
        foreign=next(r for r in out if r['reference']=='new')
        self.assertIn('old',foreign['merged_references'])
        self.assertIn('Český rozhlas Rádio Praha',foreign['name_aliases'])
        self.assertTrue(any(r['name']=='Rádio Praha' for r in out))
    def test_programme_profiles_preserve_station_numbers_and_significant_query(self):
        a=row('Radio 128','https://icecast8.play.cz/radio-128.mp3','a',home='https://a.example/')
        b=row('Radio 256','https://icecast8.play.cz/radio-256.mp3','b',home='https://b.example/')
        c=row('Channel One','https://icecast8.play.cz/channel_high.aac?channel=one','c',home='https://c.example/')
        d=row('Channel Two','https://icecast8.play.cz/channel_low.aac?channel=two','d',home='https://d.example/')
        self.assertEqual(len(select_stations([a,b,c,d],NAMES)[0]),4)
    def test_generic_mounts_and_different_language_channels_do_not_merge(self):
        a=row('Red Service','https://red.example/live_high.aac','a')
        b=row('Blue Service','https://blue.example/live_low.aac','b')
        self.assertEqual(len(select_stations([a,b],NAMES)[0]),2)
    def test_network_subchannels_keep_their_entire_path_not_just_shared_leaf(self):
        rows=[row('Network '+name,'https://streams.example/'+name+'/play.mp3',name,
                  home='https://network.example/') for name in ('news','classic','jazz','rock')]
        self.assertEqual(len(select_stations(rows,NAMES)[0]),4)
        rows=[row('Network '+name,'https://streams.example/'+name+'/hls.m3u8',name,
                  home='https://network.example/') for name in ('news','classic','jazz','rock')]
        self.assertEqual(len(select_stations(rows,NAMES)[0]),4)
        a=row('English Service','https://en.stream.example/international_high.aac','a',home='https://english.station.example/')
        b=row('French Service','https://fr.stream.example/international_low.aac','b',home='https://french.station.example/')
        a['languages']=['english'];b['languages']=['french']
        self.assertEqual(len(select_stations([a,b],NAMES)[0]),2)
    def test_receiver_examples_merge_with_curated_name_url_and_reference(self):
        for names in [('Rádio Expres','RÁDIO EXPRES'), ('Info_vojna','InfoVojna'),
                      ('Rádio Mária Slovensko','Rádio Maria Slovensko'),
                      ('Rádio Melody','Radio Melody'), ('Rusyn FM','RusynFM')]:
            with self.subTest(names=names):
                a=row(names[0],'https://old.example/main','curated',protected=True)
                b=row(names[1],'https://new.example/320','extra')
                out,review,stats=select_stations([a,b],NAMES)
                self.assertEqual(len(out),1)
                for k in ('name','url','reference'):self.assertEqual(out[0][k],a[k])
                self.assertEqual(out[0]['merged_references'],['extra'])
                self.assertEqual(len(out[0]['stream_variants']),2)
                self.assertFalse(review)
    def test_directory_prefixes_do_not_create_second_station(self):
        self.assertEqual(name_key('SRo1 Rádio Slovensko'),name_key('Rádio Slovensko'))
        self.assertEqual(name_key('SRo3: Rádio Devín'),name_key('Rádio Devín'))
        self.assertEqual(name_key('Rádio Best FM'),name_key('BestFM'))
        self.assertNotEqual(name_key('SRo2 Rádio Regina Východ'),name_key('SRo2 Rádio Regina Západ'))
    def test_distinct_subchannels_and_station_numbers_are_not_merged(self):
        names=['Rádio Expres','Rádio Expres - Best Of 90s','Rádio Expres - Detské hity',
               'InfoVojna','InfoVojna 2','Classical Radio','Classicals Radio']
        rows=[row(n,'https://shared.example/'+str(i),str(i)) for i,n in enumerate(names)]
        out,review,_=select_stations(rows,NAMES)
        self.assertEqual(len(out),len(names));self.assertFalse(review)
    def test_unconfirmed_homonyms_with_distinct_homepages_are_withheld(self):
        a=row('Radio Sunshine','https://a.example/live','a',home='https://a.example/')
        b=row('Radio Sunshine','https://b.example/live','b',home='https://b.example/')
        out,review,_=select_stations([a,b],NAMES)
        self.assertFalse(out);self.assertEqual(len(review),2)
        self.assertEqual({r['review_reason'] for r in review},{'unresolved-same-name-identities'})
    def test_same_name_different_countries_remain_separate(self):
        a=row('Radio One','https://a.example/live','a')
        b=row('Radio One','https://b.example/live','b',country='DE')
        self.assertEqual(len(select_stations([a,b],NAMES)[0]),2)
    def test_unicode_identity_does_not_collapse_non_latin_stations(self):
        self.assertNotEqual(name_key('北京广播'),name_key('上海广播'))
        self.assertNotEqual(name_key('Авторадіо'),name_key('Бізнес Радіо'))
        self.assertTrue(name_key('北京广播'))
    def test_encoding_labels_merge_but_genre_and_live_labels_remain(self):
        self.assertEqual(name_key('Radio Test (AAC)'),name_key('Rádio Test [128 kbps]'))
        self.assertEqual(name_key('SomaFM Lush (128k AAC)'),name_key('SomaFM Lush (320k MP3)'))
        self.assertEqual(name_key('Radio Paradise Main Mix 128k AAC'),name_key('Radio Paradise Main Mix 192k MP3'))
        self.assertEqual(name_key('We House Radio (AAC+ High)'),name_key('We House Radio (MP3 128)'))
        self.assertNotEqual(name_key('Radio Test (Live)'),name_key('Radio Test'))
        self.assertNotEqual(name_key('Radio Test 80s'),name_key('Radio Test 90s'))
    def test_transport_variants_ignore_only_known_tracking(self):
        a=row('Rusyn FM','https://host.example/live.mp3','a',home=None,protected=True)
        b=row('RusynFM','http://host.example/live.mp3?utm_source=web','b',home=None)
        self.assertEqual(len(select_stations([a,b],NAMES)[0]),1)
        c=row('RusynFM','https://host.example/live.mp3?channel=other','c',home='https://other.example/')
        self.assertEqual(len(select_stations([a,c],NAMES)[1]),1)
    def test_only_repeated_letter_typos_with_shared_evidence_merge(self):
        a=row('Slobodný vysielač','http://host.example:8010/mp3','a',protected=True)
        b=row('Sllobodný vysielač','http://host.example:8010/aac','b',home=None)
        self.assertEqual(len(select_stations([a,b],NAMES)[0]),1)
        self.assertFalse(one_typo('classicalradio','classicalsradio'))
        self.assertFalse(one_typo('radiostation1','radiostation2'))
    def test_shared_network_homepage_does_not_merge_subchannels(self):
        a=row('Radio Test','https://shared.example/main','a')
        b=row('Radio Test Chill','https://shared.example/chill','b')
        self.assertEqual(len(select_stations([a,b],NAMES)[0]),2)
    def test_reported_broadcaster_channel_bindings_wait_for_identity_proof(self):
        a=row('Europa 2 - Fitness','https://stream.bauermedia.sk/fitness-hi.aac','a',home='https://rayo.sk/fitness')
        out,review,_=select_stations([a],NAMES)
        self.assertFalse(out)
        self.assertEqual(review[0]['review_reason'],'broadcaster-channel-identity-unconfirmed')
    def test_placeholder_entries_are_not_real_stations(self):
        out,review,_=select_stations([row('TEST-Station','https://test.example/live','a')],NAMES)
        self.assertFalse(out);self.assertEqual(review[0]['review_reason'],'placeholder-or-test-entry')
    def test_unknown_unhealthy_and_unsupported_rows_stay_in_review(self):
        rows=[row('Unknown','https://a.example/','a',country=None),
              row('No website','https://b.example/','b',home=None),
              row('Unavailable','https://c.example/','c')]
        rows[2]['healthy']=False
        before=copy.deepcopy(rows)
        out,review,stats=select_stations(rows,NAMES)
        self.assertFalse(out);self.assertEqual(len(review),3)
        self.assertEqual(stats['review_rows'],3);self.assertEqual(rows,before)
    def test_country_contradiction_is_reviewed_not_silently_moved(self):
        item=row('Radio Ekspres','https://stream.nextmedia.si/live','a',home='https://www.radioekspres.si/')
        out,review,_=select_stations([item],NAMES)
        self.assertFalse(out);self.assertEqual(review[0]['countrycode'],'SK')
        self.assertEqual(review[0]['review_reason'],'country-evidence-needs-review')
    def test_repeat_selection_is_stable_and_keeps_curated_identities(self):
        a=row('Radio','https://a.example/live','a',protected=True)
        b=row('RADIO','https://b.example/live','b')
        first=select_stations([a,b],NAMES)[0]
        again=select_stations(first,NAMES)[0]
        for key in ('name','reference','url','source_ids','aliases'):
            self.assertEqual(first[0][key],again[0][key])


class Reply:
    status=200
    headers={'Content-Type':'audio/mpeg','icy-name':'Radio Test'}
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def geturl(self):return 'https://stream.example/live'
    def read(self,n):self.bound=n;return self.body[:n]


class StreamAuditTests(unittest.TestCase):
    def test_known_station_needs_failures_on_three_dates_and_48_hours(self):
        item=row('Known station','https://known.example/live','known',country='DE')
        item['known_working']=True
        for timestamp in ('2026-11-03T12:00:00+00:00','2026-11-03T23:00:00+00:00','2026-11-04T12:00:00+00:00'):
            check={'status':'connection-unconfirmed','checked_at':timestamp}
            out,review,_=apply_stream_checks([item],{item['url']:check})
            self.assertEqual(len(out),1);self.assertFalse(review)
            item=out[0]
        self.assertEqual(item['failure_days'],['2026-11-03','2026-11-04'])
        out,review,_=apply_stream_checks([item],{item['url']:{'status':'connection-unconfirmed',
            'checked_at':'2026-11-05T12:00:00+00:00'}})
        self.assertFalse(out);self.assertEqual(review[0]['review_reason'],'persistent-unavailability')
        self.assertEqual(review[0]['reference'],'known')
    def test_recovered_known_station_resets_outage_history(self):
        item=row('Known station','https://known.example/live','known',country='DE')
        item.update(known_working=True,first_failure_at='2026-11-03T12:00:00+00:00',failure_days=['2026-11-03','2026-11-04'])
        out,review,_=apply_stream_checks([item],{item['url']:{'status':'audio-confirmed','checked_at':'2026-11-05T12:00:00+00:00'}})
        self.assertFalse(review);self.assertEqual(out[0]['failure_days'],[])
        self.assertIsNone(out[0]['first_failure_at'])
        self.assertEqual(out[0]['last_audio_at'],'2026-11-05T12:00:00+00:00')
    def test_access_restriction_does_not_complete_a_short_failure_window(self):
        item=row('Known station','https://known.example/live','known',country='DE')
        item.update(known_working=True,first_failure_at='2026-11-03T23:50:00+00:00',
                    last_failure_at='2026-11-05T00:10:00+00:00',
                    failure_days=['2026-11-03','2026-11-04','2026-11-05'])
        out,review,_=apply_stream_checks([item],{item['url']:{'status':'http-error','http_status':403,
            'checked_at':'2026-11-06T12:00:00+00:00'}})
        self.assertEqual(len(out),1);self.assertFalse(review)
    def test_deferred_or_access_restricted_probe_does_not_age_a_known_outage(self):
        item=row('Known station','https://known.example/live','known',country='DE');item['known_working']=True
        item.update(first_failure_at=None,last_failure_at=None,failure_days=[])
        for check in ({'status':'host-check-unconfirmed','requested':False,'checked_at':'2026-11-05T12:00:00+00:00'},
                      {'status':'http-error','http_status':403,'checked_at':'2026-11-05T12:00:00+00:00'}):
            out,review,_=apply_stream_checks([item],{item['url']:check})
            self.assertFalse(review);self.assertEqual(out[0]['failure_days'],[])
    def test_known_status_does_not_keep_a_wrong_station_redirect(self):
        item=row('Known station','https://known.example/live','known',country='DE');item['known_working']=True
        other=row('Other programme','https://other.example/live','other',country='DE')
        out,review,_=apply_stream_checks([item,other],{
            item['url']:{'status':'audio-confirmed','final_url':other['url']},other['url']:{'status':'audio-confirmed'}})
        self.assertEqual([r['reference'] for r in out],['other'])
        self.assertEqual(review[0]['review_reason'],'redirects-to-another-station')
    def test_known_source_failure_does_not_hide_the_station_before_live_check(self):
        item=row('Known station','https://known.example/live','known',country='DE')
        item.update(known_working=True,healthy=False)
        out,review,_=select_stations([item],NAMES)
        self.assertEqual(len(out),1);self.assertFalse(review)
    def test_owner_confirmed_slovak_originals_survive_outage_without_url_rewrite(self):
        for check in ({'status':'connection-unconfirmed'},
                      {'status':'http-error','http_status':503},
                      {'status':'http-error','http_status':404,'confirmed_failure':True},
                      {'status':'audio-confirmed','final_url':'https://other.example/live'}):
            with self.subTest(check=check):
                item=row('Original SK','http://original.example/live','original',protected=True)
                item['stream_variants']=[{'url':'https://alternative.example/live'}]
                out,review,stats=apply_stream_checks([item],{item['url']:check,
                    'https://alternative.example/live':{'status':'audio-confirmed'}})
                self.assertEqual(len(out),1);self.assertFalse(review)
                for field in ('name','url','reference'):self.assertEqual(out[0][field],item[field])
                self.assertEqual(stats['original_slovak_stations_preserved'],1)
    def test_real_socket_deadline_interrupts_dripping_http_headers(self):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                try:
                    if self.path=='/slow':
                        self.connection.sendall(b'HTTP/1.1 200 OK\r\nContent-Type: audio/mpeg\r\nX-Drip: ')
                        for unused in range(30):
                            self.connection.sendall(b'x');time.sleep(.1)
                    else:
                        self.send_response(200);self.send_header('Content-Type','audio/mpeg')
                        self.end_headers();self.wfile.write(b'ID3'+b'x'*128)
                except OSError:pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':.01},daemon=True)
        thread.start()
        try:
            # Only this controlled loopback fixture bypasses the public-URL check.
            with patch('stream_audit.url_key',side_effect=lambda url:url):
                base='http://127.0.0.1:'+str(server.server_port)
                started=time.monotonic()
                good=probe({'url':base+'/good'},timeout=.3)
                slow=probe({'url':base+'/slow'},timeout=.3)
            self.assertEqual(good['status'],'audio-confirmed')
            self.assertNotEqual(slow['status'],'audio-confirmed')
            self.assertLess(time.monotonic()-started,1.5)
        finally:
            server.shutdown();server.server_close()
    def test_expired_audit_window_defers_without_claiming_an_audio_check(self):
        rows=[row('Radio A','https://a.example/live','a')]
        with tempfile.TemporaryDirectory() as directory,patch('stream_audit.probe') as network:
            checks=audit(rows,Path(directory)/'audit.json.gz',workers=1,timeout=1,budget_seconds=0)
        network.assert_not_called()
        self.assertEqual(checks[rows[0]['url']]['status'],'audit-budget-unconfirmed')
        self.assertFalse(checks[rows[0]['url']]['requested'])
    def test_dripping_stream_does_not_wait_for_a_full_buffer(self):
        class Drip:
            def read(self,n):raise AssertionError('A full-buffer read would stall')
            def read1(self,n):return b'x'
        with patch('stream_audit.time.monotonic',side_effect=[0,0,1,2,8]):
            self.assertEqual(read_sample(Drip(),5),b'xxx')
    def test_fresh_check_is_reused_without_turning_uncertainty_into_success(self):
        rows=[row('Radio A','https://a.example/live','a')]
        result={'url':rows[0]['url'],'status':'connection-unconfirmed',
                'checked_at':datetime.now(timezone.utc).isoformat()}
        with tempfile.TemporaryDirectory() as directory,patch('stream_audit.probe',return_value=result) as network:
            target=Path(directory)/'audit.json.gz'
            audit(rows,target,workers=1,timeout=1)
            checks=audit(rows,target,workers=1,timeout=1)
            self.assertEqual(network.call_count,1)
            self.assertEqual(checks[rows[0]['url']]['status'],'connection-unconfirmed')
            audit(rows,target,workers=1,timeout=1,max_age=0)
            self.assertEqual(network.call_count,2)
    def test_unreachable_host_shortcut_never_claims_individual_station_failure(self):
        rows=[row('Radio '+str(i),'https://same.example/'+str(i),str(i)) for i in range(10)]
        def unavailable(r,timeout):
            return {'url':r['url'],'status':'connection-unconfirmed','error':'timeout',
                    'checked_at':'2026-11-03T00:00:00+00:00'}
        with tempfile.TemporaryDirectory() as directory,patch('stream_audit.probe',side_effect=unavailable) as network:
            checks=audit(rows,Path(directory)/'audit.json.gz',workers=1,timeout=1)
        self.assertEqual(network.call_count,4)
        self.assertEqual(sum(r['status']=='host-check-unconfirmed' for r in checks.values()),6)
        self.assertFalse(any(r.get('confirmed_failure') for r in checks.values()))
    def test_timeout_is_retained_for_review_not_claimed_dead_or_playable(self):
        rows=[row('Radio A','https://a.example/live','a'),row('Radio B','https://b.example/live','b')]
        checks={rows[0]['url']:{'status':'connection-unconfirmed'},
                rows[1]['url']:{'status':'http-error','http_status':404,'confirmed_failure':True}}
        out,review,stats=apply_stream_checks(rows,checks)
        self.assertFalse(out)
        self.assertEqual([r['reference'] for r in review],['a','b'])
        self.assertEqual(review[0]['review_reason'],'live-audio-not-confirmed')
        self.assertEqual(review[1]['review_reason'],'confirmed-unavailable-or-non-audio')
    def test_other_station_redirect_cannot_masquerade_as_original(self):
        a=row('Europa 2 Fitness','https://a.example/live','a')
        b=row('Rádio Melody','https://b.example/live','b')
        checks={a['url']:{'status':'audio-confirmed','final_url':b['url']},b['url']:{'status':'audio-confirmed'}}
        out,review,_=apply_stream_checks([a,b],checks)
        self.assertEqual([r['reference'] for r in out],['b'])
        self.assertEqual(review[0]['review_reason'],'redirects-to-another-station')
    def test_verified_alternative_retains_identity(self):
        a=row('Radio A','https://a.example/old','a')
        a['stream_variants']=[{'url':'https://a.example/new'}]
        checks={a['url']:{'status':'http-error','confirmed_failure':True},
                'https://a.example/new':{'status':'audio-confirmed'}}
        out,review,_=apply_stream_checks([a],checks)
        self.assertFalse(review);self.assertEqual(out[0]['url'],'https://a.example/new')
        self.assertEqual(out[0]['reference'],'a')
    def test_real_audio_header_and_bounded_sample(self):
        response=Reply();response.body=b'ID3'+b'x'*2000
        with patch('stream_audit.build_opener') as opener:
            opener.return_value.open.return_value=response
            result=probe(row('Radio Test','https://stream.example/live','a'))
        self.assertEqual(result['status'],'audio-confirmed');self.assertEqual(response.bound,1024)
    def test_html_status_200_never_passes_as_audio(self):
        response=Reply();response.body=b'<!doctype html>Not found';response.headers={'Content-Type':'text/html'}
        with patch('stream_audit.build_opener') as opener:
            opener.return_value.open.return_value=response
            result=probe(row('Radio Test','https://stream.example/live','a'))
        self.assertEqual(result['status'],'non-audio-or-unrecognised')
    def test_timeout_is_unconfirmed_not_dead(self):
        with patch('stream_audit.build_opener') as opener:
            opener.return_value.open.side_effect=TimeoutError('temporary timeout')
            result=probe(row('Radio Test','https://stream.example/live','a'))
        self.assertEqual(result['status'],'connection-unconfirmed')
    def test_private_redirect_is_rejected(self):
        with self.assertRaises(ValueError):
            Redirects().redirect_request(None,None,302,'',{},'http://127.0.0.1/audio')


class OriginalSourceTests(unittest.TestCase):
    def test_original_order_names_urls_and_separate_identity(self):
        lines=['#NAME Original\n']
        expected=[]
        for i in range(1001):
            reference=f'4097:0:2:{i+1:X}:1:1:0:0:0:0'
            name=f'Original {1001-i}'
            url=f'https://stream.example/{i}'
            lines.append('#SERVICE '+reference+':'+url.replace(':','%3a')+'\n#DESCRIPTION '+name+'\n')
            expected.append((name,url))
        source=''.join(lines)
        rows=original_source_list(source,{'4097:0:2:1:1:1:0:0:0:0'})
        self.assertEqual([(r['name'],r['url']) for r in rows],expected)
        self.assertEqual({r['group'] for r in rows},{SOURCE_GROUP})
        self.assertEqual(len({r['reference'] for r in rows}),1001)
        self.assertEqual(rows,original_source_list(source,set()))
    def test_empty_source_view_does_not_replace_existing_data(self):
        with self.assertRaises(ValueError):original_source_list('#NAME Empty\n',set())


if __name__=='__main__':unittest.main()
