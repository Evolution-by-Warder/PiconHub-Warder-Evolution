#!/usr/bin/env python3
"""Build the Warder bouquet from owned SK/CZ data and a temporary public source."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import tempfile
import unicodedata
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen

SOURCE_URL = 'https://raw.githubusercontent.com/openhdf/hdfradio/master/userbouquet.iptv_radio.radio'
ROOT = Path(__file__).resolve().parents[1]
BOUQUETS = ROOT / 'bouquets'
OWNED = BOUQUETS / 'userbouquet.warder.sk-cz.radio'
OUTPUT = BOUQUETS / 'userbouquet.warder.radio'
REPORT = ROOT / 'catalog/world-radio-update.json'
MAX_BYTES = 4 * 1024 * 1024
MARKER = '1:64:2:0:0:0:0:0:0:0:'
COUNTRIES = {'slowakei': 'SK', 'slovensko': 'SK', 'slovakia': 'SK',
             'tschechien': 'CZ', 'cechy': 'CZ', 'cesko': 'CZ',
             'czechia': 'CZ', 'czech republic': 'CZ', 'ceska republika': 'CZ'}
BRANDING = re.compile(r'hdf\s*radio|hdfreaks', re.I)
HEX = re.compile(r'^[0-9a-fA-F]+$')


@dataclass(frozen=True)
class Entry:
    reference: str
    name: str
    url: str | None


def label_key(name):
    return ''.join(c for c in unicodedata.normalize('NFKD', name.casefold())
                   if not unicodedata.combining(c)).strip()


def parse(text):
    """Reject truncated/unsupported records instead of publishing partial input."""
    lines = text.lstrip('\ufeff').splitlines()
    if not lines or not lines[0].startswith('#NAME '):
        raise ValueError('Missing bouquet header')
    entries = []
    i = 1
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if not line.startswith('#SERVICE ') or i + 1 >= len(lines):
            raise ValueError(f'Incomplete service at line {i + 1}')
        description = lines[i + 1]
        if not description.startswith('#DESCRIPTION '):
            raise ValueError(f'Missing service description at line {i + 2}')
        name = description[13:].strip()
        if not name or any(ord(c) < 32 for c in name):
            raise ValueError('Empty or invalid description')
        fields = line[9:].split(':', 10)
        if len(fields) != 11 or not all(HEX.fullmatch(v) for v in fields[:10]):
            raise ValueError('Invalid service reference')
        if fields[1] == '64':
            url = None
        elif fields[0] in ('4097', '5001', '5002', '8193') and fields[1] == '0':
            url = unquote(fields[10]).strip()
            # Known source editorial annotation is not part of the stream URL.
            url = re.sub(r'\s+:\s*K\.S\.\d{8}$', '', url).strip()
            parsed = urlsplit(url)
            if parsed.scheme not in ('http', 'https') or not parsed.hostname:
                raise ValueError('Invalid stream URL')
            if any(c.isspace() or ord(c) < 32 for c in url):
                raise ValueError('Whitespace/control character in stream URL')
        else:
            raise ValueError('Unsupported entry type')
        entries.append(Entry(':'.join(fields[:10]), name, url))
        i += 2
    return entries


def url_key(url):
    # Keep protocol, query strings and path escapes; distinct streams may use them.
    return url.rstrip('/')


def local_placeholder(url):
    host = urlsplit(url).hostname
    if host == 'localhost':
        return True
    try:
        address = ipaddress.ip_address(host)
        return address.is_loopback or address.is_unspecified
    except ValueError:
        return False


def owned_entries(text):
    entries = parse(text)
    countries = []
    section = None
    counts = Counter()
    refs = set()
    for entry in entries:
        if entry.url is None:
            section = COUNTRIES.get(label_key(entry.name))
            if section is None:
                raise ValueError('Owned bouquet must contain SK/CZ sections only')
            countries.append(section)
        else:
            if section is None or entry.reference in refs:
                raise ValueError('Missing owned section or duplicate owned identity')
            refs.add(entry.reference)
            counts[section] += 1
    if countries != ['SK', 'CZ'] or not counts['SK'] or not counts['CZ']:
        raise ValueError('Owned sections must be Slovensko then Čechy, both nonempty')
    if BRANDING.search(text):
        raise ValueError('Unexpected branding in owned data')
    return entries, counts


def render_marker(name):
    return f'#SERVICE {MARKER}\n#DESCRIPTION {name}\n'


def build(source, owned, previous):
    own, country_counts = owned_entries(owned)
    upstream = parse(source)
    old = parse(previous) if previous else []
    own_urls = {url_key(e.url) for e in own if e.url}
    assigned = {e.reference for e in own if e.url}
    old_refs = defaultdict(set)
    url_refs = defaultdict(set)
    for entry in old:
        if entry.url and entry.reference.split(':')[2] == '2':
            old_refs[(url_key(entry.url), entry.name)].add(entry.reference)
            url_refs[url_key(entry.url)].add(entry.reference)
    lines = ['#NAME Warder Radio Streams\n']
    # Preserve every byte of the owned body, including IDs used by existing picons.
    body = owned.split('\n', 1)[1]
    lines.append(body if body.endswith('\n') else body + '\n')
    section = None
    pending = []
    seen = set()
    excluded = Counter()
    stats = Counter()
    excluded_sections = set()
    for entry in upstream:
        if entry.url is None:
            # Source-level update banners are metadata, not country sections.
            if BRANDING.search(entry.name) or label_key(entry.name).startswith('update '):
                stats['source_metadata_removed'] += 1
                continue
            section = COUNTRIES.get(label_key(entry.name))
            if section:
                excluded_sections.add(section)
                pending = []
            else:
                pending = [entry.name]
            continue
        if section:
            excluded[section] += 1
            continue
        if local_placeholder(entry.url):
            # Upstream sometimes encodes subgroup headings as loopback streams.
            if not BRANDING.search(entry.name):
                pending.append(entry.name)
            stats['placeholder_headings_converted'] += 1
            continue
        if BRANDING.search(entry.name) or BRANDING.search(entry.url):
            stats['source_branding_removed'] += 1
            continue
        key = (url_key(entry.url), entry.name)
        if url_key(entry.url) in own_urls:
            stats['owned_url_duplicates_removed'] += 1
            continue
        if key in seen:
            stats['exact_duplicates_removed'] += 1
            continue
        seen.add(key)
        for heading in pending:
            lines.append(render_marker(heading))
        pending = []
        candidates = sorted(old_refs[key])
        if not candidates and len(url_refs[key[0]]) == 1:
            candidates = sorted(url_refs[key[0]])
        ref = next((r for r in candidates if r not in assigned
                    and any(int(v, 16) for v in r.split(':')[3:10])), None)
        if ref is not None:
            stats['foreign_references_retained'] += 1
        else:
            nonce = 0
            while True:
                digest = hashlib.sha256(f'world|{key[0]}|{entry.name}|{nonce}'.encode()).hexdigest()
                sid = f'{int(digest[:4], 16) or 1:X}'
                tsid = f'{int(digest[4:8], 16) or 1:X}'
                ref = f'4097:0:2:{sid}:{tsid}:ED:0:0:0:0'
                if ref not in assigned:
                    break
                nonce += 1
            stats['foreign_references_created'] += 1
        assigned.add(ref)
        # Audio service type 2 avoids switching the receiver into television mode.
        lines.append(f'#SERVICE {ref}:{entry.url.replace(":", "%3a")}\n#DESCRIPTION {entry.name}\n')
        stats['foreign_stations'] += 1
    if excluded_sections != {'SK', 'CZ'} or not excluded['SK'] or not excluded['CZ']:
        raise ValueError('Source SK/CZ country sections missing; refusing unsafe merge')
    result = ''.join(lines)
    if BRANDING.search(result):
        raise ValueError('Source branding leaked into generated bouquet')
    parsed = parse(result)
    playable = [e for e in parsed if e.url]
    assert len({e.reference for e in playable}) == len(playable)
    assert all(e.reference.split(':')[2] == '2' for e in playable)
    assert result.split('\n', 1)[1].startswith(body)
    report = {'schema': 1, 'owned_stations': dict(country_counts),
              'excluded_source_stations': dict(excluded),
              'foreign_stations': stats['foreign_stations'], 'total_stations': len(playable),
              'source_sha256': hashlib.sha256(source.encode()).hexdigest(),
              'owned_sha256': hashlib.sha256(owned.encode()).hexdigest(),
              'bouquet_sha256': hashlib.sha256(result.encode()).hexdigest(),
              'processing': {k: v for k, v in sorted(stats.items())
                             if k not in ('foreign_references_retained', 'foreign_references_created')},
              'validation': 'structure-only; individual stream availability is not asserted'}
    return result, report


def download():
    request = Request(SOURCE_URL, headers={'User-Agent': 'Warder-radio-catalogue/1',
                                          'Cache-Control': 'no-cache'})
    with urlopen(request, timeout=45) as response:
        raw = response.read(MAX_BYTES + 1)
    if not raw or len(raw) > MAX_BYTES:
        raise ValueError('Source download is empty or exceeds the size limit')
    return raw.decode('utf-8-sig')


def replace(path, text):
    if path.exists() and path.read_text(encoding='utf-8') == text:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                     delete=False) as handle:
        handle.write(text)
        temporary = Path(handle.name)
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-file', type=Path, help='Offline source for verification')
    args = parser.parse_args()
    source = args.source_file.read_text(encoding='utf-8-sig') if args.source_file else download()
    owned = OWNED.read_text(encoding='utf-8')
    previous = OUTPUT.read_text(encoding='utf-8') if OUTPUT.exists() else ''
    result, report = build(source, owned, previous)
    previous_world = max(0, len([e for e in parse(previous) if e.url]) - sum(report['owned_stations'].values())) if previous else 0
    if report['foreign_stations'] < max(3000, previous_world * 0.9):
        raise ValueError('Unexpectedly small source; existing bouquet has been preserved')
    replace(OUTPUT, result)
    replace(REPORT, json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('owned_stations', 'foreign_stations', 'total_stations')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
