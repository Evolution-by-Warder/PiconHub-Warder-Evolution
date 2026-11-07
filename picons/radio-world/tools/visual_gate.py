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
def merge_ledgers(paths):
    result={'entries':[],'source_holds':[]}
    for path in paths:
        value=read(path);result['entries']+=value['entries'];result['source_holds']+=value.get('source_holds',[])
    return result
def identity_blocks(ledger):
    return {(r['country'],r['ref']) for r in ledger.get('source_holds',[])}
def explicit_source_resolution(entry):
    digest=entry.get('resolution_evidence_sha256','')
    return entry.get('resolves_source_hold') is True and len(digest)==64 and all(c in '0123456789abcdef' for c in digest)
def validate_selection(selection,ledger):
    decisions={};records={};blocked=identity_blocks(ledger)
    for entry in ledger['entries']:
        key=fingerprint(entry['row']);decision=entry['decision']
        if decision not in ('approve','hold'):raise ValueError('Unknown visual decision')
        if key in decisions and decisions[key]!=decision:raise ValueError('Conflicting exact-render decisions')
        decisions[key]=decision;records[key]=entry
    seen=set()
    for row in selection:
        identity=(row['country'],row['ref']);key=fingerprint(row)
        if identity in seen:raise ValueError('Duplicate country/reference')
        seen.add(identity)
        if decisions.get(key)!='approve':raise ValueError('Unreviewed or held exact artwork: '+row['ref'])
        if identity in blocked and not explicit_source_resolution(records[key]):raise ValueError('Unresolved pre-render source hold: '+row['ref'])
    return len(seen)
def assert_no_held(index,ledger,load_manifest):
    countries={r['id']:r for r in index['countries']};cache={};checked=0
    approved={fingerprint(e['row']):e for e in ledger['entries'] if e['decision']=='approve'}
    rejected={fingerprint(e['row']) for e in ledger['entries'] if e['decision']=='hold'}
    blocked=identity_blocks(ledger)
    if approved.keys() & rejected:raise ValueError('Conflicting exact-render decisions')
    holds=[e['row'] for e in ledger['entries'] if e['decision']=='hold']+ledger.get('source_holds',[])
    for row in holds:
        country=countries[row['country']];checked+=1
        if not country['release']:continue
        url=country['release']['url']
        if url not in cache:cache[url]=load_manifest(country['release'])
        manifest=cache[url];name=row['ref'].replace(':','_')+'.png'
        variants={size+'/'+style:manifest['packages'][size][style]['files'].get(name) for size in SIZES for style in STYLES}
        if not any(variants.values()):continue
        if all(variants.values()):
            current=dict(country=row['country'],ref=row['ref'],variants={k:{'sha256':v} for k,v in variants.items()});key=fingerprint(current)
            if key in approved and key not in rejected:
                if (row['country'],row['ref']) not in blocked or explicit_source_resolution(approved[key]):continue
        raise ValueError('Held or partially corrected reference restored: '+row['country']+' '+row['ref'])
    return checked
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--ledger',required=True,action='append');parser.add_argument('--index');parser.add_argument('--selection');args=parser.parse_args()
    ledger=merge_ledgers(args.ledger)
    if args.selection:print('Exact reviewed selection:',validate_selection(read(args.selection)['entries'],ledger))
    if args.index:
        from saved_artwork_import import get
        print('Held references absent across all nine variants:',assert_no_held(read(args.index),ledger,lambda e:json.loads(get(e))))
