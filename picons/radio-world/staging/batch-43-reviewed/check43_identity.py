import gzip,hashlib,json,urllib.request
from pathlib import Path
p=Path('picons/radio-world/staging/batch-43-reviewed')
cfg=json.loads((p/'configuration.json').read_bytes())
def get(r):
    b=urllib.request.urlopen(r['url'],timeout=90).read()
    assert len(b)==r['bytes']and hashlib.sha256(b).hexdigest()==r['sha256']
    return b
world_rows=json.loads(gzip.decompress(get(cfg['world'])))
world={r['reference']:r for r in world_rows}
countries={r['id']:r for r in json.loads(get(cfg['baseline_index']))['countries']}
raw=(p/'selection.json.gz').read_bytes();assert hashlib.sha256(raw).hexdigest()==cfg['selection_sha256']
rows=json.loads(gzip.decompress(raw))['entries'];bad=[]
for r in rows:
    actual=world[r['ref']];label=countries[r['country']]['name']
    if actual['group']!=label or any(actual[k]!=r['station'][k]for k in('name','url','group')):
        bad.append(dict(ref=r['ref'],country=r['country'],candidate_country_label=label,actual_pinned_world=actual,source_station=r['station'],all_world_matches=[v for v in world_rows if v['reference']==r['ref']],all_exact_name_url_matches=[v for v in world_rows if v['name']==r['station']['name']and v['url']==r['station']['url']]))
print('EXACT_IDENTITY_DIAGNOSTIC '+json.dumps(bad,ensure_ascii=False),flush=True)
assert not bad,'Pinned world/country identity disagreement; importer gate remains unchanged'
