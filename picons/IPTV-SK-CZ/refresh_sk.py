from pathlib import Path
from html.parser import HTMLParser
from urllib.request import Request,urlopen
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor
import json,hashlib,re
R=Path(__file__).resolve().parent
class PlayerList(HTMLParser):
 def __init__(self):super().__init__();self.rows=[];self.href=None
 def handle_starttag(self,t,a):
  a=dict(a)
  if t=='a' and a.get('href','').startswith('/player/') and 'data-ids' in a:self.href=a['href']
  if t=='div' and 'radioitem' in a.get('class','') and self.href:self.rows.append({'name':a.get('title',''),'page_url':urljoin('https://www.radia.sk',self.href)})
  if t=='span' and 'radiologo' in a.get('class','') and self.rows:self.rows[-1]['logo_class']=a['class']
p=PlayerList();p.feed((R/'research/radia-sk-player.html').read_text());rows=list({x['page_url']:x for x in p.rows}.values())
(R/'research/radia-sk-stations.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
print('Slovak directory records',len(rows),flush=True)
folder=R/'research/sk-player-pages';folder.mkdir(exist_ok=True)
def fetch(row):
 row=dict(row);target=folder/(hashlib.sha256(row['page_url'].encode()).hexdigest()[:20]+'.html')
 try:
  if not target.exists():
   with urlopen(Request(row['page_url'],headers={'User-Agent':'Mozilla/5.0'}),timeout=10) as response:target.write_bytes(response.read(2*1024*1024))
  row['file']=str(target.relative_to(R));s=target.read_text()
  row['stream_candidates']=list(dict.fromkeys(re.findall(r'https?[^\s<>"\']+\.(?:mp3|aac|m3u8)(?:[^\s<>"\']*)',s)))
 except Exception as error:row['error']=str(error)
 return row
with ThreadPoolExecutor(max_workers=6) as pool:results=list(pool.map(fetch,rows))
(R/'research/radia-sk-stream-pages.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
print('Retrieved',sum('file' in r for r in results),'stream candidate pages',sum(bool(r.get('stream_candidates')) for r in results),flush=True)
print(json.dumps(results[:2],ensure_ascii=False),flush=True)
