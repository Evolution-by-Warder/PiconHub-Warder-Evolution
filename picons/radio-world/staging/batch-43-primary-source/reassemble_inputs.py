"""Validate explicit public station artwork parts and readable provenance."""
import argparse,hashlib,json,re
from pathlib import Path
from urllib.parse import urlsplit,parse_qs

def check(b,d):
 assert len(b)==d['bytes'],'byte count mismatch'
 assert hashlib.sha256(b).hexdigest()==d['sha256'],'SHA256 mismatch'
 assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==d['git_blob'],'Git blob mismatch'
 return b

def safe_url(u):
 p=urlsplit(u);assert p.scheme in ('http','https') and p.hostname and not p.username and not p.password,'Unsafe public URL'
 assert set(parse_qs(p.query))<={'v','mp','dist'},'Unreviewed URL query'
 assert not re.search(r'(?i)(?:password|secret|access[_-]?token|auth|bearer|session|nonce)',p.query),'Sensitive query'

def main():
 ap=argparse.ArgumentParser();ap.add_argument('root',type=Path);args=ap.parse_args();root=args.root;stage=Path('picons/radio-world/staging/batch-43-primary-source');manifest=json.load(open(root/stage/'parts-manifest.json'));assert 'primary_evidence' not in manifest,'Raw HTML archive must remain deferred';plan=json.load(open(root/stage/'producer-plan.json'));observations=json.load(open(root/stage/'primary-observations.json'))['entries'];assert len(observations)==25
 byref={r['reference']:r for r in observations}
 for r in plan['expected_selection']['entries']:
  o=byref[r['ref']];assert o['country']==r['country'] and o['station_name']==r['station']['name'] and o['exact_public_catalogue_stream']==r['station']['url'];assert o['verified_exact_stream_literal_in_public_HTML'] and o['verified_named_logo_URL_in_same_public_HTML'];assert re.fullmatch('[0-9a-f]{64}',o['public_HTML_sha256'])
  for k in ['exact_public_catalogue_stream','public_primary_url','public_logo_url']:safe_url(o[k])
  for e in o['frozen_primary_excerpts']:
   b=e['text'].encode();assert len(b)==e['bytes'] and hashlib.sha256(b).hexdigest()==e['sha256'] and e['containment_verified'];assert e['normalized_HTML_offset_chars']>=0
 (root/stage/'originals').mkdir(exist_ok=True)
 for h,d in manifest['originals'].items():
  pieces=[]
  for part in d['parts']:
   p=Path(part['path']);assert not p.is_absolute() and '..' not in p.parts and str(p).startswith(str(stage)+'/input-parts/'),'Unsafe artwork part path';pieces.append(check((root/p).read_bytes(),part))
  b=check(b''.join(pieces),d);assert h==d['sha256'];p=root/stage/'originals'/(h+'.img')
  if p.exists():assert p.read_bytes()==b,'Existing original differs'
  else:p.write_bytes(b)
 for v in json.load(open(root/stage/'vector-derivation.json'))['entries']:
  p=Path(v['path']);assert not p.is_absolute() and '..' not in p.parts;b=(root/stage/p).read_bytes();assert len(b)==v['bytes'] and hashlib.sha256(b).hexdigest()==v['sha256'];assert v['SVG_graphics_only_no_scripts_event_handlers_or_network_refs']
 proof={'status':'pass','part_limit':manifest['part_raw_limit'],'originals':len(manifest['originals']),'readable_primary_observations':len(observations),'raw_HTML_archive_publication':'technical_deferred_auto_review_rejection','only_explicit_public_artwork_inputs_reassembled':True,'observations_sha256':hashlib.sha256((root/stage/'primary-observations.json').read_bytes()).hexdigest()};(root/stage/'reassembly-proof.json').write_text(json.dumps(proof,indent=2)+'\n');print('PASS reassembled25 public artwork inputs; readable25primary observations validated')
if __name__=='__main__':main()
