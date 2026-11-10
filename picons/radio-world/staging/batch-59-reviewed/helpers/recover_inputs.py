"""Recover only the selected batch59 inputs on the existing authorized Actions runner."""
import json,gzip,copy,hashlib,re,subprocess,html,sys
from pathlib import Path
S=Path('picons/radio-world/staging');stage=S/'batch-59-reviewed';prev=S/'batch-58-reviewed'
sys.path.insert(0,'picons/radio-world/tools')
from visual_gate import read,merge_ledgers,validate_selection
from saved_artwork_import import get
def sha(b):return hashlib.sha256(b).hexdigest()
def write(p,x):
 b=(json.dumps(x,indent=2,ensure_ascii=False)+'\n').encode();p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(gzip.compress(b,mtime=0)if p.suffix=='.gz'else b)
cfg=read(prev/'configuration.json');raw=(prev/'countries.proposed.json').read_bytes()
assert sha(raw)=='89124925d70bb2fd9d0805bdf383e2a7d90c834c6d68326fbacdcfbcc356b40b'
desc=read(stage/'source-inputs/recovery-spec.json')
world=json.loads(gzip.decompress(get(cfg['world'])));current=json.loads(gzip.decompress(get(desc['current'])));audit=json.loads(gzip.decompress(get(desc['audit'])))['checks']
countries={c['id']:c['name']for c in json.loads(raw)['countries']}
paths=[S/'source-ledger-reviewed-20261107/visual-ledger.json.gz',S/'visual-review-34-36/decisions.json.gz']+[S/f'batch-{n}-reviewed/visual-ledger.json.gz'for n in range(39,59)]
ledger=merge_ledgers(paths);approved=[e['row']for e in ledger['entries']if e['decision']=='approve'];known={(e['row']['country'],e['row']['ref'])for e in ledger['entries']}
rows=[];facts=[];pairs=[];keys=['url','checked_at','http_status','content_type','icy_name','sample_bytes','sample_sha256','status']
for code,name,url,oldname,oldurl in desc['pairs']:
 matches=[r for r in approved if r.get('station',{}).get('name')==oldname and r['station'].get('url')==oldurl]
 assert matches,(name,'missing approved original')
 assert len({tuple(sorted((k,v[0])for k,v in r['variants'].items()))for r in matches})==1,(name,'ambiguous artwork')
 old=matches[0];assert validate_selection([old],ledger)==1
 candidates=[r for r in world if r['name']==name and r['url']==url and r['group']==countries[code]];assert len(candidates)==1,(name,'ambiguous catalogue tuple');st=candidates[0]
 assert any(w['reference']==st['reference']and all(w[k]==st[k]for k in ['name','url','group'])for w in current),(name,'current identity changed')
 assert (code,st['reference'])not in known and st['reference']not in cfg['held_references']
 a=audit[url];b=audit[oldurl];r=copy.deepcopy(old);r.update(ref=st['reference'],country=code,station={k:st[k]for k in ['name','url','group']},index=590000+len(rows));r['asset_root']=r['asset_root'].removesuffix('/verified-assets')
 r['provenance']=copy.deepcopy(old.get('provenance',{}));r['provenance'].update(alias_of_approved_ref=old['ref'],alias_of_approved_country=old['country'],stream_audit_main_commit='481e9b9154a510c64c743de72c1a73ed808307bf',identity_basis='Explicit named endpoint pair and, where required, exact publisher page stream literal')
 r['final_visual_approval']=dict(decision='approve',reason='Byte-identical reuse of all nine historical approved variants; no new graphic or render',reviewed_variants=r['variants'])
 f=dict(station=st,approved=old,new_audit={k:a.get(k)for k in keys},approved_audit={k:b.get(k)for k in keys})
 if name in ['Gravity Radio 105.3','Radio Effe Italia','Agnus Rádió -Cluj Napoca 88,3 FM']:
  p=old['provenance'];page=p.get('page_final_url')or p['page_url'];q=subprocess.run(['curl','-fLsS','--max-time','35',page],capture_output=True);assert q.returncode==0,(name,'publisher unavailable')
  body=html.unescape(q.stdout.decode('utf8',errors='replace')).replace('\\/','/');assert url in body,(name,'no exact publisher stream');at=body.index(url)
  f['primary_page_observation']=dict(station=st,approved_ref=old['ref'],page_url=page,http_fetch_exit=0,bytes=len(q.stdout),sha256=sha(q.stdout),exact_new_stream_literal=True,literal_context=body[max(0,at-60):at+len(url)+60])
 rows.append(r);facts.append(f);pairs.append([name,url,oldname,oldurl,a['icy_name']])
assert len(rows)==16 and len({r['ref']for r in rows})==16
write(stage/'selection.json.gz',dict(entries=rows));write(stage/'visual-ledger.json.gz',dict(entries=[dict(row=r,decision='approve',reason=r['final_visual_approval']['reason'],reviewed_variants=r['variants'])for r in rows],source_holds=[],pending_sources=[]))
write(stage/'source-inputs/public-observations.json',dict(schema=1,stream_audit=desc['audit'],current_world=desc['current'],entries=facts,no_new_endpoint_requests=True,no_new_artwork=True))
(stage/'baseline.previous.json').write_bytes(raw);cfg.update(batch='59-reviewed',references=16,parent_candidate='16f6944792e2bf43f8d1faf67a7016439cceaa85',expected_coverage=3338,selection_sha256=sha((stage/'selection.json.gz').read_bytes()),baseline_index=dict(url='https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/16f6944792e2bf43f8d1faf67a7016439cceaa85/picons/radio-world/staging/batch-58-reviewed/countries.proposed.json',bytes=len(raw),sha256=sha(raw)))
write(stage/'configuration.json',cfg)
src=prev/'helpers';(stage/'helpers/audit_candidate_preservation.py').write_bytes((src/'audit_candidate_preservation.py').read_bytes());(stage/'helpers/source_readback.py').write_bytes((src/'source_readback.py').read_bytes())
s=(src/'build_existing_payload.py').read_text().replace('batch-58','batch-59').replace('batch58','batch59').replace('payload58','payload59').replace('new58','new59');s=re.sub("expected='[a-f0-9]+'","expected='dbf57a4280875a1d95fb96f2fd125fc49c48496d'",s);(stage/'helpers/build_existing_payload.py').write_text(s)
template=(stage/'helpers/verify-template.py.txt').read_text();(stage/'helpers/verify59.py').write_text(template.replace('EXPECTED_PAIRS_PLACEHOLDER',repr(pairs)))
write(stage/'results/recovery-note.json',dict(reason='Local exec environment unavailable before batch59 commit; recovered selected inputs using existing GitHub Actions and original immutable data',last_verified_batch58='16f6944792e2bf43f8d1faf67a7016439cceaa85',identities=16,source_png_instances=144,new_authentication=False,new_production_write=False,audio_container_exception='Radio Bergeijk FLAC: exact named HTTP200 audio-confirmed application/ogg endpoint; no hold bypass',downloader_scope='11 modified countries; full131-country replay already passed in58; global protected-PNG checks unchanged'))
front=read(S/'batch-56-reviewed/results/next-source-observations.json.gz')
write(stage/'results/next-source-observations.json.gz',dict(schema=1,next_batch=60,inherited_frontier=front,configuration_holds_unchanged=923,completed_selection_refs=[r['ref']for r in rows],pending_policy='Do not admit generic ICY, ambiguous cross-host name matches, or tokenized RadioArt /h URLs under the existing free streamf rule. Do not repeat completed56-59 checks.',next='Read final59 HEAD and this frontier; require new primary publisher evidence for CLAZZ or remaining cross-host candidates. Keep new artwork separate for approval.'))
print('Recovered16 exact identities /144 approved PNG variants; ready for existing verification/build pipeline')
