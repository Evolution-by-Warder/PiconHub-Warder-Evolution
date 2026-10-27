#!/usr/bin/env python3
"""Reproduce authentic preview picons using pinned logos and immutable masters.

Pillow/CairoSVG are build-host dependencies, never receiver dependencies.
"""
import copy,csv,hashlib,io,json,zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
from PIL import Image
import cairosvg
from component_masks import components
ROOT=Path(__file__).resolve().parent
MASTERS=ROOT.parents[1]/'plugin/artwork/templates/picons'

def sha(raw):return hashlib.sha256(raw).hexdigest()

def load_logo(path,fix=None,pixel_fix=None,monochrome=None):
    raw=path.read_bytes()
    if path.suffix=='.svg':
        tree=ET.fromstring(raw)
        for node in tree.iter():
            for key,value in node.attrib.items():
                if key.endswith('href') and not value.startswith(('#','data:image/png;base64,','data:image/jpeg;base64,')):raise ValueError('External SVG resource')
        if fix:
            original=copy.deepcopy(tree)
            group=tree if fix.get('svg_child') is None else tree[fix['svg_child']]
            for index in fix['children']:
                old=group[index].get('style','')
                group[index].set('style',old+';fill:'+fix['fill'])
            # Only explicit, reviewed vector components may change.
            if fix.get('svg_child') is None:
                for i,node in enumerate(original):
                    if i not in fix['children']:assert ET.tostring(node)==ET.tostring(tree[i])
            else:
                for i,node in enumerate(original):
                    if i!=fix['svg_child']:assert ET.tostring(node)==ET.tostring(tree[i])
                for i,node in enumerate(original[fix['svg_child']]):
                    if i not in fix['children']:assert ET.tostring(node)==ET.tostring(group[i])
            raw=ET.tostring(tree)
        raw=cairosvg.svg2png(bytestring=raw,output_width=1320)
    logo=Image.open(io.BytesIO(raw)).convert('RGBA')
    if monochrome is not None:
        pixels=list(logo.getdata())
        if any(a and (r,g,b)!=(255,255,255) for r,g,b,a in pixels):raise ValueError('Logo is not the reviewed white monochrome source')
        logo.putdata([tuple(monochrome)+(a,) if a else (r,g,b,a) for r,g,b,a in pixels])
    if pixel_fix:
        before=logo.tobytes();raw=bytearray(before);groups=components(logo);allowed=set()
        for index in pixel_fix['components']:
            allowed.update(groups[index])
        rgb=bytes(pixel_fix['rgb'])
        for index in allowed:raw[index*4:index*4+3]=rgb
        for index in range(logo.width*logo.height):
            if index not in allowed:assert raw[index*4:index*4+4]==before[index*4:index*4+4]
            assert raw[index*4+3]==before[index*4+3]
        logo=Image.frombytes('RGBA',logo.size,bytes(raw))
    bbox=logo.getbbox()
    if not bbox:raise ValueError('Empty logo')
    return logo.crop(bbox)

def build():
    config=json.loads((ROOT/'catalog/artwork.json').read_text())
    rows=list(csv.DictReader((ROOT/'catalog/DAB_radio_picon_mapping.csv').open(encoding='utf-8-sig')))
    masters={}
    for style,digest in config['master_sha256'].items():
        p=MASTERS/(style+'-sablona.png');assert sha(p.read_bytes())==digest
        masters[style]=Image.open(p).convert('RGBA');assert masters[style].size==(220,132)
    source_links={}
    for station,spec in config['stations'].items():
        provenance=spec.get('provenance',{})
        link=spec.get('source') or provenance.get('url') or provenance.get('source_page')
        if not isinstance(link,str) or not link.startswith('https://'):
            raise ValueError('Missing source provenance: '+station)
        source_links[station]=link
    records=[];station_files={}
    for station,spec in sorted(config['stations'].items()):
        outputs={}
        for style,relative in spec['variants'].items():
            source=ROOT/relative;assert sha(source.read_bytes())==spec['source_sha256'][style]
            logo=load_logo(source,spec.get('svg_component_fixes',{}).get(style) or (spec.get('white_component_fix') if style=='white' else None),spec.get('pixel_component_fixes',{}).get(style),spec.get('monochrome_variants',{}).get(style))
            logo.thumbnail(tuple(config['logo_fit']),Image.Resampling.LANCZOS)
            result=masters[style].copy() if style in masters else Image.new('RGBA',(220,132))
            x,y=(220-logo.width)//2,(132-logo.height)//2;result.alpha_composite(logo,(x,y))
            if style in masters:
                # Frozen border and every pixel outside the fitted logo stay exact.
                for box in [(0,0,220,y),(0,y+logo.height,220,132),(0,y,x,y+logo.height),(x+logo.width,y,220,y+logo.height)]:
                    assert result.crop(box).tobytes()==masters[style].crop(box).tobytes()
            output=io.BytesIO();result.save(output,format='PNG',compress_level=9);outputs[style]=output.getvalue()
        station_files[station]=outputs
    for row in rows:
        station=row['station'];name=row['picon_filename']
        if station not in station_files:continue
        hashes={}
        for style,raw in station_files[station].items():
            folder=ROOT/'preview/authentic'/style;folder.mkdir(parents=True,exist_ok=True);(folder/name).write_bytes(raw);hashes[style]=sha(raw)
        records.append(dict(row,logo_source=source_links[station],logo_verified='SOURCE_CHECKED',sha256=hashes,status='REVIEW' if config['stations'][station].get('review') else 'QC_READY',approved_master_v9=False))
    report={'schema':1,'station_count':len(station_files),'reference_count':len(records),'records':records,'unresolved':config['unresolved'],'status':'authentic-artwork-awaiting-visual-acceptance','master_sha256':config['master_sha256']}
    (ROOT/'catalog/authentic-preview.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(report['station_count'],'stations',report['reference_count'],'references',len(records)*3,'PNG')
if __name__=='__main__':build()
