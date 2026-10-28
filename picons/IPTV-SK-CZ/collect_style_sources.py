"""Pin official negative artwork found on the stations' own pages."""
from pathlib import Path
from urllib.request import Request,urlopen
import json,re,hashlib,xml.etree.ElementTree as ET
R=Path(__file__).resolve().parent
pages=json.loads((R/'research/pages.json').read_text())
entries=[]
def pin(country,identity,style,url,raw,page,kind='download'):
    suffix='.svg' if kind=='inline-svg' else Path(url.split('?')[0]).suffix
    path=R/'sources'/('style-'+hashlib.sha256(raw).hexdigest()[:24]+suffix)
    path.write_bytes(raw)
    spec=dict(country=country,identity_key=identity,style=style,url=url,
              source_page=page,source_type=kind,path=str(path.relative_to(R)),
              sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),
              evidence='Exact official negative brand artwork observed on the station homepage; no recolouring.')
    entries.append(spec)
for p in pages:
    if p['url']=='https://trnavske.radio/' and p.get('file'):
        text=(R/p['file']).read_text()
        vector=next(m for m in re.findall(r'<svg\b[^>]*>.*?</svg>',text,re.S) if 'class="h__logo"' in m)
        assert '#fff' in vector and '#f15b38' in vector
        pin('SK','trnavskeradio','black',p['url']+'#warder-negative-header-logo',ET.tostring(ET.fromstring(vector)),p['url'],'inline-svg')
    if p['url']=='https://www.freshradio.sk/':
        image=next(i for i in p['images'] if i.get('class')=='wnd-logo-img')
        url=image['src'];assert 'white-transparent' in url
        with urlopen(Request(url,headers={'User-Agent':'Warder-Radio-Catalog/1.0'}),timeout=12) as response:
            raw=response.read(4*1024*1024+1)
        assert len(raw)<=4*1024*1024
        pin('SK','freshradio','black',url,raw,p['url'])
(R/'catalog/style-sources.json').write_text(json.dumps({'rows':entries},ensure_ascii=False,indent=2)+'\n')
print('Official negative sources:',len(entries))
