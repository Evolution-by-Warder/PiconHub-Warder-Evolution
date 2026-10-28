from pathlib import Path
from urllib.parse import urlsplit,unquote
import json,re,unicodedata
R=Path(__file__).resolve().parent
stations=json.loads((R/'catalog/stations.json').read_text())['stations']
def norm(s):return re.sub(r'[^a-z0-9]','',unicodedata.normalize('NFKD',s.casefold()).encode('ascii','ignore').decode())
def urlkey(u):
 p=urlsplit(unquote(u));return ((p.hostname or '').lower(),p.port or (443 if p.scheme=='https' else 80),p.path.rstrip('/'),p.query)
def looseurl(u):
 k=urlkey(u);return(k[0],k[2],k[3])
def names(s):
 s=re.sub(r'\s*\((?:flac|vorbis|mp3|aac|ogg|\d+\s*kbps)\)\s*','',s,flags=re.I)
 return {norm(s),norm(re.sub(r'^(?:radio|rádio|cesky rozhlas|český rozhlas|cro|sro)\s*(?:\d+\s*-\s*)?','',s,flags=re.I))}
rows=[]
for st in stations:
 candidates=[]
 for r in json.loads((R/('research/'+st['country']+'-radio-browser.json')).read_text()):
  score=100 if any(looseurl(st['stream_url'])==looseurl(r.get(k,'')) for k in ('url','url_resolved') if r.get(k)) else 80 if names(st['name'])&names(r['name']) else 0
  if score:candidates.append(dict(score=score,name=r['name'],homepage=r['homepage'],favicon=r['favicon'],url=r['url'],stationuuid=r['stationuuid'],lastcheckok=r.get('lastcheckok')))
 candidates.sort(key=lambda r:(-r['score'],-r['lastcheckok'],not bool(r['favicon'])))
 rows.append(dict(st,candidates=candidates))
(R/'catalog/logo-candidates.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
print('With candidate',sum(bool(r['candidates']) for r in rows),'of',len(rows))
for r in rows:
 if not r['candidates']:print('MISSING',r['country'],r['name'])
for r in rows[:20]:
 if r['candidates']:print('MATCH',r['name'],[(c['name'],c['score'],c['favicon']) for c in r['candidates'][:1]])
