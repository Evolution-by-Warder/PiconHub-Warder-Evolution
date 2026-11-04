#!/usr/bin/env python3
"""Audit seven actual broadcaster webpages for original radio-logo URLs.

Research only. No PNG is selected, fetched or distributed. Exact stations and
references must match our current, independent four-country source audit.
Copyright/brand permission and correct programme identity still need review.
"""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import urljoin,urlsplit
from urllib.request import Request,urlopen

ROOT=Path("picons/IPTV-SK-CZ")
OUT=ROOT/"catalog/official-radio-source-batch-20261104.json"
AUDIT=ROOT/"catalog/world-radio-alias-scan-20261104.json"
HTML_MAX=3*1024*1024
STATIONS=(
 dict(country="PL",station="Polskie Radio Katowice",ref="4097:0:2:B4FF:D92A:ED:0:0:0:0",
      page="https://www.radio.katowice.pl/"),
 dict(country="PL",station="Polskie Radio Poznań",ref="4097:0:2:130A:2B66:ED:0:0:0:0",
      page="https://www.radiopoznan.fm/"),
 dict(country="AT",station="Antenne Salzburg",ref="4097:0:2:895E:1C76:ED:0:0:0:0",
      page="https://www.antennesalzburg.at/"),
 dict(country="AT",station="Antenne Steiermark",ref="4097:0:2:45CD:FE77:EC:0:0:0:0",
      page="https://steiermark.antenne.at/"),
 dict(country="DE",station="Antenne Bayern - 2000er Hits",ref="4097:0:2:D289:8EE7:ED:0:0:0:0",
      page="https://www.antenne.de/webradio/2000er-hits"),
 dict(country="HU",station="Rádió 88 Retro",ref="4097:0:2:A333:B889:ED:0:0:0:0",
      page="https://www.radio88.hu/"),
 dict(country="HU",station="Kossuth",ref="4097:0:2:6413:D6E3:ED:0:0:0:0",
      page="https://mediaklikk.hu/kossuth/"),
)

class LogoCandidateParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls=[]
        self.title=""
        self.in_title=False

    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=="title":
            self.in_title=True
        if tag=="meta":
            key=str(attrs.get("property") or attrs.get("name") or "").lower()
            if key in ("og:image","og:image:url","twitter:image","twitter:image:src"):
                self.urls.append((attrs.get("content",""),"meta:"+key,attrs.get("content","")))
        if tag=="link":
            rel=str(attrs.get("rel") or "").lower()
            if "icon" in rel or "image_src" in rel:
                self.urls.append((attrs.get("href",""),"link:"+rel,""))
        if tag in ("img","source"):
            parts=[attrs.get("src",""),attrs.get("data-src",""),attrs.get("data-lazy-src",""),attrs.get("srcset","")]
            text=" ".join(str(attrs.get(k) or "") for k in ("alt","title","class","id"))
            urls=[part.split(",")[0].strip().split(" ")[0] for part in parts if part]
            for url in urls:
                if re.search(r"logo|brand|station|radio|kossuth|antenne|pozna|katowice|retro|channel|program|app.?icon", url+" "+text,re.I):
                    self.urls.append((url,"img:"+text[:90],attrs.get("alt","")))
        if tag=="svg":
            cls=(attrs.get("class","")+" "+attrs.get("id","")).lower()
            if "logo" in cls:
                self.urls.append(("inline-svg","inline:"+cls[:60],""))

    def handle_endtag(self,tag):
        if tag=="title":self.in_title=False

    def handle_data(self,data):
        if self.in_title:
            self.title+=data[:160]

def score(role,url,alt):
    text=(role+" "+url+" "+alt).lower()
    if "og:image" in role:return 30
    if "logo" in text and "radio" in text:return 25
    if "logo" in text:return 20
    if "brand" in text:return 15
    if "station" in text:return 14
    if "icon" in text:return 5
    return 2

def main():
    base=json.loads(AUDIT.read_text(encoding="utf-8"))
    report={"schema":1,"date":"2026-11-04","status":"official_html_candidates_only",
            "source_catalogue":"catalog/world-radio-alias-scan-20261104.json",
            "scope":"seven station-specific official broadcaster pages",
            "production_changed":False,"station_results":[]}
    for item in STATIONS:
        country=item["country"]
        ref=item["ref"]
        candidates=[r for r in base["shortlist_for_official_logo_research"][country] if r["reference"]==ref]
        assert len(candidates)==1 and candidates[0]["name"]==item["station"],ref
        result=dict(item)
        result["stream_url"]=candidates[0]["stream_url"]
        result.update(status="pending",candidates=[])
        try:
            request=Request(item["page"],headers={"User-Agent":"Mozilla/5.0 (Warder PiconHub broadcaster provenance auditor)"})
            with urlopen(request,timeout=27) as response:
                content_type=response.headers.get("content-type","")
                assert "html" in content_type.lower(), "Unexpected HTML type"
                body=response.read(HTML_MAX+1)
                assert len(body)<=HTML_MAX
                result["final_url"]=response.geturl()
                result["html_sha256"]=hashlib.sha256(body).hexdigest()
                result["html_bytes"]=len(body)
            parser=LogoCandidateParser()
            parser.feed(body.decode("utf-8",errors="replace"))
            result["page_title"]=parser.title.strip()
            seen=set()
            items=[]
            for url,role,alt in parser.urls:
                url=str(url or "").strip().strip("\"'")
                if not url:continue
                if url=="inline-svg":
                    absolute="inline-svg"
                else:
                    absolute=urljoin(result["final_url"],url)
                    parsed=urlsplit(absolute)
                    if parsed.scheme not in ("http","https"):continue
                if absolute in seen:continue
                seen.add(absolute)
                items.append(dict(url=absolute,role=role,alt=alt[:150],
                                  score=score(role,absolute,alt),
                                  source_page=item["page"],asset_origin_verified=False,
                                  exact_station_logo_verified=False))
            items.sort(key=lambda x:(-x["score"],x["url"]))
            result["candidates"]=items[:26]
            result["total_detected"]=len(items)
            result["status"]="read"
        except Exception as exc:
            result["status"]="read_failed"
            result["error"]=(type(exc).__name__+": "+str(exc))[:300]
        report["station_results"].append(result)
        print(country,item["station"],result["status"],len(result["candidates"]))
    report["pages_read"]=sum(r["status"]=="read" for r in report["station_results"])
    report["image_url_candidates"]=sum(len(r["candidates"]) for r in report["station_results"])
    report["editorial_policy"]=[
        "An OG/image source is not proof of the correct logo; inspect original file and station context.",
        "Use only broadcaster-owned and provenance-verified assets; no AI logo invention.",
        "Preserve all three Warder official masters and all old production picons byte-for-byte.",
        "Kossuth August 2026 was an audio/programme relaunch; do not infer visual identity changed without graphical evidence.",
        "Do not publish any image from this report until its original source hash and visual approval are recorded.",
    ]
    OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("PASS: pages",report["pages_read"],"candidate image paths",report["image_url_candidates"],"production unchanged")

if __name__=="__main__":main()
