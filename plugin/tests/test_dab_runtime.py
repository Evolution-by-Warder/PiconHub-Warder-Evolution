import types
import copy,hashlib,io,json,pathlib,tempfile,threading,unittest,zipfile
from unittest.mock import patch
from test_warder_interface import engine,model,sync,png,prefs,fixture

dab=engine.dab
NAME='4115_0_2_1019_C98_3_EB0000_1019_100D_10BC.png'
OTHER='4115_0_2_1019_C98_3_EB0000_1019_10C4_10BC.png'
URL='https://raw.githubusercontent.com/'+dab.REPOSITORY+'/'+'a'*40+'/picons/DAB/packages/transparent.zip'

def source():
    raw=png();out=io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:z.writestr(NAME,raw)
    blob=out.getvalue();package={'url':URL,'bytes':len(blob),'sha256':hashlib.sha256(blob).hexdigest(),'resolution':'220x132','files':{NAME:hashlib.sha256(raw).hexdigest()}}
    document={'schema':1,'status':'verified','packages':{s:dict(package) for s in ['transparent','white','black']}}
    def opener(url):return io.BytesIO(json.dumps(document).encode() if url==dab.MANIFEST_URL else blob)
    return document,blob,opener

class DABSelectionTests(unittest.TestCase):
    def profile(self,selection='DAB',resolution='220x132',method='all_inc'):
        setting=lambda v:types.SimpleNamespace(value=v)
        return types.SimpleNamespace(warder_selectors=setting(selection),resolution=setting(resolution),method=setting(method),background=setting('transparent'),picon_folder=setting('user_defined'),picon_folder_user=setting('/tmp/picon'),sats=setting(''))
    def test_dab_only_does_not_require_a_fake_satellite(self):
        p=model.profile_preferences(self.profile());self.assertTrue(p['dab_only']);self.assertEqual(p['positions'],[])
    def test_profile_position_casing_does_not_hide_matching_dab_services(self):
        p=model.profile_preferences(self.profile("235E DAB"))
        document=source()[0]
        planned=dab.plan(document,p,"/tmp")
        self.assertIsNotNone(planned)
        self.assertEqual(planned[0]["dab_names"],{NAME})

    def test_mixed_selection_keeps_native_position_bindings(self):
        p=model.profile_preferences(self.profile('235E DAB'));self.assertFalse(p['dab_only']);self.assertTrue(p['include_dab']);self.assertEqual(p['positions'],['23.5E'])
    def test_dab_rejects_unsupported_resolution_and_tv_only_mode(self):
        for p in [self.profile(resolution='50x30'),self.profile(method='sync_tv')]:
            with self.assertRaises(ValueError):model.profile_preferences(p)
    def test_satellite_only_does_not_enable_dab_fetching(self):
        p=model.profile_preferences(self.profile('235E'));self.assertFalse(p['include_dab']);self.assertFalse(p['dab_only'])

class DABRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=pathlib.Path(self.tmp.name);self.target=self.root/'picon';self.target.mkdir();self.box=self.root/'enigma2';self.box.mkdir()
        self.prefs=prefs(self.target,sync.UPDATE_MODE_SYNC_TV_RADIO);self.prefs.update(dab_only=True,include_dab=True)
        self.bouquet(NAME)
    def bouquet(self,name):
        (self.box/'userbouquet.dab.radio').write_text('#SERVICE '+name[:-4].replace('_',':')+':http%3a//private.invalid/secret\n#DESCRIPTION Test\n')
    def test_whole_satellite_package_installs_native_and_dab_radio_together(self):
        tv="1_0_1_1_1_1_EB0000_0_0_0.png"
        d,b,url,op=fixture({tv:png(),NAME:png()})
        result=self.runner(op).run([prefs(self.target,sync.UPDATE_MODE_INCREMENTAL)])
        self.assertEqual(result,{"added":2,"changed":0,"removed":0})
        self.assertEqual((self.target/NAME).read_bytes(),png())

    def test_published_catalog_installs_without_overriding_its_approval_status(self):
        root=pathlib.Path(__file__).parents[2]/'picons/DAB'
        document=(root/'catalog/release.json').read_bytes()
        parsed=json.loads(document)
        self.assertEqual(parsed['status'],'verified')
        package=parsed['packages']['white']
        def opener(url):
            if url==dab.MANIFEST_URL:return io.BytesIO(document)
            self.assertEqual(url,package['url'])
            return (root/'packages'/url.rsplit('/',1)[1]).open('rb')
        (self.target/OTHER).write_bytes(b'preserved')
        p=dict(self.prefs,style='white',update_mode=sync.UPDATE_MODE_INCREMENTAL)
        result=self.runner(opener).run([p])
        self.assertEqual(result,{'added':82,'changed':0,'removed':0})
        self.assertEqual((self.target/OTHER).read_bytes(),b'preserved')
    def test_real_candidate_packages_install_all_three_styles_without_deleting_unknown_files(self):
        root=pathlib.Path(__file__).parents[2]/'picons/DAB'
        document=json.loads((root/'catalog/release-candidate.json').read_text())
        # Approval is simulated solely in this isolated test opener. The real
        # candidate catalog must remain rejected by read_manifest.
        self.assertEqual(document['status'],'candidate')
        document['status']='verified'
        p=dict(self.prefs,update_mode=sync.UPDATE_MODE_INCREMENTAL)
        for style,package in document['packages'].items():
            with self.subTest(style=style):
                target=self.root/style;target.mkdir();(target/OTHER).write_bytes(b'preserved')
                p.update(style=style,destination=str(target))
                def opener(url):
                    if url==dab.MANIFEST_URL:return io.BytesIO(json.dumps(document).encode())
                    self.assertEqual(url,package['url'])
                    return (root/'packages'/url.rsplit('/',1)[1]).open('rb')
                result=self.runner(opener).run([p])
                self.assertEqual(result,{'added':82,'changed':0,'removed':0})
                self.assertEqual((target/OTHER).read_bytes(),b'preserved')
                for name,digest in package['files'].items():
                    self.assertEqual(hashlib.sha256((target/name).read_bytes()).hexdigest(),digest)
    def runner(self,opener):return engine.PiconRunner(opener=opener,enigma2_dir=str(self.box),lock_path=str(self.root/'lock'))
    def test_only_exact_receiver_reference_is_installed_unknown_picon_preserved(self):
        d,b,op=source();(self.target/OTHER).write_bytes(b'user logo');result=self.runner(op).run([self.prefs]);self.assertEqual(result,{'added':1,'changed':0,'removed':0});self.assertEqual((self.target/OTHER).read_bytes(),b'user logo');self.assertEqual((self.target/NAME).read_bytes(),png());self.assertFalse(list(self.target.glob('.piconhub-stage-*')))
    def test_failed_package_hash_does_not_replace_existing_data(self):
        d,b,op=source();(self.target/NAME).write_bytes(b'original')
        def wrong(url):return op(url) if url==dab.MANIFEST_URL else io.BytesIO(b'corrupt')
        with self.assertRaises(engine.PiconError):self.runner(wrong).run([self.prefs])
        self.assertEqual((self.target/NAME).read_bytes(),b'original')
    def test_preview_catalog_is_never_installable(self):
        d,b,op=source();d['status']='preview'
        with self.assertRaisesRegex(ValueError,'not approved'):dab.read_manifest(lambda u:io.BytesIO(json.dumps(d).encode()))
    def test_untrusted_url_missing_style_and_invalid_filename_are_rejected(self):
        for change in ('url','style','filename'):
            d,b,op=source()
            if change=='url':d['packages']['white']['url']='https://evil.invalid/picons.zip'
            if change=='style':d['packages'].pop('black')
            if change=='filename':d['packages']['white']['files']={'../../escape.png':'0'*64}
            with self.assertRaises(ValueError):dab.read_manifest(lambda u:io.BytesIO(json.dumps(d).encode()))
    def test_tv_only_never_requests_a_dab_source(self):
        d,b,url,op=fixture();p=prefs(self.target,sync.UPDATE_MODE_INCREMENTAL);seen=[]
        def record(u):seen.append(u);return op(u)
        self.runner(record).run([p]);self.assertNotIn(dab.MANIFEST_URL,seen)
    def test_radio_bouquets_keep_ten_fields_and_strip_private_url(self):
        self.assertEqual(dab.bouquet_names(self.box),{NAME})
    def test_dab_non_reference_station_names_are_not_guessed(self):
        d,b,op=source();self.bouquet(OTHER)
        with self.assertRaises(engine.PiconError):self.runner(op).run([self.prefs])
        self.assertFalse(list(self.target.glob('*.png')))
    def test_plan_full_dab_selection_and_satellite_filter_are_distinct(self):
        d,b,op=source();p=dict(self.prefs,update_mode=sync.UPDATE_MODE_INCREMENTAL)
        self.assertEqual(dab.plan(d,p,self.box)[0]['dab_names'],{NAME})
        p.update(dab_only=False,positions=['19.2e']);self.assertIsNone(dab.plan(d,p,self.box))
    def test_bad_png_hash_and_zip_links_cannot_escape(self):
        d,b,op=source();queue,job=dab.plan(d,self.prefs,self.box);stage=engine.Stage(queue);self.addCleanup(stage.cleanup)
        out=io.BytesIO();info=zipfile.ZipInfo(NAME);info.external_attr=(0o120777<<16)
        with zipfile.ZipFile(out,'w') as z:z.writestr(info,b'../../escape')
        archive=stage.work/'bad.zip';archive.write_bytes(out.getvalue())
        with self.assertRaises(ValueError):dab.unpack(stage,archive,job,lambda:None)
    def test_cancel_before_write_preserves_originals(self):
        d,b,op=source();cancel=threading.Event();cancel.set();r=self.runner(op);r.cancel=cancel
        with self.assertRaises(engine.Cancelled):r.run([self.prefs])
        self.assertFalse(list(self.target.glob('*.png')))
    def test_new_network_allowlist_is_repository_and_path_scoped(self):
        self.assertTrue(dab.trusted_url(URL));self.assertTrue(dab.trusted_url(dab.MANIFEST_URL))
        for url in [URL.replace('raw.githubusercontent.com','evil.invalid'),URL.replace('/packages/','/preview/'),URL.replace('/'+'a'*40+'/', '/main/'),URL+'?redirect=evil']:
            self.assertFalse(dab.trusted_url(url))

