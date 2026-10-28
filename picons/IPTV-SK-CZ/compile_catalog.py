"""Build a refresh candidate using recent discovery checks and pinned identity rules.
Keeps the original full bouquet intact on disk. Publication requires review.
"""
from pathlib import Path
from urllib.parse import urlsplit,unquote,urlunsplit,parse_qsl,urlencode
import json,hashlib,re,runpy,contextlib,io
R=Path(__file__).resolve().parent
with contextlib.redirect_stdout(io.StringIO()):M=runpy.run_path(str(R/'plan_refresh.py'))
key,recent=M['key'],M['recent'];old=json.loads((R/'catalog/stations.json').read_text())['stations']
original=R.parent/'deliverables/radio-fixed/userbouquet.warder.radio';raw=original.read_text()
publishers={'SK':json.loads((R/'research/radia-sk-stations.json').read_text()),'CZ':json.loads((R/'research/radia-stations.json').read_text())}
publisher_names={}
def canonical_url(u):
 p=urlsplit(unquote(u));return (p.hostname,p.port,p.path.rstrip('/'),p.query)
def stable_stream(u):
 p=urlsplit(u)
 if (p.hostname or '').endswith('.radiojar.com'):
  p=p._replace(query=urlencode([(k,v) for k,v in parse_qsl(p.query) if k not in ('rj-tok','rj-ttl')]))
 return urlunsplit(p)
def aliases(name):
 name=re.sub(r'\([^)]*(?:\d+\s*k|ogg|flac|vorbis|mp3|aac)[^)]*\)', '', name, flags=re.I)
 name=re.sub(r'\s*\d+\s*(?:kbps|kb)\s*$','',name,flags=re.I)
 name=re.sub(r'\s*[-|]?\s*(?:flac|hd|ogg|vorbis|mp3|aac)\s*$','',name,flags=re.I)
 name=re.sub(r'\s*\d+\s*$','',name) if re.search(r'\s+(?:aac|mp3)\s+\d+\s*$',name,re.I) else name
 name=re.sub(r'(?:32|64|128|192|256|320)$','',name)
 name=re.sub(r'^RTVS\s*','',name,flags=re.I)
 k=key(name)
 k={'infovojnask':'infovojna','infovojna2':'infovojna','kissradio':'kiss','impulsraaadio':'impuls','radiodechovka':'dechovka','class icprague':'classicpraha','classicprague':'classicpraha','hitfmplus':'hitradiofmplus','hitradiofmcrystal':'hitradiocrystal','hitradiocrystal':'hitradiocrystal','fajnfresh':'fajnfresh','metalheart':'metalheartradio','raduoproglas':'proglas','wehouseradio':'wehouse','wehouse':'wehouse','zonerundergroundnetwork':'zun','zunradio':'zun','patriarsi':'patriaradio','jubilanti':'betahramejubilantom','radiaczbirds':'relaxacezpevptaku','radiaczfire':'relaxaceohenvkrbu','radiaczsea':'relaxacemore','radiacztrain':'relaxacejedoucivlak','countryradio':'country','funradio':'fun','funradio8090':'fun8090','funradiocz':'funcz','funradioceskoslovenskehity':'funcz','funradiodance':'fundance','funradiochill':'funchill','funradiomilenialky':'funmilenialky','patriarsi':'patriaradio','helax937':'helax','cityfm':'hitradiocity','hitradiocity937fm':'hitradiocity','citymilenium':'hitradiomilenium','radiovlnaoldiesparty':'vlnaoldiesparty'}.get(k,k)
 return {'frekvence1actve':'frekvence1','evropa2actve':'evropa2','evropa2radio':'evropa2','evropa2aac':'evropa2','evropa2mp3':'evropa2','radio1':'1','bestfm':'bestfm','sro1radioslovensko256k':'slovensko'}.get(k,k)
def rank(r):
 codec=r.get('codec','').upper();bit=r.get('bitrate',0)
 return (codec=='MP3',codec in ('AAC','AAC+'),0<bit<=320,bit)
publisher_names={c:{aliases(r['name']):r['name'] for r in rows} for c,rows in publishers.items()}
reserved=set()
for line in raw.splitlines():
 if line.startswith('#SERVICE '):reserved.add('_'.join(line[9:].split(':',10)[:10]))
registry_path=R/'catalog/identity-registry.json'
registry=json.loads(registry_path.read_text())['stations'] if registry_path.exists() else []
assigned=set();catalog=[];skipped=[];duplicates=[]
for country in ['SK','CZ']:
 groups={};rb=json.loads((R/f'research/{country}-radio-browser.json').read_text())
 for row in rb:
  name=' '.join(row['name'].split());u=row.get('url_resolved') or row['url'];k=aliases(name)
  if country=='SK' and k=='pyramida':
   skipped.append({'country':country,'name':name,'reason':'Programme ended 2025-02-28 per STVR; not a current station','evidence':'https://www.stvr.org/media/a542/file/item/sk/0002/programovy_koncept_stvr_2025.WEZw.pdf'});continue
  if not recent(row) or row.get('codec','').upper() not in ('MP3','AAC','AAC+','OGG','FLAC','OPUS') or not row.get('homepage') or not k:continue
  if not M['identity_consistent'](name,row):skipped.append({'country':country,'name':name,'reason':'Station identity conflicts with broadcaster stream path'});continue
  home=urlsplit(row['homepage']).hostname or ''
  if home.endswith(('.fr','.si','.ua')) or home in ('www.laradioplus.com','laradioplus.com') or re.search(r'\b(?:TV|Televize|Television)\b',name,re.I) or name.startswith(('Óčko','TA3')):
   skipped.append({'country':country,'name':name,'reason':'Foreign-country homepage or television entry; not a local radio service'});continue
  if urlsplit(u).scheme not in ('http','https'):continue
  cro={'d-dur.rozhlas.cz':('ddur',('d-dur','ddur')),'jazz.rozhlas.cz':('jazz',('jazz',)),'dvojka.rozhlas.cz':('dvojka',('cro2','dvojka')),'vltava.rozhlas.cz':('vltava',('cro3','vltava'))}
  if country=='CZ' and home in cro and any(token in u.lower() for token in cro[home][1]):k=cro[home][0]
  if home in ('radia.cz','www.radia.cz') and urlsplit(row['homepage']).path.startswith('/radia/'):
   slug=urlsplit(row['homepage']).path.strip('/').split('/')[-1];station=next((r for r in publishers['CZ'] if r['slug']==slug),None)
   if station:k=aliases(station['name'])
  groups.setdefault(k,[]).append(row)
 urls_seen={}
 for k,rows in sorted(groups.items()):
  row=max(rows,key=rank);u=stable_stream(row.get('url_resolved') or row['url']);uk=canonical_url(u)
  if uk in urls_seen:duplicates.append({'country':country,'name':row['name'],'same_stream_as':urls_seen[uk]});continue
  matched=[x for x in old if x['country']==country and ((aliases(x['name'])==k and not x['name'].strip().isdigit()) or canonical_url(x['stream_url']) in {canonical_url(r.get('url_resolved') or r['url']) for r in rows})]
  uuids={r['stationuuid'] for r in rows}
  previous=[x for x in registry if x['country']==country and (uuids & set(x.get('source_stationuuids',[])))]
  ref=next((x['service_reference'] for x in previous if x['service_reference'].replace(':','_') not in assigned),None)
  if ref is None:ref=next((x['service_reference'] for x in matched if x['service_reference'].replace(':','_') not in assigned),None)
  if ref is None:
   nonce=0
   while True:
    h=hashlib.sha256(f'{country}|{k}|{nonce}'.encode()).hexdigest().upper();sid=f'{int(h[:4],16) or 1:X}';tsid=f'{int(h[4:8],16) or 1:X}';ref=f'4097:0:2:{sid}:{tsid}:EC:0:0:0:0'
    if ref.replace(':','_') not in reserved and ref.replace(':','_') not in assigned:break
    nonce+=1
  assigned.add(ref.replace(':','_'));name=publisher_names[country].get(k) or ' '.join(row['name'].split())
  if name=='RÁDIO FM':name='Rádio_FM'
  name=re.sub(r'[\x00-\x1f\x7f]',' ',name).strip()
  entry={'country':country,'name':name,'service_reference':ref,'picon_filename':ref.replace(':','_')+'.png','stream_url':u,'homepage':row['homepage'],'source_stationuuids':sorted(uuids),'source_stationuuid':row['stationuuid'],'catalogue_lastcheck':row['lastchecktime_iso8601'],'identity_key':k,'retained_original_reference':bool(matched),'status':'refresh-candidate-requires-review'}
  entry['reference_aliases']=sorted({x['service_reference'] for x in matched+previous} | {a for x in previous for a in x.get('reference_aliases',[])})
  catalog.append(entry);urls_seen[uk]=name
# Retain unresolved old entries: missing discovery metadata is not proof of closure.
# Two explicitly identified stale entries are excluded from the SK selection.
excluded_old=[];retained_unverified=[]
for row in old:
 identity=aliases(row['name'])
 if any(x['country']==row['country'] and (x['identity_key']==identity or canonical_url(x['stream_url'])==canonical_url(row['stream_url'])) for x in catalog):continue
 if row['country']=='SK' and row['name'] in ('N-Radio','Radio Yes','SRo 7 - Radio Pyramida'):
  excluded_old.append(dict(row,reason={'N-Radio':'This address belongs to French NRadio, not a current Slovak station.','Radio Yes':'Radio Yes ended; Radio Topolcany is listed under its current identity.','SRo 7 - Radio Pyramida':'Radio Pyramida ended 2025-02-28 according to STVR.'}[row['name']],evidence=['https://www.fluxradios.com/Radios-France/France-Groupe-Isa-Media-Development/NRadio-France','https://www.radia.sk/radia/yes','https://www.stvr.org/media/a542/file/item/sk/0002/programovy_koncept_stvr_2025.WEZw.pdf']))
  continue
 stem=row['service_reference'].replace(':','_')
 if stem in assigned:continue
 entry=dict(row,identity_key=identity,retained_original_reference=True,status='retained-original-awaiting-verification',homepage='',source_stationuuid=None,catalogue_lastcheck=None)
 catalog.append(entry);assigned.add(stem);retained_unverified.append(row['name'])
# A merged codec variant keeps its original picon identity as an alias. Never
# assign an alias which is the primary reference of another current programme.
primaries={r['service_reference'] for r in catalog};alias_owner={}
for r in catalog:
 aliases_for_station=[]
 for ref in r.get('reference_aliases',[]):
  if ref in primaries or ref in alias_owner:continue
  alias_owner[ref]=r['service_reference'];aliases_for_station.append(ref)
 r['reference_aliases']=aliases_for_station
# Extract the original blocks exactly; replace only Slovensko and Cechy sections.
lines=raw.splitlines(keepends=True);sections=[];start=0
for i,line in enumerate(lines):
 if line.startswith('#SERVICE ') and line[9:].split(':')[1]=='64':
  if i>start:sections.append(lines[start:i])
  start=i
sections.append(lines[start:]);out=[];replaced=set()
def block(country):
 label='Slovensko' if country=='SK' else 'Čechy';result=['#SERVICE 1:64:2:0:0:0:0:0:0:0:\n','#DESCRIPTION '+label+'\n']
 for r in sorted((x for x in catalog if x['country']==country),key=lambda x:aliases(x['name'])):
  result.extend(['#SERVICE '+r['service_reference']+':'+r['stream_url'].replace(':','%3a')+'\n','#DESCRIPTION '+r['name']+'\n'])
 return result
unchanged=[]
for section in sections:
 label=next((l[13:].strip() for l in section[:3] if l.startswith('#DESCRIPTION ')),None)
 c={'Slovensko':'SK','Čechy':'CZ'}.get(label)
 if c:out.extend(block(c));replaced.add(c)
 else:out.extend(section);unchanged.append(''.join(section))
assert replaced=={'SK','CZ'} and len(assigned)==len(catalog)
final=''.join(out)
assert all(s in final for s in unchanged)
folder=R/'output';folder.mkdir(exist_ok=True)
(folder/'userbouquet.warder.radio').write_text(final)
(folder/'userbouquet.warder.sk-cz.radio').write_text('#NAME Warder IPTV rádiá SK/CZ\n'+''.join(block('SK')+block('CZ')))
report={'schema':1,'status':'candidate-not-production','source_bouquet_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),'output_bouquet_sha256':hashlib.sha256((folder/'userbouquet.warder.radio').read_bytes()).hexdigest(),'stations':catalog,'excluded_old':excluded_old,'retained_original_pending_verification':retained_unverified,'skipped':skipped,'duplicate_stream_records':duplicates,'other_country_sections_unchanged':True,'limitations':['Recent Radio Browser online checks are not receiver playback confirmation.','No arbitrary station logo may be substituted for unresolved artwork.','FMSTREAM printed labels may contain older or incomplete entries.']}
registry_path.write_text(json.dumps({'schema':1,'stations':[{k:r[k] for k in ('country','name','identity_key','service_reference','reference_aliases','stream_url','source_stationuuids') if k in r} for r in catalog]},ensure_ascii=False,indent=2)+'\n')
(R/'catalog/refreshed-stations.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print({c:sum(x['country']==c for x in catalog) for c in ['SK','CZ']},'duplicate streams removed',len(duplicates),'foreign/TV/identity conflicts',len(skipped),'retained refs',sum(x['retained_original_reference'] for x in catalog))
