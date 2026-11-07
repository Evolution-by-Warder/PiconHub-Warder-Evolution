"""Read-only byte/provenance regression for six already visually reviewed singletons."""
from pathlib import Path
import gzip,json,hashlib,io
from zipfile import ZipFile
from PIL import Image
p=Path('continuation/country-singletons');c=p/'ci-reproduce';plan=json.load(open(c/'reproduce-plan.json'));sel=json.load(open(c/'accepted-selection.json'))['entries']
sha=lambda b:hashlib.sha256(b).hexdigest()
blob=lambda b:hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
originals=[]
for d,e in plan['originals'].items():
 b=(c/'upload-originals'/Path(e['path']).name).read_bytes();assert sha(b)==d==e['sha256']and len(b)==e['bytes']and blob(b)==e['git_blob'];originals.append({'sha256':d,'usage':e['usage'],'bytes':len(b)})
active={r['source']for r in plan['render_sources']['stations']}|{r['black_source']for r in plan['render_sources']['stations']if r.get('black_source')};assert len(originals)==8 and len(active)==7 and {d for d,e in plan['originals'].items()if e['usage']=='active'}==active
superseded={d for d in plan['originals']if d not in active};assert len(superseded)==1 and all('superseded-MS' in plan['originals'][d]['usage']for d in superseded)
world=json.loads(gzip.decompress(Path('sources-data/world.json.gz').read_bytes()));world={r['reference']:r for r in world}
byref={r['reference']:r for r in plan['render_sources']['stations']};wanted={v[0]for r in sel for v in r['variants'].values()};found={}
for folder in ['rendered-0-8','rendered-ms-uniform-badge','render-sm-km']:
 for zpath in (p/folder).glob('*.zip'):
  with ZipFile(zpath)as z:
   for name in z.namelist():
    b=z.read(name);d=sha(b)
    if d in wanted:found[d]=(b,str(zpath),name)
checks=[]
for r in sel:
 t=byref[r['ref']];w=world[r['ref']];assert r['country']==t['country'];assert all(r['station'][k]==w[k]==t[k]for k in ['name','url','group']);assert r['source_sha256']==t['source']and t['source']in active
 assert set(r['variants'])=={s+'/'+b for s in ['50x30','220x132','400x240']for b in ['transparent','white','black']}
 for k,v in r['variants'].items():
  b,z,name=found[v[0]];assert len(b)==v[1]and blob(b)==v[2]and name==r['ref'].replace(':','_')+'.png';im=Image.open(io.BytesIO(b));assert im.format=='PNG'and im.size==tuple(map(int,k.split('/')[0].split('x')));im.load()
 checks.append({'country':r['country'],'ref':r['ref'],'source':t['source'],'black_source':t.get('black_source'),'variants':r['variants']})
assert len(sel)==6 and len(wanted)==54
sm=next(r for r in plan['render_sources']['stations']if r['country']=='SM');assert 'positivo' in plan['originals'][sm['source']]['url']and 'negativo'in plan['originals'][sm['black_source']]['url'];ms=next(r for r in plan['render_sources']['stations']if r['country']=='MS');assert ms['source']=='0db88f4eb4d32e7f3b0d42d2450a5ca840876fd43c6a731204dcf24f2437c538'and 'black_source'not in ms
out={'schema':1,'status':'local-byte-and-provenance-pass-awaiting-pinned-export','references':6,'pngs':54,'staged_originals':8,'active_originals':7,'superseded_originals':list(superseded),'all_original_bytes_sha_and_git_blobs_pass':True,'all54_existing_png_bytes_sha_git_blob_dimensions_pass':True,'catalogue_exact_name_stream_country_group_pass':True,'colour_policy':{'SM':'untouched official positive and official negative selected explicitly','MS':'latest official uniform source all backgrounds; superseded source evidence-only','other_countries':'same untouched saved source all backgrounds'},'new_pngs':0,'new_zips':0,'visual_reviews_repeated':False,'entries':checks,'originals':originals}
Path('continuation/quality-tools/batch42-singleton-independent-proof.json').write_text(json.dumps(out,indent=2)+'\n');print('PASS six references54PNG eightoriginals sevenactive; no render/ZIP creation')
