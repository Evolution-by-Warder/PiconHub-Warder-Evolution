from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.request import urlopen
import json,hashlib,io
from PIL import Image
R=Path(__file__).resolve().parent
revision='e777edf594dab41a31ad2d5fedff5a579c8a3b5b';report=json.loads((R/'research/approved-radio-refresh.json').read_text());mapping={'Fun Radio Z':'fun','Melody Z':'melody','ReginaBA':'reginazapad','ReginaBB':'reginastred','ReginaKE':'reginavychod'}
tasks=[]
for row in report['mappings']:
 if row['station'] in mapping:
  for res,styles in row['artwork'].items():
   for style,spec in styles.items():tasks.append((mapping[row['station']],res,style,spec))
def get(task):
 name,res,style,spec=task;url='https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/'+revision+'/'+spec['path'];p=R/'approved'/name/res/(style+'.png');p.parent.mkdir(parents=True,exist_ok=True)
 if not p.exists():
  with urlopen(url,timeout=10) as response:p.write_bytes(response.read(2*1024*1024))
 raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==spec['sha256'];im=Image.open(io.BytesIO(raw));assert im.size==tuple(map(int,res.split('x')));im.verify()
 return name,res,style,{'path':str(p.relative_to(R)),'sha256':spec['sha256'],'source_url':url}
records={}
with ThreadPoolExecutor(max_workers=6) as pool:
 for name,res,style,spec in pool.map(get,tasks):records.setdefault(name,{}).setdefault(res,{})[style]=spec
(R/'catalog/approved-passthrough.json').write_text(json.dumps({'source_revision':revision,'stations':records},ensure_ascii=False,indent=2)+'\n');print('Verified approved PNG variants',len(tasks),flush=True)
