"""Factory-only, opt-in-by-published-manifest automatic updater.

The protected repository factory/update/manifest.json is the release authority.
An absent/invalid/offline manifest means the installed app starts unchanged.
"""
import hashlib
import json
import ast
import re
import shutil
import tempfile
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

from factory_update_stage import stage_verified_zip, MAX_PACKAGE
from factory_update_transaction import begin
from workspace_paths import verify_required_directories

REPO = 'Evolution-by-Warder/PiconHub-Warder-Evolution'
MANIFEST_URL = 'https://raw.githubusercontent.com/' + REPO + '/factory-warder-development/factory/update/manifest.json'
VERSION_FILE = '.factory-version.json'
VERSION = re.compile(r'^factory-v(\d+)\.(\d+)\.(\d+)$')
MAX_MANIFEST = 16384


def version_tuple(value):
    match = VERSION.fullmatch(value) if isinstance(value, str) else None
    if not match:
        raise ValueError('Invalid Factory version')
    return tuple(map(int, match.groups()))


def read_version(app):
    try:
        data = json.loads((Path(app) / VERSION_FILE).read_text(encoding='utf-8'))
        return version_tuple(data['version'])
    except (OSError, ValueError, KeyError, TypeError):
        return (0, 0, 0)


def fetch(url, *, opener=None, limit=MAX_MANIFEST):
    opener = opener or urllib.request.urlopen
    req = urllib.request.Request(url, headers={'User-Agent': 'Warder-Picon-Factory/1', 'Accept': 'application/json'})
    with opener(req, timeout=8) as response:
        if response.geturl() != url:
            raise ValueError('Unexpected redirect')
        body = response.read(limit + 1)
    if len(body) > limit:
        raise ValueError('Response too large')
    return body


def validate_manifest(data, current):
    if not isinstance(data, dict) or data.get('schema') != 1:
        raise ValueError('Invalid manifest schema')
    version = data.get('version')
    v = version_tuple(version)
    if v <= tuple(current):
        return None
    asset = 'warder-picon-factory-' + '.'.join(map(str, v)) + '.zip'
    expected = 'https://github.com/' + REPO + '/releases/download/' + version + '/' + asset
    if data.get('url') != expected or not isinstance(data.get('size'), int) or type(data['size']) is not int or not 1024 < data['size'] <= MAX_PACKAGE:
        raise ValueError('Untrusted Factory release URL/size')
    sha = data.get('sha256')
    if not isinstance(sha, str) or not re.fullmatch('[0-9a-f]{64}', sha):
        raise ValueError('Invalid release SHA-256')
    return {'version': version, 'url': expected, 'sha256': sha, 'size': data['size']}


def download_release(info, destination, *, opener=None):
    opener = opener or urllib.request.urlopen
    req = urllib.request.Request(info['url'], headers={'User-Agent': 'Warder-Picon-Factory/1', 'Accept': 'application/octet-stream'})
    digest = hashlib.sha256()
    total = 0
    with opener(req, timeout=30) as response, Path(destination).open('wb') as out:
        final = urlsplit(response.geturl())
        # GitHub's release asset CDN is allowed, arbitrary hosts are not.
        if final.scheme != 'https' or final.username or final.password or final.port not in (None, 443) or final.hostname not in ('github.com', 'release-assets.githubusercontent.com'):
            raise ValueError('Untrusted asset redirect')
        if final.hostname == 'github.com' and response.geturl() != info['url']:
            raise ValueError('Untrusted asset redirect')
        if 'text/html' in response.headers.get('Content-Type', '').lower():
            raise ValueError('HTML instead of release ZIP')
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:break
            total += len(chunk)
            if total > info['size'] or total > MAX_PACKAGE:
                raise ValueError('Release too large')
            digest.update(chunk)
            out.write(chunk)
    if total != info['size'] or digest.hexdigest() != info['sha256']:
        raise ValueError('Release size/hash mismatch')


def attempt_update(app, *, manifest_fetch=fetch, downloader=download_release, reporter=None):
    """Called while the launcher lock is held and before the GUI starts."""
    app = Path(app).resolve()
    def report(msg):
        if reporter: reporter(msg)
    phase = 'preflight'
    try:
        workspace = app.parents[1]
        structure_ok, findings = verify_required_directories(workspace)
        if not structure_ok:
            raise PermissionError('Read-only workspace preflight failed: ' + '; '.join(findings))
        phase = 'manifest: ' + MANIFEST_URL
        # An existing but unversioned application is NOT version 0: replacing it
        # could silently downgrade a user's newer or locally modified build.
        if app.exists() and read_version(app) == (0, 0, 0):
            report('Update deferred: installed Factory version cannot be verified')
            return 'unknown_installed_version'
        data = json.loads(manifest_fetch(MANIFEST_URL))
        info = validate_manifest(data, read_version(app))
        if info is None:
            return 'up_to_date'
        with tempfile.TemporaryDirectory(prefix='.factory-update-', dir=app.parent) as tmp:
            tmp = Path(tmp)
            package = tmp / 'release.zip'
            phase = 'release: ' + info['url']
            downloader(info, package)
            phase = 'verify-and-activate'
            stage = stage_verified_zip(package, info['sha256'], tmp / 'staging')
            # Release ZIP is APP-ONLY, not a D:\ deployment bundle.
            if not (stage / 'engine.py').is_file() or not (stage / 'factory_launcher.py').is_file() or not (stage / 'requirements-runtime.txt').is_file():
                raise ValueError('Release is not an application-only package')
            # Validate every shipped Python module BEFORE replacing the running app.
            # Syntax errors or truncated modules must never activate a release.
            modules = list(stage.rglob('*.py'))
            if not modules:
                raise ValueError('Release contains no Python modules')
            for module in modules:
                if module.is_symlink():
                    raise ValueError('Symlink in release Python modules')
                ast.parse(module.read_bytes(), filename=str(module))
            embedded = json.loads((stage / VERSION_FILE).read_text(encoding='utf-8'))
            if embedded.get('version') != info['version']:
                raise ValueError('Release version mismatch')
            # stage_verified_zip creates a marker; transaction uses it.
            begin(stage, app, authorized=True)
        report('Factory update activated; awaiting GUI startup confirmation: ' + info['version'])
        return 'pending_gui_confirmation'
    except Exception as exc:
        report('Update skipped at ' + phase + '; installed Factory preserved: ' + type(exc).__name__ + ': ' + str(exc))
        return 'skipped'
