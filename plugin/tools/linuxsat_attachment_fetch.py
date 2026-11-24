#!/usr/bin/env python3
"""Authorized Azzurra attachment acquisition. Review only; never publishes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, build_opener, HTTPCookieProcessor, HTTPRedirectHandler
from urllib.parse import urlencode
from http.cookiejar import CookieJar

BASE = "https://www.linuxsat-support.com"
THREAD = BASE + "/thread/157954-picons-dtt-italia-by-azzurra/"
HOST = "www.linuxsat-support.com"
MAX_HTML = 8 * 1024 * 1024
MAX_FILE = 16 * 1024 * 1024

def safe(url):
    p = urlsplit(url)
    if p.scheme != "https" or p.hostname != HOST or p.port not in (None,443) or p.username or p.password:
        raise ValueError("Unexpected LinuxSat URL")
    return url

class Redirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        safe(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)

class Page(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.forms, self.links, self.form = [], [], None
        self.feed(html)
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "form":
            self.form = {"action": a.get("action",""), "method": a.get("method","get").lower(), "fields": {}, "password": []}
        elif tag == "input" and self.form is not None and a.get("name"):
            typ = a.get("type","text").lower()
            if typ == "hidden":
                self.form["fields"][a["name"]] = a.get("value","")
            elif typ == "password":
                self.form["password"].append(a["name"])
            elif typ in ("text","email"):
                self.form.setdefault("users",[]).append(a["name"])
        elif tag == "a" and a.get("href"):
            self.links.append(a["href"])
    def handle_endtag(self, tag):
        if tag == "form" and self.form is not None:
            self.forms.append(self.form)
            self.form = None

def attachment_id(url):
    m = re.fullmatch(r"/attachment/(\d+)(?:-[^/]+)?/?",urlsplit(url).path)
    return m.group(1) if m else None

class Session:
    def __init__(self):
        self.opener = build_opener(Redirect(), HTTPCookieProcessor(CookieJar()))
    def get(self, url, limit=MAX_HTML, data=None):
        req = Request(safe(url), data=data, headers={"User-Agent":"Warder-SAT-Picon-Manager/1.0","Accept":"*/*"})
        with self.opener.open(req, timeout=30) as response:
            final = safe(response.geturl())
            raw = response.read(limit+1)
        if len(raw)>limit:
            raise ValueError("Response exceeds size limit")
        return final, raw
    def login(self, username, password):
        url, raw = self.get(BASE+"/login/")
        forms = [f for f in Page(raw.decode("utf-8","replace")).forms if f["password"]]
        if len(forms)!=1:
            raise ValueError("Login form unavailable or ambiguous")
        form = forms[0]
        if form["method"]!="post" or len(form["password"])!=1 or len(form.get("users",[]))!=1:
            raise ValueError("Unsupported login form")
        fields = dict(form["fields"])
        fields[form["users"][0]]=username
        fields[form["password"][0]]=password
        target = safe(urljoin(url,form["action"]))
        if not urlsplit(target).path.startswith("/login"):
            raise ValueError("Unexpected login endpoint")
        self.get(target,data=urlencode(fields).encode())
    def collect(self, output, known):
        pending=[THREAD]
        visited=set()
        attachments={}
        while pending:
            url=pending.pop(0)
            if url in visited:
                continue
            if len(visited)>=40:
                raise ValueError("Thread pagination exceeds limit")
            visited.add(url)
            final,raw=self.get(url)
            if not re.match(r"^/thread/157954(?:[-/]|$)",urlsplit(final).path):
                raise ValueError("Thread inaccessible after login")
            page=Page(raw.decode("utf-8","replace"))
            for href in page.links:
                candidate=urljoin(final,href)
                try:
                    safe(candidate)
                except ValueError:
                    continue
                aid=attachment_id(candidate)
                if aid:
                    attachments.setdefault(aid,candidate)
                elif re.match(r"^/thread/157954(?:[-/]|$)",urlsplit(candidate).path):
                    from urllib.parse import parse_qs
                    q=parse_qs(urlsplit(candidate).query)
                    if set(q)=={"pageNo"} and len(q["pageNo"])==1 and q["pageNo"][0].isdigit():
                        pending.append(candidate.split("#")[0])
        if not attachments:
            raise ValueError("No attachment links; authenticated access not confirmed")
        new=[]
        for aid,url in sorted(attachments.items(),key=lambda pair:int(pair[0])):
            if aid in known:
                continue
            if len(new)>=100:
                raise ValueError("New attachment batch exceeds limit")
            _,raw=self.get(url,MAX_FILE)
            if raw.startswith(b"\x89PNG\r\n\x1a\n"):
                ext=".png"
            elif raw[:4]==b"RIFF" and raw[8:12]==b"WEBP":
                ext=".webp"
            elif raw.startswith(b"\xff\xd8\xff"):
                ext=".jpg"
            elif raw.startswith(b"PK\x03\x04"):
                ext=".zip"
            else:
                raise ValueError("Unexpected attachment content; no checkpoint advance")
            digest=hashlib.sha256(raw).hexdigest()
            (output/(digest+ext)).write_bytes(raw)
            new.append({"attachment_id":aid,"sha256":digest,"bytes":len(raw),"type":ext})
        return {"status":"REVIEW_REQUIRED" if new else "UNCHANGED_SKIP","pages":len(visited),"attachment_count":len(attachments),"new":new,"no_publication":True}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--baseline",type=Path,required=True)
    args=parser.parse_args()
    try:
        username=os.environ["LINUXSAT_USERNAME"]
        password=os.environ["LINUXSAT_PASSWORD"]
        if not username or not password:
            raise ValueError("Missing credentials")
        data=json.loads(args.baseline.read_text())
        known=set(str(x) for x in data["attachment_ids"])
        args.output.mkdir(parents=True,exist_ok=True)
        session=Session()
        session.login(username,password)
        report=session.collect(args.output,known)
        (args.output/"report.json").write_text(json.dumps(report,indent=2)+"\n")
        print(report["status"],"new:",len(report["new"]))
    except Exception as exc:
        # Do not log exception text: it may contain sensitive URLs or form data.
        print("SOURCE_ERROR_NO_ADVANCE:",type(exc).__name__)
        return 2
    return 0

if __name__=="__main__":
    raise SystemExit(main())
