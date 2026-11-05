#!/usr/bin/env python3
"""Read-only source provenance for new Warder radio logos; no graphics are published.

Fetch exact broadcaster-owned pages and record source candidate links, without
automatically equating family and station-specific subchannel logos.
"""
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

OUTPUT=Path("picons/IPTV-SK-CZ/catalog/radio-source-at-hu-20261105.json")
PAGES=(
    dict(country="AT",station="Antenne Salzburg",
         reference="4097:0:2:895E:1C76:ED:0:0:0:0",
         stream="https://edge69.streamonkey.net/antsalzburg-live",
         page="https://www.antennesalzburg.at/",
         caution="Main broadcaster program; do not confuse generic media owner logo with station mark"),
    dict(country="HU",station="Rádió 88 Retro",
         reference="4097:0:2:A333:B889:ED:0:0:0:0",
         stream="http://stream1.radio88.hu:8300/;stream",
         page="https://www.radio88.hu/radio88/",
         caution="Current on-site REPLAY branding may be an updated name; do not treat old 2015 RADIO88 logo as verified RETRO programme artwork"),
    dict(country="HU",station="Rádió 88 Retro",
         reference="4097:0:2:A333:B889:ED:0:0:0:0",
         stream="http://stream1.radio88.hu:8300/;stream",
         page="https://www.radio88.hu/megujulnak-a-webradioink/",
         caution="Official broadcaster's announcement mentions REPLAY, LIGHT, ENERGY; reconcile old Retro identity with live program before alias"),
    dict(country="HU",station="Club Dance Online - Retro",
         reference="4097:0:2:35D8:904A:ED:0:0:0:0",
         stream="http://stream.clubdance.online:8000/retro",
         page="https://clubdance.online/",
         caution="Look for exact Retro subchannel identity, not main Club Dance brand"),
)

class LogoFinder(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items=[]
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        kind=None
        if tag=="meta" and (a.get("property") or a.get("name") or "").lower() in ("og:image","twitter:image"):
            kind="social-preview"
            src=a.get("content") or ""
            alt=""
        elif tag in ("img","source"):
            kind=tag
            src=a.get("src") or a.get("data-src") or ""
            alt=a.get("alt") or a.get("title") or ""
        elif tag=="link" and ("icon" in (a.get("rel") or "").lower() or "image_src" in (a.get("rel") or "").lower()):
            kind="site-icon"
            src=a.get("href") or ""
            alt=""
        elif tag=="a" and any(x in (a.get("href") or "").lower() for x in (".png",".jpg",".svg",".ai",".eps")):
            kind="download-link"
            src=a.get("href") or ""
            alt=""
        else:
            return
        text=(src+" "+alt).lower()
        if not src or kind in ("img","source") and not any(q in text for q in ("logo","radio88","replay","retro","antenne","salzburg","club","dance","icon","brand")):
            return
        self.items.append((kind,src,alt[:160]))

def safe_url(page,href):
    raw=href.strip().strip('"').strip("'").split(",")[0].strip()
    if not raw or raw.startswith(("data:","javascript:","blob:")):
        return None
    url=urljoin(page,raw)
    p=urlparse(url)
    return url if p.scheme in ("https","http") and p.hostname else None

def main():
    world=json.loads(Path("picons/IPTV-SK-CZ/catalog/world-radio-alias-scan-20261104.json").read_text())
    report={"schema":1,"date":"2026-11-05","status":"research_only_not_approved",
            "no_production_mutation":True,"stations":[]}
    checked=set()
    for seed in PAGES:
        assert any(x["reference"]==seed["reference"] and x["name"]==seed["station"]
                   and x["stream_url"]==seed["stream"]
                   for x in world["shortlist_for_official_logo_research"][seed["country"]])
        item=dict(seed,status="not_checked",assets=[])
        try:
            if seed["page"] in checked:raise ValueError("Duplicate source page")
            checked.add(seed["page"])
            req=Request(seed["page"],headers={"User-Agent":"Mozilla/5.0 (Warder Radio editorial source verification)"})
            with urlopen(req,timeout=25) as res:
                mime=res.headers.get("Content-Type","")
                if "html" not in mime:raise ValueError("Not a broadcaster HTML page")
                body=res.read(2000001)
                if len(body)>2000000:raise ValueError("Page exceeds content limit")
                item["effective_url"]=res.url
                item["source_html_sha256"]=hashlib.sha256(body).hexdigest()
                item["source_html_bytes"]=len(body)
            finder=LogoFinder()
            finder.feed(body.decode("utf-8","replace"))
            seen=set()
            for kind,url,alt in finder.items:
                absolute=safe_url(item["effective_url"],url)
                if absolute is None or absolute in seen:continue
                seen.add(absolute)
                item["assets"].append(dict(role=kind,url=absolute,alt=alt,
                                           original_bytes_verified=False,source_hash_verified=False,
                                           exact_station_logo=False))
                if len(item["assets"])>=50:break
            item["status"]="page_audited"
        except Exception as e:
            item["status"]="blocked"
            item["error"]=str(e)[:450]
        report["stations"].append(item)
        print("AUDIT",seed["country"],seed["station"],item["status"],len(item["assets"]))
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    assert len(report["stations"])==len(PAGES)
    print("PASS: source URL provenance recorded; no production PNGs created")

if __name__=="__main__":
    main()
