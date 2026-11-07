"""Reproduce only approved new public station PNGs from immutable inputs."""
import argparse,gzip,hashlib,io,json,re,subprocess,tempfile,urllib.request,urllib.parse,zipfile
from pathlib import Path
import PIL
from PIL import Image
STAGE='picons/radio-world/staging/primary-pending183-source-20261107'
SIZES=('50x30','220x132','400x240');STYLES=('transparent','white','black');KEYS={s+'/'+b for s in SIZES for b in STYLES}
def sha(b):return hashlib.sha256(b).hexdigest()
def blob(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def checked(b,d):
 assert len(b)==d['bytes'] and sha(b)==d['sha256'] and blob(b)==d['git_blob'],'Frozen bytes/SHA/Gitblob mismatch';return b
def put(p,b):
 if p.exists():assert p.read_bytes()==b,'Refusing unequal existing output'
 else:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=Path('.'));ap.add_argument('--chunk',required=True);ap.add_argument('--resource-cache',type=Path);a=ap.parse_args();assert re.fullmatch(r'\d{3}',a.chunk);stage=a.root/STAGE;cp=stage/'chunks'/('chunk-'+a.chunk);raw=(cp/'producer-plan.json').read_bytes();p=json.loads(raw);rows=p['expected_selection']['entries'];assert p['stage']==STAGE and p['chunk']==a.chunk and len(rows)==p['references'] and p['png_instances']==len(rows)*9;assert PIL.__version__=='13.0.0';resources={}
 for k,d in p['resources'].items():
  assert re.fullmatch('[0-9a-f]{40}',d['commit']);path=Path(d['path']);assert not path.is_absolute() and '..' not in path.parts
  if a.resource_cache:b=(a.resource_cache/(k+'.blob')).read_bytes()
  else:
   u='https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/'+d['commit']+'/'+urllib.parse.quote(d['path'],safe='/')
   with urllib.request.urlopen(u,timeout=60) as r:b=r.read(d['bytes']+1)
  resources[k]=checked(b,d)
 assert set(resources)=={'renderer','verifier','white','black','catalogue','country_index'}
 world=json.loads(gzip.decompress(resources['catalogue']));index=json.loads(resources['country_index']);assert index['catalogue_sha256']==sha(resources['catalogue']);labels={c['id']:c['name'] for c in index['countries']};facts=json.load(open(stage/p['public_observations_filename']));byref={o['row']['ref']:o for o in facts['entries']};ledger=json.load(open(stage/p['visual_ledger_filename']));votes={e['row']['ref']:e for e in ledger['entries']};originals={};programme_names=[]
 for r in rows:
  assert set(r['variants'])==KEYS and r['source_commit'] is None and r['asset_root']==STAGE;st=r['station'];assert st['group']==labels[r['country']] and st['group']!='HDF Radio zoznam';assert any(w['reference']==r['ref'] and all(w[k]==st[k] for k in ('name','url','group')) for w in world),'Canonical country tuple absent'
  v=votes[r['ref']];assert v['decision']=='approve' and v['reviewed_variants']==r['variants'];assert r['final_visual_approval']['decision']=='approve' and r['final_visual_approval']['reviewed_variants']==r['variants']
  o=byref[r['ref']];assert o['row']['station']==st and o['row']['country']==r['country'];assert o['binding_kind']=='protocol_reconciled' and o['exact_primary_literal'] is False;api=o['own_public_API'];assert api['title']==st['name'] and api['route_page_radio_id_matches'];assert o['own_JS']['primary_script_src_observed'] and o['own_JS']['route_literal']=='/ajax/json_player/'
  compare=o['exact_mount_comparison'];assert compare['canonical_stream_URL_and_service_reference_not_rewritten'] and compare['both_canonical_and_advertised_endpoints_status']==200;assert compare['only_transport_scheme_and_generic_public_player_label_differ'];c=urllib.parse.urlsplit(st['url']);x=urllib.parse.urlsplit(api['src']);assert c.hostname==x.hostname and c.path==x.path;assert urllib.parse.parse_qs(x.query)=={'aw_0_1st.playerId':['jazzradio_web']};heads=o['public_stream_station_facts'];assert len(heads)==2 and all(h['request_method']=='HEAD' and h['status_code']==200 for h in heads);assert heads[0]['requested_url']==st['url'] and heads[0]['public_station_name']==heads[1]['public_station_name'];programme_names.append(heads[0]['public_station_name']);assert o['source']['primary_image_URL_observed'] and o['source']['exact_alt_matches_programme'];h=o['source']['sha256'];assert h==r['provenance']['source_sha256'];d=p['originals'][h];path=Path(d['path']);assert path.parts[0]=='originals' and '..' not in path.parts;originals[h]=checked((stage/path).read_bytes(),d)
 assert len(set(programme_names))==len(rows),'Station-specific programme identifiers required'
 outputs={}
 with tempfile.TemporaryDirectory(prefix='warder-primary-safe-') as td:
  t=Path(td);(t/'masters').mkdir();(t/'originals').mkdir()
  for h,b in originals.items():(t/'originals'/(h+'.img')).write_bytes(b)
  for style in ('white','black'):(t/'masters'/(style+'.png')).write_bytes(resources[style])
  for k,f in [('renderer','render_verified_batch.py'),('verifier','verify_batch.py')]:(t/f).write_bytes(resources[k])
  (t/'world.json.gz').write_bytes(resources['catalogue']);(t/'sources.json').write_text(json.dumps(p['render_sources'],indent=2,ensure_ascii=False)+'\n');subprocess.run(['python3',str(t/'render_verified_batch.py'),str(t),str(t/'world.json.gz'),str(t/'masters')],check=True);m=json.load(open(t/'manifest.json'))
  for size in SIZES:
   for style in STYLES:
    with zipfile.ZipFile(t/m['packages'][size][style]['path']) as z:
     assert z.testzip() is None and len(z.namelist())==len(rows)
     for r in rows:
      b=z.read(r['ref'].replace(':','_')+'.png');h,n,bid=r['variants'][size+'/'+style];assert len(b)==n and sha(b)==h and blob(b)==bid,'PNG differs from actual approved output';im=Image.open(io.BytesIO(b));assert im.mode=='RGBA' and im.size==tuple(map(int,size.split('x')));im.verify();outputs[h]=b
 assert len(outputs)==p['unique_pngs'];writes={stage/'verified-assets'/(h+'.png'):b for h,b in outputs.items()}
 for path,b in writes.items():
  if path.exists():assert path.read_bytes()==b,'Unequal existing staged PNG'
 for path,b in writes.items():put(path,b)
 proof={'status':'pass','chunk':a.chunk,'references':len(rows),'PNG_instances':len(rows)*9,'unique_PNGs':len(outputs),'producer_plan_sha256':sha(raw),'all_SHA256_bytes_Gitblob_RGBA_dimensions_integrity_match':True,'strict_canonical_country_group_ref_stream_gate':'pass','binding_kind':'protocol_reconciled','canonical_URLs_or_references_rewritten':False,'public_observations_sha256':sha((stage/p['public_observations_filename']).read_bytes()),'all_nine_actual_visual_votes_checked':True,'raw_HTML_or_JS_archive_published':False,'existing_production_files_changed':False};put(cp/'reproduction-proof.json',(json.dumps(proof,indent=2)+'\n').encode());print('PASS source producer',len(rows),'refs',len(outputs),'exact PNGs')
if __name__=='__main__':main()
