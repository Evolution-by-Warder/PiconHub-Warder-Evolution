from pathlib import Path
from urllib.request import Request,urlopen
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit,urlunsplit
from html.parser import HTMLParser
class Page(HTMLParser):
 def __init__(self):
  super().__init__();self.images=[];self.links=[];self.title="";self.in_title=False;self.link=None
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=="title":self.in_title=True
  if tag=="img" or tag=="meta" and a.get("property")=="og:image" or tag=="link" and "icon" in a.get("rel",""):self.images.append(a)
  if tag=="a" and a.get("href"):self.link={"href":a["href"],"text":""}
 def handle_data(self,data):
  if self.in_title:self.title+=data
  if self.link is not None:self.link["text"]+=data
 def handle_endtag(self,tag):
  if tag=="title":self.in_title=False
  if tag=="a" and self.link is not None:
   self.links.append(self.link);self.link=None
import json,hashlib
R=Path(__file__).resolve().parent
rows=json.loads((R/'catalog/logo-candidates.json').read_text());urls=set()
for r in rows:
 for c in r['candidates'][:1]:
  if c['homepage'] and urlsplit(c['homepage']).hostname:urls.add(c['homepage'])
urls.update(['https://radia.cz/','https://informace.rozhlas.cz/kontakt-pro-novinare-a-logotypy-ceskeho-rozhlasu-7753966'])
folder=R/'research/pages';folder.mkdir(exist_ok=True)
def fetch(url):
 key=hashlib.sha256(url.encode()).hexdigest()[:20];target=folder/(key+'.html');record={'url':url,'file':str(target.relative_to(R))}
 try:
  if target.exists():raw=target.read_bytes();final=url
  else:
   p=urlsplit(url);https=urlunsplit(('https',p.netloc,p.path,p.query,p.fragment))
   with urlopen(Request(https,headers={'User-Agent':'Mozilla/5.0 (Warder radio logo source verification)'}),timeout=10) as response:
    raw=response.read(3*1024*1024);final=response.url
   target.write_bytes(raw)
  page=Page();page.feed(raw.decode('utf-8','replace'));record.update(final_url=final,title=page.title,images=page.images,links=[x for x in page.links if any(w in (x['href']+' '+x['text']).lower() for w in ('logo','logotyp','.svg','.zip'))])
 except Exception as e:record['error']=str(e)
 return record
with ThreadPoolExecutor(max_workers=8) as pool:
 records=list(pool.map(fetch,sorted(urls)))
(R/'research/pages.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
print('Retrieved',sum('error' not in r for r in records),'of',len(records),'pages',flush=True)
for r in records:
 if 'radia.cz' in r['url'] or 'informace.rozhlas' in r['url']:print(json.dumps(r,ensure_ascii=False)[:13000],flush=True)
