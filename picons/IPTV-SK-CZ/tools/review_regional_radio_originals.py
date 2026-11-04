#!/usr/bin/env python3
"""Review original assets for three broadcasters, no production changes.

Only URLs *already discovered in publisher's own pages* in pinned Warder source
audit are allowed. Preserve original fonts/colours/alpha; no interpolation
except approved proportional fit and standard resize. Never auto-publish.
"""
import hashlib
import io
import json
from pathlib import Path
from urllib.request import Request,urlopen
import zipfile
from PIL import Image,ImageDraw,ImageFont
from defusedxml import ElementTree as SafeET
import cairosvg

REVIEW=Path("picons/IPTV-SK-CZ/review/official-regional-radio-20261104")
AUDIT=Path("picons/IPTV-SK-CZ/catalog/official-radio-source-batch-20261104.json")
MASTER=Path("plugin/artwork/templates/picons")
SHA=lambda b:hashlib.sha256(b).hexdigest()
LIMIT=2*1024*1024
MASTERS={
 "black":"61e69f7fc46e340453bf74ccd7af6ac9d8eba9f8e232884659e1ea99f6abf3fe",
 "white":"c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589",
}
SIZES=((50,30),(220,132),(400,240))
STYLES=("transparent","white","black")
SOURCES=(
 dict(country="PL",name="Polskie Radio Katowice",slug="katowice-header",reference="4097:0:2:B4FF:D92A:ED:0:0:0:0",
      source="https://www.radio.katowice.pl/img2/rk_logo_de.png",ext="png"),
 dict(country="PL",name="Polskie Radio Katowice",slug="katowice-app-icon",reference="4097:0:2:B4FF:D92A:ED:0:0:0:0",
      source="https://www.radio.katowice.pl/apple-touch-icon.png",ext="png"),
 dict(country="PL",name="Polskie Radio Poznań",slug="poznan-og",reference="4097:0:2:130A:2B66:ED:0:0:0:0",
      source="https://radiopoznan.fm/v3/img/logo.png",ext="png"),
 dict(country="PL",name="Polskie Radio Poznań",slug="poznan-original-blue-on-white",reference="4097:0:2:130A:2B66:ED:0:0:0:0",
      source="https://radiopoznan.fm/uploads/assets/5j85fdjl3wrwpa4_logo-radio_poznan_logo-poziom-1080x675.jpg",ext="jpg",
      source_page="https://radiopoznan.fm/informacje/pozostale/przerwa-techniczna-w-nadawaniu-radia"),
 dict(country="PL",name="Polskie Radio Poznań",slug="poznan-white-vector",reference="4097:0:2:130A:2B66:ED:0:0:0:0",
      source="https://radiopoznan.fm/v7/img/logo-white.svg",ext="svg"),
 dict(country="AT",name="Antenne Steiermark",slug="steiermark-button",reference="4097:0:2:45CD:FE77:EC:0:0:0:0",
      source="https://steiermark.antenne.at/uploads/media-assets/AS-Logo-Button.webp",ext="webp"),
 dict(country="AT",name="Antenne Steiermark",slug="steiermark-og",reference="4097:0:2:45CD:FE77:EC:0:0:0:0",
      source="https://steiermark.antenne.at/media/1024-QBE62OCK.png",ext="png"),
)

def original(entry):
    path=REVIEW/entry["slug"]/("original."+entry["ext"])
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        body=path.read_bytes()
    else:
        with urlopen(Request(entry["source"],headers={"User-Agent":"Warder Radio official-logo review/1.0"}),timeout=35) as resp:
            body=resp.read(LIMIT+1)
    assert 0<len(body)<=LIMIT
    kind=entry["ext"]
    if kind=="svg":
        raw=body.lower()
        for forbidden in (b"<!doctype",b"<!entity",b"<script",b"<image",b"<foreignobject",b"javascript:",b"@import"):
            if forbidden in raw:raise ValueError("Unsafe SVG content "+entry["slug"])
        tree=SafeET.fromstring(body)
        assert tree.tag.endswith("svg")
        raster=cairosvg.svg2png(bytestring=body,scale=4,unsafe=False)
        icon=Image.open(io.BytesIO(raster)).convert("RGBA")
    else:
        icon=Image.open(io.BytesIO(body))
        assert icon.format.lower()==("jpeg" if kind=="jpg" else kind)
        icon=icon.convert("RGBA")
    assert 80<=icon.width<=9000 and 50<=icon.height<=9000
    bb=icon.getchannel("A").getbbox()
    assert bb
    icon=icon.crop(bb)
    raw_wh=list(icon.size)
    icon.thumbnail((192,104),Image.Resampling.LANCZOS)
    assert icon.width>=35 and icon.height>=20
    path.write_bytes(body)
    return body,icon,raw_wh

def put_png(image):
    buf=io.BytesIO()
    image.save(buf,"PNG")
    return buf.getvalue()

def sheet(success,rendered):
    font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",18)
    small=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",13)
    width=1190
    rowh=290
    result=Image.new("RGB",(width,105+rowh*len(success)),"#102136")
    draw=ImageDraw.Draw(result)
    draw.text((20,17),"WARDER RADIO | 3 BROADCASTERS | ORIGINAL GRAPHICS REVIEW",font=font,fill="#e5f5fc")
    draw.text((20,50),"No recolouring. Transparent, White, Black on original Warder masters; review only.",font=small,fill="#a5c9dd")
    for i,meta in enumerate(success):
        y=85+i*rowh
        draw.text((25,y),meta["name"]+" — "+meta["slug"],font=small,fill="#9eeaf6")
        for j,style in enumerate(STYLES):
            x=20+j*386
            tile=Image.new("RGB",(342,206),"#8896a8" if style=="transparent" else "#111d30")
            if style=="transparent":
                grid=ImageDraw.Draw(tile)
                for gy in range(0,206,18):
                    for gx in range(0,342,18):
                        if (gx//18+gy//18)%2:
                            grid.rectangle((gx,gy,gx+17,gy+17),fill="#647b93")
            preview=rendered[(meta["slug"],style)].resize((342,205),Image.Resampling.LANCZOS)
            tile.paste(preview,(0,0),preview)
            result.paste(tile,(x,y+27))
            draw.text((x+10,y+243),style.upper(),font=small,fill="#e6f1f8")
        draw.text((25,y+267),meta["source_sha256"][:52],font=small,fill="#a4c3dc")
    result.save(REVIEW/"review-sheet.png")

def main():
    mapping=json.loads(AUDIT.read_text(encoding="utf8"))
    checked={}
    for item in mapping["station_results"]:
        checked[(item["country"],item["station"])]=item
    for e in SOURCES:
        entry=checked[(e["country"],e["name"])]
        assert entry["ref"]==e["reference"] and entry["status"]=="read"
        if e["slug"] == "poznan-original-blue-on-white":
            assert e["source"] == "https://radiopoznan.fm/uploads/assets/5j85fdjl3wrwpa4_logo-radio_poznan_logo-poziom-1080x675.jpg"
            assert e["source_page"].startswith("https://radiopoznan.fm/informacje/")
        else:
            assert e["source"] in {asset["url"] for asset in entry["candidates"]}
    ROOT=Path("picons")
    for e in SOURCES:
        info=json.loads((ROOT/("IPTV-"+e["country"])/"catalog/release.json").read_text())
        assert e["reference"].replace(":","_")+".png" not in info["packages"]["220x132"]["transparent"]["files"]
    masters={"transparent":Image.new("RGBA",(220,132),(0,0,0,0))}
    for style,digest in MASTERS.items():
        b=(MASTER/(style+"-sablona.png")).read_bytes()
        assert SHA(b)==digest
        masters[style]=Image.open(io.BytesIO(b)).convert("RGBA")
        assert masters[style].size==(220,132)
    output={"schema":1,"stage":"review_only","sources":[],"no_production_changes":True,
            "original_colours_preserved":True,"master_sha256":MASTERS}
    succeeded=[];rendered={}
    for entry in SOURCES:
        e=dict(entry)
        try:
            raw,mark,raw_wh=original(entry)
        except Exception as exc:
            e.update(status="blocked",reason=(type(exc).__name__+": "+str(exc))[:250],
                     production_approved=False)
            output["sources"].append(e)
            print("BLOCKED SOURCE",entry["slug"],e["reason"])
            continue
        variants={}
        fname=entry["reference"].replace(":","_")+".png"
        for style in STYLES:
            board=masters[style].copy()
            board.alpha_composite(mark,((220-mark.width)//2,(132-mark.height)//2))
            rendered[(e["slug"],style)]=board
            for w,h in SIZES:
                key="%dx%d/%s"%(w,h,style)
                final=board if (w,h)==(220,132) else board.resize((w,h),Image.Resampling.LANCZOS)
                body=put_png(final)
                file=REVIEW/e["slug"]/"artwork"/("%dx%d"%(w,h))/style/fname
                file.parent.mkdir(parents=True,exist_ok=True)
                file.write_bytes(body)
                variants[key]={"sha256":SHA(body),"bytes":len(body),"path":str(file.relative_to(REVIEW))}
        e.update(status="rendered_for_review",source_sha256=SHA(raw),source_bytes=len(raw),
                 source_dimensions=raw_wh,fit_dimensions=list(mark.size),renders=variants,
                 current_edition_verified=False,production_approved=False)
        output["sources"].append(e)
        succeeded.append(e)
        print("Warder review",e["slug"],len(variants),"SHA",e["source_sha256"])
    if not succeeded:raise ValueError("No valid official visual source")
    sheet(succeeded,rendered)
    REVIEW.mkdir(parents=True,exist_ok=True)
    (REVIEW/"manifest.json").write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print("PASS",len(succeeded),"source editions",len(succeeded)*9,"review picons; 0 production changes")

if __name__=="__main__":main()
