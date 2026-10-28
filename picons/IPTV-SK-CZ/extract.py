from pathlib import Path
from urllib.parse import unquote
import json,csv,hashlib
ROOT=Path(__file__).resolve().parent
p=ROOT.parent/'deliverables/radio-fixed/userbouquet.warder.radio'
rows=[];section='';ref=''
for line in p.read_text().splitlines():
 if line.startswith('#SERVICE '):ref=line[9:]
 elif line.startswith('#DESCRIPTION '):
  name=line[13:];f=ref.split(':',10)
  if f[1]=='64':section=name
  elif section in ('Slovensko','Čechy'):
   assert f[0]=='4097' and f[2]=='2'
   rows.append(dict(country='SK' if section=='Slovensko' else 'CZ',name=name,service_reference=':'.join(f[:10]),picon_filename='_'.join(f[:10])+'.png',stream_url=unquote(f[10])))
assert len(rows)==212 and len({r['picon_filename'] for r in rows})==212
(ROOT/'catalog/stations.json').write_text(json.dumps({'schema':1,'bouquet_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'stations':rows},ensure_ascii=False,indent=2)+'\n')
with (ROOT/'catalog/stations.csv').open('w') as out:
 w=csv.DictWriter(out,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print('Extracted',len(rows))
