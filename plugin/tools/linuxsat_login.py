"""Use the site's normal browser sign-in. Keep the session in memory only."""
import base64
import hashlib
import json
import os
import re
from contextlib import contextmanager
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

BASE = "https://www.linuxsat-support.com"
THREAD = BASE + "/thread/157954-picons-dtt-italia-by-azzurra/"
LOGIN = BASE + "/cms/login/"
LIMIT = 8 * 1024 * 1024
FILE_LIMIT = 16 * 1024 * 1024
PROOF_ID = "151974"
PROOF_HASH = "f2c1d4f903b5e29c39fd86d1c0006f239f5a5a5b0dd0a2237deb329a6d6ee70e"


class SourceError(Exception):
    """Only fixed diagnostics and numeric HTTP statuses may enter this exception."""


def trusted(url):
    if urlsplit(url)[:2] != ("https", "www.linuxsat-support.com"):
        raise SourceError("unexpected_origin")
    return url


def file_id(url):
    match = re.fullmatch(r"/cms/file-download/(\d+)/?", urlsplit(url).path)
    return match[1] if match else None


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.member = False
        self.links = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "li" and a.get("id") == "userMenu":
            self.member = True
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])


class Session:
    def __init__(self, page):
        self.page = page

    def request(self, url, stage, *, limit=LIMIT, method="GET"):
        # Browser cookies, redirect policy and bounded streaming stay in the same origin.
        result = self.page.evaluate("""async ({url, method, limit}) => {
            const r = await fetch(url, {method, credentials: 'same-origin', redirect: 'error',
                cache: 'no-store', signal: AbortSignal.timeout(45000)});
            if (!r.ok) return {status: r.status};
            const headers = Object.fromEntries(['etag', 'last-modified', 'content-length',
                'content-type', 'content-disposition'].map(k => [k, r.headers.get(k) || '']));
            let length = 0, encoded = '';
            if (r.body) {
                const reader = r.body.getReader();
                for (;;) {
                    const {done, value} = await reader.read();
                    if (done) break;
                    length += value.length;
                    if (length > limit) { await reader.cancel(); return {tooLarge: true}; }
                    for (let i = 0; i < value.length; i += 8192)
                        encoded += String.fromCharCode(...value.subarray(i, i + 8192));
                }
            }
            return {status: r.status, headers, bytes: btoa(encoded)};
        }""", {"url": trusted(url), "method": method, "limit": limit})
        if result.get("tooLarge"):
            raise SourceError(stage + "_size_limit")
        if result["status"] != 200:
            raise SourceError(f"{stage}_HTTP_{result['status']}")
        return url, result["headers"], base64.b64decode(result["bytes"], validate=True)

    def proof(self):
        page_url, _, raw = self.request(THREAD, "proof_post")
        page = Page(raw.decode("utf-8", "replace"))
        if not page.member:
            raise SourceError("download_session_not_authenticated")
        links = [urljoin(page_url, link) for link in page.links]
        url = next((link for link in links if file_id(link) == PROOF_ID), None)
        if not url:
            raise SourceError("proof_attachment_missing")
        _, _, blob = self.request(url, "proof_download", limit=FILE_LIMIT)
        digest = hashlib.sha256(blob).hexdigest()
        if not blob.startswith(b"\x89PNG\r\n\x1a\n") or digest != PROOF_HASH:
            raise SourceError("proof_png_or_digest_mismatch")
        print(json.dumps({"verified_member_session": True, "attachment_id": PROOF_ID,
                          "bytes": len(blob), "sha256": digest}))


def verification_required(page):
    return page.locator('iframe[src*="captcha" i], iframe[src*="challenges.cloudflare.com"], '
                        '[class~="g-recaptcha"], [class~="h-captcha"], .cf-turnstile, '
                        'input[autocomplete="one-time-code"], input[name*="captcha" i]').count() > 0


@contextmanager
def authenticated():
    from playwright.sync_api import sync_playwright

    username = os.environ.get("LINUXSAT_USERNAME")
    password = os.environ.get("LINUXSAT_PASSWORD")
    if not username or not password:
        raise SourceError("repository_secrets_unavailable")
    with sync_playwright() as engine:
        browser = engine.chromium.launch(channel="chrome")
        context = browser.new_context(service_workers="block", accept_downloads=False)
        try:
            # Only the forum may receive requests from a page containing account credentials.
            context.route("**/*", lambda r: r.continue_() if urlsplit(r.request.url)[:2] ==
                          ("https", "www.linuxsat-support.com") else r.abort())
            page = context.new_page()
            response = page.goto(LOGIN, wait_until="domcontentloaded")
            if not response or response.status != 200:
                raise SourceError(f"login_page_HTTP_{response.status if response else 0}")
            if verification_required(page):
                raise SourceError("interactive_verification_required")
            form = page.locator("form").filter(has=page.locator('input[type="password"]'))
            if form.count() != 1 or (form.get_attribute("method") or "").lower() != "post":
                raise SourceError("login_form_unavailable")
            action = trusted(urljoin(page.url, form.get_attribute("action") or page.url))
            if urlsplit(action).path.rstrip("/") != "/cms/login":
                raise SourceError("unexpected_login_action")
            form.locator('input[name="username"]').fill(username)
            form.locator('input[type="password"]').fill(password)
            form.locator('button[type="submit"], input[type="submit"]').click()
            page.wait_for_load_state("domcontentloaded")
            if verification_required(page) or "multifactor" in urlsplit(page.url).path:
                raise SourceError("interactive_verification_required")
            if page.locator('form input[type="password"]').count():
                raise SourceError("login_form_returned_after_submit")
            page.goto(THREAD, wait_until="domcontentloaded")
            if page.locator("#userMenu").count() != 1 or page.locator("#userLogin").count():
                raise SourceError("authenticated_member_marker_missing")
            yield Session(page)
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    try:
        with authenticated() as session:
            session.proof()
    except SourceError as error:
        print("SOURCE_ERROR_NO_ADVANCE", error)
        raise SystemExit(2)
    except Exception as error:
        print("SOURCE_ERROR_NO_ADVANCE", type(error).__name__)
        raise SystemExit(2)
