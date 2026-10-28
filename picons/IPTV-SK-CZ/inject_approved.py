from pathlib import Path
import json
R=Path(__file__).resolve().parent
approved=json.loads((R/'catalog/approved-passthrough.json').read_text());data=json.loads((R/'catalog/refreshed-artwork-sources.json').read_text());downloads=json.loads((R/'catalog/downloaded-logos.json').read_text());count=0
for row in data['rows']:
 if row['country']!='SK' or row['identity_key'] not in approved['stations']:continue
 variants=approved['stations'][row['identity_key']];source=variants['220x132']['transparent'];url=source['source_url']
 spec={'url':url,'source_page':'https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/blob/'+approved['source_revision']+'/picons/radio-refresh-20261027/approval.json','identity':row['name'],'evidence':'Exact owner-approved artwork reused in all nine variants; same identity as satellite packages.','approved_variants':variants}
 row['logo']=spec;downloads[url]=dict(spec,path=source['path'],sha256=source['sha256'],bytes=(R/source['path']).stat().st_size);count+=1
(R/'catalog/refreshed-artwork-sources.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');(R/'catalog/downloaded-logos.json').write_text(json.dumps(downloads,ensure_ascii=False,indent=2)+'\n');print('Exact approved station artwork bindings',count)
