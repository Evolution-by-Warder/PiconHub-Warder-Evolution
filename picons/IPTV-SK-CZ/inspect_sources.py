from pathlib import Path
from urllib.request import Request,urlopen
from html.parser import HTMLParser
import json,hashlib
R=Path(__file__).resolve().parent
class Images(HTMLParser):
 def __init__(self):super().__init__();self.images=[]
 def handle_starttag(self,t,a):
  a=dict(a)
  if t=='img':self.images.append(a)
p=R/'research/radia-directory.html'
if not p.exists():
 with urlopen(Request('https://radia.cz/radia',headers={'User-Agent':'Mozilla/5.0'}),timeout=15) as response:p.write_bytes(response.read(4*1024*1024))
x=Images();x.feed(p.read_text());imgs=[i for i in x.images if '/media/' in i.get('src','')]
(R/'research/radia-logos.json').write_text(json.dumps(imgs,ensure_ascii=False,indent=2)+'\n')
print('Directory logos',len(imgs));print('\n'.join(i.get('alt','') for i in imgs))
rows=json.loads((R/'research/pages.json').read_text());print('\nSK official logo candidates:')
for p in rows:
 if any(t in p['url'] for t in ['.sk','funradio','rtvs']):
  imgs=[i for i in p.get('images',[]) if any(t in str(i).lower() for t in ['logo','brand'])]
  print(p['url'],str(imgs)[:700])
