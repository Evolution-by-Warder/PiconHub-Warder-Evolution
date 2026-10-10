"""Current picon package discovery for the OE-Alliance feed used by OpenATV."""
from __future__ import annotations

import base64
import hashlib
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

from source_inventory import SourceError, stream_verified_archive

REPOSITORY = "oe-alliance/picons-feed"
BRANCH = "gh-pages"
API = f"https://api.github.com/repos/{REPOSITORY}/contents/Packages?ref={BRANCH}"
RAW_ROOT = f"https://raw.githubusercontent.com/{REPOSITORY}/{BRANCH}/"
ALLOWED_API_HOSTS = frozenset(("api.github.com",))
ALLOWED_PACKAGE_HOSTS = frozenset(("raw.githubusercontent.com",))
TIMESTAMP = re.compile(r"_(\d{4}-\d{2}-\d{2}--\d{2}-\d{2}-\d{2})_all\.ipk$")
SHA1 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _request(url, max_bytes, opener=None):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_API_HOSTS:
        raise SourceError("Unapproved OpenATV feed index endpoint")
    opener = opener or urllib.request.urlopen
    request = urllib.request.Request(url, headers={
        "User-Agent": "WarderPiconFactory/1.0",
        "Accept": "application/vnd.github+json",
    })
    with opener(request, timeout=40) as response:
        final = urllib.parse.urlsplit(response.geturl())
        if final.scheme != "https" or final.hostname not in ALLOWED_API_HOSTS:
            raise SourceError("OpenATV feed index redirected outside approved GitHub API")
        payload = response.read(max_bytes + 1)
        if len(payload) > max_bytes:
            raise SourceError("OpenATV feed index exceeds size limit")
        return payload


def parse_packages(data):
    """Parse current picon IPKs from an opkg Packages index without one naming convention."""
    if not isinstance(data, str) or len(data.encode("utf-8")) > 8_000_000:
        raise SourceError("Invalid OpenATV Packages index")
    packages = []
    for block in re.split(r"\n\s*\n", data.strip()):
        fields = {}
        for line in block.splitlines():
            if line[:1].isspace() or ":" not in line:
                continue
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
        name = fields.get("Package", "")
        filename = fields.get("Filename", "").removeprefix("./")
        digest = fields.get("SHA256sum", "").lower()
        match = TIMESTAMP.search(filename)
        if (not name.startswith("enigma2-plugin-picons-") or
            not Path(filename).name.startswith("enigma2-plugin-picons-") or "220x132" not in filename or not any(x in filename for x in ("srp-", "utf8snp-")) or
            "transparent" not in filename or not filename.endswith(".ipk") or
            Path(filename).is_absolute() or "\\" in filename or
            any(part in ("", ".", "..") for part in filename.split("/")) or
            not SHA256.fullmatch(digest)):
            continue
        try:
            size = int(fields.get("Size", "0"))
        except ValueError:
            continue
        if not 0 < size <= 450_000_000:
            continue
        packages.append({"name": name, "filename": filename, "version": fields.get("Version", ""),
                         "sha256": digest, "size": size, "timestamp": match.group(1) if match else ""})
    if not packages:
        raise SourceError("No verified 220x132 transparent SRP/UTF8SNP picon IPKs found in feed")
    # Preserve independent styles and naming families; newest dated release within each family.
    selected = {}
    for item in packages:
        family = re.sub(r"_\d{4}-\d{2}-\d{2}--\d{2}-\d{2}-\d{2}_all\.ipk$", "", item["filename"])
        previous = selected.get(family)
        if previous is None or (item["timestamp"], item["version"]) > (previous["timestamp"], previous["version"]):
            selected[family] = item
    return sorted(selected.values(), key=lambda item: item["filename"])


def discover_current(opener=None):
    """Read the verified GitHub content API and return its current package index.

    GitHub's blob SHA-1 is checked before any `Packages` text is trusted. The
    package bytes themselves are checked with feed-published SHA-256 values.
    """
    raw = _request(API, 1_000_000, opener)
    try:
        record = json.loads(raw)
        encoded = record["content"].replace("\n", "")
        content = base64.b64decode(encoded, validate=True)
        blob_sha = record["sha"].lower()
    except (KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise SourceError("Invalid GitHub feed index response") from exc
    digest = hashlib.sha1(f"blob {len(content)}\0".encode("ascii") + content).hexdigest()
    if not SHA1.fullmatch(blob_sha) or digest != blob_sha or record.get("path") != "Packages":
        raise SourceError("OpenATV feed index Git blob SHA-1 mismatch")
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SourceError("OpenATV feed index is not UTF-8") from exc
    return {"source": "openatv8", "repository": REPOSITORY, "branch": BRANCH,
            "index_sha1": blob_sha, "packages": parse_packages(text)}


def download_package(package, target, opener=None):
    filename = package["filename"]
    parts = Path(filename).parts
    if (not parts or Path(filename).is_absolute() or any(p in ("", ".", "..") for p in parts) or
        not SHA256.fullmatch(package.get("sha256", ""))):
        raise SourceError("Unsafe OpenATV package record")
    url = RAW_ROOT + urllib.parse.quote(filename, safe="/-._")
    return stream_verified_archive(url, package["sha256"], target, ALLOWED_PACKAGE_HOSTS,
                                  opener=opener, max_bytes=450_000_000)

# OpenATV's picons feed can lag behind the independently published upstream
# packages. Only fall back to upstream releases when the feed has no matching
# verified packages; never silently accept an unverified asset.
RELEASES_API = 'https://api.github.com/repos/picons/picons/releases/latest'
RELEASE_HOSTS = frozenset(('github.com', 'release-assets.githubusercontent.com',
                           'objects.githubusercontent.com'))


def parse_release_assets(data):
    if not isinstance(data, dict) or not isinstance(data.get('assets'), list):
        raise SourceError('Invalid upstream picon release metadata')
    result = []
    for asset in data['assets']:
        if not isinstance(asset, dict):
            continue
        name = asset.get('name', '')
        url = asset.get('browser_download_url', '')
        digest = asset.get('digest', '')
        size = asset.get('size', 0)
        parsed = urllib.parse.urlsplit(url) if isinstance(url, str) else None
        if (not isinstance(name, str) or not name.startswith('enigma2-plugin-picons-')
            or not name.endswith('.ipk') or '220x132' not in name
            or not any(kind in name for kind in ('srp-', 'utf8snp-'))
            or 'transparent' not in name or '/' in name or '\\' in name
            or not isinstance(digest, str) or not digest.startswith('sha256:')
            or not SHA256.fullmatch(digest[7:])
            or not isinstance(size, int) or not 0 < size <= 450_000_000
            or parsed.scheme != 'https' or parsed.hostname != 'github.com'
            or not parsed.path.startswith('/picons/picons/releases/download/')
            or parsed.path.rsplit('/', 1)[-1] != urllib.parse.quote(name, safe='-._')):
            continue
        match = TIMESTAMP.search(name)
        result.append({'name': name.split('_')[0], 'filename': name,
                       'version': str(data.get('tag_name', '')),
                       'sha256': digest[7:], 'size': size,
                       'timestamp': match.group(1) if match else '',
                       'url': url, 'origin': 'upstream-release'})
    if not result:
        raise SourceError('No SHA-256 verified 220x132 transparent packages in upstream release')
    return sorted(result, key=lambda item: item['filename'])


def discover_release(opener=None):
    raw = _request(RELEASES_API, 8_000_000, opener)
    try:
        record = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise SourceError('Invalid upstream release JSON') from exc
    packages = parse_release_assets(record)
    fingerprint = hashlib.sha256(json.dumps([(p['filename'], p['sha256']) for p in packages],
                                            sort_keys=True).encode('utf-8')).hexdigest()
    return {'source': 'openatv8', 'repository': 'picons/picons',
            'branch': 'releases', 'index_sha1': fingerprint,
            'packages': packages, 'origin': 'upstream-release'}


_feed_discover_current = discover_current


def discover_current(opener=None):
    try:
        return _feed_discover_current(opener=opener)
    except SourceError as feed_error:
        try:
            return discover_release(opener=opener)
        except SourceError as release_error:
            raise SourceError(f'Feed: {feed_error}; upstream: {release_error}') from release_error


_feed_download_package = download_package


def download_package(package, target, opener=None):
    if package.get('origin') != 'upstream-release':
        return _feed_download_package(package, target, opener=opener)
    url = package.get('url', '')
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != 'https' or parsed.hostname != 'github.com'
        or not parsed.path.startswith('/picons/picons/releases/download/')
        or parsed.path.rsplit('/', 1)[-1] != urllib.parse.quote(package.get('filename', ''), safe='-._')
        or not SHA256.fullmatch(package.get('sha256', ''))):
        raise SourceError('Unapproved upstream release asset')
    return stream_verified_archive(url, package['sha256'], target,
                                   RELEASE_HOSTS, opener=opener, max_bytes=450_000_000)


def naming_family(package):
    """Return verified filename naming family; never infer from PNG appearance."""
    name = Path(package.get('filename', '')).name.lower()
    if name.startswith('enigma2-plugin-picons-srp-'):
        return 'srp'
    if name.startswith('enigma2-plugin-picons-utf8snp-'):
        return 'utf8snp'
    return 'unknown'


def naming_inventory(packages):
    result = {'srp': [], 'utf8snp': [], 'unknown': []}
    for package in packages:
        result[naming_family(package)].append(package['filename'])
    return {key: {'count': len(value), 'filenames': value} for key, value in result.items()}
