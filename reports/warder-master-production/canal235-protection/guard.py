"""Fail-closed preflight for Vhannibal writes affecting protected CANAL data.

Input: JSON list of writes on stdin. Each write can supply path, reference,
position, selector_id, station_names. Output: JSON decisions; exit 1 if any
write is blocked or requires an independent missing-reference check.
Protection matching never creates receiver aliases or changes service types.
"""
from pathlib import Path
import json, re, sys, unicodedata

ROOT=Path(__file__).resolve().parent

def reference_parts(value):
    raw=str(value).replace('\\','/').rsplit('/',1)[-1]
    raw=re.sub(r'\.png$','',raw,flags=re.I).replace(':','_').strip('_')
    parts=raw.split('_')
    if len(parts)!=10:return None
    try:return tuple(int(x,16) for x in parts)
    except ValueError:return None

def identity(parts):
    return parts[3:7] if parts else None

def normalized_name(value):
    value=unicodedata.normalize('NFKD',str(value)).casefold()
    value=''.join(x for x in value if not unicodedata.combining(x))
    value=re.sub(r'\b(?:uhd|hd|sd)\b','',value)
    return re.sub(r'[^a-z0-9]','',value)

def validate_plan(plan, policy=None, baseline=None):
    policy=policy or json.loads((ROOT/'policy.json').read_text())
    baseline=baseline or json.loads((ROOT/policy['baseline_file']).read_text())
    protected={identity(reference_parts(r)) for r in baseline['protected_reference_filenames']}
    families={n:family for family,names in policy['explicit_station_families'].items() for n in names}
    result=[]
    for write in plan:
        path=str(write.get('path','')).replace('\\','/').casefold()
        selector=str(write.get('selector_id','')).upper()
        parts=reference_parts(write.get('reference') or write.get('path',''))
        pos=str(write.get('position','')).casefold().replace(',','.').replace('°','')
        is235=(parts is not None and parts[6]>>16==235) or '/23.5e/' in '/'+path or pos in ('23.5e','235e','23.5','235')
        package=selector in policy['protected_selectors'] or any(p.casefold() in path for p in policy['protected_provider_paths']) or 'canalplus_sk' in path or 'canalplus_cz' in path
        names=write.get('station_names',[])
        if isinstance(names,str):names=[names]
        family=next((families[normalized_name(n)] for n in names if normalized_name(n) in families),None)
        if package:reason='BLOCK_PROTECTED_CANAL_PACKAGE'
        elif is235 and identity(parts) in protected:reason='BLOCK_PROTECTED_STATION_REFERENCE'
        elif is235 and family:reason='BLOCK_PROTECTED_STATION_FAMILY'
        elif is235:reason='HOLD_235E_MISSING_REFERENCE_AND_BRAND_CHECK'
        else:reason='ALLOW_OUTSIDE_PROTECTED_SCOPE'
        result.append({'path':write.get('path'),'reference':write.get('reference'),'allowed':reason.startswith('ALLOW_'),'reason':reason})
    return result

if __name__=='__main__':
    decisions=validate_plan(json.load(sys.stdin))
    print(json.dumps({'allowed':all(x['allowed'] for x in decisions),'decisions':decisions},ensure_ascii=False,indent=2))
    raise SystemExit(0 if all(x['allowed'] for x in decisions) else 1)
