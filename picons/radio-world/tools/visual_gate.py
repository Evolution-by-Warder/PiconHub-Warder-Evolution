"""Require exact reviewed renders and prevent held references returning to candidate packs."""
import argparse,gzip,json
from pathlib import Path
SIZES=('50x30','220x132','400x240')
STYLES=('transparent','white','black')
VARIANTS={s+'/'+c for s in SIZES for c in STYLES}
def read(path):
    raw=Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)
def fingerprint(row):
    variants=row['variants']
    if set(variants)!=VARIANTS:raise ValueError('Nine exact variants required')
    hashes=[]
    for name in sorted(VARIANTS):
        value=variants[name];digest=value['sha256'] if isinstance(value,dict) else value[0]
        if len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):raise ValueError('Invalid SHA256')
        hashes.append((name,digest))
    return row['country'],row['ref'],tuple(hashes)
def validate_selection(selection,ledger):
    decisions={}
    for entry in ledger['entries']:
        key=fingerprint(entry['row']);decision=entry['decision']
        if decision not in ('approve','hold'):raise ValueError('Unknown visual decision')
        if key in decisions and decisions[key]!=decision:raise ValueError('Conflicting exact-render decisions')
        decisions[key]=decision
    seen=set()
    for row in selection:
        identity=(row['country'],row['ref'])
        if identity in seen:raise ValueError('Duplicate country/reference')
        seen.add(identity)
        if decisions.get(fingerprint(row))!='approve':raise ValueError('Unreviewed or held exact artwork: '+row['ref'])
    return len(seen)
def assert_no_held(index,ledger,load_manifest):
    countries={r['id']:r for r in index['countries']};cache={};checked=0
    for entry in ledger['entries']:
        if entry['decision']!='hold':continue
        row=entry['row'];country=countries[row['country']];checked+=1
        if not country['release']:continue
        url=country['release']['url']
        if url not in cache:cache[url]=load_manifest(country['release'])
        manifest=cache[url];name=row['ref'].replace(':','_')+'.png'
        for size in SIZES:
            for style in STYLES:
                if name in manifest['packages'][size][style]['files']:
                    raise ValueError('Held reference restored: '+row['country']+' '+row['ref']+' '+size+'/'+style)
    return checked
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--ledger',required=True);parser.add_argument('--index');parser.add_argument('--selection');args=parser.parse_args()
    ledger=read(args.ledger)
    if args.selection:print('Exact reviewed selection:',validate_selection(read(args.selection)['entries'],ledger))
    if args.index:
        from saved_artwork_import import get
        print('Held references absent across all nine variants:',assert_no_held(read(args.index),ledger,lambda e:json.loads(get(e))))
