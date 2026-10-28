"""Discover review candidates on the station's own observed homepage, not logo guesses."""
from pathlib import Path
from urllib.parse import urlsplit,urljoin
import json,re,hashlib,xml.etree.ElementTree as ET
R=Path(__file__).resolve().parent
scope={'__file__':str(R/'compile_catalog.py')};code=(R/'compile_catalog.py').read_text();# load helpers without regenerating output
import runpy,contextlib,io
with contextlib.redirect_stdout(io.StringIO()):m=runpy.run_path(str(R/'compile_catalog.py'))
aliases=m['aliases'];pages=json.loads((R/'research/pages.json').read_text());data=json.loads((R/'catalog/refreshed-artwork-sources.json').read_text())
def urlkey(u):
 p=urlsplit(u);return ((p.hostname or '').removeprefix('www.'),p.path.rstrip('/'))
byurl={urlkey(p['url']):p for p in pages if 'error' not in p}
DENY=('facebook','instagram','google','apple','android','zoznam','partner','reklam','kampan','kampaň','sponsor','toplist')
selected=[]
for row in data['rows']:
 existing=row.get('logo')
 if existing and existing.get('approved_variants'):continue
 p=byurl.get(urlkey(row.get('homepage','')))
 if not p:continue
 options=[]
 for img in p.get('images',[]):
  url=img.get('data-src') or img.get('data-pagespeed-lazy-src') or img.get('src') or img.get('content') or img.get('href') or ''
  if not url or url.startswith('data:') or any(x in url.lower() for x in DENY):continue
  full=urljoin(p.get('final_url',p['url']),url).split('#')[0]
  label=img.get('alt') or img.get('title') or '';label_key=aliases(label);station_key=row['identity_key']
  score=0
  if label_key and (label_key==station_key or len(station_key)>3 and station_key in label_key):score+=8
  if 'logo' in url.lower():score+=3
  if 'logo' in ((img.get('class') or '')+' '+(img.get('id') or '')).lower():score+=3
  if full.lower().split('?')[0].endswith('.svg'):score+=2
  if img.get('property')=='og:image' and 'logo' not in url.lower():score=-100
  if img.get('rel') and not score>=8:continue
  structural=any(w in (url+' '+(img.get('class') or '')+' '+(img.get('id') or '')).lower() for w in ('logo','brand','/stanice/'))
  if score>=8 and structural:options.append((score,full,label))
 if options:
  _,url,label=max(options)
  if existing and not (url.lower().endswith('.svg') and not existing['url'].lower().split('?')[0].endswith('.svg')):continue
  row['logo']={'url':url,'source_page':p.get('final_url',p['url']),'identity':label or row['name'],'evidence':'Station-name-matching logo element on its own homepage; visual review pending.'};selected.append(row['name'])
# Explicitly identified inline vector logos, copied without redrawing.
inline=[('https://www.evropa2.cz/','evropa2',lambda s:next(x for x in re.findall(r'<svg\b[^>]*>.*?</svg>',s,re.S) if '<title>Evropa 2</title>' in x)),('https://www.subfm.sk/','subfm',lambda s:re.search(r'<h1>\s*<\?xml[^>]*>\s*(<svg\b.*?</svg>)',s,re.S)[1]),('http://www.radiokosice.sk/','kosice',lambda s:re.search(r'<span name="radiokosice"[^>]*>(<svg\b.*?</svg>)',s,re.S)[1])]
known=json.loads((R/'catalog/downloaded-logos.json').read_text())
for page,identity,extract in inline:
 p=byurl.get(urlkey(page))
 if not p:continue
 try:
  vector=extract((R/p['file']).read_text(errors='replace'))
  if 'xmlns=' not in vector.split('>',1)[0]:vector=vector.replace('<svg','<svg xmlns="http://www.w3.org/2000/svg"',1)
  root=ET.fromstring(vector)
  if root.get('preserveAspectRatio')=='':del root.attrib['preserveAspectRatio']
  raw=ET.tostring(root);digest=hashlib.sha256(raw).hexdigest();path=R/'sources'/('inline-'+digest[:24]+'.svg');path.write_bytes(raw)
  url=p.get('final_url',page)+'#warder-source-logo'
  spec={'url':url,'source_page':p.get('final_url',page),'identity':identity,'evidence':'Exact inline station logo SVG extracted from the identified homepage logo element.','source_type':'inline-svg','path':str(path.relative_to(R)),'sha256':digest,'bytes':len(raw)}
  known[url]=spec
  for r in data['rows']:
   if r['identity_key']==identity and r['country']==('CZ' if identity=='evropa2' else 'SK'):r['logo']=spec;selected.append(r['name'])
 except Exception as e:print('Inline source review:',identity,str(e))
(R/'catalog/downloaded-logos.json').write_text(json.dumps(known,ensure_ascii=False,indent=2)+'\n')
(R/'catalog/refreshed-artwork-sources.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
print('Additional candidates',len(selected),selected)
print('Total source candidates',sum(bool(r['logo']) for r in data['rows']),'of',len(data['rows']))
