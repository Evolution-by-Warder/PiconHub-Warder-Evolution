#!/usr/bin/env python3
"""Produce review-only Warder radio picons from SHA-1-pinned original station vectors.

Sources remain unaltered. BLACK/WHITE use ONLY frozen Warder master PNGs.
No source is fetched from search results or third-party logo aggregator.
No production package, station catalogue, update feed, or service reference is edited.
"""
import hashlib
import io
import json
from pathlib import Path
from urllib.request import Request, urlopen
import zipfile

import cairosvg
from defusedxml import ElementTree as DefusedET
from PIL import Image, ImageDraw, ImageFont

ROOT = Path("picons")
MASTER_ROOT = Path("plugin/artwork/templates/picons")
OUTPUT = Path("picons/IPTV-SK-CZ/review/antenne-salzburg-20261105")
SOURCE_MAX = 128 * 1024
MASTER_HASHES = {
    "white": "c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589",
    "black": "61e69f7fc46e340453bf74ccd7af6ac9d8eba9f8e232884659e1ea99f6abf3fe",
}
SIZES = ((50, 30), (220, 132), (400, 240))
STYLES = ("transparent", "white", "black")
SOURCES = (
    {
        "slug":"antenne-salzburg",
        "country":"AT",
        "station":"Antenne Salzburg",
        "reference":"4097:0:2:895E:1C76:ED:0:0:0:0",
        "official_station_page":"https://www.antennesalzburg.at/",
        "source_page":"https://commons.wikimedia.org/wiki/File:Antenne_Salzburg_logo.svg",
        "source_url":"https://upload.wikimedia.org/wikipedia/commons/f/f7/Antenne_Salzburg_logo.svg",
        "source_sha1":"7d8b4ebb71766c3c2edc1591a3ffd8044de102a6",
        "source_kind":"Antenne Salzburg GmbH broadcaster source, Commons 2023 edition",
        "author":"Antenne Salzburg GmbH",
        "license":"PD-textlogo with trademark caveat",
        "license_url":"https://commons.wikimedia.org/wiki/Commons:Licensing",
        "scale":5,
        "identity_status":"Name matches official broadcaster; compare current 2026 logo before release"
    },
)


def digest(body, algorithm="sha256"):
    return hashlib.new(algorithm, body).hexdigest()


def get(url):
    if url != "https://upload.wikimedia.org/wikipedia/commons/f/f7/Antenne_Salzburg_logo.svg":
        raise ValueError("Unapproved source URL")
    req = Request(url, headers={"User-Agent": "WarderRadioPiconReview/1.0 (source-verification)"})
    with urlopen(req, timeout=40) as handle:
        response = handle.read(SOURCE_MAX + 1)
    if not 0 < len(response) <= SOURCE_MAX:
        raise ValueError("Oversize or empty original vector")
    return response


def validate_vector(raw):
    lower = raw.lower()
    for banned in (b"<!doctype", b"<!entity", b"<script", b"<image", b"<foreignobject",
                   b"@import", b"javascript:", b"url(http", b"url(//"):
        if banned in lower:
            raise ValueError("SVG contains forbidden external/dynamic content: " + str(banned))
    node = DefusedET.fromstring(raw)
    if not node.tag.endswith("svg"):
        raise ValueError("Not SVG")
    for element in node.iter():
        for key, value in element.attrib.items():
            if key.lower().endswith("href") and ("://" in value or value.startswith("//")):
                raise ValueError("External reference in SVG")
    return True


def inspect_baseline(src):
    folder = ROOT / ("IPTV-" + src["country"])
    coverage = json.loads((folder / "coverage.json").read_text())
    with open(folder / "plan.json", encoding="utf8") as fh:
        plan = json.load(fh)
    with open(folder / "catalog/release.json", encoding="utf8") as fh:
        manifest = json.load(fh)
    assert coverage["total_stations"] == plan["catalogue_stations"] == manifest["catalogue_stations"]
    existing = manifest["packages"]["220x132"]["transparent"]["files"]
    filename = src["reference"].replace(":", "_") + ".png"
    assert filename not in existing, "Already published in Warder format"
    with zipfile.ZipFile(folder / "packages" / ("iptv-" + src["country"].lower() + "-transparent-220x132.zip")) as archive:
        assert filename not in archive.namelist()
    return filename


def rgba_png(img):
    out = io.BytesIO()
    img.save(out, "PNG")
    return out.getvalue()


def put_preview(source, images, target):
    fontfile = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    title_font = ImageFont.truetype(fontfile, 24)
    small_font = ImageFont.truetype(fontfile, 18)
    sheet = Image.new("RGB", (1160, 620), "#142236")
    d = ImageDraw.Draw(sheet)
    d.text((35, 22), source["station"] + "  |  WARDER REVIEW ONLY", font=title_font, fill="#d8eef8")
    d.text((35, 61), source["reference"], font=small_font, fill="#a1bdd1")
    lefts = (36, 398, 760)
    for style, x in zip(STYLES, lefts):
        d.text((x + 6, 115), style.upper(), font=small_font, fill="#85e2fa")
        image = images[("220x132", style)]
        preview = Image.new("RGB", (300, 180), "#8895a7" if style == "transparent" else "#0a182b")
        if style == "transparent":
            draw = ImageDraw.Draw(preview)
            for cy in range(0, 180, 20):
                for cx in range(0, 300, 20):
                    if (cx // 20 + cy // 20) % 2:
                        draw.rectangle([cx, cy, cx + 19, cy + 19], fill="#6b7b90")
        large = image.resize((300, 180), Image.Resampling.LANCZOS)
        preview.paste(large, (0, 0), large)
        sheet.paste(preview, (x + 10, 160))
        d.text((x + 8, 362), "220 x 132   (shown x1.36)", font=small_font, fill="#e1edf9")
    d.text((35, 430), "Original colours & full lettering preserved; no Warder master changed.", font=small_font, fill="#b5cedf")
    d.text((35, 465), "Source: " + source["source_page"], font=small_font, fill="#a6d7e3")
    d.text((35, 500), "License: " + source["license"], font=small_font, fill="#a6d7e3")
    d.text((35, 555), "Must pass visual identity and licence review before production.", font=small_font, fill="#ffd48c")
    sheet.save(target)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    masters = {}
    for style, expected in MASTER_HASHES.items():
        raw = (MASTER_ROOT / (style + "-sablona.png")).read_bytes()
        if digest(raw) != expected:
            raise ValueError("Warder approved master SHA changed")
        masters[style] = Image.open(io.BytesIO(raw)).convert("RGBA")
        assert masters[style].size == (220, 132)
    overall = {
        "schema": 1, "date": "2026-11-04", "stage": "review_not_production",
        "original_master_sha256": MASTER_HASHES, "no_colour_change": True,
        "no_stretching": True, "new_production_refs": 0, "sources": [],
    }
    for station in SOURCES:
        filename = inspect_baseline(station)
        raw = get(station["source_url"])
        if digest(raw, "sha1") != station["source_sha1"]:
            raise ValueError("Original source changed: " + station["slug"])
        validate_vector(raw)
        png = cairosvg.svg2png(bytestring=raw, scale=station["scale"], unsafe=False)
        logo = Image.open(io.BytesIO(png)).convert("RGBA")
        box = logo.getchannel("A").getbbox()
        if not box:
            raise ValueError("Empty vector rendering")
        logo = logo.crop(box)
        if logo.width < 100 or logo.height < 40:
            raise ValueError("Vector resolution insufficient for Warder rendering")
        crop_size = logo.size
        logo.thumbnail((192, 104), Image.Resampling.LANCZOS)
        folder = OUTPUT / station["slug"]
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "source.svg").write_bytes(raw)
        variants = {}
        rendered = {}
        for style in STYLES:
            board = (Image.new("RGBA", (220,132), (0,0,0,0)) if style == "transparent" else masters[style].copy())
            offset = ((220 - logo.width) // 2, (132 - logo.height) // 2)
            board.alpha_composite(logo, offset)
            for width, height in SIZES:
                resolution = "%sx%s" % (width, height)
                output_image = board if (width,height) == (220,132) else board.resize((width,height), Image.Resampling.LANCZOS)
                assert output_image.mode == "RGBA" and output_image.size == (width,height)
                payload = rgba_png(output_image)
                rel = "artwork/%s/%s/%s" % (resolution, style, filename)
                file = folder / rel
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(payload)
                check = Image.open(io.BytesIO(payload))
                assert check.size == (width,height) and check.mode == "RGBA"
                variants[resolution + "/" + style] = {"path": rel, "bytes": len(payload), "sha256": digest(payload)}
                rendered[(resolution,style)] = output_image
        put_preview(station, rendered, folder / "review-sheet.png")
        detail = dict(station)
        detail.update(source_sha256=digest(raw), source_bytes=len(raw),
                      logo_crop_before_fit=list(crop_size), logo_fit=list(logo.size),
                      renders=variants, artwork_reviewed_by_owner=False,
                      production_commit=None, quality="needs_visual_review")
        (folder / "provenance.json").write_text(json.dumps(detail, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        attribution = [
            "# " + station["station"] + " — review-only picon provenance",
            "Source: " + station["source_page"], "Author: " + station["author"],
            "Source file SHA-1: " + station["source_sha1"],
            "Source file SHA-256: " + digest(raw),
            "License: " + station["license"] + " — " + station["license_url"],
            "Warder operation: SVG was rasterised, alpha-cropped, proportionally",
            "scaled to 192x104 max, centred and composited onto existing, unchanged",
            "Warder black/white masters; transparent variant has no frame.",
            "No logo pixels are recoloured or manually reconstructed.",
            "Review stage only: not a production package or a station endorsement.",
        ]
        (folder / "ATTRIBUTION.md").write_text("\n".join(attribution)+"\n",encoding="utf-8")
        overall["sources"].append(detail)
        print("REVIEW PREPARED", station["country"], station["station"], len(variants), "verified picons, sha1:", station["source_sha1"])
    (OUTPUT / "manifest.json").write_text(json.dumps(overall, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    assert len(overall["sources"]) == 1
    print("PASS: 1 original station logo, 9 deterministic Warder review picons; no production mutation")

if __name__ == "__main__":
    main()
