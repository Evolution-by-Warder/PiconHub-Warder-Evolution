"""Assemble batch80 from 20 already-approved, saved RADIO BOB rows. No new rendering."""
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path('picons/radio-world/staging')
STAGE = ROOT / 'batch-80-reviewed'
PREVIOUS = ROOT / 'batch-79-reviewed'
EXTRA = ROOT / 'prepared-radio-bob-capacity'
CHECKPOINT = '3a41f370a3f8c1be9cb8ccf41755b540946af6ff'
BASE = 'https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/'
sha = lambda b: hashlib.sha256(b).hexdigest()


def read(path):
    raw=path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def write(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(obj,indent=2,ensure_ascii=False)+'\n').encode('utf-8')
    path.write_bytes(gzip.compress(raw,mtime=0) if path.suffix == '.gz' else raw)


def main():
    observations=read(PREVIOUS/'results/next-source-observations.json')
    six=read(PREVIOUS/'results/approved-unpublished-capacity.json.gz')['entries']
    fourteen=read(EXTRA/'selection.json.gz')['entries']
    assert len(six)==6 and len(fourteen)==14
    refs={r['ref'] for r in six+fourteen}
    assert len(refs)==20
    assert refs == set(observations['capacity_deferred_references']) | set(observations['prepared_extra_references'])
    assert not set(observations['capacity_deferred_references']) & set(observations['prepared_extra_references'])
    assert read(EXTRA/'preparation-only.json')['status']=='prepared-not-integrated'
    baseline_raw=(PREVIOUS/'countries.proposed.json').read_bytes()
    baseline=json.loads(baseline_raw)
    assert sum(row['picons'] for row in baseline['countries']) == 3462
    cfg=read(PREVIOUS/'configuration.json')
    assert len(cfg['held_references'])==923
    assert not refs.intersection(cfg['held_references'])
    for row in six+fourteen:
        assert row['country']=='DE' and row['station']['group']=='Germany'
        assert len(row['variants'])==9 and row['ref']==row['station']['reference']
        assert len(row['source_commit'])==40 and row['asset_root'].startswith('picons/radio-world/staging/')
        assert all(len(value)==3 for value in row['variants'].values())
        assert row['final_visual_approval']['decision']=='approve'
    write(STAGE/'selection.json.gz',dict(entries=six+fourteen))
    write(STAGE/'visual-ledger.json.gz',dict(entries=[
        dict(row=row,decision='approve',reason=row['final_visual_approval']['reason'],
             reviewed_variants=row['variants']) for row in six+fourteen],
        source_holds=[],pending_sources=[]))
    cfg.update(
        batch='80-reviewed',references=20,expected_coverage=3482,
        parent_candidate=CHECKPOINT,
        baseline_index=dict(url=BASE+CHECKPOINT+'/picons/radio-world/staging/batch-79-reviewed/countries.proposed.json',
                            bytes=len(baseline_raw),sha256=sha(baseline_raw)),
        selection_filename='selection.json.gz',
        selection_sha256=sha((STAGE/'selection.json.gz').read_bytes()),
        visual_ledger_filename='visual-ledger.json.gz',
    )
    write(STAGE/'configuration.json',cfg)
    write(STAGE/'source-preservation.json',dict(
        state='saved-approved-input-only',references=20,PNG_instances=180,
        source_commits=sorted({r['source_commit'] for r in six+fourteen}),
        refs=sorted(refs),baseline_checkpoint=CHECKPOINT,
        previous_coverage=3462,new_candidate_coverage=3482,
        originals_rerendered=0,production_changed=False,
    ))
    print('Preflight PASS: reuse 6+14 saved rows / 180 original PNGs, no source rerender',flush=True)


if __name__=='__main__':
    main()
