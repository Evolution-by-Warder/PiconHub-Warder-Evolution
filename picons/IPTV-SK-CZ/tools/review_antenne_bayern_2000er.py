#!/usr/bin/env python3
"""Review ANTENNE BAYERN '2000er Hits' exact webcast logos in Warder style.

The 3 raster editions were discovered on the broadcaster's current 2000er
programme page, not guessed from a parent network. No image is recoloured,
redrawn or published to production. Review sheet enables exact choice.
"""
import hashlib,io,json
from pathlib import Path
from urllib.request import Request,urlopen
from PIL import Image,ImageDraw,ImageFont

OUT=Path("picons/IPTV-SK-CZ/review/antenne-bayern-2000er-20261104")
ROOT=Path("picons/IPTV-DE")
ROOT_AUDIT=Path("picons/IPTV-SK-CZ/catalog/world-radio-alias-scan-20261104.json")
SOURCE_PAGE="https://www.antenne.de/webradio/2000er-hits"
REF="4097:0:2:D289:8EE7:ED:0:0:0:0"
STREAM="https://s2-webradio.antenne.de/2000er-hits"
TARGET=REF.replace(":","_")+".png"
SOURCES=(
 ("publisher-jpeg-576","https://www.antenne.de/media/cache/3/version/7320/streamlogo_2000er_aby-v1.jpg/576b868d30f09328.jpg","jpg"),
 ("publisher-webp-65d","https://www.antenne.de/media/cache/3/version/7320/streamlogo_2000er_aby-v1.jpg/65d6a1cd91647a8a.webp","webp"),
 ("publisher-jpeg-a5","https://www.antenne.de/media/cache/3/version/7320/streamlogo_2000er_aby-v1.jpg/a5a146f163e99e07.jpg","jpg"),
)
SIZES=((50,30),(220,132),(400,240))
STYLES=("transparent","white","black")
MASTERS={"white":"c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589",
         "black":"61e69f7fc46e340453bf74ccd7af6ac9d8eba9f8e232884659e1ea99f6abf3fe"}
SHA=lambda b:hashlib.sha256(b).hexdigest()
MAX=2*1024*1024

def verify_identity():
    report=json.loads(ROOT_AUDIT.read_text(encoding="utf8"))
    rows=[r for r in report["shortlist_for_official_logo_research"]["DE"] if r["reference"]==REF]
    assert len(rows)==1 and rows[0]["name"]=="Antenne Bayern - 2000er Hits"
    assert rows[0]["stream_url"]==STREAM
    d=json.loads((ROOT/"catalog/release.json").read_text())
    assert TARGET not in d["packages"]["220x132"]["black"]["files"]

PINNED_SHA256 = {
    "publisher-jpeg-576": "ae3414170b1762c06f56f95ed0fe7901f1ce7db7be2c3f2f45aba5b8d96dbaa5",
    "publisher-webp-65d": "25936aa26612af8eaf03fbea6369cc29652d548c99335ce0bee06f83052ff262",
    "publisher-jpeg-a5": "4431986c233f0b9e0ac4c212d8a1420f79ea805c946e3286b805985032776285"
}

def source(slug,url,kind):
    assert url in [u for _,u,_ in SOURCES]
    name=OUT/slug/("official."+kind)
    name.parent.mkdir(parents=True,exist_ok=True)
    if name.is_file():raw=name.read_bytes()
    else:
        with urlopen(Request(url,headers={"User-Agent":"Warder-Radio-Broadcaster-Logo-Review"}),timeout=35) as rsp:
            raw=rsp.read(MAX+1)
    assert 0<len(raw)<=MAX
    if SHA(raw)!=PINNED_SHA256[slug]:
        raise ValueError("Publisher stream-logo artwork changed: "+slug)
    image=Image.open(io.BytesIO(raw))
    image.load()
    assert image.format.lower()==("jpeg" if kind=="jpg" else kind)
    assert image.width>=128 and image.height>=128
    wh=list(image.size)
    logo=image.convert("RGBA")
    bbox=logo.getchannel("A").getbbox()
    assert bbox
    logo=logo.crop(bbox)
    logo.thumbnail((192,104),Image.Resampling.LANCZOS)
    name.write_bytes(raw)
    return raw,logo,wh

def png(image):
    b=io.BytesIO();image.save(b,"PNG");return b.getvalue()

def contact(data,previews):
    fw=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",19)
    sm=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",14)
    sheet=Image.new("RGB",(1180,120+300*len(data)),"#0b2036")
    d=ImageDraw.Draw(sheet)
    d.text((20,20),"ANTENNE BAYERN 2000er Hits — OFFICIAL WEBSTREAM MARKS / WARDER REVIEW",font=fw,fill="#e7f7fb")
    d.text((20,54),"Three publisher-supplied sizes/formats. No recolouring, template masters unchanged.",font=sm,fill="#a2cce0")
    for i,row in enumerate(data):
        y=93+300*i
        d.text((24,y),row["slug"]+" · "+str(row["source_dimensions"]),font=sm,fill="#93e5f7")
        for j,style in enumerate(STYLES):
            x=22+386*j
            tile=Image.new("RGB",(330,199),"#8494a5" if style=="transparent" else "#0c1728")
            if style=="transparent":
                grid=ImageDraw.Draw(tile)
                for yy in range(0,199,17):
                    for xx in range(0,330,17):
                        if (xx//17+yy//17)%2:grid.rectangle((xx,yy,xx+16,yy+16),fill="#677b90")
            im=previews[(row["slug"],style)].resize((330,198),Image.Resampling.LANCZOS)
            tile.paste(im,(0,0),im)
            sheet.paste(tile,(x,y+26))
            d.text((x+10,y+238),style.upper(),font=sm,fill="#dbf3fa")
        d.text((24,y+274),row["source_sha256"],font=sm,fill="#a7c7d5")
    OUT.mkdir(parents=True,exist_ok=True)
    sheet.save(OUT/"review-sheet.png")

def main():
    verify_identity()
    masters={"transparent":Image.new("RGBA",(220,132),(0,0,0,0))}
    for style,sha in MASTERS.items():
        raw=(Path("plugin/artwork/templates/picons")/(style+"-sablona.png")).read_bytes()
        assert SHA(raw)==sha
        im=Image.open(io.BytesIO(raw)).convert("RGBA")
        assert im.size==(220,132)
        masters[style]=im
    entries=[];previews={}
    for slug,url,kind in SOURCES:
        try:
            raw,logo,wh=source(slug,url,kind)
        except Exception as error:
            entries.append(dict(slug=slug,url=url,status="blocked",reason=str(error)[:240]))
            print("BLOCKED",slug,type(error).__name__,str(error)[:180])
            continue
        variants={}
        for style in STYLES:
            board=masters[style].copy()
            board.alpha_composite(logo,((220-logo.width)//2,(132-logo.height)//2))
            previews[(slug,style)]=board
            for w,h in SIZES:
                res="%dx%d"%(w,h)
                icon=board if (w,h)==(220,132) else board.resize((w,h),Image.Resampling.LANCZOS)
                body=png(icon)
                out=OUT/slug/"artwork"/res/style/TARGET
                out.parent.mkdir(parents=True,exist_ok=True)
                out.write_bytes(body)
                variants[res+"/"+style]=dict(path=str(out.relative_to(OUT)),sha256=SHA(body),bytes=len(body))
        entries.append(dict(slug=slug,url=url,kind=kind,status="reviewed_render_only",source_dimensions=wh,
                            source_bytes=len(raw),source_sha256=SHA(raw),fit=list(logo.size),rendered=variants,
                            original_logo_unmodified=True,approved_for_production=False))
        print("REVIEW",slug,wh,len(variants),"source",SHA(raw))
    yes=[r for r in entries if r.get("status")=="reviewed_render_only"]
    if not yes:raise ValueError("No official logo could be rendered")
    contact(yes,previews)
    report=dict(schema=1,stage="review_only",source_page=SOURCE_PAGE,
                radio_station="Antenne Bayern - 2000er Hits",service_reference=REF,
                stream_url=STREAM,master_sha256=MASTERS,originals=entries,production_unchanged=True,
                no_colour_changes=True,require_exact_visual_approval=True)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"manifest.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print("PASS",len(yes),"broadcaster image editions",len(yes)*9,"Warder review picons")

if __name__=="__main__":main()
