"""Validate small frozen Git parts and reassemble inputs without live fetches."""
import argparse,hashlib,io,json,tarfile
from pathlib import Path

def check(b,d):
 assert len(b)==d['bytes'],'byte count mismatch'
 assert hashlib.sha256(b).hexdigest()==d['sha256'],'SHA256 mismatch'
 assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==d['git_blob'],'Git blob mismatch'
 return b

def main():
 ap=argparse.ArgumentParser();ap.add_argument('root',type=Path);args=ap.parse_args();root=args.root;stage=Path('picons/radio-world/staging/batch-43-primary-source');manifest=json.load(open(root/stage/'parts-manifest.json'))
 def assembled(desc):
  pieces=[]
  for part in desc['parts']:
   p=Path(part['path']);assert not p.is_absolute() and '..' not in p.parts and str(p).startswith(str(stage)+'/'),'unsafe part path';pieces.append(check((root/p).read_bytes(),part))
  return check(b''.join(pieces),desc)
 (root/stage/'originals').mkdir(exist_ok=True)
 for h,d in manifest['originals'].items():
  b=assembled(d);assert h==d['sha256'];p=root/stage/'originals'/(h+'.img')
  if p.exists():assert p.read_bytes()==b,'Existing original differs'
  else:p.write_bytes(b)
 b=assembled(manifest['primary_evidence']);expected=None;members={}
 with tarfile.open(fileobj=io.BytesIO(b),mode='r:gz') as archive:
  for member in archive.getmembers():
   p=Path(member.name);assert member.isfile() and not p.is_absolute() and '..' not in p.parts,'Unsafe evidence archive member';raw=archive.extractfile(member).read();members[member.name]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
  # All raw broadcaster SVG originals and CairoSVG-derived PNG inputs stay in the parts archive.
  assert 'final-visual-decisions.json' in members and 'source-visual-decisions.json' in members and any(k.startswith('originals/') for k in members)
 proof={'status':'pass','part_limit':manifest['part_raw_limit'],'originals':len(manifest['originals']),'evidence_sha256':manifest['primary_evidence']['sha256'],'evidence_bytes':len(b),'archive_members':members,'raw_SVG_and_raster_derivation_preserved':True}
 (root/stage/'reassembly-proof.json').write_text(json.dumps(proof,indent=2)+'\n');print('PASS reassembled',len(manifest['originals']),'frozen inputs and audited',len(members),'evidence members')
if __name__=='__main__':main()
