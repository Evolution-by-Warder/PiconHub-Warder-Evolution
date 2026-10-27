#!/usr/bin/env python3
"""Create deterministic DAB ZIPs; previews cannot become verified implicitly."""
import argparse,hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def build(revision,approval=None):
    if len(revision)!=40 or any(c not in '0123456789abcdef' for c in revision):raise ValueError('Immutable source commit required')
    catalog=json.loads((ROOT/'catalog/authentic-preview.json').read_text())
    approved=json.loads(approval.read_text()) if approval else None
    if approved:
        if not approved.get('approved_master_v9') or not approved.get('owner_confirmation') or approved.get('artwork_manifest_sha256')!=hashlib.sha256((ROOT/'catalog/authentic-preview.json').read_bytes()).hexdigest():raise ValueError('Artwork approval does not match candidate')
    packages={}
    for style in ('transparent','white','black'):
        target=ROOT/'packages'/('dab-'+style+'-220x132.zip');target.parent.mkdir(exist_ok=True)
        files={r['picon_filename']:r['sha256'][style] for r in catalog['records']}
        with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
            for name,digest in sorted(files.items()):
                data=(ROOT/'preview/authentic'/style/name).read_bytes()
                if hashlib.sha256(data).hexdigest()!=digest:raise ValueError('Artwork hash mismatch')
                member=zipfile.ZipInfo(name,(1980,1,1,0,0,0));member.external_attr=0o100644<<16;member.compress_type=zipfile.ZIP_DEFLATED;archive.writestr(member,data)
        data=target.read_bytes();packages[style]={'resolution':'220x132','url':'https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/'+revision+'/picons/DAB/packages/'+target.name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'files':files}
    report={'schema':1,'status':'verified' if approved else 'candidate','station_count':catalog['station_count'],'reference_count':catalog['reference_count'],'packages':packages,'unresolved':catalog['unresolved']}
    output=ROOT/'catalog'/('release.json' if approved else 'release-candidate.json')
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    return report
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--revision',required=True);p.add_argument('--approval',type=Path);a=p.parse_args();d=build(a.revision,a.approval);print(d['status'],{s:x['bytes'] for s,x in d['packages'].items()})
