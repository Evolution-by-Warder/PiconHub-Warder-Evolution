"""LinuxSat session and one-file acceptance test. No response bodies enter logs."""
import hashlib
import json
import os
import re
from html.parser import HTMLParser
from http.cookiejar import CookieJar
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin, urlsplit
from urllib.request import build_opener, HTTPCookieProcessor, HTTPRedirectHandler, Request

BASE = "https://www.linuxsat-support.com"
THREAD = BASE + "/thread/157954-picons-dtt-italia-by-azzurra/"
LIMIT = 8 * 1024 * 1024
FILE_LIMIT = 16 * 1024 * 1024
PROOF_ID = "151974"
PROOF_HASH = "f2c1d4f903b5e29c39fd86d1c0006f239f5a5a5b0dd0a2237deb329a6d6ee70e"


class SourceError(Exception):
    """Only fixed diagnostics and numeric HTTP statuses may be used here."""


def trusted(url):
    if urlsplit(url)[:2] != ("https", "www.linuxsat-support.com"):
        raise SourceError("unexpected_origin")
    return url


class Redirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        trusted(urljoin(req.full_url, newurl))
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.forms = []
        self.form = None
        self.member = False
        self.challenge = False
        self.links = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if (a.get("class", "").split() and set(a["class"].split()) & {"g-recaptcha", "h-captcha", "cf-turnstile"}
                or tag == "input" and "captcha" in a.get("name", "").lower()):
            self.challenge = True
        if tag == "li" and a.get("id") == "userMenu":
            self.member = True
        if tag == "form":
            self.form = {"action": a.get("action", ""), "method": a.get("method", "get").lower(),
                         "password": [], "user": [], "hidden": {}}
        if tag == "input" and self.form is not None and a.get("name"):
            typ = a.get("type", "text").lower()
            if typ == "hidden":
                self.form["hidden"][a["name"]] = a.get("value", "")
            elif typ == "password":
                self.form["password"].append(a["name"])
            elif typ in ("email", "text"):
                self.form["user"].append(a["name"])
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])
            path = urlsplit(urljoin(BASE, a["href"])).path
            if path.rstrip("/") == "/logout" or "jsLogout" in a.get("class","").split():
                self.member = True
        if tag == "body" and re.fullmatch(r"[1-9]\d*", a.get("data-user-id", "")):
            self.member = True

    def handle_endtag(self, tag):
        if tag == "form" and self.form is not None:
            self.forms.append(self.form)
            self.form = None


def file_id(url):
    match = re.fullmatch(r"/cms/file-download/(\d+)/?", urlsplit(url).path)
    return match[1] if match else None


class Session:
    def __init__(self):
        self.opener = build_opener(Redirect(), HTTPCookieProcessor(CookieJar()))

    def request(self, url, stage, *, data=None, limit=LIMIT, method=None):
        request = Request(trusted(url), data=data, method=method, headers={
            "User-Agent": "Warder-SAT-Picon-Manager/1.0", "Accept": "*/*"})
        try:
            with self.opener.open(request, timeout=40) as response:
                raw = response.read(limit + 1)
                if len(raw) > limit:
                    raise SourceError(stage + "_size_limit")
                return trusted(response.geturl()), response.headers, raw
        except HTTPError as exc:
            raise SourceError(f"{stage}_HTTP_{exc.code}") from None
        except (URLError, OSError):
            raise SourceError(stage + "_transport_error") from None

    def login(self):
        username = os.environ.get("LINUXSAT_USERNAME")
        password = os.environ.get("LINUXSAT_PASSWORD")
        if not username or not password:
            raise SourceError("repository_secrets_unavailable")
        url, _, raw = self.request(BASE + "/cms/login/", "login_page")
        page = Page(raw.decode("utf-8", "replace"))
        if page.challenge:
            raise SourceError("interactive_verification_required")
        forms = [f for f in page.forms if f["password"]]
        if len(forms) != 1:
            raise SourceError("login_form_unavailable")
        form = forms[0]
        action = trusted(urljoin(url, form["action"]))
        if (urlsplit(action).path.rstrip("/") != "/cms/login" or form["method"] != "post"
                or len(form["user"]) != 1 or len(form["password"]) != 1):
            raise SourceError("unsupported_login_form")
        fields = dict(form["hidden"])
        fields[form["user"][0]] = username
        fields[form["password"][0]] = password
        self.request(action, "login_submit", data=urlencode(fields).encode())
        _, _, raw = self.request(THREAD, "member_session")
        if not Page(raw.decode("utf-8", "replace")).member:
            raise SourceError("authenticated_member_marker_missing")

    def proof(self):
        page_url, _, raw = self.request(THREAD + "?postID=790931", "proof_post")
        links = [urljoin(page_url, link) for link in Page(raw.decode("utf-8","replace")).links]
        url = next((link for link in links if file_id(link) == PROOF_ID), None)
        if not url:
            raise SourceError("proof_attachment_missing")
        _, _, blob = self.request(url, "proof_download", limit=FILE_LIMIT)
        digest = hashlib.sha256(blob).hexdigest()
        if not blob.startswith(b"\x89PNG\r\n\x1a\n") or digest != PROOF_HASH:
            raise SourceError("proof_png_or_digest_mismatch")
        print(json.dumps({"verified_member_session": True, "attachment_id": PROOF_ID,
                          "bytes": len(blob), "sha256": digest}))


if __name__ == "__main__":
    try:
        session = Session()
        session.login()
        session.proof()
    except SourceError as error:
        print("SOURCE_ERROR_NO_ADVANCE", error)
        raise SystemExit(2)
    except Exception:
        print("SOURCE_ERROR_NO_ADVANCE unexpected_response")
        raise SystemExit(2)
