"""Build promotion metadata only after all country43 gates; never edit the live index."""
import hashlib,json,re,subprocess,urllib.parse,urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
p=Path('picons/radio-world/staging/batch-43-reviewed')
def sha(b):return hashlib.sha256(b).hexdigest()
def blob(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def put(name,value,text=False):
    b=value.encode()if text else(json.dumps(value,indent=2,ensure_ascii=False)+'\n').encode()
    f=p/name;assert not f.exists()or f.read_bytes()==b,'Refusing unequal promotion metadata '+name
    if not f.exists():f.write_bytes(b)
idxraw=(p/'countries.proposed.json').read_bytes();idx=json.loads(idxraw);countries=idx['countries']
down=json.loads((p/'downloader-proof.json').read_bytes());pres=json.loads((p/'production-preservation-proof.json').read_bytes());adm=json.loads((p/'png-admission-proof.json').read_bytes())
assert len(countries)==len({r['id']for r in countries})==219
covered=sum(r['picons']for r in countries);assert covered==3011 and down['index_sha256']==sha(idxraw)
assert down['radio_version']=='0.1.9.2'and{r['style']for r in down['styles']}=={'transparent','white','black'}
assert all(s['first']['failed']==s['repeat']['failed']==s['repeat_zip_requests']==0 and s['user_data_preserved']for s in down['styles'])
assert pres['protected_png_variant_entries']==10332 and pres['candidate_references']==covered
assert adm['all_new_pngs_bound_to_exact_approved_reviews']and adm['references']['covered']==covered
available=[r for r in countries if r['release']]
urls={r['release']['url']:r['release']for r in available}
def fetch(pair):
    url,r=pair
    assert urllib.parse.urlsplit(url).hostname=='raw.githubusercontent.com'and re.fullmatch('[0-9a-f]{40}',r['commit'])and'/'+r['commit']+'/'in url
    b=urllib.request.urlopen(url,timeout=90).read();assert len(b)==r['bytes']and sha(b)==r['sha256'],url
    return url,(json.loads(b),blob(b),len(b),sha(b))
with ThreadPoolExecutor(max_workers=8)as pool:manifests=dict(pool.map(fetch,sorted(urls.items())))
elements={};packages={};png_aliases=0;seen_collections=set()
for r in available:
    m,g,bcount,digest=manifests[r['release']['url']];collection=r['collection']
    assert re.fullmatch('[A-Za-z0-9_-]+',collection)and m['collection']==collection
    path='picons/'+collection+'/catalog/release.json'
    element=dict(path=path,mode='100644',type='blob',sha=g)
    assert path not in elements or elements[path]==element;elements[path]=element
    first=collection not in seen_collections;seen_collections.add(collection)
    assert set(m['packages'])=={'50x30','220x132','400x240'}
    for size,styles in m['packages'].items():
        assert set(styles)=={'transparent','white','black'}
        for style,e in styles.items():
            assert isinstance(e['files'],dict)and all(re.fullmatch('[0-9a-f]{64}',h)for h in e['files'].values())
            if first:png_aliases+=len(e['files'])
            pieces=e.get('parts')or[e]
            for number,part in enumerate(pieces,1):
                url=part['url'];assert urllib.parse.urlsplit(url).hostname=='raw.githubusercontent.com'
                assert part['bytes']>0 and re.fullmatch('[0-9a-f]{64}',part['sha256'])
                entry=dict(url=url,sha256=part['sha256'],bytes=part['bytes'],collection=collection,resolution=size,style=style,pngcount=len(part.get('files',e['files'])),countries=[])
                if url in packages:
                    prior=packages[url];assert all(prior[k]==entry[k]for k in entry if k!='countries')
                else:packages[url]=entry
                if r['id']not in packages[url]['countries']:packages[url]['countries'].append(r['id'])
for e in packages.values():e['countries'].sort()
inventory=[packages[u]for u in sorted(packages)]
assert png_aliases==adm['candidate_png_variant_entries_including_aliases']
elements=[elements[k]for k in sorted(elements)]
sums=''.join(e['sha256']+'  '+e['url']+'\n'for e in inventory)
proof=dict(schema=1,status='verified-promotion-artifacts-only-not-production',results_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),countries=len(countries),available=len(available),complete=sum(r['status']=='complete'for r in countries),covered=covered,total_references=adm['references']['total'],remaining=adm['references']['total']-covered,png_variant_entries_including_aliases=png_aliases,protected_production_png_variant_entries=10332,index_sha256=sha(idxraw),index_git_blob=blob(idxraw),index_bytes=len(idxraw),canonical_manifest_elements=len(elements),immutable_manifest_urls_verified=len(manifests),all_nine_variants_checked=True,package_urls=len(inventory),candidate_sha256sums_sha256=sha(sums.encode()),zip_or_png_generated=False,production_index_edited=False)
put('canonical-manifest-elements.json',elements);put('candidate-package-inventory.json',inventory);put('candidate-SHA256SUMS.txt',sums,text=True);put('promotion-proof.json',proof)
print(json.dumps(proof,indent=2))
