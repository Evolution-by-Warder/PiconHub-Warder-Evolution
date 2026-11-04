#!/usr/bin/env python3
"""Evaluate whole, official ESKA ROCK logo variants; never repaint lettering.

The base wordmark from the broadcaster is already frozen in provenance.json.
Frozen review source bytes are SHA-256 verified even if the publisher changes live URLs.\nAlternative publisher-provided logos are treated as independent, *unapproved*
source compositions, not as permission to recolour the original.
"""
from pathlib import Path
import hashlib, io, json
from urllib.request import Request, urlopen

import cairosvg
from defusedxml import ElementTree as ET
from PIL import Image, ImageDraw, ImageFont

ROOT=Path("picons/IPTV-SK-CZ/review/eskarock-20261104")
BASE=Path("plugin/artwork/templates/picons")
EXPECTED_MASTERS={
  "white":"c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589",
  "black":"61e69f7fc46e340453bf74ccd7af6ac9d8eba9f8e232884659e1ea99f6abf3fe",
}
SOURCE_SHA256={
    "player-wordmark":"93e95da63a16c53c199e3266071e008ca025c907a4aedfbbe30895c8c97dc4a7",
    "station-signet":"332021552b0e72292d20b9cc2d5cb3251ae6b064d061044761d04e9a1b037d0",
    "official-og":"87bf174ed3bd9c5d11ab14276fb746e69f59f3d587d7845c30f2e441d14a4a65",
    "app-icon":"4060c58e2aff69413d331c67906a5abf5273e18d8e63d4858ac3fa9e2c4a0cac",
}
SOURCES=(
  ("player-wordmark","https://www.eskarock.pl/media/eskarock/desktop/images/player-logo.svg","svg"),
  ("station-signet","https://www.eskarock.pl/media/desktop/site_header/images/signets/signet-eskarock.svg","svg"),
  ("official-og","https://cdn.files.smcloud.net/t/logo-eska-rock-og.png","png"),
  ("app-icon","https://www.eskarock.pl/web-app-manifest-512x512.png","png"),
)
W,H=220,132
REF="4097_0_2_A68C_EC79_ED_0_0_0_0.png"
MASTER_SIZE=(W,H)
SHA=lambda raw:hashlib.sha256(raw).hexdigest()

def original(url, kind, frozen_source):
    assert url in {s[1] for s in SOURCES}
    if frozen_source.is_file():
        # A published review snapshot is immutable even when the broadcaster
        # rotates a server-side asset at the same URL. Re-render the audited
        # exact bytes, and keep all source SHA checks as fail-closed gates.
        raw=frozen_source.read_bytes()
    else:
        with urlopen(Request(url,headers={"User-Agent":"Warder Radio official-logo verifier/1.0"}),timeout=35) as f:
            raw=f.read(512*1024+1)
    assert 0<len(raw)<=512*1024
    if kind=="svg":
        lowered=raw.lower()
        assert b"<svg" in lowered and all(bad not in lowered for bad in (b"<!doctype",b"<!entity",b"<script",b"<image",b"<foreignobject",b"javascript:"))
        ET.fromstring(raw)
        render=cairosvg.svg2png(bytestring=raw,scale=2,unsafe=False)
    else:
        assert raw[:8]==b"\x89PNG\r\n\x1a\n",url
        render=raw
    image=Image.open(io.BytesIO(render)).convert("RGBA")
    assert image.width>=64 and image.height>=64
    bb=image.getchannel("A").getbbox()
    assert bb
    return raw,image.crop(bb)

def composite(image, masters, style):
    fit=image.copy()
    fit.thumbnail((192,104),Image.Resampling.LANCZOS)
    out=masters[style].copy() if style in masters else Image.new("RGBA",(W,H),(0,0,0,0))
    out.alpha_composite(fit,((W-fit.width)//2,(H-fit.height)//2))
    return out,fit.size

def png_bytes(image):
    buf=io.BytesIO()
    image.save(buf,"PNG")
    return buf.getvalue()

def make_sheet(previews,src_info):
    cols=["transparent","white","black"]
    font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",19)
    small=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",14)
    panel=Image.new("RGB",(1200,260+len(src_info)*285),"#102035")
    d=ImageDraw.Draw(panel)
    d.text((24,20),"ESKA ROCK | OFICIALNE ALTERNATIVNE LOGA — IBA REVIEW",font=font,fill="#dfeffa")
    d.text((24,55),"Kazdy original je cely, bez prefarbenia. Siva/transparentna poza iba na ukazke.",font=small,fill="#adc9da")
    for i,info in enumerate(src_info):
        y=96+i*285
        d.text((24,y),info["slug"]+" | "+info["source_url"][-67:],font=small,fill="#91dcf9")
        for j,style in enumerate(cols):
            x=24+j*388
            base=Image.new("RGB",(330,199),"#7a8797" if style=="transparent" else "#0c172a")
            if style=="transparent":
                bg=ImageDraw.Draw(base)
                for yy in range(0,199,18):
                    for xx in range(0,330,18):
                        if (xx//18+yy//18)%2:bg.rectangle([xx,yy,xx+17,yy+17],fill="#586d87")
            a=previews[(info["slug"],style)].resize((330,198),Image.Resampling.LANCZOS)
            base.paste(a,(0,0),a)
            panel.paste(base,(x,y+23))
            d.text((x+8,y+229),style.upper(),font=small,fill="#eef7fc")
    d.text((24,panel.height-40),"Original color-preserved candidates — do not publish without owner/identity QC.",font=small,fill="#ffcf81")
    panel.save(ROOT/"alternatives-sheet.png")

def main():
    dest=ROOT/"alternatives"
    dest.mkdir(parents=True,exist_ok=True)
    master={}
    for style,sha in EXPECTED_MASTERS.items():
        raw=(BASE/(style+"-sablona.png")).read_bytes()
        assert SHA(raw)==sha
        master[style]=Image.open(io.BytesIO(raw)).convert("RGBA")
        assert master[style].size==MASTER_SIZE
    entries=[]
    previews={}
    for slug,url,kind in SOURCES:
        folder=dest/slug
        folder.mkdir(parents=True,exist_ok=True)
        try:
            raw,source=original(url,kind,folder/("original."+kind))
        except Exception as error:
            # Fail closed per-asset. Record why the official URL did not yield a
            # suitable source, but do not invent a replacement image.
            entries.append(dict(slug=slug,source_url=url,status="blocked",reason=str(error)[:400]))
            print("BLOCKED OFFICIAL ALTERNATIVE",slug,error)
            continue
        if SHA(raw)!=SOURCE_SHA256[slug]:
            # An upstream URL can change its bytes; never silently take an
            # unreviewed logo or overwrite the frozen source. Optional whole
            # logos are blocked individually. The preferred OG candidate
            # remains fail-closed and must exactly match its reviewed source.
            if slug == "official-og":
                raise ValueError("Approved review candidate source changed: "+slug)
            entries.append(dict(slug=slug,source_url=url,status="blocked_source_changed",
                                expected_sha256=SOURCE_SHA256[slug],
                                observed_sha256=SHA(raw),publishing_allowed=False))
            print("BLOCKED SOURCE HASH",slug,SHA(raw))
            continue
        (folder/("original."+kind)).write_bytes(raw)
        renders={}
        for style in ("transparent","white","black"):
            image,fit=composite(source,master,style)
            previews[(slug,style)]=image
            for width,height in ((50,30),(220,132),(400,240)):
                name="%dx%d/%s/%s"%(width,height,style,REF)
                file=folder/name
                file.parent.mkdir(parents=True,exist_ok=True)
                final=image if (width,height)==MASTER_SIZE else image.resize((width,height),Image.Resampling.LANCZOS)
                body=png_bytes(final)
                file.write_bytes(body)
                renders["%dx%d/%s"%(width,height,style)]=dict(bytes=len(body),sha256=SHA(body),filename=name)
        entries.append(dict(slug=slug,source_url=url,kind=kind,status="candidate_only",
                            original_sha256=SHA(raw),original_bytes=len(raw),
                            original_dimensions=[source.width,source.height],
                            fit=fit,renders=renders,official_domain_only=True,
                            visual_qc="pending",publishing_allowed=False))
        print("REVIEW SOURCE",slug,len(renders),"Warder PNGs",SHA(raw))
    if not any(x["status"]=="candidate_only" for x in entries):
        raise ValueError("No verified alternative official source could be rendered")
    m=dict(schema=1,stage="review_not_production",date="2026-11-04",station="ESKA ROCK",
           reference=REF,files=entries,
           preferred_review_candidate="official-og",
           preferred_source_sha256=SOURCE_SHA256["official-og"],
           chosen_for_review_reason="High-resolution original full wordmark with native black backing; strong red/white contrast across three Warder masters.",
           production_approved=False,
           notice="No colour changes, no production changes, alternative source edition must be separately approved.")
    (ROOT/"alternatives.json").write_text(json.dumps(m,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    make_sheet(previews,[x for x in entries if x["status"]=="candidate_only"])
    print("PASS: official alternatives review prepared, production protected")

if __name__=="__main__":main()
