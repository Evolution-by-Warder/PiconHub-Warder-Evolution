"""Look up frozen Radio Browser UUIDs; accept only new icons with exact identity evidence."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit, urlencode
from urllib.request import Request, urlopen
import argparse,base64,gzip,json,socket,subprocess,time,unicodedata
from radio_source_helpers import dump,SHA,push_checkpoint

def norm(text):
 return ''.join(c for c in unicodedata.normalize('NFKD',text.casefold()) if c.isalnum())

def stream_key(url):
 p=urlsplit(url)
 if p.scheme not in ('http','https'):return None
 return (p.netloc.casefold(),p.path,p.query)

def verified_new_icons(programme, records, known_urls):
 ids={x[14:] for x in programme.get('source_ids',[]) if x.startswith('radio-browser:')}
 names={norm(x) for x in [programme['name'],*programme.get('name_aliases',[])]}
 streams={stream_key(u) for u in [programme['url'],*programme.get('aliases',[]),*[v['url'] for v in programme.get('stream_variants',[])]]};streams.discard(None)
 output=[]
 for record in records:
  if record.get('stationuuid') not in ids:continue
  if record.get('countrycode','').upper()!=programme.get('countrycode','').upper():continue
  if norm(record.get('name','')) not in names:continue
  if not any(stream_key(record.get(k,'')) in streams for k in ['url','url_resolved']):continue
  icon=record.get('favicon','').strip()
  if urlsplit(icon).scheme not in ('http','https') or icon in known_urls:continue
  output.append((icon,dict(source_station_uuid=record['stationuuid'],current_metadata_name=record['name'],current_metadata_country=record['countrycode'],current_metadata_stream=record.get('url'),current_metadata_resolved_stream=record.get('url_resolved'),current_metadata_image_url=icon,current_metadata_last_change=record.get('lastchangetime_iso8601'),identity_rule='Frozen source UUID plus exact normalized name, country and an unchanged stream endpoint. Only HTTP/HTTPS transport may differ.')))
 return output

def api_batch(ids, servers):
 errors=[]
 for server in servers*2:
  try:
   url=server+'/json/stations/byuuid?'+urlencode({'uuids':','.join(ids)})
   with urlopen(Request(url,headers={'User-Agent':'WarderRadioPiconReview/2026.11','Accept':'application/json'}),timeout=12) as response:
    data=response.read(4*1024*1024+1)
   if len(data)>4*1024*1024:raise ValueError('Oversized metadata response')
   rows=json.loads(data)
   if not isinstance(rows,list) or any(not isinstance(r,dict) or r.get('stationuuid') not in ids for r in rows):raise ValueError('Unexpected UUID in response')
   return dict(rows=rows,api_server=server,errors=[])
  except Exception as exc:errors.append(type(exc).__name__+': '+str(exc)[:180])
 return dict(rows=[],errors=errors)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--input',required=True,type=Path);ap.add_argument('--output',required=True,type=Path);ap.add_argument('--commit',action='store_true');args=ap.parse_args()
 seed=json.loads(gzip.decompress(base64.b64decode(args.input.read_bytes())));root=args.output;root.mkdir(parents=True,exist_ok=True)
 servers=[]
 try:
  for info in socket.getaddrinfo('all.api.radio-browser.info',443,type=socket.SOCK_STREAM):
   try:
    host=socket.gethostbyaddr(info[4][0])[0]
    if host.endswith('.api.radio-browser.info') and 'https://'+host not in servers:servers.append('https://'+host)
   except OSError:pass
 except OSError:pass
 for host in ['https://de1.api.radio-browser.info','https://nl1.api.radio-browser.info']:
  if host not in servers:servers.append(host)
 uuids=sorted({x[14:] for p in seed['programmes'] for x in p.get('source_ids',[]) if x.startswith('radio-browser:')});batches=[uuids[i:i+100] for i in range(0,len(uuids),100)];records={};failures=[]
 if uuids:
  probe=api_batch(uuids[:1],servers)
  if probe['errors']:
   dump(root/'refresh-summary.json',dict(status='blocked_api_unavailable',errors=probe['errors'],production_changed=False))
   if args.commit:
    subprocess.run(['git','add','--',str(root)],check=True);subprocess.run(['git','commit','--quiet','-m','Preserve explicit Radio metadata API unavailability'],check=True);push_checkpoint()
   raise SystemExit('Radio Browser API unavailable; no station identity or production output changed.')
  servers=[probe['api_server']]+[x for x in servers if x!=probe['api_server']]
 saved=root/'metadata-batches';saved.mkdir(exist_ok=True)
 def get_batch(item):
  n,ids=item;p=saved/f'batch-{n:04d}.json'
  if p.exists():
   previous=json.loads(p.read_text())
   if not previous.get('errors'):return n,previous
  response=api_batch(ids,servers);dump(p,response);return n,response
 with ThreadPoolExecutor(4) as pool:
  for n,response in pool.map(get_batch,enumerate(batches)):
   for r in response['rows']:records[r['stationuuid']]=r
   if response['errors']:failures.append(dict(batch=n,errors=response['errors']))
   if (n+1)%10==0:print('Metadata UUID batches',n+1,'/',len(batches),'records',len(records),flush=True)
 known=set(seed['known_image_urls']);receivers={r['reference']:r for r in seed['remaining_receivers']};queue=[];used=set()
 for p in seed['programmes']:
  ids=[x[14:] for x in p.get('source_ids',[]) if x.startswith('radio-browser:')];rows=[records[i] for i in ids if i in records];icons=verified_new_icons(p,rows,known)
  if not icons:continue
  urls=list(dict.fromkeys(u for u,e in icons));evidence={u:e for u,e in icons}
  for ref in [p['reference'],*p.get('merged_references',[])]:
   if ref not in receivers or ref in used:continue
   used.add(ref);queue.append(dict(receivers[ref],station_id=p['id'],country=p['countrycode'],homepages=p.get('homepages',[]),favicon_urls=urls,metadata_refresh_evidence_by_url=evidence))
 output=dict(schema=1,catalogue_snapshot=seed['catalogue_snapshot'],ready_references=seed['ready_references'],reviewed_source_hashes=seed['reviewed_source_hashes'],approved_graphics={},queue=queue)
 (root/'new-artwork-input.b64').write_bytes(base64.b64encode(gzip.compress(json.dumps(output,ensure_ascii=False,separators=(',',':')).encode())))
 summary=dict(project='Radio plugin',frozen_catalogue_snapshot=seed['catalogue_snapshot'],queried_source_uuids=len(uuids),returned_source_uuids=len(records),failed_api_batches=failures,programme_count=len(seed['programmes']),new_icon_candidate_receivers=len(queue),new_icon_urls=len({u for r in queue for u in r['favicon_urls']}),already_saved_references=len(seed['ready_references']),already_reviewed_hashes=len(seed['reviewed_source_hashes']),production_changed=False,updated_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
 dump(root/'refresh-summary.json',summary);print(summary,flush=True)
 if args.commit:
  subprocess.run(['git','add','--',str(root)],check=True)
  if subprocess.run(['git','diff','--cached','--quiet']).returncode:subprocess.run(['git','commit','--quiet','-m','Save exact UUID metadata refresh for unresolved Radio picons'],check=True);push_checkpoint()

if __name__=='__main__':main()
