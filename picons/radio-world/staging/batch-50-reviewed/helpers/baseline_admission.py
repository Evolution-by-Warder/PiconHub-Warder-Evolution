"""Pre-ZIP country admission: never replace an approved existing filename."""
import hashlib,json,urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
BASELINE_SHA='e04ad76db2d8d4cf4e434222228a75f1d066916739781c4d7731f28f1dffb1b2'
VARIANTS={f'{size}/{style}'for size in('50x30','220x132','400x240')for style in('transparent','white','black')}
def require(ok,message):
    if not ok:raise ValueError(message)
def sha(b):return hashlib.sha256(b).hexdigest()
def fetch_release(desc,cache):
    require(desc['url'].startswith('https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/'+desc['commit']+'/'),'Unpinned baseline manifest')
    f=Path(cache)/(desc['sha256']+'.json');f.parent.mkdir(parents=True,exist_ok=True)
    raw=f.read_bytes()if f.exists()else urllib.request.urlopen(desc['url'],timeout=90).read(desc['bytes']+1)
    require(len(raw)==desc['bytes']and sha(raw)==desc['sha256'],'Baseline manifest bytes/SHA differ')
    if not f.exists():f.write_bytes(raw)
    return json.loads(raw)
def inspect(rows,baseline_raw,cache):
    require(sha(baseline_raw)==BASELINE_SHA,'Wrong protected baseline')
    countries={r['id']:r for r in json.loads(baseline_raw)['countries']};codes={r['country']for r in rows}
    require(codes<=countries.keys(),'Unknown selected country')
    descriptors={countries[c]['release']['url']:countries[c]['release']for c in codes if countries[c]['release']}
    with ThreadPoolExecutor(max_workers=8)as pool:manifests=dict(zip(descriptors,pool.map(lambda d:fetch_release(d,cache),descriptors.values())))
    eligible=[];reused=[];held=[]
    for r in rows:
        desc=countries[r['country']]['release'];name=r['ref'].replace(':','_')+'.png';existing={}
        if desc:
            m=manifests[desc['url']]
            for variant in VARIANTS:
                size,style=variant.split('/');digest=m['packages'][size][style]['files'].get(name)
                if digest:existing[variant]=digest
        if not existing:eligible.append(r);continue
        record=dict(country=r['country'],ref=r['ref'],filename=name,manifest=desc,existing_variants=existing)
        if set(existing)==VARIANTS and all(existing[k]==(r['variants'][k]['sha256']if isinstance(r['variants'][k],dict)else r['variants'][k][0])for k in VARIANTS):
            record['kind']='already-covered-exact-approved-artwork';reused.append(record)
        else:
            record['kind']='new-artwork-conflicts-with-approved-existing-filename'if set(existing)==VARIANTS else'partially-existing-approved-filename-requires-separate-repair'
            held.append(record)
    proof=dict(schema=1,status='baseline-disjoint-preflight-only-not-source-ready',baseline_sha256=BASELINE_SHA,input_references=len(rows),new_references=len(eligible),already_covered_identical=len(reused),held_new_artwork=len(held),only_selected_country_manifests_fetched=len(manifests),reused=reused,held=held,new_identities=[dict(country=r['country'],ref=r['ref'],index=r.get('index'))for r in eligible],no_prior_png_or_zip_modified=True)
    return eligible,proof
if __name__=='__main__':
    import argparse,gzip
    p=argparse.ArgumentParser();p.add_argument('--selection',type=Path,required=True);p.add_argument('--baseline',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--new-selection',type=Path);p.add_argument('--cache',type=Path,required=True);a=p.parse_args()
    b=a.selection.read_bytes();data=json.loads(gzip.decompress(b)if b[:2]==b'\x1f\x8b'else b);rows=data['entries']if isinstance(data,dict)else data
    new,proof=inspect(rows,a.baseline.read_bytes(),a.cache);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(proof,indent=2)+'\n')
    if a.new_selection:a.new_selection.write_text(json.dumps(dict(status='disjoint-only-not-new-source-approval',entries=new),indent=2)+'\n')
    print(json.dumps({k:v for k,v in proof.items()if k not in('new_identities','reused','held')},indent=2))
