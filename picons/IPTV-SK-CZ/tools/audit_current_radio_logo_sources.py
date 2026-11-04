#!/usr/bin/env python3
"""Collect source imagery candidates from current broadcaster-owned pages.

No asset is used or published automatically. This reads only the exact allowlisted
publisher pages and records candidate logo URLs and origin evidence for QA.
"""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

OUT = Path("picons/IPTV-SK-CZ/catalog/radio-official-source-audit-20261104.json")
MAX_HTML = 4 * 1024 * 1024
PAGES = (
    ("HU", "Kossuth Rádió", "https://mediaklikk.hu/kossuth/"),
    ("HU", "Kossuth Rádió", "https://mediaklikk.hu/cikk/2026/08/23/augusztus-24-en-indul-a-megujult-kossuth/"),
    ("PL", "ESKA ROCK", "https://www.eskarock.pl/"),
    ("PL", "ESKA ROCK", "https://radioeskasa.grupazpr.pl/marka/1009"),
    ("PL", "ESKA ROCK", "https://srrr.grupazpr.pl/marka/1019"),
    ("DE", "radio3 (rbb)", "https://www.rbb-online.de/unternehmen/presse/programmwochen/radio3/"),
)

class Images(HTMLParser):
    def __init__(self):
        super().__init__()
        self.found = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta":
            prop = (a.get("property") or a.get("name") or "").lower()
            if prop in ("og:image", "og:image:url", "twitter:image", "twitter:image:src"):
                self.found.append((prop, a.get("content", ""), ""))
        elif tag == "link":
            rel = (a.get("rel") or "").lower()
            if "icon" in rel or "image_src" in rel:
                self.found.append(("link:" + rel, a.get("href", ""), ""))
        elif tag in ("img", "source"):
            src = a.get("src") or a.get("data-src") or a.get("srcset") or ""
            alt = a.get("alt") or a.get("title") or ""
            lo = (src + " " + alt).lower()
            if any(word in lo for word in ("logo", "kossuth", "eska", "rock", "radio3", "logotyp", "brand", "ikon")):
                self.found.append((tag, src, alt))

def main():
    results = []
    for country, station, page in PAGES:
        item = dict(country=country, station=station, page=page, page_status="pending", assets=[])
        try:
            req = Request(page, headers={"User-Agent": "Mozilla/5.0 (compatible; Warder Radio source audit/1.0; editorial review)"})
            with urlopen(req, timeout=25) as response:
                content_type = response.headers.get("content-type", "")
                if "text/html" not in content_type and "application/xhtml" not in content_type:
                    raise ValueError("Unexpected content type: " + content_type)
                body = response.read(MAX_HTML + 1)
                item.update(http_status=response.status, final_url=response.url,
                            content_type=content_type, html_bytes=len(body),
                            html_sha256=hashlib.sha256(body).hexdigest())
            if len(body) > MAX_HTML:
                raise ValueError("HTML exceeded size limit")
            parser = Images()
            parser.feed(body.decode("utf-8", errors="replace"))
            seen = set()
            for kind, url, alt in parser.found:
                url = url.split(",")[0].strip().strip("\\'\"").split(" 2x")[0].split(" 1x")[0]
                if not url or url.startswith(("data:", "blob:", "javascript:")):
                    continue
                absolute = urljoin(item.get("final_url", page), url)
                p = urlparse(absolute)
                if p.scheme != "https" and p.scheme != "http":
                    continue
                if absolute in seen:
                    continue
                seen.add(absolute)
                item["assets"].append(dict(role=kind, url=absolute, alt=alt[:120],
                                           page_owned=True, publisher_supplied_candidate=True,
                                           current_logo_confirmed=False))
                if len(item["assets"]) >= 45:
                    break
            item["page_status"] = "read"
        except (ValueError, HTTPError, URLError, TimeoutError, OSError) as error:
            item["page_status"] = "read_failed"
            item["error"] = str(error)[:400]
        results.append(item)
        print("SOURCE", station, page, item["page_status"], len(item["assets"]))
    report = {
        "schema": 1, "date": "2026-11-04", "status": "source_candidates_only_not_published",
        "purpose": "identify current official broadcaster logos for original Warder picons",
        "known_rebrand": {
            "HU Kossuth Rádió": "Relaunched August 24, 2026; legacy pre-2026 logo may be outdated; confirm current brand manually.",
            "PL ESKA ROCK": "Use radio operator ZPR Media site/assets, not ESKA ROCK TV or generic ESKA branding.",
        },
        "report": results,
        "review_rules": [
            "An OG image can be an article cover and is not an approved radio station logo.",
            "Favicon can be a generic publisher icon; no automatic logo selection.",
            "Do not use third-party rebrands, historical logos or search-engine thumbnails.",
            "No original bitmaps downloaded or committed by this audit.",
        ],
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("PASS SOURCE AUDIT",sum(x["page_status"]=="read" for x in results),
          "pages read;",sum(len(x["assets"]) for x in results),"candidate asset links; NO PNG changed")

if __name__=="__main__":
    main()
