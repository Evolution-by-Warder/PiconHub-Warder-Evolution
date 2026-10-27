#!/usr/bin/env python3
"""Append owner-authorized ASA artwork while preserving the 80 approved DAB PNGs."""
import argparse, csv, hashlib, io, json, shutil, tempfile, zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import urlopen
from xml.etree import ElementTree as ET
import cairosvg
from PIL import Image, ImageDraw

HERE=Path(__file__).resolve().parent
ROOT=Path(tempfile.mkdtemp(prefix='warder-asa-'))
CURRENT=ROOT/'current'
OUT=ROOT/'out'
BASE='ee5bccd2b06eb42ab9913cf158873443cc018682'
REPO='Evolution-by-Warder/PiconHub-Warder-Evolution'
URL='https://www.dabplus.de/wp-content/themes/dabplus21/assets/svg/asa-logo.svg'
SVG_SHA='3c4d930cb58e2b56f04a41c00dbed6dacc83a8ba6707dd42878b3602c2c3e0f8'
STYLES=('transparent','white','black')
SIZES=((50,30),(220,132),(400,240))
REFS=('4115_0_2_1019_C98_3_EB0000_1019_10C4_10BC.png','4115_0_2_1019_5_85_C00000_1019_10C4_10BC.png')
def sha(b):return hashlib.sha256(b).hexdigest()
def write(path,b):
    p=OUT/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
def document(path,d):write(path,(json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode())
def build():
    raw=(ROOT/'asa-official.svg').read_bytes();assert sha(raw)==SVG_SHA
    for node in ET.fromstring(raw).iter():
        assert all(not k.endswith('href') or v.startswith('#') for k,v in node.attrib.items())
    logo=Image.open(io.BytesIO(cairosvg.svg2png(bytestring=raw,output_width=2400))).convert('RGBA')
    logo=logo.crop(logo.getbbox())
    config=json.loads((CURRENT/'artwork.json').read_text())
    masters={}
    for style,digest in config['master_sha256'].items():
        b=(CURRENT/(style+'-sablona.png')).read_bytes();assert sha(b)==digest
        masters[style]=Image.open(io.BytesIO(b)).convert('RGBA');assert masters[style].size==(220,132)
    variants={};art={}
    for size in SIZES:
        size_key='%dx%d'%size
        fit=(round(192*size[0]/220),round(104*size[1]/132))
        scaled=logo.copy();scaled.thumbnail(fit,Image.Resampling.LANCZOS)
        x,y=(size[0]-scaled.width)//2,(size[1]-scaled.height)//2
        variants[size_key]={}
        for style in STYLES:
            if style=='transparent':background=Image.new('RGBA',size)
            elif size==(220,132):background=masters[style].copy()
            else:background=masters[style].convert('RGBa').resize(size,Image.Resampling.LANCZOS).convert('RGBA')
            result=background.copy();result.alpha_composite(scaled,(x,y))
            for box in ((0,0,size[0],y),(0,y+scaled.height,size[0],size[1]),(0,y,x,y+scaled.height),(x+scaled.width,y,size[0],y+scaled.height)):
                assert result.crop(box).tobytes()==background.crop(box).tobytes()
            out=io.BytesIO();result.save(out,format='PNG',compress_level=9);data=out.getvalue()
            path='picons/DAB/asa/artwork/'+size_key+'/'+style+'/asa-de.png'
            write(path,data);variants[size_key][style]={'path':path,'sha256':sha(data),'bytes':len(data)};art[size_key,style]=data
    write('picons/DAB/sources/official/asa-logo.svg',raw)
    write('picons/DAB/sources/owner/asa.jpg',(ROOT/'asa-owner-original.jpg').read_bytes())
    spec={'variants':{s:'sources/official/asa-logo.svg' for s in STYLES},'source':URL,'source_sha256':{s:SVG_SHA for s in STYLES},'provenance':{'url':URL,'source_page':'https://www.dabplus.de/asa/','owner_reference':'sources/owner/asa.jpg','identity':'Exact official ASA / Automatic Safety Alert logo corresponding to the owner-supplied reference.'},'variant_policy':'Preserve original official colours, geometry and tagline on all frozen backgrounds. No invented or recoloured logo.'}
    config['stations']['ASA DE']=spec;config['unresolved'].pop('ASA DE',None)
    document('picons/DAB/catalog/artwork.json',config)
    rows=list(csv.DictReader((CURRENT/'DAB_radio_picon_mapping.csv').open(encoding='utf-8-sig')))
    asa_rows=[r for r in rows if r['station']=='ASA DE'];assert {r['picon_filename'] for r in asa_rows}==set(REFS)
    for row in asa_rows:row.update(logo_source=URL,logo_verified='SOURCE_CHECKED')
    stream=io.StringIO(newline='');w=csv.DictWriter(stream,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
    write('picons/DAB/catalog/DAB_radio_picon_mapping.csv',stream.getvalue().encode('utf-8-sig'))
    preview=json.loads((CURRENT/'authentic-preview.json').read_text());assert len(preview['records'])==80
    old_records=list(preview['records'])
    for row in asa_rows:
        preview['records'].append(dict(row,logo_source=URL,logo_verified='SOURCE_CHECKED',sha256={s:sha(art['220x132',s]) for s in STYLES},status='QC_READY',approved_master_v9=False))
        for style in STYLES:
            data=art['220x132',style];name=row['picon_filename']
            write('picons/DAB/preview/authentic/'+style+'/'+name,data)
            orbital='23.5e' if '_EB0000_' in name else '19.2e'
            write('picons/'+orbital+'/dab/'+style+'/'+name,data)
    assert preview['records'][:80]==old_records
    preview.update(station_count=52,reference_count=82);preview['unresolved'].pop('ASA DE',None)
    document('picons/DAB/catalog/authentic-preview.json',preview)
    release=json.loads((CURRENT/'release.json').read_text());assert release['reference_count']==80
    def package(style):
        p=release['packages'][style];raw=urlopen(p['url'],timeout=60).read()
        assert len(raw)==p['bytes'] and sha(raw)==p['sha256']
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            assert len(z.namelist())==80 and set(z.namelist())==set(p['files'])
            old={n:z.read(n) for n in z.namelist()}
            assert all(sha(b)==p['files'][n] for n,b in old.items())
        output=io.BytesIO(raw)
        with zipfile.ZipFile(output,'a',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            for name in REFS:
                info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.external_attr=0o100644<<16;info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,art['220x132',style])
        data=output.getvalue()
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            assert len(z.namelist())==82 and all(z.read(n)==b for n,b in old.items())
            assert all(z.read(n)==art['220x132',style] for n in REFS)
        path='picons/DAB/packages/dab-'+style+'-220x132.zip';write(path,data)
        p.update(bytes=len(data),sha256=sha(data));p['files'].update({n:sha(art['220x132',style]) for n in REFS})
        return style,{'preserved':80,'added':2,'bytes':len(data),'sha256':sha(data)}
    with ThreadPoolExecutor(max_workers=3) as pool:evidence=dict(pool.map(package,STYLES))
    release.update(station_count=52,reference_count=82);release['unresolved'].pop('ASA DE',None)
    (ROOT/'next-release.json').write_text(json.dumps(release,ensure_ascii=False,indent=2)+'\n')
    plan={'schema':1,'status':'owner-authorized','owner_direction':'Create ASA DE from the supplied logo in all standard sizes/backgrounds and include it only in standalone DAB and the full 23.5E satellite packages, excluding Canal+/Skylink/provider groups; publish on GitHub. 27 October 2026.','baseline_commit':BASE,'official_source':URL,'source_sha256':SVG_SHA,'master_sha256':config['master_sha256'],'references':list(REFS),'artwork':variants,'satellite_selectors':['235E'],'standalone_sources':['DAB'],'excluded_selectors':['192E','SKYLINK','CANALPLUS_SK','CANALPLUS_CZ'],'standalone_packages':evidence,'preservation':'Every pre-existing approved DAB PNG is byte-identical; 80 retained + 2 ASA references per archive.'}
    document('picons/DAB/asa/approval.json',plan)
    sheet=Image.new('RGB',(720,310),(55,65,75));draw=ImageDraw.Draw(sheet)
    for i,style in enumerate(STYLES):
        image=Image.open(io.BytesIO(art['220x132',style]));sheet.paste(image,(10+240*i,55),image);draw.text((10+240*i,20),style,fill='white')
    draw.text((10,220),'Official ASA source / frozen Warder masters / 220x132',fill='white')
    sheet.save(ROOT/'review.png')
    print(json.dumps(plan['standalone_packages'],indent=2),flush=True)
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();OUT=args.output.resolve();CURRENT.mkdir()
    baseline='https://raw.githubusercontent.com/'+REPO+'/'+BASE+'/'
    for name in ('artwork.json','release.json','authentic-preview.json','DAB_radio_picon_mapping.csv'):
        (CURRENT/name).write_bytes(urlopen(baseline+'picons/DAB/catalog/'+name,timeout=60).read())
    for style in ('white','black'):
        name=style+'-sablona.png'
        (CURRENT/name).write_bytes(urlopen(baseline+'plugin/artwork/templates/picons/'+name,timeout=60).read())
    shutil.copyfile(HERE.parent/'sources/official/asa-logo.svg',ROOT/'asa-official.svg')
    shutil.copyfile(HERE.parent/'sources/owner/asa.jpg',ROOT/'asa-owner-original.jpg')
    build()
    shutil.copyfile(ROOT/'review.png',OUT/'review.png')
    shutil.copyfile(ROOT/'next-release.json',OUT/'release-unpinned.json')
    print('Pin release-unpinned.json URLs only after the generated ZIP assets are publicly verified at their immutable commit.')
