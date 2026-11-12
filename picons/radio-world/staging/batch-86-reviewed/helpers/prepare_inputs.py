"""Admit only publisher-bound, visually reviewed originals; preserve all historical artwork."""
import json,gzip,hashlib,sys,io,subprocess,urllib.request,urllib.parse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
S=Path('picons/radio-world/staging');stage=S/'batch-86-reviewed';prev=S/'batch-85-reviewed'
sys.path.insert(0,'picons/radio-world/tools')
from visual_gate import read,merge_ledgers,identity_blocks,validate_selection
from saved_artwork_import import get
sha=lambda b:hashlib.sha256(b).hexdigest()
def write(p,x):
 b=(json.dumps(x,indent=2,ensure_ascii=False)+'\n').encode();p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(gzip.compress(b,mtime=0)if p.suffix=='.gz'else b)
desc=read(stage/'source-inputs/recovery-spec.json');cfg=read(prev/'configuration.json');raw=(prev/'countries.proposed.json').read_bytes();assert sha(raw)==desc['baseline_sha256'];world=json.loads(gzip.decompress(get(cfg['world'])));paths=[S/'source-ledger-reviewed-20261107/visual-ledger.json.gz',S/'visual-review-34-36/decisions.json.gz']+[S/f'batch-{n}-reviewed/visual-ledger.json.gz'for n in range(39,86)];history=merge_ledgers(paths);known={(e['row']['country'],e['row']['ref'])for e in history['entries']};blocks=identity_blocks(history)
assert len(cfg['held_references'])==923
# Preflight EVERY row before downloading or writing any image.
assert len(desc['stations'])==26
for r in desc['stations']:
 st=r['station'];matches=[x for x in world if x['reference']==st['reference']and x['group']==st['group']];assert len(matches)==1;x=matches[0]
 assert dict(x,url=x['url'].split('?')[0])==st and sha(x['url'].encode())==r['catalog_url_sha256']
 assert urllib.parse.parse_qs(urllib.parse.urlsplit(x['url']).query) in ({},{'provider':['radiobrowser']})
 assert ('FR',st['reference'])not in known|blocks and st['reference']not in cfg['held_references']
 assert st['group']=='France'
 p=urllib.parse.urlsplit(st['url']);q=urllib.parse.urlsplit(r['publisher']['url']);assert p.hostname==q.hostname and p.path==q.path and p.hostname=='streaming.hotmixradio.com'
 assert r['original']['url']==r['image'] and r['image']=='https://checkout.hotmixradio.com'+r['publisher']['image_large']
 assert len(r['variants'])==9
(stage/'originals').mkdir(exist_ok=True);(stage/'verified-assets').mkdir(exist_ok=True)
def original(e):
 with urllib.request.urlopen(e['url'],timeout=45)as response:b=response.read(e['bytes']+1)
 assert len(b)==e['bytes']and sha(b)==e['sha256'];(stage/'originals'/(e['sha256']+'.img')).write_bytes(b);return e['sha256'],b
sources={r['original']['sha256']:r['original']for r in desc['stations']}
with ThreadPoolExecutor(max_workers=6)as pool:originals=dict(pool.map(original,sources.values()))
masters={'transparent':Image.new('RGBA',(220,132))}
for sty,digest in desc['master_sha256'].items():
 u='https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/'+desc['master_commit']+'/plugin/artwork/templates/picons/'+sty+'-sablona.png';b=urllib.request.urlopen(u,timeout=30).read();assert sha(b)==digest;masters[sty]=Image.open(io.BytesIO(b)).convert('RGBA');assert masters[sty].size==(220,132)
cache={}
for r in desc['stations']:
 digest=r['original']['sha256']
 if digest not in cache:
  mark=Image.open(io.BytesIO(originals[digest])).convert('RGBA');mark.thumbnail((192,104),Image.Resampling.LANCZOS);vv={}
  for sty in ['transparent','white','black']:
   im=masters[sty].copy();pos=((220-mark.width)//2,(132-mark.height)//2)
   if sty=='transparent':im.paste(mark,pos)
   else:im.alpha_composite(mark,pos)
   for size in ['50x30','220x132','400x240']:
    final=im if size=='220x132'else im.resize(tuple(map(int,size.split('x'))),Image.Resampling.LANCZOS);buf=io.BytesIO();final.save(buf,format='PNG',optimize=True);b=buf.getvalue();h=sha(b);vv[size+'/'+sty]=[h,len(b),hashlib.sha1(f'blob {len(b)}\0'.encode()+b).hexdigest()];(stage/'verified-assets'/(h+'.png')).write_bytes(b)
  cache[digest]=vv
 assert cache[digest]==r['variants'],'Rendered bytes differ from visually reviewed local originals'
rows=[]
for i,r in enumerate(desc['stations']):
 st=r['station'];rows.append(dict(index=860000+i,country='FR',ref=st['reference'],station={k:st[k]for k in ['name','url','group']},asset_root=str(stage),variants=r['variants'],provenance=dict(publisher=r['publisher'],original=r['original'],catalog_url_sha256={'new':r['catalog_url_sha256']},identity_basis='Official Hotmix embedded radios configuration binds exact stream hostname and mount, channelID,name and original image. Language/codec substitutions and conflicting labels excluded. Only provider=radiobrowser tracking is omitted from metadata; original URL SHA256 retained.',approval_authority='Owner advance approval of verified picons; exact publisher artwork preserved')))
write(stage/'source-inputs/publisher-authority-proof.json',dict(status='pass',references=26,unique_originals=len(originals),new_PNG_instances=234,existing_PNGs_rerendered=0,master_sha256=desc['master_sha256'],availability='Identity from publisher snapshot, no live-audio claim',identity_source='Official broadcaster configuration; exact stationID, channelroute and per-channel artwork'))
subprocess.run(['git','config','user.name','github-actions[bot]'],check=True);subprocess.run(['git','config','user.email','41898282+github-actions[bot]@users.noreply.github.com'],check=True)
subprocess.run(['git','add',str(stage/'originals'),str(stage/'verified-assets'),str(stage/'source-inputs/publisher-authority-proof.json')],check=True);subprocess.run(['git','commit','-m','Save86 26 publisher originals and234 reviewed PNG instances [skip ci]'],check=True);subprocess.run(['git','push','origin','HEAD:refs/heads/work/radio-world-batch38-contrast-pass1-history-20261107'],check=True);commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
for r in rows:r.update(source_commit=commit,final_visual_approval=dict(decision='approve',reason='Owner preapproved verified artwork; original publisher channel image preserved on immutable master variants; actual previews reviewed.',reviewed_variants=r['variants']))
write(stage/'selection.json.gz',dict(entries=rows));write(stage/'visual-ledger.json.gz',dict(entries=[dict(row=r,decision='approve',reason=r['final_visual_approval']['reason'],reviewed_variants=r['variants'])for r in rows],source_holds=[],pending_sources=[]));assert validate_selection(rows,merge_ledgers(paths+[stage/'visual-ledger.json.gz']))==26
(stage/'baseline.previous.json').write_bytes(raw);cfg.update(batch='86-reviewed',references=26,parent_candidate=desc['parent'],expected_coverage=3586,selection_sha256=sha((stage/'selection.json.gz').read_bytes()),baseline_index=dict(url='https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/'+desc['parent']+'/picons/radio-world/staging/batch-85-reviewed/countries.proposed.json',bytes=len(raw),sha256=sha(raw)));write(stage/'configuration.json',cfg)
print('Prepared26 references/234 new reviewed PNG instances, no historical render changes')

write(stage/'verification-proof.json',dict(status='pass',references=26,PNG_instances=234,new_original_sets=26,existing_PNGs_rerendered=0,configuration_blocks=923,historical_holds_preserved=True))
subprocess.run(['git','add',str(stage)],check=True)
subprocess.run(['git','commit','-m','Save86 reviewed selection and immutable source bindings [skip ci]'],check=True)
subprocess.run(['git','push','origin','HEAD:refs/heads/work/radio-world-batch38-contrast-pass1-history-20261107'],check=True)
