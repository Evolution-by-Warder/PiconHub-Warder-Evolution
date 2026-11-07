import copy,json
from pathlib import Path
from aggregate_source_metadata import aggregate
p=Path(__file__).parent
def fixture(chunk):
    canonical=p/'chunks'/('chunk-'+chunk)/'visual-ledger.json'
    return json.load(open(canonical if canonical.exists() else p/('visual-ledger-chunk-'+chunk+'.json')))
one=fixture('001');two=fixture('002')
# Distinct groups must survive, including complete non-URL evidence records.
original=copy.deepcopy(two['source_holds']);one['source_holds']=original[:2];two['source_holds']=original[2:]
one['pending_sources']=[{'index':59,'reason':'technical SVG preview deferred','evidence_sha256':original[2]['source_sha256']}]
two['pending_sources']=[{'index':26,'reason':'ownership pending','evidence_sha256':'pending-not-an-artwork-fingerprint'}]
a={'entries':[e['row'] for e in one['entries'] if e['decision']=='approve']};b={'entries':[e['row'] for e in two['entries'] if e['decision']=='approve']};before=copy.deepcopy((a,one,b,two));sel,ledger=aggregate([(a,one),(b,two)])
assert (a,one,b,two)==before
assert sel['entries']==a['entries']+b['entries'] and len(sel['entries'])==21
assert len(ledger['entries'])==31 and sum(e['decision']=='hold' for e in ledger['entries'])==10
assert ledger['source_holds']==original and len(ledger['source_holds'])==4
assert ledger['pending_sources']==one['pending_sources']+two['pending_sources']
print('PASS 21 approve / 10 rendered hold / 4 source exclusions; evidence and pending groups unchanged')
