"""Check sanitized primary excerpts against anonymously fetched, frozen HTML.
No HTML, response headers, cookies, credentials or scripts are published by this
checker. Pass the local frozen SHA256.html.gz directory when available.
"""
import argparse,gzip,hashlib,html,json
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--observations',type=Path,required=True);ap.add_argument('--frozen-html-root',type=Path,required=True);args=ap.parse_args();count=0
for r in json.load(open(args.observations))['entries']:
 raw=gzip.decompress((args.frozen_html_root/(r['public_HTML_sha256']+'.html.gz')).read_bytes());assert hashlib.sha256(raw).hexdigest()==r['public_HTML_sha256'];text=html.unescape(raw.decode('utf8',errors='replace')).replace('\\/','/');assert hashlib.sha256(text.encode()).hexdigest()==r['normalized_public_HTML_sha256']
 for e in r['frozen_primary_excerpts']:
  b=e['text'].encode();assert len(b)==e['bytes'] and hashlib.sha256(b).hexdigest()==e['sha256'];offset=e['normalized_HTML_offset_chars'];assert text[offset:offset+len(e['text'])]==e['text'] and e['containment_verified'];count+=1
print('PASS',count,'exact sanitized excerpt containment checks against25 frozen public primary HTML hashes')
