"""Combine immutable chunks; permit only proved WHITE render-hold replacements."""
from copy import deepcopy

def aggregate(chunks):
    rows=[]; active={}; source_holds=[]; pending=[]; superseded=[]
    for selection, ledger in chunks:
        positives={e['row']['ref']:e['row'] for e in ledger['entries'] if e['decision']=='approve'}
        assert len(positives)==len(selection['entries'])
        assert all(positives[r['ref']]==r for r in selection['entries'])
        rows.extend(deepcopy(selection['entries']))
        for e in ledger['entries']:
            ref=e['row']['ref']
            if ref in active:
                old=active[ref]; proof=e.get('supersedes_render_hold');a=old['row'];b=e['row']
                assert old['decision']=='hold' and e['decision']=='approve' and proof,'Only explicit held-to-approved replacement permitted'
                assert proof['source_commit']==a['source_commit'] and proof['variants']==a['variants']
                assert all(a[k]==b[k]for k in ('country','ref','station'))
                assert all(a['provenance'][k]==b['provenance'][k]for k in ('source_sha256','source_url'))
                assert b['provenance']['original_alpha_preserved'] and b['provenance']['original_visible_RGB_pure_white'] and b['provenance']['white_only_visible_RGB_changed_to_black']
                assert set(a['variants'])==set(b['variants']) and len(b['variants'])==9
                for key in a['variants']:
                    if key.endswith('/white'):assert a['variants'][key]!=b['variants'][key]
                    else:assert a['variants'][key]==b['variants'][key],'Protected TRANSPARENT/BLACK variant changed'
                superseded.append(deepcopy(old))
            active[ref]=deepcopy(e)
        source_holds.extend(deepcopy(ledger.get('source_holds',[])))
        pending.extend(deepcopy(ledger.get('pending_sources',[])))
    entries=list(active.values());assert len({r['ref']for r in rows})==len(rows)
    assert not ({r['ref']for r in rows}&{e['row']['ref']for e in entries if e['decision']=='hold'})
    assert not ({r['ref']for r in rows}&{e['ref']for e in source_holds}),'Source identity holds cannot be bypassed'
    result={'entries':entries,'source_holds':source_holds,'pending_sources':pending}
    if superseded:result['superseded_render_holds']=superseded
    return {'entries':rows},result
