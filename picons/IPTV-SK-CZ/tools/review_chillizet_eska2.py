#!/usr/bin/env python3
"""Only render original Antenne Vorarlberg official press assets into Warder review PNGs."""
import hashlib,io,json,struct
from pathlib import Path
from urllib.request import Request,urlopen
from PIL import Image,ImageDraw,ImageFont

ROOT=Path("picons/IPTV-SK-CZ/review/chillizet-eska2-20261104")
MASTER=Path("plugin/artwork/templates/picons")
AUDIT=Path("picons/IPTV-SK-CZ/catalog/world-radio-alias-scan-20261104.json")
BASE=""
PAGE="https://newsroom.eurozet.pl/presskits/chillizet; https://dwa.eska.pl/"
STYLE=("transparent","white","black")
SIZES=((50,30),(220,132),(400,240))
SHAS={"white":"c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589",
      "black":"61e69f7fc46e340453bf74ccd7af6ac9d8eba9f8e232884659e1ea99f6abf3fe"}
STATIONS=(
  dict(slug="chillizet",name="Chilli ZET",
       reference="4097:0:2:418A:25BD:ED:0:0:0:0",
       stream_url="https://n-4-1.dcs.redcdn.pl/sc/o2/Eurozet/live/chillizet.livx",
       src="https://prowly-prod.s3.eu-west-1.amazonaws.com/uploads/4587/assets/32565/Logo_ChilliZET_RGB.jpg",
       page="https://newsroom.eurozet.pl/presskits/chillizet",ext="jpg",source_sha256="769a5207e46a57a41a47a4d1e5d4755c98ed0f7ae0f93a101e8edfa3180fe814"),
  dict(slug="eska2",name="ESKA 2",
       reference="4097:0:2:B0F1:AC26:ED:0:0:0:0",
       stream_url="https://ic1.smcdn.pl/1530-1.mp3",
       src="https://cdn.files.smcloud.net/t/eska2-logo.png",
       page="https://dwa.eska.pl/",ext="png",source_sha256="143bd8c8157fae3c6ba01e062edf5eaf1f979d0901e99f028cb57a2bb1208651"),
)

sha=lambda b:hashlib.sha256(b).hexdigest()

def src_bytes(station,folder):
    file=folder/("original."+station["ext"])
    if file.is_file(): raw=file.read_bytes()
    else:
        url=station["src"]
        if not (url.startswith("https://prowly-prod.s3.eu-west-1.amazonaws.com/uploads/4587/assets/") or
                url.startswith("https://cdn.files.smcloud.net/t/")):
            raise ValueError("Unapproved broadcaster asset host")
        with urlopen(Request(url,headers={"User-Agent":"Warder-PiconHub-original-logo-review"}),timeout=35) as response:
            raw=response.read(2000001)
    assert 0<len(raw)<2000000
    if station["source_sha256"]: assert sha(raw)==station["source_sha256"]
    image=Image.open(io.BytesIO(raw));image.load()
    assert image.format in ("PNG","JPEG") and image.width>300 and image.height>150
    dims=list(image.size)
    image=image.convert("RGBA")
    bb=image.getchannel("A").getbbox()
    assert bb
    image=image.crop(bb);image.thumbnail((192,104),Image.Resampling.LANCZOS)
    file.write_bytes(raw)
    return raw,image,dims

def png(image):
    f=io.BytesIO();image.save(f,"PNG");return f.getvalue()

def preview(items,rendered):
    sheet=Image.new("RGB",(1190,820),"#122137")
    d=ImageDraw.Draw(sheet)
    font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",21)
    small=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",15)
    d.text((28,23),"CHILLIZET / ESKA 2 - ORIGINAL BROADCASTER LOGOS - WARDER REVIEW",font=font,fill="#d5f1fb")
    d.text((28,63),"Original manufacturer PNG/JPG, approved frozen Warder backgrounds, no logo recolouring.",font=small,fill="#a9c9dc")
    for i,item in enumerate(items):
        y=110+i*338
        d.text((30,y),item["name"]+" / "+item["reference"],font=small,fill="#b4e8f5")
        for j,style in enumerate(STYLE):
            x=28+j*386
            bg=Image.new("RGB",(330,198),"#8595a9" if style=="transparent" else "#0b1928")
            if style=="transparent":
                draw=ImageDraw.Draw(bg)
                for yy in range(0,198,16):
                    for xx in range(0,330,16):
                        if (xx//16+yy//16)%2:draw.rectangle((xx,yy,xx+15,yy+15),fill="#677b93")
            img=rendered[(item["slug"],style)].resize((330,198),Image.Resampling.LANCZOS)
            bg.paste(img,(0,0),img)
            sheet.paste(bg,(x,y+32))
            d.text((x+7,y+244),style.upper(),font=small,fill="#91e7fa")
        d.text((30,y+281),"Source SHA256 "+item["source_sha256"],font=small,fill="#acc6d8")
    d.text((28,788),"Review-only originals; no production ZIPs or station catalogues modified.",font=small,fill="#ffdba5")
    sheet.save(ROOT/"review-sheet.png")

def main():
    data=json.loads(AUDIT.read_text())
    old=data["shortlist_for_official_logo_research"]["PL"]
    for station in STATIONS:
        matches=[x for x in old if x["reference"]==station["reference"]]
        assert len(matches)==1 and matches[0]["name"]==station["name"]
        assert matches[0]["stream_url"]==station["stream_url"]
    ROOT.mkdir(parents=True,exist_ok=True)
    masters={"transparent":Image.new("RGBA",(220,132),(0,0,0,0))}
    for style,expected in SHAS.items():
        raw=(MASTER/(style+"-sablona.png")).read_bytes()
        assert sha(raw)==expected
        masters[style]=Image.open(io.BytesIO(raw)).convert("RGBA")
        assert masters[style].size==(220,132)
    items=[];rendered={}
    for station in STATIONS:
        folder=ROOT/station["slug"]
        folder.mkdir(parents=True,exist_ok=True)
        raw,mark,original_wh=src_bytes(station,folder)
        name=station["reference"].replace(":","_")+".png"
        variants={}
        for style in STYLE:
            board=masters[style].copy()
            board.alpha_composite(mark,((220-mark.width)//2,(132-mark.height)//2))
            rendered[(station["slug"],style)]=board
            for w,h in SIZES:
                res="%dx%d"%(w,h)
                img=board if (w,h)==(220,132) else board.resize((w,h),Image.Resampling.LANCZOS)
                body=png(img)
                assert struct.unpack(">II",body[16:24])==(w,h)
                path=folder/"artwork"/res/style/name
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(body)
                variants[res+"/"+style]=dict(bytes=len(body),sha256=sha(body),path=str(path.relative_to(folder)))
        item=dict(station)
        item.update(source_url=station["src"],source_page=station["page"],source_sha256=sha(raw),
                    source_bytes=len(raw),source_dimensions=original_wh,fitted_dimensions=list(mark.size),
                    renders=variants,production_approved=False,visual_approval_pending=True,
                    source_owner="Eurozet press kit / Grupa ZPR official publisher asset")
        items.append(item)
        (folder/"provenance.json").write_text(json.dumps(item,ensure_ascii=False,indent=2)+"\n")
        print("REVIEW",item["name"],len(variants),"picons",sha(raw))
    preview(items,rendered)
    (ROOT/"manifest.json").write_text(json.dumps(dict(schema=1,stage="review_only",
          original_source=PAGE,masters=SHAS,stations=items,production_changed=False),
          ensure_ascii=False,indent=2)+"\n")
    assert len(items)==2 and all(len(x["renders"])==9 for x in items)
    print("PASS: 18 Warder preview PNGs from official originals, 0 production files")

if __name__=="__main__": main()
