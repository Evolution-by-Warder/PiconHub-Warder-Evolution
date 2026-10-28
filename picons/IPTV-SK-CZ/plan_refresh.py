"""Conservative candidate refresh: publisher identity plus recent catalogue evidence.
No uncertain station is deleted or renamed, and no discovery row is called live-tested.
"""
from pathlib import Path
from urllib.parse import urlsplit,unquote
from datetime import datetime,timezone
import json,re,unicodedata
R=Path(__file__).resolve().parent
old=json.loads((R/'catalog/stations.json').read_text())['stations']
def norm(v):
 s=unicodedata.normalize('NFKD',v.casefold()).encode('ascii','ignore').decode()
 s=re.sub(r'\([^)]*(?:flac|vorbis|kbps|aac|mp3)[^)]*\)','',s)
 s=re.sub(r'^(?:cesky rozhlas|sro|cro)\s*\d*\s*[-:]?\s*','',s)
 s=re.sub(r'^radio\s*','',s)
 return re.sub('[^a-z0-9]','',s)
ALIASES={'7sk':'7','impulsradio':'impuls','rsi':'slovakiainternational','regina':'reginazapad','reginazapad':'reginazapad','reginastred':'reginastred','reginavychod':'reginavychod','fm':'fm','funradioczsk':'funcz','funradio8090roky':'fun8090','funradiodance':'fundance','fajnradiofresh':'fajnfresh','fajnfreshradio':'fajnfresh','webra dioepigon':'epigon','webradioepigon':'epigon','spinradio':'spin','spin962fm':'spin','hit radiocity':'hitradiocity','country':'country','hitradiocityosmdesatka':'hitradioosmdesatka','hitradiocitydevadesatka':'hitradiodevadesatka','hitradiocitymilenium':'hitradiomilenium','hitradiocityzonalasky':'hitradiozonalasky','devin':'devin','patria':'patriaradio','dvojka':'dvojka','ceskyrozhlas2praha':'dvojka'}
def key(s):
 # Historical bouquet title: this is Dvojka (cro2), not Radio Praha (cro7).
 if s=='Cesky rozhlas 2 - Praha':return 'dvojka'
 n=norm(s);return ALIASES.get(n,n)
def urlkey(u):
 p=urlsplit(unquote(u));return (p.hostname,p.path.rstrip('/'),p.query)
def identity_consistent(name,row):
 # Radio Browser currently labels a Radiozurnal Sport URL as Olomouc too.
 # The broadcaster's station-specific rozhlas.stream paths cannot be interchanged.
 expected={'olomouc':'olomouc','radiozurnalsport':'radiozurnal_sport'}
 wanted=expected.get(key(name))
 if not wanted:return True
 for field in ('url','url_resolved'):
  u=row.get(field,'');p=urlsplit(u)
  if p.hostname=='rozhlas.stream' and wanted not in p.path.lower():return False
 return True
def score(row):
 codec=row.get('codec','').upper();bitrate=row.get('bitrate',0)
 return (codec=='MP3',codec in ('AAC','AAC+'),0<bitrate<=320,bitrate,str(row.get('lastchecktime','')))
catalogs={c:json.loads((R/f'research/{c}-radio-browser.json').read_text()) for c in ['SK','CZ']}
now=datetime.now(timezone.utc)
def recent(r):
 try:stamp=datetime.fromisoformat(r['lastchecktime_iso8601'].replace('Z','+00:00'));return r.get('lastcheckok')==1 and 0<=(now-stamp).total_seconds()<3*86400
 except (KeyError,ValueError,TypeError):return False
publishers={'SK':json.loads((R/'research/radia-sk-stations.json').read_text()),'CZ':json.loads((R/'research/radia-stations.json').read_text())}
result=[];used={c:set() for c in catalogs}
for row in old:
 country=row['country'];matches=[r for r in catalogs[country] if recent(r) and identity_consistent(row['name'],r) and any(urlkey(row['stream_url'])==urlkey(r.get(k,'')) for k in ['url','url_resolved'] if r.get(k))]
 match_kind='same-stream'
 if not matches:
  matches=[r for r in catalogs[country] if recent(r) and identity_consistent(row['name'],r) and key(r['name'])==key(row['name'])];match_kind='same-name'
 candidate=max(matches,key=score) if matches else None
 if candidate:used[country].add(key(candidate['name']))
 result.append(dict(row,action='review-replacement' if candidate and match_kind=='same-name' else 'keep',discovery_match_kind=match_kind if candidate else None,candidate_stream=(candidate.get('url_resolved') or candidate['url']) if candidate else None,candidate_name=candidate['name'] if candidate else None,catalogue_lastcheck=candidate.get('lastchecktime_iso8601') if candidate else None,receiver_or_direct_live_test=False))
added=[]
for country,stations in publishers.items():
 existing={key(r['name']) for r in old if r['country']==country}|used[country]
 for station in stations:
  name=station['name'];identity=key(name)
  if identity in existing:continue
  matches=[r for r in catalogs[country] if recent(r) and identity_consistent(name,r) and key(r['name'])==identity]
  if not matches:continue
  candidate=max(matches,key=score);existing.add(identity)
  added.append({'country':country,'name':name,'stream_url':candidate.get('url_resolved') or candidate['url'],'publisher_page':station.get('page_url') or 'https://radia.cz/radia/'+station['slug'],'catalogue_lastcheck':candidate.get('lastchecktime_iso8601'),'action':'review-addition','receiver_or_direct_live_test':False})
doc={'schema':1,'status':'candidate-not-published','built_at':now.isoformat(),'existing':result,'additions':added,'notes':['No deletion based on a transient request failure.','Publisher identity plus a recent Radio Browser check is discovery evidence, not a direct playback test.','Service references for retained stations remain unchanged.','Confirm meaningful station aliases and publisher stream identity before publication.']}
(R/'catalog/refresh-candidate.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n')
print('Existing:',len(result),'candidate replacements:',sum(r['action']=='review-replacement' for r in result),'publisher-backed candidate additions:',len(added))
print([(r['country'],r['name']) for r in added])
