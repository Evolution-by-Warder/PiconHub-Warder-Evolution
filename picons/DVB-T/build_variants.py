#!/usr/bin/env python3
"""Compose original transparent CZ/SK DTT logos on immutable Warder masters.

Pillow is a build-host dependency only. No service identities or logo colours
are changed. ZIP payloads retain every original PNG basename.
"""
import argparse,hashlib,io,json,stat,zipfile
from pathlib import Path
from PIL import Image,ImageDraw
MASTER_HASHES={'white':'c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589','black':'61e69f7fc46e340453bf74ccd7af6ac9d8eba9f8e232884659e1ea99f6abf3fe'}
SOURCE_HASH='277fe3e91a482c008342e35d41a4d2c340abb5c59e54ba714040f96a7a6e1d77'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def build(source,masters,output):
    raw=source.read_bytes();assert sha(raw)==SOURCE_HASH,'Unexpected transparent source'
    output.mkdir(parents=True,exist_ok=True)
    records={};unique={};rendered={style:{} for style in MASTER_HASHES};frames={}
    for style,digest in MASTER_HASHES.items():
        raw=(masters/(style+'-sablona.png')).read_bytes();assert sha(raw)==digest
        frames[style]=Image.open(io.BytesIO(raw)).convert('RGBA');assert frames[style].size==(220,132)
    with zipfile.ZipFile(source) as archive:
        assert archive.testzip() is None
        for member in archive.infolist():
            assert Path(member.filename).name==member.filename and member.filename.endswith('.png')
            data=archive.read(member);digest=sha(data);records[member.filename]={'transparent':digest}
            unique.setdefault(digest,data)
    assert len(records)==2674 and len(unique)==203
    for digest,data in sorted(unique.items()):
        original=Image.open(io.BytesIO(data)).convert('RGBA');assert original.size==(220,132)
        bbox=original.getbbox();assert bbox
        logo=original.crop(bbox);logo.thumbnail((192,104),Image.Resampling.LANCZOS)
        x,y=(220-logo.width)//2,(132-logo.height)//2
        for style,master in frames.items():
            result=master.copy();result.alpha_composite(logo,(x,y))
            for box in ((0,0,220,y),(0,y+logo.height,220,132),(0,y,x,y+logo.height),(x+logo.width,y,220,y+logo.height)):
                assert result.crop(box).tobytes()==master.crop(box).tobytes()
            out=io.BytesIO();result.save(out,format='PNG',compress_level=9)
            rendered[style][digest]=out.getvalue()
    packages={}
    for style in frames:
        temporary=output/(style+'.zip')
        with zipfile.ZipFile(temporary,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
            for name,record in sorted(records.items()):
                data=rendered[style][record['transparent']];record[style]=sha(data)
                info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=(stat.S_IFREG|0o644)<<16
                archive.writestr(info,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
        raw=temporary.read_bytes();digest=sha(raw);filename='warder-dvb-t-sk-cz-220x132-'+style+'-'+digest[:16]+'.zip';temporary.rename(output/filename)
        parts=[]
        for i,offset in enumerate(range(0,len(raw),4*1024*1024)):
            chunk=raw[offset:offset+4*1024*1024];name=filename+'.part%02d'%i;(output/name).write_bytes(chunk)
            parts.append({'filename':name,'bytes':len(chunk),'sha256':sha(chunk)})
        packages[style]={'filename':filename,'bytes':len(raw),'sha256':digest,'png_count':len(records),'parts':parts}
        with zipfile.ZipFile(output/filename) as archive:
            assert set(archive.namelist())==set(records) and archive.testzip() is None
            for name,record in records.items():assert sha(archive.read(name))==record[style]
    sample=list(unique)[::max(1,len(unique)//16)][:16]
    sheet=Image.new('RGB',(660,16*142),(24,35,51))
    for row,digest in enumerate(sample):
        for col,style in enumerate(('transparent','white','black')):
            data=unique[digest] if style=='transparent' else rendered[style][digest]
            im=Image.open(io.BytesIO(data)).convert('RGBA');sheet.paste(im,(col*220,row*142),im)
    sheet.save(output/'review.png')
    report={'schema':1,'status':'verified-build','resolution':'220x132','png_count':2674,'unique_images':203,'source_transparent_zip_sha256':SOURCE_HASH,'master_sha256':MASTER_HASHES,'logo_fit':[192,104],'operation':'Preserve original colours and service basenames; crop transparent margins, fit proportionally inside frozen Warder masters, alpha-composite without recolouring or invention. Transparent archive remains unchanged.','owner_authorization':'Explicit owner instruction to derive white and black from the transparent package, 27 October 2026.','packages':packages,'records':records}
    (output/'variants.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({s:{k:v for k,v in p.items() if k!='parts'} for s,p in packages.items()},indent=2))
    return report
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--masters',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();build(a.source,a.masters,a.output)
