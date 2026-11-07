"""Independent manifest subset proof against immutable production batch 33."""
import argparse,concurrent.futures,hashlib,json,re,urllib.request,time
from pathlib import Path
BASE='https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/'
PRODUCTION='8180aa0df6e185efad120338bc53ca04bc5e492a'
def get(e):
    assert e['url'].startswith(BASE)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(e['url'],timeout=60) as r: raw=r.read(e['bytes']+1)
            assert len(raw)==e['bytes'] and hashlib.sha256(raw).hexdigest()==e['sha256']
            return json.loads(raw)
        except OSError:
            if attempt==2: raise
            time.sleep(2**attempt)
def main():
    p=argparse.ArgumentParser();p.add_argument('--candidate',type=Path,required=True);p.add_argument('--production',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    prod=json.loads(a.production.read_bytes());candidate=json.loads(a.candidate.read_bytes())
    old={r['id']:r for r in prod['countries']};new={r['id']:r for r in candidate['countries']}
    assert len(old)==len(new)==219 and old.keys()==new.keys()
    assert sum(r['picons'] for r in old.values())==1084
    assert sum(bool(r['release']) for r in old.values())==33
    for code,r in old.items():
        n=new[code];assert n['stations']==r['stations'] and n['collection']==r['collection'] and n['picons']>=r['picons'],code
        if n['release']:
            e=n['release'];assert re.fullmatch(r'[0-9a-f]{40}',e['commit']) and e['url'].startswith(BASE+e['commit']+'/')
    entries={e['url']:e for d in (old,new) for r in d.values() if (e:=r['release'])}
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        manifests=dict(zip(entries,pool.map(get,entries.values())))
    protected=0;comparisons=[];seen=set()
    for code,r in old.items():
        if not r['release']:continue
        before=manifests[r['release']['url']];after=manifests[new[code]['release']['url']]
        identity=(r['release']['url'],new[code]['release']['url'])
        if identity in seen: continue
        seen.add(identity);count=0
        for size in ('50x30','220x132','400x240'):
            for style in ('transparent','white','black'):
                b=before['packages'][size][style]['files'];n=after['packages'][size][style]['files']
                assert b.items()<=n.items(),(code,size,style)
                count+=len(b)
        protected+=count;comparisons.append(dict(country=code,collection=r['collection'],protected_png_variant_entries=count))
    a.output.write_text(json.dumps(dict(schema=1,production_commit=PRODUCTION,production_country_count=219,production_available_countries=33,production_country_references=1084,candidate_country_count=219,candidate_available_countries=sum(bool(r['release']) for r in new.values()),candidate_references=sum(r['picons'] for r in new.values()),verified_manifest_urls=len(manifests),protected_png_variant_entries=protected,scope='Independent exact SHA-256 manifest subset comparison, all nine variants; shared SK/CZ manifest counted once. Archive byte validation is recorded separately in build/downloader proofs.',comparisons=comparisons),indent=2)+'\n')
    print(a.output.read_text())
if __name__=='__main__':main()
