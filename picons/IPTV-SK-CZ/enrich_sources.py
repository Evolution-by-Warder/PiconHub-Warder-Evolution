from pathlib import Path
from urllib.parse import urlsplit
import json,runpy,contextlib,io,re
R=Path(__file__).resolve().parent
with contextlib.redirect_stdout(io.StringIO()):m=runpy.run_path(str(R/'compile_catalog.py'))
aliases=m['aliases'];rows=json.loads((R/'catalog/refreshed-stations.json').read_text())['stations'];old=json.loads((R/'catalog/artwork-sources.json').read_text())['rows'];radia=json.loads((R/'research/radia-stations.json').read_text());sk=json.loads((R/'research/sk-station-logos.json').read_text());rb={c:json.loads((R/f'research/{c}-radio-browser.json').read_text()) for c in ['SK','CZ']}
def base(url):
 h=urlsplit(url).hostname or '';return '.'.join(h.split('.')[-2:])
byref={r['picon_filename']:r['logo'] for r in old if r['logo']};byname={(r['country'],aliases(r['name'])):r['logo'] for r in old if r['logo']}
rs={aliases(r['name']):r for r in radia}
result=[]
for row in rows:
 spec=byref.get(row['picon_filename']) or byname.get((row['country'],row['identity_key']))
 if not spec and row['country']=='CZ' and row['identity_key'] in rs:
  r=rs[row['identity_key']];spec={'source_page':'https://radia.cz/radia/'+r['slug'],'url':r['logo'],'identity':r['name'],'evidence':'Station-specific named broadcaster-directory artwork.'}
 if not spec and row['country']=='SK':
  r=next((x for x in sk if x['name'] and aliases(x['name'])==row['identity_key'] and x['logo']),None)
  if r:
   src=r['logo'].split(',')[-1].strip().split()[0];spec={'source_page':r['page'],'url':src,'identity':r['name'],'evidence':'Station-specific named artwork on the rendered station player; visual review required.'}
 if not spec and row['country']=='SK':
  r=next((x for x in json.loads((R/'research/radia-sk-stations.json').read_text()) if aliases(x['name'])==row['identity_key']),None)
  if r:
   slug=r['page_url'].split('/player/')[1].split('/')[0]
   spec={'source_page':r['page_url'],'url':'https://cdn.radia.sk/_radia/loga/app/'+slug+'@2x.png','identity':r['name'],'evidence':'Named station in public broadcaster directory; station-specific CDN asset candidate, visual review required.'}
 if not spec:
  candidates=[r for r in rb[row['country']] if aliases(r['name'])==row['identity_key'] and r.get('favicon') and base(r['homepage'])==base(r['favicon']) and base(r['favicon']) not in ('ibb.co','imgur.com','google.com','goo.gl','facebook.com')]
  candidates=[r for r in candidates if urlsplit(r['favicon']).scheme in ('https','http') and not r['favicon'].endswith('.ico')]
  if candidates:
   r=max(candidates,key=lambda r:('svg' in r['favicon'],bool(re.search('180|192|256|512|logo',r['favicon'])),r['lastcheckok']))
   spec={'source_page':r['homepage'],'url':r['favicon'],'identity':r['name'],'evidence':'Logo hosted on the station homepage domain; discovered through Radio Browser, visual verification pending.'}
 if spec and (spec['url'].endswith('/assets/images/cd.png') or 'zeno.fm/static/icons/' in spec['url']):
  spec=None # Generic CD/player/platform artwork is not the station logo.
 decisions=json.loads((R/'catalog/manual-artwork-sources.json').read_text())['rows']
 override=next((x for x in decisions if x['country']==row['country'] and x['identity_key']==row['identity_key']),None)
 if override:spec=override
 if spec and (R/'catalog/style-sources.json').exists():
  extras=[x for x in json.loads((R/'catalog/style-sources.json').read_text())['rows'] if x['country']==row['country'] and x['identity_key']==row['identity_key']]
  if extras:spec=dict(spec,style_sources={x['style']:x for x in extras})
 result.append(dict(row,logo=spec))
(R/'catalog/refreshed-artwork-sources.json').write_text(json.dumps({'schema':1,'status':'source-candidates-require-visual-review','rows':result},ensure_ascii=False,indent=2)+'\n')
print('Selected sources',sum(bool(r['logo']) for r in result),'of',len(result))
print('Missing:',[(r['country'],r['name']) for r in result if not r['logo']])
