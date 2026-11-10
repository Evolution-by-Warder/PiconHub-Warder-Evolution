"""Authenticate only technical quarantine resolution; never create an artwork approval."""
import hashlib,json
from pathlib import Path

RECEIPT_SHA='f883c90f951d3027ba4a6946c604958acefde15d99a217e696eb91a9139d0314'
RECEIPT_BLOB='2a8d58e477dc376e8ae095ba7c5c08a20f42f024'
SNAPSHOT_SHA='e97f6edfbea8c020e137f58b6e2b493aeb0123edaf179acd5defac9dfd4b13ee'
SNAPSHOT_BLOB='d31cbd35dc4e6914330bf93751c7532a2958bc11'
SNAPSHOT_COMMIT='2322e554ea89b024db8c184ed193e5be40c8a996'
FINAL_SHA='5caa5d293c351c73e161fa1cbc5ff252949a2605a517e1086d8949c644d0f593'
FINAL_BLOB='f8aa4db17f98b2d4ba337cc124db28be1bca3915'
FINAL_COMMIT='890c9edb644d676f5b33855268f39aefbad65be8'
TECHNICAL='technical-unavailable-local-review'
VARIANTS={f'{size}/{style}'for size in('50x30','220x132','400x240')for style in('transparent','white','black')}
def require(ok,message):
    if not ok:raise ValueError(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def blob(raw):return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
def authority(receipt_path,snapshot_path,final_path):
    raw=Path(receipt_path).read_bytes();snapshot_raw=Path(snapshot_path).read_bytes()
    require(len(raw)==13135 and sha(raw)==RECEIPT_SHA and blob(raw)==RECEIPT_BLOB,'Actual immutable recovery receipt differs')
    require(len(snapshot_raw)==5618333 and sha(snapshot_raw)==SNAPSHOT_SHA and blob(snapshot_raw)==SNAPSHOT_BLOB,'Actual immutable row binding differs')
    final_raw=Path(final_path).read_bytes()
    require(len(final_raw)==7088290 and sha(final_raw)==FINAL_SHA and blob(final_raw)==FINAL_BLOB,'Final immutable source freeze differs')
    final=json.loads(final_raw);final_by_index={e['index']:e for e in final['entries']}
    receipt=json.loads(raw);snapshot=json.loads(snapshot_raw)
    require(receipt['immutable_row_binding']['commit']==SNAPSHOT_COMMIT and receipt['immutable_row_binding']['git_blob']==SNAPSHOT_BLOB,'Wrong receipt/snapshot binding')
    passing=set(receipt['source_review']['source_pass_indices']);approved=set(receipt['final_review']['approve_indices'])
    require(len(passing)==68 and len(approved)==54 and approved<=passing,'Actual recovery decision inventory differs')
    require(len(snapshot['entries'])==1519,'Wrong frozen inventory')
    by_index={e['index']:e for e in snapshot['entries']};result={}
    for index in sorted(approved):
        e=by_index[index];new=final_by_index[index];row=e['row'];identity=(row['country'],row['ref'])
        require(new['status']=='logo-frozen' and all(new['row'][k]==e['row'][k]for k in('ref','country','zeno_mount'))and all(new['row']['station'][k]==e['row']['station'][k]for k in('name','url','group')) and new['source']['sha256']==e['source']['sha256'] and new['api_evidence']['sha256']==e['api_evidence']['sha256'],'Recovered source changed across final freeze')
        require(all(new['api_station'][k]==e['api_station'][k]for k in('country','streamURL','streamName')),'Final API identity changed')
        require(e['status']=='logo-frozen' and identity not in result,'Invalid source binding')
        result[identity]=dict(index=index,country=row['country'],ref=row['ref'],station=row['station'],source_sha256=e['source']['sha256'],api_sha256=e['api_evidence']['sha256'],receipt_sha256=RECEIPT_SHA,snapshot_sha256=SNAPSHOT_SHA)
    return result

def recovery(path,expected_sha,approved):
    require(path is not None and isinstance(expected_sha,str)and len(expected_sha)==64,'Actual new physical recovery proof and its pinned SHA256 required')
    raw=Path(path).read_bytes();require(sha(raw)==expected_sha,'New physical recovery proof bytes do not match the pinned digest')
    proof=json.loads(raw)
    require(proof['schema']==1 and proof['status']=='pass' and proof['old_manual_receipt_sha256']==RECEIPT_SHA,'Wrong physical recovery proof/old receipt binding')
    require(proof['frozen_source_commit']==SNAPSHOT_COMMIT and proof['final_frozen_source_commit']==FINAL_COMMIT,'Wrong old/final source freeze binding')
    entries=proof['entries'];require(bool(entries)and len(entries)==proof['references'] and proof['png_instances']==9*len(entries),'Wrong recovery count')
    bound={}
    for item in entries:
        identity=(item['country'],item['ref']);require(identity in approved and identity not in bound,'Unrelated or duplicate recovery proof identity')
        old=approved[identity];require(item['index']==old['index'] and item['source_sha256']==old['source_sha256'] and item['api_sha256']==old['api_sha256'],'New proof source/API/receipt identity differs')
        require(item['source_commit']==proof['source_pixel_commit'] and len(item['source_commit'])==40,'Actual pixel commit binding missing')
        require(item['decision']=='approve' and set(item['reviewed_variants'])==VARIANTS and set(item['variants'])==VARIANTS,'Actual fresh all-nine visual approval missing')
        bound[identity]=item
    return dict(sha256=expected_sha,entries=bound,source_pixel_commit=proof['source_pixel_commit'])

def authorize(row,entry,holds,approved,physical):
    """Caller separately verifies actual nine-variant fingerprints with visual_gate."""
    identity=(row['country'],row['ref'])
    require(identity in approved,'Reference is not one of the54 actual positive recovery receipts')
    require(bool(holds) and all(h.get('hold_kind')==TECHNICAL for h in holds),'A genuine source/identity/HDF rejection cannot be cleared by technical recovery')
    require(all((h['country'],h['ref'])==identity for h in holds),'Wrong quarantined identity')
    require(entry.get('resolves_source_hold')is True and physical is not None and entry.get('resolution_evidence_sha256')==physical['sha256'],'Missing exact verified resolution evidence; a random64hex digest is not evidence')
    require(identity in physical['entries'],'Exact physical recovery proof does not include this reference')
    artifact=physical['entries'][identity]
    require(row['source_commit']==artifact['source_commit']==physical['source_pixel_commit'] and row['variants']==artifact['variants'],'Actual source pixel commit/nine fingerprints differ from physical proof')
    proof=approved[identity];provenance=row.get('provenance',{})
    require(provenance.get('source_sha256')==proof['source_sha256'] and provenance.get('page_sha256')==proof['api_sha256'],'Recovery source/API content changed')
    require(all(row['station'][k]==proof['station'][k]for k in('name','url','group')),'Recovery station identity changed')
    for h in holds:
        frozen=h.get('snapshot_evidence',{})
        require(frozen.get('commit')==SNAPSHOT_COMMIT and frozen.get('git_blob')==SNAPSHOT_BLOB and frozen.get('source_sha256')==proof['source_sha256'] and frozen.get('api_sha256')==proof['api_sha256'],'Technical hold is not bound to the exact recovered source')
    return dict(country=identity[0],ref=identity[1],index=proof['index'],source_sha256=proof['source_sha256'],api_sha256=proof['api_sha256'],resolution_evidence_sha256=physical['sha256'],old_manual_receipt_sha256=RECEIPT_SHA)
