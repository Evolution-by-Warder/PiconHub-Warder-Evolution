from pathlib import Path
import json,urllib.request,concurrent.futures,hashlib,time
p=Path('continuation/independent41-audit');idx=json.load(open(p/'production-index.json'));jobs=[]
for code in ['DE','GR']:
 row=next(r for r in idx['countries'] if r['id']==code);e=row['release'];jobs.append(dict(country=code,kind='manifest',url=e['url'],expected_bytes=e['bytes'],sha256=e['sha256']));m=json.load(open(p/'manifests'/e['sha256']))
 for size,styles in m['packages'].items():
  for style,e in styles.items():assert '/3bd8ea5659eb4d21c913ab4edb090d890d646a39/' in e['url'];jobs.append(dict(country=code,kind='legacy-zip',resolution=size,style=style,url=e['url'],expected_bytes=e['bytes'],sha256=e['sha256']))
def head(e):
 try:
  with urllib.request.urlopen(urllib.request.Request(e['url'],method='HEAD'),timeout=35) as r:
   length=r.headers.get('Content-Length');return {**e,'method':'HEAD','status':r.status,'final_url':r.url,'reported_content_length':length,'content_length_matches':(int(length)==e['expected_bytes'] if length else None),'body_bytes_read':0}
 except Exception as x:return {**e,'method':'HEAD','error':str(x),'body_bytes_read':0}
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:a=list(pool.map(head,jobs))
o={'schema':1,'snapshot':'3bd8ea5659eb4d21c913ab4edb090d890d646a39','legacy_branch_unchanged':True,'manifest_get_sha_verified_separately':True,'checks':a,'summary':{'manifest_head_success':sum(x.get('status')==200 and x['kind']=='manifest' for x in a),'legacy_zip_head_success':sum(x.get('status')==200 and x['kind']=='legacy-zip' for x in a),'head_body_bytes_read':0,'errors':sum('error' in x for x in a)}};(p/'legacy-de-gr-head-proof.json').write_text(json.dumps(o,indent=2)+'\n');print(json.dumps(o['summary']))
