#!/usr/bin/env python3
"""Render real Polskie Radio Białystok brand-kit originals into Warder review.

Three separate *whole* approved-by-broadcaster source variants are shown for
editorial comparison, not for automatic substitution or production.
Never recolour text, recreate geometry, alter frozen Warder masters, or edit
the published country packages.
"""
import hashlib
import io
import json
from pathlib import Path
import zipfile

from PIL import Image,ImageDraw,ImageFont

ROOT=Path("picons/IPTV-SK-CZ/review/radio-bialystok-official-brandkit-20261104")
SOURCES={
 "blue-transparent-full-name": ("logo/PRB.png","6e7aaf42ca9ce01093ddbb0a186e51a98dfc9281bdacea609bae4f6c429645e0"),
 "white-on-blue-original": ("logo/PRB_1.jpg","868d296c3c66f1c4992f98e9ea66649f6bb2edbeb45155427948842ef9a6663f"),
 "blue-symbol-only": ("logo/prb_small.png","dd5c89aefe7d102435bebc33afdae00e8520ae01dd53dc938c42ac4e0319dd2a"),
}
ZIP_SHA="386a1b9466197c8bc593b4491f2f1e48e4eb7d5a07e1771dfd1d595edbd3f255"
MASTER_SHA={
 "white":"c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589",
 "black":"61e69f7fc46e340453bf74ccd7af6ac9d8eba9f8e232884659e1ea99f6abf3fe",
}
SIZES=((50,30),(220,132),(400,240))
STYLES=("transparent","white","black")
TARGET="4097_0_2_BC04_A7A6_ED_0_0_0_0.png"
SHA=lambda b:hashlib.sha256(b).hexdigest()

def png(img):
    b=io.BytesIO();img.save(b,"PNG");return b.getvalue()

def sheet(items,renders):
    font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",20)
    small=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",14)
    w,h=1160,160+len(items)*295
    im=Image.new("RGB",(w,h),"#0d2137")
    d=ImageDraw.Draw(im)
    d.text((22,18),"POLSKIE RADIO BIAŁYSTOK — OFFICIAL BROADCASTER KIT, WARDER REVIEW",font=font,fill="#ddf5fd")
    d.text((22,55),"3 whole original logo compositions · source colours unchanged · nine variants each",font=small,fill="#b5d1e2")
    for i,obj in enumerate(items):
        y=96+i*295
        d.text((30,y),obj["slug"]+"   ["+obj["original_name"]+"]",font=small,fill="#c5f1fb")
        for j,style in enumerate(STYLES):
            x=20+j*380
            bg=Image.new("RGB",(340,205),"#8395aa" if style=="transparent" else "#0c1728")
            if style=="transparent":
                draw=ImageDraw.Draw(bg)
                for cy in range(0,205,16):
                    for cx in range(0,340,16):
                        if (cx//16+cy//16)%2:draw.rectangle((cx,cy,cx+15,cy+15),fill="#677d95")
            icon=renders[(obj["slug"],style)].resize((340,204),Image.Resampling.LANCZOS)
            bg.paste(icon,(0,0),icon)
            im.paste(bg,(x,y+29))
            d.text((x+9,y+242),style.upper(),font=small,fill="#a9effc")
        d.text((30,y+271),obj["source_sha256"][:55],font=small,fill="#a5cedf")
    im.save(ROOT/"warder-options-sheet.png")

def main():
    metadata=json.loads((ROOT/"inventory.json").read_text(encoding="utf8"))
    assert metadata["source_sha256"]==ZIP_SHA and metadata["station"]=="Polskie Radio Bialystok"
    b=(ROOT/"original-logo-kit.zip").read_bytes()
    assert SHA(b)==ZIP_SHA
    masters={"transparent":Image.new("RGBA",(220,132),(0,0,0,0))}
    for style,hash_value in MASTER_SHA.items():
        raw=(Path("plugin/artwork/templates/picons")/(style+"-sablona.png")).read_bytes()
        assert SHA(raw)==hash_value
        masters[style]=Image.open(io.BytesIO(raw)).convert("RGBA")
        assert masters[style].size==(220,132)
    ROOT.mkdir(parents=True,exist_ok=True)
    details=[];visual={}
    with zipfile.ZipFile(io.BytesIO(b)) as kit:
        for slug,(member,expected_hash) in SOURCES.items():
            raw=kit.read(member)
            assert SHA(raw)==expected_hash
            mark=Image.open(io.BytesIO(raw)).convert("RGBA")
            source_size=mark.size
            bounds=mark.getchannel("A").getbbox()
            assert bounds
            mark=mark.crop(bounds)
            mark.thumbnail((192,104),Image.Resampling.LANCZOS)
            assert mark.width>=100 and mark.height>=60
            variants={}
            for style in STYLES:
                base=masters[style].copy()
                base.alpha_composite(mark,((220-mark.width)//2,(132-mark.height)//2))
                visual[(slug,style)]=base
                for width,height in SIZES:
                    size="%dx%d"%(width,height)
                    rendered=base if (width,height)==(220,132) else base.resize((width,height),Image.Resampling.LANCZOS)
                    data=png(rendered)
                    out=ROOT/"warder"/slug/size/style/TARGET
                    out.parent.mkdir(parents=True,exist_ok=True)
                    out.write_bytes(data)
                    variants[size+"/"+style]={"path":str(out.relative_to(ROOT)),"sha256":SHA(data),"bytes":len(data)}
            details.append({"slug":slug,"original_name":member,"source_sha256":expected_hash,
                            "source_dimensions":list(source_size),"fit_dimensions":list(mark.size),
                            "rendered":variants,"visual_review_pending":True,
                            "production_approved":False,
                            "editorial_note":("Symbol only; not preferred for full-name station" if slug=="blue-symbol-only"
                              else "Original broadcaster logo; verify current on-air branding")})
    sheet(details,visual)
    report={"schema":1,"stage":"review_not_production","date":"2026-11-04",
            "source":"https://www.radio.bialystok.pl/images/logo/logo.zip",
            "source_page":"https://www.radio.bialystok.pl/reklama",
            "zip_sha256":ZIP_SHA,
            "station_reference":"4097:0:2:BC04:A7A6:ED:0:0:0:0",
            "styles":STYLES,"resolutions":["%dx%d"%size for size in SIZES],
            "masters_sha256":MASTER_SHA,"variants":details,
            "logo_recolouring":False,"source_overwritten":False,
            "no_production_changes":True,
            "rights_status":"broadcaster publishes downloadable logo kit; redistribution and trademark rights to confirm",
            "quality_status":"waiting for visual choice between current broadcaster designs"}
    (ROOT/"warder-options.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    assert len(details)==3 and all(len(x["rendered"])==9 for x in details)
    print("PASS 3 original broadcaster sources, 27 Warder review PNGs, no production mutation")

if __name__=="__main__":main()
