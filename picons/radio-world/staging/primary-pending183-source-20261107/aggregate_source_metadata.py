"""Combine immutable chunk metadata without losing exclusion/pending evidence."""
from copy import deepcopy

def aggregate(chunks):
    rows=[]; entries=[]; source_holds=[]; pending=[]
    for selection, ledger in chunks:
        positives={e['row']['ref']:e['row'] for e in ledger['entries'] if e['decision']=='approve'}
        assert len(positives)==len(selection['entries'])
        assert all(positives[r['ref']]==r for r in selection['entries'])
        rows.extend(deepcopy(selection['entries']))
        entries.extend(deepcopy(ledger['entries']))
        source_holds.extend(deepcopy(ledger.get('source_holds',[])))
        pending.extend(deepcopy(ledger.get('pending_sources',[])))
    assert len({r['ref'] for r in rows})==len(rows)
    assert len({e['row']['ref'] for e in entries})==len(entries)
    assert not ({r['ref'] for r in rows}&{e['row']['ref'] for e in entries if e['decision']=='hold'})
    assert not ({r['ref'] for r in rows}&{e['ref'] for e in source_holds})
    return {'entries':rows},{'entries':entries,'source_holds':source_holds,'pending_sources':pending}
