"""Reproduce owner-upload/DAB radio logo candidates; never publish or change feeds.

Uses frozen canonical RGBA originals and reviewed semantic masks. No network,
colour thresholding, component detection, sharpening or logo invention runs here.
Pillow 12.3.0 reproduces the recorded output hashes.
"""
from pathlib import Path
import argparse,csv,hashlib,io,json,stat,zipfile
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'picons/IPTV-SK-CZ/sources/radio-logos-20261030'
SHA=lambda raw:hashlib.sha256(raw).hexdigest()

def checked(path,digest):
    raw=path.read_bytes()
    if SHA(raw)!=digest:raise ValueError('Frozen source hash differs: '+str(path))
    return raw

def protected(pixels,mask):
    return SHA(bytes(c for pixel,selected in zip(pixels,mask) if not selected for c in pixel))

def png(image):
    out=io.BytesIO();image.save(out,format='PNG');return out.getvalue()

def zip_member(archive,name,raw):
    info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
    info.external_attr=(stat.S_IFREG|0o644)<<16;archive.writestr(info,raw)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--record',action='store_true',help='Record newly reviewed output hashes in the candidate plan.')
    args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    plan_path=BASE/'prepared-artwork.json';plan=json.loads(plan_path.read_text())
    catalogue=ROOT/'picons/IPTV-SK-CZ/catalog'
    stations=json.loads((catalogue/'stations.json').read_text())['stations'];lookup={r['identity_key']:r for r in stations}
    release=json.loads((catalogue/'release.json').read_text());existing=set(plan.get('baseline_file_inventory', release['packages']['220x132']['transparent']['files']))
    owned=(ROOT/'picons/IPTV-SK-CZ/bouquets/userbouquet.warder.sk-cz.radio').read_text()
    world=(ROOT/'picons/IPTV-SK-CZ/bouquets/userbouquet.warder.radio').read_text()
    masters={}
    for style,digest in plan['master_sha256'].items():
        raw=checked(ROOT/'plugin/artwork/templates/picons'/(style+'-sablona.png'),digest)
        masters[style]=Image.open(io.BytesIO(raw)).convert('RGBA');assert masters[style].size==(220,132)
    refs={};files={};protected_checks=0
    for row in plan['artwork']:
        checked(BASE/row['original_path'],row['source_sha256'])
        original=Image.open(io.BytesIO(checked(BASE/row['canonical_path'],row['canonical_sha256']))).convert('RGBA')
        pixels=list(original.get_flattened_data());entries=[]
        for key in row['identity_keys']:
            station=lookup[key];filename=station['picon_filename']
            assert station['country'] in ('SK','CZ') and filename not in existing and filename not in refs
            assert not station.get('reference_aliases'), 'Record aliases explicitly before adding them.'
            service='#SERVICE '+station['service_reference']+':'
            assert service in owned and service in world
            refs[filename]=row['slug'];entries.append({k:station[k] for k in ('country','name','identity_key','service_reference','picon_filename','stream_url')})
        row['stations']=entries;outputs={}
        for style in ('transparent','white','black'):
            mark=original.copy();mask_spec=row.get(style+'_mask')
            if mask_spec:
                mask_image=Image.open(io.BytesIO(checked(BASE/mask_spec['file'],mask_spec['sha256']))).convert('L')
                assert mask_image.size==original.size
                mask=list(mask_image.get_flattened_data());assert set(mask)<={0,255}
                assert sum(bool(x) for x in mask)==mask_spec['pixels']
                assert protected(pixels,mask)==mask_spec['protected_pixels_sha256']
                changed=[]
                for pixel,selected in zip(pixels,mask):
                    assert not selected or pixel[3]>0
                    changed.append((*mask_spec['colour'],pixel[3]) if selected else pixel)
                assert protected(changed,mask)==mask_spec['protected_pixels_sha256']
                assert all(before[3]==after[3] for before,after in zip(pixels,changed))
                mark.putdata(changed);protected_checks+=1
            mark.thumbnail((192,104),Image.Resampling.LANCZOS)
            canvas=Image.new('RGBA',(220,132),(0,0,0,0)) if style=='transparent' else masters[style].copy()
            pos=((220-mark.width)//2,(132-mark.height)//2);canvas.alpha_composite(mark,pos)
            for w,h in ((50,30),(220,132),(400,240)):
                res=str(w)+'x'+str(h);im=canvas if res=='220x132' else canvas.resize((w,h),Image.Resampling.LANCZOS)
                raw=png(im);meta={'sha256':SHA(raw),'bytes':len(raw)};key=res+'/'+style
                if not args.record:assert row['outputs'][key]==meta,(row['slug'],key)
                outputs[key]=meta
                target=out/'artwork'/res/style/(row['slug']+'.png');target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
                for station in entries:files[res+'/'+style+'/'+station['picon_filename']]=raw
        row['outputs']=outputs
    assert len(refs)==plan['new_reference_files_per_variant']==plan['new_station_entries']==30
    assert len(files)==30*9 and len(plan['artwork'])==26
    mapping=io.StringIO(newline='');writer=csv.writer(mapping);writer.writerow(('Zdroj','Krajina','Stanica','Service reference','Picon'))
    for row in plan['artwork']:
        for station in row['stations']:writer.writerow((row['uploaded_filename'] or row['source']['url'],station['country'],station['name'],station['service_reference'],station['picon_filename']))
    mapping_raw=mapping.getvalue().encode('utf-8-sig');(out/'Warder-radio-parovanie.csv').write_bytes(mapping_raw)
    # Neutral checkerboard is a review aid only; exported transparent PNGs do not
    # contain the checkerboard or any other invented background.
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',18)
    small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',14)
    pages=[]
    chunks=(plan['artwork'][:8],plan['artwork'][8:16],plan['artwork'][16:23],plan['artwork'][23:])
    for page,chunk in enumerate(chunks,1):
        sheet=Image.new('RGB',(1080,125+len(chunk)*165),'#1c2432');draw=ImageDraw.Draw(sheet)
        label='ZIP OD MAJITEĽA' if page<4 else 'DABPLUS.CZ → ORIGINÁLY STANÍC'
        draw.text((25,20),f'WARDER RÁDIÁ · {label} · {page}/4',font=font,fill='white')
        for x,label in zip((300,560,820),('TRANSPARENT','BIELE','ČIERNE')):draw.text((x,68),label,font=small,fill='#a8bad2')
        for i,row in enumerate(chunk):
            y=110+i*165;name=row['stations'][0]['name']
            if len(name)>29:
                mid=name.rfind(' ',0,29);mid=mid if mid>0 else 28
                draw.text((22,y+28),name[:mid],font=small,fill='white');draw.text((22,y+47),name[mid:].strip(),font=small,fill='white')
            else:draw.text((22,y+35),name,font=small,fill='white')
            if len(row['stations'])>1:draw.text((22,y+70),f"{len(row['stations'])} referencie",font=small,fill='#a8bad2')
            for j,style in enumerate(('transparent','white','black')):
                x=280+j*260;im=Image.open(out/'artwork/220x132'/style/(row['slug']+'.png'))
                if style=='transparent':
                    for yy in range(0,132,11):
                        for xx in range(0,220,11):draw.rectangle((x+xx,y+yy,x+xx+10,y+yy+10),fill='#596579' if (xx//11+yy//11)%2 else '#69768a')
                sheet.paste(im,(x,y),im)
        p=out/f'Warder-radio-loga-{page}.png';sheet.save(p);pages.append(p)
    readme=('WARDER — RÁDIO PICONY, NÁVRH NA VIZUÁLNU KONTROLU\n\n'
        '26 grafických predlôh pre 30 doteraz chýbajúcich položiek nášho SK/CZ bouquetu.\n'
        '23 predlôh z dodaného ZIPu: 26 referencií. Tri predlohy objavené cez dabplus.cz\n'
        'a prevzaté vo väčšom rozlíšení z oficiálnych stránok staníc: 4 referencie.\n'
        'Rozmery 50×30, 220×132, 400×240; Transparent, Biele, Čierne.\n'
        'Vybraný rozmer a variant rozbaľte: PNG súbory patria priamo do priečinka picon.\n'
        'Žiadny nový IPK nie je potrebný. Produkčný katalóg zatiaľ zostáva nezmenený.\n'
        'Rádio Český Jukebox a Luc Radio: dodané sú iba všeobecné symboly.\n'
        'Dance Radio FM: adresa v bouquete je holandská; dodaný český symbol nezameniť.\n'
        'Staré Crystal, Dragon, Hitradio FM a Rock Radio Gold potrebujú potvrdiť identitu.\n'
        'Pôvodné slabšie rastrové podklady zostali bez vymyslených detailov a písma.\n'
        'Šachovnica je len v náhľadoch; transparentné PNG majú skutočnú alfa priehľadnosť.\n')
    (out/'README.txt').write_text(readme)
    with zipfile.ZipFile(out/'Warder-radio-picony-SK-CZ-navrh.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for name,raw in sorted(files.items()):zip_member(archive,'picons/'+name,raw)
        zip_member(archive,'Warder-radio-parovanie.csv',mapping_raw)
        zip_member(archive,'README.txt',readme.encode())
        for p in pages:zip_member(archive,'ukazky/'+p.name,p.read_bytes())
    with zipfile.ZipFile(out/'Warder-radio-picony-SK-CZ-navrh.zip') as archive:
        assert len(archive.namelist())==276 and len(set(archive.namelist()))==276
        assert archive.testzip() is None
        for name,raw in files.items():
            assert archive.read('picons/'+name)==raw
            with Image.open(io.BytesIO(raw)) as im:assert im.size==tuple(map(int,name.split('/')[0].split('x'))) and im.mode=='RGBA';im.verify()
    plan['verification']={'canonical_graphics':26,'unique_generated_pngs':234,'service_reference_pngs':270,'full_glyph_masks_checked':protected_checks,'all_unmasked_rgba_and_source_alpha_preserved':True,'all_existing_picons_preserved':True,'master_sources_unchanged':True,'exact_bouquet_references_checked':30,'zip_crc_and_png_decode_checked':True,'production_catalogue_changed':False}
    if args.record:plan_path.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
    (out/'overenie.json').write_text(json.dumps(plan['verification'],indent=2)+'\n')
    print(json.dumps(plan['verification'],ensure_ascii=False))
    print(out/'Warder-radio-picony-SK-CZ-navrh.zip')

if __name__=='__main__':main()
