"""Validate original production authority and exact enumerated stream aliases."""
import re,gzip,hashlib,json,sys,urllib.parse
from pathlib import Path
S=Path(__file__).resolve().parents[1];R=S.parents[1];sys.path.insert(0,str(R/'tools'))
from visual_gate import read,merge_ledgers,validate_selection,identity_blocks
from saved_artwork_import import get
sys.path.insert(0,str(S.parent/'batch-50-reviewed/helpers'));import baseline_admission
cfg=read(S/'configuration.json');desc=read(S/'source-inputs/recovery-spec.json');facts=read(S/'source-inputs/public-observations.json');rows=read(S/'selection.json.gz')['entries'];assert len(rows)==cfg['references']==1
paths=[R/'staging/source-ledger-reviewed-20261107/visual-ledger.json.gz',R/'staging/visual-review-34-36/decisions.json.gz']+[R/f'staging/batch-{n}-reviewed/visual-ledger.json.gz'for n in range(39,77)];history=merge_ledgers(paths)
audit=json.loads(gzip.decompress(get(desc['audit'])))['checks'];world=json.loads(gzip.decompress(get(desc['current'])));prod=json.loads(get(desc['production_index']));prod={c['id']:c for c in prod['countries']};cache={}

# Resolve immutable catalogue records by reference/hash only in memory. Never persist URL query values.
def original(st):
 matches=[x for x in world if x['reference']==st['reference'] and x['group']==st['group']]
 assert len(matches)==1
 item=matches[0]
 pair,side=next((p,k)for p in desc['pairs'] for k in ('new','old') if p[k]['reference']==st['reference'] and p[k]['group']==st['group'])
 assert hashlib.sha256(item['url'].encode()).hexdigest()==pair['catalog_url_sha256'][side]
 assert {**item,'url':item['url'].split('?')[0]}==st
 assert set(urllib.parse.parse_qs(urllib.parse.urlsplit(item['url']).query,keep_blank_values=True))<=set(pair['allowed_query_names'])
 return item
def observation(st):
 original(st);result=dict(desc['live_observations'][st['reference']]);result['url']=st['url']
 if 'final_url'in result:result['final_url']=result['final_url'].split('?')[0]
 return result

for r,f,p in zip(rows,facts['entries'],desc['pairs']):
 st=p['new'];old=p['old'];assert f['station']==st and f['approved_station']==old and original(st) in world
 assert r['ref']==st['reference']and r['station']=={k:st[k]for k in ['name','url','group']}and r['ref']not in cfg['held_references']
 for x,ss in [(f['new_audit'],st),(f['approved_audit'],old)]:
  assert x=={k:observation(ss).get(k)for k in x}and x['url']==ss['url'] and x['status']=='audio-confirmed'and x['http_status']==200 and x['content_type'].startswith('audio/')and x['sample_bytes']>0
 binding=p['exact_audio_binding'];assert binding['approved']['url']==old['url'] and binding['candidate']['url']==st['url'] and binding['match']['bytes']>=32768 and len(binding['match']['sha256'])==64
 if p['kind']=='official-player-provider-alias':
  assert p['publisher']['url']=='https://radioamore.gr/' and old['url'] in p['publisher']['excerpt']
  assert st['url']=='http://s4.onweb.gr:8442/;' and old['url']=='https://sh.onweb.gr:7072/;'
  assert ':8442/stream' in p['provider_playlist']['body']
 else:
  assert p['kind']=='exact-provider-service-alias' and old['url']=='http://live.onweb.gr:8010/;' and st['url'] in ['http://s6.onweb.gr:8010/stream','http://s6.onweb.gr:8010/;stream']
  for dns in p['provider_dns'].values():assert any(a.get('data')=='51.195.218.226' for a in dns['Answer'])
  for pl in p['provider_playlists']:assert 'Palmos Radio 93.4' in pl['body'] and 'www.palmosradio.gr' in pl['body'] and ':8010/stream' in pl['body']
 code=r['country'];rel=prod[code]['release'];assert rel==f['production_release']==r['provenance']['production_release'];cache.setdefault(code,json.loads(get(rel)));manifest=cache[code];oldfile=old['reference'].replace(':','_')+'.png'
 assert (code,old['reference'])not in identity_blocks(history)
 assert not any(e['decision']=='hold'and e['row']['country']==code and e['row']['ref']==old['reference']for e in history['entries'])
 for v,(digest,n,blob)in r['variants'].items():
  size,style=v.split('/');assert digest==manifest['packages'][size][style]['files'][oldfile];data=(S/'verified-assets'/f'{digest}.png').read_bytes();assert hashlib.sha256(data).hexdigest()==digest and len(data)==n and hashlib.sha1(f'blob {n}\0'.encode()+data).hexdigest()==blob
 assert r['final_visual_approval']['reviewed_variants']==r['variants']and r['asset_root']==str(S.relative_to(Path.cwd())) if S.is_absolute() else r['asset_root']==str(S)
assert validate_selection(rows,merge_ledgers(paths+[S/'visual-ledger.json.gz']))==len(rows)
baseline_admission.BASELINE_SHA=cfg['baseline_index']['sha256'];raw=(S/'baseline.previous.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==baseline_admission.BASELINE_SHA
new,result=baseline_admission.inspect(rows,raw,Path('/tmp/radio-alias-manifests'));assert len(new)==len(rows)and not result['reused']and not result['held']
proof=dict(status='pass',references=1,png_instances=9,approved_candidate_authority_verified=True,explicit_named_endpoint_pairs=1,source_hold_exceptions=0,new_renders=0,successful_selected_stream_observations=2,exact_compressed_audio_bindings=1)
(S/'verification-proof.json').write_text(json.dumps(proof,indent=2)+'\n');print(proof)
