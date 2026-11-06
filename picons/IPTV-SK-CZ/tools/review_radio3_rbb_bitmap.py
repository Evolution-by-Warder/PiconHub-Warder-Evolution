#!/usr/bin/env python3
"""Review official radio3/rbb broadcaster-supplied bitmap without altering logo.

Never touch production Warder picon archives, catalogues, feeds or earlier reviews.
"""
import io,hashlib,json
from pathlib import Path
from urllib.request import Request,urlopen

from PIL import Image,ImageDraw,ImageFont

ROOT=Path('picons/IPTV-SK-CZ/review/foreign-radio-20261104/radio3-official-rbb')
ROOT.mkdir(parents=True,exist_ok=True)
TEMPLATES=Path('plugin/artwork/templates/picons')
MASTERS={'black':'61e69f7fc46e340453bf74ccd7af6ac9d8eba9f8e232884659e1ea99f6abf3fe',
         'white':'c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589'}
URL='https://www.rbb-online.de/content/dam/rbb/rbb/unternehmen/presse/presseinformationen/2024/03/radio3_Logo_auf_Hintergrund-1-.jpg.jpg/size=966x543.jpg'
PAGE='https://www.rbb-online.de/unternehmen/presse/programmwochen/radio3/'
REF='4097_0_2_C634_62DF_ED_0_0_0_0.png'
SHA=lambda b:hashlib.sha256(b).hexdigest()

def original():
    frozen=ROOT/'official-rbb.jpg'
    if frozen.is_file():
        return frozen.read_bytes()
    with urlopen(Request(URL,headers={'User-Agent':'WarderRadioOfficialSourceAudit/1.0'}),timeout=40) as r:
        b=r.read(3*1024*1024+1)
    assert 0<len(b)<3*1024*1024
    return b

def make():
    raw=original()
    assert raw[:3]==b'\xff\xd8\xff', "Official station source is not JPG"
    image=Image.open(io.BytesIO(raw))
    image.load()
    assert image.width>=300 and image.height>=150
    source_wh=image.size
    source=image.convert('RGBA')
    frozen=ROOT/'official-rbb.jpg'
    if frozen.is_file():
        provenance=ROOT/'provenance.json'
        if provenance.exists():
            before=json.loads(provenance.read_text())
            assert before['source_sha256']==SHA(raw)
    else:
        frozen.write_bytes(raw)
    source.thumbnail((192,104),Image.Resampling.LANCZOS)
    expected_name=REF
    assert not any((Path('picons/IPTV-DE/packages')/n).is_dir() for n in (expected_name,))
    masters={'transparent':Image.new('RGBA',(220,132),(0,0,0,0))}
    for style,digest in MASTERS.items():
        data=(TEMPLATES/(style+'-sablona.png')).read_bytes()
        assert SHA(data)==digest
        masters[style]=Image.open(io.BytesIO(data)).convert('RGBA')
        assert masters[style].size==(220,132)
    results={}
    rendered={}
    for style in ('transparent','white','black'):
        board=masters[style].copy()
        board.alpha_composite(source,((220-source.width)//2,(132-source.height)//2))
        rendered[style]=board
        for w,h in ((50,30),(220,132),(400,240)):
            output=board if (w,h)==(220,132) else board.resize((w,h),Image.Resampling.LANCZOS)
            buf=io.BytesIO()
            output.save(buf,'PNG')
            data=buf.getvalue()
            name='%dx%d/%s/%s'%(w,h,style,REF)
            target=ROOT/'artwork'/name
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(data)
            results['%dx%d/%s'%(w,h,style)]=dict(path=str(Path('artwork')/name),bytes=len(data),sha256=SHA(data))
    sheet=Image.new('RGB',(1180,365),'#112038')
    d=ImageDraw.Draw(sheet)
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',20)
    small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',15)
    d.text((24,14),'radio3 (rbb) — OFICIALNY ORIGINAL OD VYSIELATELA · REVIEW ONLY',font=font,fill='#e5f6fc')
    d.text((24,43),'Original JPG + vlastne pozadie · Transparent / White / Black — bez prefarbenia.',font=small,fill='#b1cddd')
    for i,style in enumerate(('transparent','white','black')):
        x=24+i*382
        b=Image.new('RGB',(325,195),'#8290a5' if style=='transparent' else '#081827')
        icon=rendered[style].resize((325,195),Image.Resampling.LANCZOS)
        b.paste(icon,(0,0),icon)
        sheet.paste(b,(x,87))
        d.text((x+6,290),style.upper(),font=small,fill='#9ce9f5')
    d.text((24,332),'SOURCE: rbb-online.de · distinct whole-image alternative; permission and brand QA pending.',font=small,fill='#d3d8e4')
    sheet.save(ROOT/'review-sheet.png')
    metadata=dict(schema=1,stage='review_only',station='radio3 (rbb)',
                  reference='4097:0:2:C634:62DF:ED:0:0:0:0',
                  official_source_page=PAGE,source_url=URL,source_sha256=SHA(raw),
                  source_bytes=len(raw),source_dimensions=list(source_wh),
                  resized_wh=list(source.size),formats=results,
                  artwork_modified=False,original_background_preserved=True,
                  master_sha256=MASTERS,production_approved=False,
                  visual_review_pending=True,licence_review_pending=True)
    (ROOT/'provenance.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('RBB OFFICIAL ORIGINAL',SHA(raw),len(raw),source_wh)
    print('9 RENDERED',len(results),'review only; existing Warder masters preserved')

if __name__=='__main__':
    make()
