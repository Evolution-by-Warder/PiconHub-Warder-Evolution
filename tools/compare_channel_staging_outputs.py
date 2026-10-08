#!/usr/bin/env python3
"""Compare full original-production and staging channel rebuild output trees."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def outputs(root: Path):
    return {p.relative_to(root/'picons').as_posix():sha(p)
            for style in ('black','white') for p in (root/'picons').glob(f'*/*/{style}/*.png')}

def sources(root: Path):
    return {p.relative_to(root/'picons').as_posix():sha(p)
            for p in (root/'picons').glob('*/*/transparent/*.png')}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('baseline',type=Path); ap.add_argument('staging',type=Path); ap.add_argument('--output',type=Path,required=True); ap.add_argument('--baseline-label',default='original production rebuild'); ap.add_argument('--staging-label',default='isolated staging rebuild'); a=ap.parse_args()
    bs,ss=sources(a.baseline),sources(a.staging); bo,so=outputs(a.baseline),outputs(a.staging)
    identities=set(bs)|set(ss); paths=set(bo)|set(so)
    mismatches=[{'path':p,'baseline_sha256':bo.get(p),'staging_sha256':so.get(p)} for p in sorted(paths) if bo.get(p)!=so.get(p)]
    source_mismatches=[p for p in sorted(identities) if bs.get(p)!=ss.get(p)]
    covered_sources={"/".join(p.split("/")[:2]+["transparent",p.split("/")[-1]]) for p in set(bo)&set(so)}
    untested=sorted(set(identities)-covered_sources)
    total_expected=2*len(identities)
    result={'baseline':a.baseline_label,'staging':a.staging_label,'source_identities':len(identities),
            'source_inputs_identical':len(source_mismatches)==0,'source_mismatch_count':len(source_mismatches),
            'black_white_variants_required':total_expected,'baseline_outputs':len(bo),'staging_outputs':len(so),
            'variants_compared':len(set(bo)&set(so)),'exact_matches':sum(bo.get(p)==so.get(p) for p in set(bo)&set(so)),
            'mismatches':mismatches,'mismatch_count':len(mismatches),'untested_identities':untested,
            'result':'PASS' if len(bo)==total_expected and len(so)==total_expected and not mismatches and not source_mismatches and not untested else 'BLOCKED'}
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('source_identities','black_white_variants_required','baseline_outputs','staging_outputs','variants_compared','exact_matches','mismatch_count','result')}))
    return 0 if result['result']=='PASS' else 1
if __name__=='__main__': raise SystemExit(main())
