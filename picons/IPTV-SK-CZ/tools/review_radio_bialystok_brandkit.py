#!/usr/bin/env python3
"""Audit Polskie Radio Białystok broadcaster-published logo kit, read-only.

Do not infer officialness from a Google image. Download exactly one
publisher-owned brand ZIP, inspect safe member names, image dimensions, and
generate a contact sheet of raster members for visual review.
No production PiconHub ZIP, licence claim or service reference is changed.
"""
import hashlib
import io
import json
from pathlib import Path
import re
import stat
from urllib.request import Request,urlopen
import zipfile

from PIL import Image,ImageDraw,ImageFont,ImageOps

ZIP_URL = "https://www.radio.bialystok.pl/images/logo/logo.zip"
SOURCE_PAGE = "https://www.radio.bialystok.pl/reklama"
SOURCE_REF = "4097:0:2:BC04:A7A6:ED:0:0:0:0"
EXPECTED_STREAM = "http://stream4.nadaje.com:15476/radiobialystok"
OUTPUT = Path("picons/IPTV-SK-CZ/review/radio-bialystok-official-brandkit-20261104")
MAX_ZIP_BYTES = 12 * 1024 * 1024
MAX_FILES = 100
MAX_TOTAL_DECOMPRESSED = 70 * 1024 * 1024
MAX_MEMBER = 18 * 1024 * 1024
MAX_IMAGE_PX = 50_000_000
SHA = lambda raw: hashlib.sha256(raw).hexdigest()


def validate_existing_station():
    # Fetch the active country candidate, never invent an Enigma2 reference.
    audit = json.loads(Path("picons/IPTV-SK-CZ/catalog/world-radio-alias-scan-20261104.json").read_text())
    matches = [r for r in audit["shortlist_for_official_logo_research"]["PL"] if r["reference"] == SOURCE_REF]
    assert len(matches) == 1
    assert matches[0]["name"] == "Polskie Radio Bialystok"
    assert matches[0]["stream_url"] == EXPECTED_STREAM
    current = json.loads(Path("picons/IPTV-PL/catalog/release.json").read_text())
    key = SOURCE_REF.replace(":", "_") + ".png"
    assert key not in current["packages"]["220x132"]["transparent"]["files"]
    return key


def retrieve_kit():
    with urlopen(Request(ZIP_URL, headers={"User-Agent":"Warder-PiconHub-original-radio-logo-review/1.0"}), timeout=45) as response:
        assert response.status == 200
        b = response.read(MAX_ZIP_BYTES + 1)
    assert 0 < len(b) <= MAX_ZIP_BYTES
    assert zipfile.is_zipfile(io.BytesIO(b)), "Official logo-kit response is not a ZIP"
    return b


def classify(name,raw):
    suffix = Path(name).suffix.lower()
    if raw.startswith(b"\x89PNG\r\n\x1a\n"): return "PNG"
    if raw.startswith(b"\xff\xd8\xff"): return "JPEG"
    if raw[:5].lower().startswith(b"<?xml") or b"<svg" in raw[:1500].lower():
        if suffix == ".svg": return "SVG"
    if raw.startswith(b"%PDF"): return "PDF"
    if suffix in (".eps",".ai"): return "vector_other"
    return "unsupported"


def contact_sheet(images):
    if not images: return False
    width = 1440
    columns = 3
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",18)
    sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",13)
    cell_w,cell_h=465,290
    rows=(len(images)+columns-1)//columns
    sheet=Image.new("RGB",(width,max(340,90+rows*cell_h)),"#0c1f32")
    draw=ImageDraw.Draw(sheet)
    draw.text((26,18),"POLSKIE RADIO BIAŁYSTOK — OFFICIAL BROADCASTER ZIP, SOURCE REVIEW",font=font,fill="#d4eff7")
    draw.text((26,48),"Only broadcaster ZIP raster thumbnails. No retouch, no Warder production render.",font=sm,fill="#a5c7d8")
    for i,(filename,image) in enumerate(images):
        x=22+(i%columns)*cell_w
        y=80+(i//columns)*cell_h
        draw.rounded_rectangle((x,y,x+450,y+cell_h-10),radius=7,fill="#182c44")
        canvas=Image.new("RGB",(432,205),"#e4edf5")
        display=image.convert("RGBA")
        display.thumbnail((410,183),Image.Resampling.LANCZOS)
        bg=Image.new("RGBA",canvas.size,(232,237,242,255))
        bg.alpha_composite(display,((432-display.width)//2,(205-display.height)//2))
        canvas.paste(bg.convert("RGB"))
        sheet.paste(canvas,(x+10,y+10))
        displayname=filename if len(filename)<57 else filename[:54]+"…"
        draw.text((x+9,y+221),displayname,font=sm,fill="#e4f4fa")
        draw.text((x+9,y+243),"%s×%s" % image.size,font=sm,fill="#acd7ef")
    OUTPUT.mkdir(parents=True,exist_ok=True)
    sheet.save(OUTPUT/"official-zip-contact-sheet.png")
    return True


def main():
    expected_filename=validate_existing_station()
    OUTPUT.mkdir(parents=True,exist_ok=True)
    raw=retrieve_kit()
    # An immutable source snapshot for future review; not a production image.
    (OUTPUT/"original-logo-kit.zip").write_bytes(raw)
    inventory=[]
    pictures=[]
    total=0
    with zipfile.ZipFile(io.BytesIO(raw)) as bundle:
        info=bundle.infolist()
        assert len(info) <= MAX_FILES
        assert len({f.filename for f in info}) == len(info), "Duplicate ZIP entries"
        for entry in info:
            if entry.is_dir(): continue
            if stat.S_ISLNK(entry.external_attr >> 16):raise ValueError("Symlink in logo kit")
            name=entry.filename.replace("\\","/")
            assert name and not name.startswith("/") and ".." not in Path(name).parts and "\x00" not in name
            assert entry.file_size <= MAX_MEMBER
            total += entry.file_size
            assert total < MAX_TOTAL_DECOMPRESSED
            file_raw=bundle.read(entry)
            assert len(file_raw)==entry.file_size
            kind=classify(name,file_raw)
            record={"file":name,"format":kind,"bytes":len(file_raw),"sha256":SHA(file_raw),"dimensions":None,"eligible_raster":False}
            if kind in ("PNG","JPEG"):
                try:
                    with Image.open(io.BytesIO(file_raw)) as image:
                        assert 0 < image.width * image.height <= MAX_IMAGE_PX
                        image.load()
                        record["dimensions"]=[image.width,image.height]
                        record["eligible_raster"]=image.width>=160 and image.height>=75
                        if record["eligible_raster"] and len(pictures)<24:
                            pictures.append((name,image.copy()))
                except Exception as e:
                    record["preview_error"]=str(e)[:200]
            inventory.append(record)
    shown=contact_sheet(pictures)
    report={"schema":1,"status":"review_only_broadcaster_source","source_page":SOURCE_PAGE,
            "source_url":ZIP_URL,"source_bytes":len(raw),"source_sha256":SHA(raw),
            "station":"Polskie Radio Bialystok","service_reference":SOURCE_REF,
            "picon_filename":expected_filename,"expected_stream":EXPECTED_STREAM,
            "archive_entries":len(inventory),"total_decompressed_bytes":total,
            "raster_previews":len(pictures),"contact_sheet_generated":shown,
            "members":inventory,
            "notes":["ZIP distributed by broadcaster. Fonts and license need inspection before redistribution.",
                     "Image members may include old/current variants. Do not auto-select by filename.",
                     "No production station or PNG files modified."]}
    (OUTPUT/"inventory.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("OFFICIAL KIT",len(raw),"bytes",SHA(raw))
    print("ZIP ENTRIES",len(inventory),"RASTER PREVIEWS",len(pictures))
    for row in inventory:print("KIT FILE",row["format"],row["bytes"],row["file"],row["dimensions"])
    print("PASS: official ZIP audited; no Warder production changes")

if __name__=="__main__":main()
