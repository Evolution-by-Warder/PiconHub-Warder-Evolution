#!/usr/bin/env python3
"""Anonymous primary Zeno source freezer. No renderer, Git, credentials or graphics approval."""
import argparse,base64,concurrent.futures as cf,datetime,email.utils,fcntl,hashlib,io,json,os,re,subprocess,threading,time,unicodedata
from collections import Counter,defaultdict
from pathlib import Path
from urllib.parse import urlsplit,urlencode,unquote,parse_qsl
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from PIL import Image

def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(b):return hashlib.sha256(b).hexdigest()
def atomic(p,obj):
 p=Path(p);t=p.with_name(p.name+'.tmp');t.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n');t.replace(p)
def canonical(u):
 p=urlsplit(u);return p._replace(query=urlencode(sorted(parse_qsl(p.query,keep_blank_values=True)))).geturl()
def same_logo(u,sid):
 try:
  p=urlsplit(u);h=(p.hostname or'').lower()
  if p.scheme!='https':return False
  if h=='proxy.zeno.fm':return unquote(p.path).rstrip('/')=='/content/stations/'+sid+'/image'
  if h=='zenoimages.s3.us-west-001.backblazeb2.com':return p.path=='/'+sid+'/images/logo'
  if h=='images.zeno.fm':
   token=p.path.rsplit('/',1)[-1];nested=base64.urlsafe_b64decode(token+'='*((4-len(token)%4)%4)).decode();return same_logo(nested,sid)
 except Exception:pass
 return False
class Freeze:
 def __init__(self,args):
  self.args=args;self.root=Path(args.root);self.root.mkdir(parents=True,exist_ok=True);(self.root/'objects').mkdir(exist_ok=True)
  self.flock=(self.root/'freezer.lock').open('a');fcntl.flock(self.flock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  self.lock=threading.RLock();self.url_locks=defaultdict(threading.Lock);self.semaphore=threading.BoundedSemaphore(4);self.cache={};self.errors={};self.counts=Counter();self.rate_until=0.;self.phase='initializing';self.started=utc();self.tasks_since_checkpoint=0;self.stop=threading.Event()
  self.input=json.loads(Path(args.input).read_text());entries=self.input['entries'];self.rows=[dict(index=e['index'],row=e['row'],status='candidate',stage1_done=False,secondary_done=False,searches=[],discovered_cards=[],details_checked=[],identity_observations=[],graphic_approved=False,source_qa_required=True)for e in entries]
  if [e['index']for e in self.rows]!=list(range(len(self.rows))):raise ValueError('input indices must be contiguous and stable')
  self.mounts=defaultdict(list)
  for e in self.rows:self.mounts[urlsplit(e['row']['station']['url']).path.strip('/')].append(e['index'])
  for directory in [Path(args.cache)]if args.cache else []:self.import_cache(directory)
  self.import_cache(self.root)
  # Output checkpoint overrides cache checkpoint only when exact row/index input matches.
  for directory in ([Path(args.cache)]if args.cache else [])+[self.root]:
   path=directory/'source-review-rows.json'
   if not path.exists():continue
   for e in json.loads(path.read_text())['entries']:
    i=e['index']
    if 0<=i<len(self.rows)and e['row']==self.rows[i]['row']:
     self.rows[i]=e
     if e.get('status')=='pending':e['stage1_done']=False;e['secondary_done']=False;e['status']='candidate'
  self.validate_restored()
 def import_cache(self,d):
  journals=[p for p in(d/'http-responses.jsonl',d/'http-success-cache.jsonl')if p.exists()]
  for line in [s for p in journals for s in p.read_text().splitlines()]:
   try:
    m=json.loads(line)
    if m.get('status')!=200 or not m.get('sha256'):continue
    source=d/'objects'/(m['sha256']+'.body')
    if not source.exists():continue
    b=source.read_bytes()
    if sha(b)!=m['sha256']:raise ValueError('cache SHA mismatch '+str(source))
    target=self.root/'objects'/source.name
    if not target.exists():target.write_bytes(b)
    m['path']='objects/'+source.name;self.cache[canonical(m['url'])]=m
   except json.JSONDecodeError:continue
 def validate_restored(self):
  for e in self.rows:
   if e['status']!='logo-frozen':continue
   st=e.get('api_station',{});s=e.get('source',{});path=self.root/'objects'/(s.get('sha256','')+'.body')
   if not path.exists()or sha(path.read_bytes())!=s.get('sha256')or not same_logo(s.get('final_url',''),str(st.get('id',''))):
    e.update(status='identity-passed',frozen_source_ready=False);e.pop('source',None)
 def record_http(self,m):
  with self.lock:
   with(self.root/'http-responses.jsonl').open('a')as f:f.write(json.dumps(m,ensure_ascii=False,separators=(',',':'))+'\n')
 def fetch(self,url):
  key=canonical(url)
  if self.stop.is_set():raise InterruptedError('freezer stopping')
  with self.url_locks[key]:
   with self.lock:old=self.cache.get(key);error=self.errors.get(key)
   if old:
    b=(self.root/old['path']).read_bytes()
    if sha(b)!=old['sha256']:raise ValueError('cached object SHA mismatch')
    with self.lock:self.counts['cache_hits']+=1
    return b,dict(old)
   if error:return None,error
   last=None
   for attempt in range(1,4):
    if self.stop.is_set():raise InterruptedError('freezer stopping')
    while True:
     with self.lock:delay=self.rate_until-time.time()
     if delay<=0:break
     if self.stop.wait(min(delay,20)):raise InterruptedError('freezer stopping')
    m=dict(url=url,fetched_utc=utc(),attempt=attempt)
    retry=False;delay=min(2**attempt,20)
    try:
     with self.semaphore:
      req=Request(url,headers={'User-Agent':'Mozilla/5.0 (public radio source verification)','Accept':'application/json,image/*;q=0.9,*/*;q=0.5'})
      with self.lock:self.counts['network_attempts']+=1
      try:response=urlopen(req,timeout=35)
      except HTTPError as ex:response=ex
      with response:
       status=response.status;headers={k.lower():v for k,v in response.headers.items()if k.lower()in('content-type','content-length','etag','last-modified','date','retry-after','cache-control','location')};m.update(status=status,final_url=response.geturl(),headers=headers,content_type=response.headers.get('content-type'))
       with self.lock:self.counts['http_'+str(status)]+=1
       if status==200:
        b=response.read(24*1024*1024+1)
        if len(b)>24*1024*1024:raise ValueError('body_over_24MiB')
        digest=sha(b);dest=self.root/'objects'/(digest+'.body')
        if not dest.exists():
         tmp=dest.with_name(dest.name+'.'+str(threading.get_ident())+'.tmp');tmp.write_bytes(b);tmp.replace(dest)
        m.update(sha256=digest,bytes=len(b),path='objects/'+dest.name);self.record_http(m)
        with self.lock:self.cache[key]=m
        return b,m
       m['error']='HTTP '+str(status);retry=status in(408,425,429,500,502,503,504)
       ra=headers.get('retry-after')
       if ra:
        try:delay=max(0,float(ra))
        except ValueError:
         try:delay=max(0,email.utils.parsedate_to_datetime(ra).timestamp()-time.time())
         except (ValueError,TypeError):pass
    except(URLError,TimeoutError,OSError)as ex:m['error']=type(ex).__name__+': '+str(ex);retry=True
    except ValueError as ex:m['error']=str(ex)
    self.record_http(m);last=m
    if not retry or attempt==3:break
    with self.lock:self.rate_until=max(self.rate_until,time.time()+delay);self.counts['bounded_retries']+=1
   with self.lock:self.errors[key]=last
   return None,last
 def logo(self,st):
  u=st.get('metaLogo')or(st.get('logoImage')or{}).get('src');sid=str(st.get('id',''))
  if not sid or not isinstance(u,str)or not same_logo(u,sid):return dict(error='generic_default_or_untrusted_station_logo_url',policy_hold=True)
  b,m=self.fetch(u)
  if b is None:return dict(m,error=m.get('error','source_unavailable'),retrieval_pending=True)
  if not same_logo(m.get('final_url',''),sid):return dict(m,error='untrusted_or_non_station_specific_logo_redirect',policy_hold=True)
  try:
   im=Image.open(io.BytesIO(b));im.verify();im=Image.open(io.BytesIO(b))
   if im.width*im.height>40_000_000:return dict(m,error='source_exceeds_40MP',policy_hold=True)
   if getattr(im,'n_frames',1)!=1:return dict(m,error='animated_source_requires_manual_review',policy_hold=True)
   return dict(m,image_path=m['path'],dimensions=list(im.size),format=im.format,mode=im.mode,pixel_sha256=sha(str(im.size).encode()+im.convert('RGBA').tobytes()),integrity_verified=True,station_id_specific=True)
  except Exception as ex:return dict(m,error='invalid_raster:'+str(ex),policy_hold=True)
 def detail(self,slug):
  url='https://zeno.fm/api/stations/'+slug;b,m=self.fetch(url)
  if b is None:return
  if urlsplit(m.get('final_url','')).hostname not in('zeno.fm','www.zeno.fm'):
   with self.lock:self.errors[canonical(url)]=dict(m,error='primary_api_redirect_outside_zeno')
   return
  try:st=json.loads(b)
  except ValueError:
   with self.lock:self.errors[canonical(url)]=dict(m,error='invalid_detail_json')
   return
  if not isinstance(st,dict)or not isinstance(st.get('streamURL'),str):
   with self.lock:self.errors[canonical(url)]=dict(m,error='invalid_detail_contract')
   return
  stream=urlsplit(st['streamURL']);mount=stream.path.strip('/')
  if stream.hostname!='stream.zeno.fm'or st.get('streamName')!=mount:return
  matches=[]
  with self.lock:
   for i in self.mounts.get(mount,[]):
    e=self.rows[i];obs=dict(station_id=st.get('id'),slug=st.get('slug'),title=st.get('title'),country=st.get('country'),streamURL=st.get('streamURL'),streamName=st.get('streamName'),api_url=url,api_sha256=m['sha256'],stream_mount_exact=True,country_exact=st.get('country')==e['row']['station']['group'])
    if obs not in e['identity_observations']:e['identity_observations'].append(obs)
    if not obs['country_exact']or not st.get('country'):continue
    if e.get('api_station')and e['api_station'].get('id')!=st.get('id'):e.update(status='hold',hold_reason='multiple_station_ids_same_stream_country',frozen_source_ready=False);continue
    if e.get('hold_reason')=='multiple_station_ids_same_stream_country':continue
    if e['status']=='logo-frozen':continue
    e.update(status='identity-passed',api_station={k:st.get(k)for k in('id','slug','title','country','region','streamURL','streamName','metaLogo','logoImage','external','description')},api_evidence=m,primary_page='https://zeno.fm/radio/'+st['slug']+'/',identity=dict(stream_mount_exact=True,stream_name_exact=True,country_exact=True,stream_url_exact=st['streamURL']==e['row']['station']['url'],title_used_for_admission=False));matches.append(i)
  if matches:
   source=self.logo(st)
   with self.lock:
    for i in matches:
     e=self.rows[i]
     if e.get('hold_reason')=='multiple_station_ids_same_stream_country':continue
     e['source']=source
     if source.get('retrieval_pending'):e.update(status='identity-passed',retrieval_pending=True)
     elif source.get('error'):e.update(status='hold',hold_reason=source['error'])
     else:e.update(status='logo-frozen',frozen_source_ready=True,graphic_approved=False,source_qa_required=True)
 def rank(self,c,name):
  def norm(x):return re.sub('[^a-z0-9]','',unicodedata.normalize('NFKD',x).encode('ascii','ignore').decode().lower())
  a=norm(c.get('title',''));b=norm(name);return 0 if a==b else 1 if a and(a in b or b in a)else 2
 def search(self,i,q):
  b,m=self.fetch('https://zeno.fm/api/stations/?'+urlencode({'query':q}))
  with self.lock:
   self.rows[i]['searches']=[x for x in self.rows[i]['searches']if canonical(x['url'])!=canonical(m['url'])]+[m]
  if b is None:return[]
  if urlsplit(m.get('final_url','')).hostname not in('zeno.fm','www.zeno.fm'):
   m['error']='primary_search_redirect_outside_zeno';return[]
  try:
   o=json.loads(b);cards=o['data']
   if not isinstance(cards,list):raise ValueError('not a search list')
  except(ValueError,KeyError,TypeError):m['error']='invalid_search_json_contract';return[]
  cards=[dict(id=c.get('id'),slug=c['slug'],title=c.get('title',''))for c in cards if isinstance(c,dict)and isinstance(c.get('slug'),str)]
  with self.lock:
   e=self.rows[i];known={c['slug']for c in e['discovered_cards']};e['discovered_cards'].extend(c for c in cards if c['slug']not in known);e['search_totals']=list(set(e.get('search_totals',[])+[o.get('total',len(cards))]))
  return sorted(cards,key=lambda c:self.rank(c,self.rows[i]['row']['station']['name']))
 def initial(self,i,secondary=False):
  with self.lock:
   e=self.rows[i];name=e['row']['station']['name']
   if e.get('secondary_done'if secondary else'stage1_done'):return
  q=name
  if secondary:
   if e['status']in('logo-frozen','identity-passed'):return
   q=' '.join(re.sub(r'\b(?:radio|rádio|r[aá]d[ií]o|fm|am|online|web|live|station)\b',' ',name,flags=re.I).split()).strip(' -–')
  if not secondary or(len(q)>=3 and q.casefold()!=name.casefold()):
   for c in self.search(i,q)[:3]:
    with self.lock:ready=self.rows[i]['status']=='logo-frozen'
    if ready:break
    self.detail(c['slug'])
    with self.lock:
     if c['slug']not in self.rows[i]['details_checked']:self.rows[i]['details_checked'].append(c['slug'])
  with self.lock:self.rows[i]['secondary_done'if secondary else'stage1_done']=True
 def pending_details(self):
  # Cached details must also be ingested: they can resolve another exact stream ref.
  with self.lock:return sorted({c['slug']for e in self.rows if e['status']not in('logo-frozen',)for c in e['discovered_cards']})
 def checkpoint(self,final=False,run_hook=True):
  with self.lock:
   rows=json.loads(json.dumps(self.rows));stats=dict(self.counts,phase=self.phase,candidates=len(rows),stage1_complete=sum(e.get('stage1_done',False)for e in rows),states=dict(Counter(e['status']for e in rows)),source_ready=sum(e['status']=='logo-frozen'for e in rows),unique_successful_urls=len(self.cache),request_concurrency_max=4,maximum_attempts=3,updated_utc=utc(),started_utc=self.started,final=final,graphic_approved=False)
   atomic(self.root/'source-review-rows.json',dict(schema=1,scope='source-only-not-graphic-approved',entries=rows));atomic(self.root/'progress.json',stats)
   # Re-export imported successful cache too, never failure-derived decisions.
   journal=self.root/'http-success-cache.jsonl';tmp=journal.with_suffix('.tmp');tmp.write_text(''.join(json.dumps(m,ensure_ascii=False,separators=(',',':'))+'\n'for m in self.cache.values()));tmp.replace(journal)
  print(json.dumps(stats),flush=True)
  if run_hook and self.args.checkpoint_hook:
   for _ in range(4):self.semaphore.acquire()
   try:result=subprocess.run([self.args.checkpoint_hook,str(self.root),self.phase],check=False)
   finally:
    for _ in range(4):self.semaphore.release()
   if result.returncode:raise RuntimeError('caller checkpoint hook failed '+str(result.returncode))
 def run_tasks(self,fn,items):
  executor=cf.ThreadPoolExecutor(max_workers=4);futures=[]
  try:
   futures=[executor.submit(fn,x)for x in items]
   for f in cf.as_completed(futures):
    f.result();self.tasks_since_checkpoint+=1
    if self.tasks_since_checkpoint>=self.args.checkpoint_every:self.checkpoint();self.tasks_since_checkpoint=0
  except BaseException:
   self.stop.set()
   for f in futures:f.cancel()
   executor.shutdown(wait=True,cancel_futures=True);raise
  else:executor.shutdown(wait=True)
  self.checkpoint()
 def run(self):
  self.checkpoint();self.phase='resume-exact-identities';self.run_tasks(self.detail,sorted({e['api_station']['slug']for e in self.rows if e['status']=='identity-passed'and e.get('api_station')}))
  self.phase='name-query-and-priority-details';self.run_tasks(self.initial,[e['index']for e in self.rows if not e.get('stage1_done')])
  self.phase='remaining-primary-details';self.run_tasks(self.detail,self.pending_details())
  self.phase='distinctive-name-discovery';self.run_tasks(lambda i:self.initial(i,True),[e['index']for e in self.rows if not e.get('secondary_done')])
  self.phase='remaining-secondary-details';self.run_tasks(self.detail,self.pending_details())
  with self.lock:
   for e in self.rows:
    if e['status']=='candidate':
     failed=[m for m in e['searches']if m.get('status')!=200 or m.get('error')]+[self.errors[canonical('https://zeno.fm/api/stations/'+c['slug'])]for c in e['discovered_cards']if canonical('https://zeno.fm/api/stations/'+c['slug'])in self.errors]
     if failed:e.update(status='pending',retrieval_pending=True,retrieval_errors=failed)
     else:e.update(status='hold',hold_reason='no_exact_stream_and_explicit_country_match_in_observed_primary_results')
  self.phase='complete-observed-source-freeze-not-graphic-approval';self.checkpoint(True)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',required=True);p.add_argument('--input',required=True);p.add_argument('--cache');p.add_argument('--checkpoint-every',type=int,default=100);p.add_argument('--checkpoint-hook');a=p.parse_args()
 if a.checkpoint_every<1:p.error('--checkpoint-every must be positive')
 f=Freeze(a)
 try:f.run()
 except BaseException:
  f.phase='interrupted-technical-pending';f.checkpoint(run_hook=False);raise
if __name__=='__main__':main()
