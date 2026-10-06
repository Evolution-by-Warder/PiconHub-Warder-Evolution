#!/usr/bin/env python3
"""Apply the frozen Warder contrast policy to an existing family report.

This is policy classification only: it reads checkpoint manifests and emits
decisions. It never invokes the renderer and never edits any PNG.
"""
import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path

CHROMATIC = re.compile(r'(?<!a)chromatic component\s+\d+', re.I)
TWO_TONE = re.compile(r'two-tone achromatic component\s+\d+', re.I)

def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

def reason_text(family):
    return ' ; '.join(str(family.get('variant_status_reason', {}).get(v, {}).get('reason') or '')
                      for v in ('transparent', 'black', 'white'))

def classify(family):
    if family.get('case_type') == 'SOURCE-UNRESOLVED':
        return ('SOURCE-UNRESOLVED', 'No approved transparent input; contrast policy does not apply.')
    if str(family.get('category', '')).startswith('G_SOURCE_QC'):
        return ('SOURCE-QC / HUMAN-REVIEW', 'Source QC blocks normal contrast processing; do not auto-fix.')
    text = reason_text(family)
    chromatic = bool(CHROMATIC.search(text))
    two_tone = bool(TWO_TONE.search(text))
    if chromatic and two_tone:
        return ('HUMAN-REVIEW: CHROMATIC + AMBIGUOUS MASK',
                'Machine reason reports both protected chromatic component(s) and two-tone achromatic component(s); no safe component/text mask is recorded.')
    if chromatic:
        return ('HUMAN-REVIEW: UNSAFE CHROMATIC',
                'Machine reason reports low-contrast chromatic component(s). The existing renderer protects chromatic components and has no recorded semantic text/wordmark mask for them.')
    if two_tone:
        return ('HUMAN-REVIEW: AMBIGUOUS MASK',
                'Machine reason reports a two-tone achromatic connected component. Existing engine rules preserve it and classify low-contrast output as REVIEW.')
    return ('HUMAN-REVIEW: OTHER',
            'No positive machine evidence for an approved automatic contrast operation.')

def split_jsonl(records, out_dir, stem, limit=240_000):
    chunks=[]; lines=[]; size=0
    for record in records:
        line=json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n'
        n=len(line.encode())
        if lines and size+n>limit:
            chunks.append(''.join(lines)); lines=[]; size=0
        lines.append(line); size+=n
    if lines: chunks.append(''.join(lines))
    result=[]
    for i,data in enumerate(chunks,1):
        name=f'{stem}-{i:02d}.jsonl'
        (out_dir/name).write_text(data)
        result.append(name)
    return result

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--families-dir',type=Path,required=True,
                    help='Directory containing family-manifest-NN.jsonl from checkpoint 6ac15b9')
    ap.add_argument('--previous-summary',type=Path,required=True,
                    help='Prior exception-reduction summary.json with the existing sheets index')
    ap.add_argument('--output-dir',type=Path,required=True)
    a=ap.parse_args(); a.output_dir.mkdir(parents=True,exist_ok=True)
    families=[]
    for p in sorted(a.families_dir.glob('family-manifest-*.jsonl')):
        families.extend(read_jsonl(p))
    if len(families)!=1223: raise SystemExit(f'expected 1223 families, found {len(families)}')
    engine=[f for f in families if f['case_type']=='ENGINE-REVIEW']
    unresolved=[f for f in families if f['case_type']=='SOURCE-UNRESOLVED']
    if (len(engine),len(unresolved))!=(903,320):
        raise SystemExit(f'unexpected family split: engine={len(engine)}, unresolved={len(unresolved)}')

    decisions=[]; mapping=[]; remaining=[]; source_unresolved=[]
    category_counts=Counter(); category_identities=Counter()
    auto=[]
    for family in families:
        decision, rationale=classify(family)
        rec={
            'family_id':family['family_id'],'case_type':family['case_type'],
            'policy_decision':decision,'policy_candidate':False,
            'member_count':family['member_count'],'provider_count':family['provider_count'],
            'satellite_count':family['satellite_count'],
            'representative_identity':family['representative_identity'],
            'member_identities':family['member_identities'],
            'source_sha256':family.get('source_sha256'),
            'existing_output_sha256':family.get('output_sha256'),
            'variant_status_reason':family.get('variant_status_reason'),
            'machine_evidence':rationale,
        }
        mapping.append({'family_id':family['family_id'],'case_type':family['case_type'],
                        'policy_decision':decision,'policy_candidate':'false',
                        'member_count':family['member_count'],
                        'representative_identity':family['representative_identity']})
        if family['case_type']=='ENGINE-REVIEW':
            decisions.append(rec); remaining.append(rec)
            if decision.startswith('SOURCE-QC'):
                kind='SOURCE QC'
            elif decision=='HUMAN-REVIEW: AMBIGUOUS MASK':
                kind='AMBIGUOUS MASK'
            elif decision=='HUMAN-REVIEW: UNSAFE CHROMATIC':
                kind='UNSAFE CHROMATIC'
            elif decision=='HUMAN-REVIEW: CHROMATIC + AMBIGUOUS MASK':
                kind='UNSAFE CHROMATIC + AMBIGUOUS MASK'
            else:
                kind='OTHER'
            category_counts[kind]+=1; category_identities[kind]+=family['member_count']
        else:
            source_unresolved.append(rec)

    if len(auto)!=0: raise AssertionError('policy candidate list must be evidence-derived; this policy pass found none')
    decision_parts=split_jsonl(decisions,a.output_dir,'policy-decision-manifest')
    remaining_parts=split_jsonl(remaining,a.output_dir,'remaining-human-review')
    unresolved_parts=split_jsonl(source_unresolved,a.output_dir,'remaining-source-unresolved')
    with (a.output_dir/'family-policy-map.csv').open('w',newline='') as fp:
        w=csv.DictWriter(fp,fieldnames=list(mapping[0]));w.writeheader();w.writerows(mapping)
    (a.output_dir/'policy-auto-fix-candidates.json').write_text(json.dumps({
        'count':0,'families':[],'reason':'No REVIEW family has a machine-recorded safe text/wordmark/component mask. Existing engine REVIEW reasons are chromatic, two-tone, or source-QC holds.'
    },ensure_ascii=False,indent=2)+'\n')
    (a.output_dir/'render-output-qc.json').write_text(json.dumps({
        'renderer_invoked':False,'candidate_family_count':0,'output_qc':'NOT_APPLICABLE',
        'reason':'No POLICY-AUTO-FIX-CANDIDATE families; no rendering or candidate PNG changes were made.'
    },ensure_ascii=False,indent=2)+'\n')

    previous=json.loads(a.previous_summary.read_text())
    sheet_index=[]
    for sheet in previous['review_sheets']:
        sheet_index.append({'path':'reports/warder-master-production/auxiliary-exception-reduction-2026-10-06/'+sheet['file'],
                            'family_ids':sheet['family_ids']})
    (a.output_dir/'remaining-review-sheets.json').write_text(json.dumps({
        'source_checkpoint':'6ac15b98028ff344c1980cb4ea461a94d22894b1',
        'sheet_count':len(sheet_index),'family_count':sum(len(x['family_ids']) for x in sheet_index),
        'sheets':sheet_index
    },ensure_ascii=False,indent=2)+'\n')

    summary={
        'source_checkpoint':'6ac15b98028ff344c1980cb4ea461a94d22894b1',
        'engine_review_families':len(engine),'policy_auto_fix_candidate_families':len(auto),
        'human_review_families':len(remaining),'source_qc_families':category_counts['SOURCE QC'],
        'source_qc_identities':category_identities['SOURCE QC'],
        'source_unresolved_families':len(unresolved),
        'source_unresolved_identities':sum(f['member_count'] for f in unresolved),
        'remaining_total_families':len(remaining)+len(unresolved),
        'policy_classification':{k:{'families':category_counts[k],'identities':category_identities[k]} for k in (
            'SAFE ACHROMATIC/TEXT','MONOCHROME WORDMARK','SAFE SEPARABLE CHROMATIC+TEXT',
            'AMBIGUOUS MASK','UNSAFE CHROMATIC','UNSAFE CHROMATIC + AMBIGUOUS MASK','SOURCE QC','OTHER')},
        'ambiguous_mask_including_overlap':{'families':category_counts['AMBIGUOUS MASK']+category_counts['UNSAFE CHROMATIC + AMBIGUOUS MASK'],
                                             'identities':category_identities['AMBIGUOUS MASK']+category_identities['UNSAFE CHROMATIC + AMBIGUOUS MASK']},
        'unsafe_chromatic_including_overlap':{'families':category_counts['UNSAFE CHROMATIC']+category_counts['UNSAFE CHROMATIC + AMBIGUOUS MASK'],
                                               'identities':category_identities['UNSAFE CHROMATIC']+category_identities['UNSAFE CHROMATIC + AMBIGUOUS MASK']},
        'decision_note':'Counts are reason-evidence classes. Chromatic+mask is reported separately to keep the disjoint breakdown additive; the overlap totals are given explicitly.',
        'renderer_invoked':False,'output_qc':'NOT_APPLICABLE_NO_CANDIDATES',
        'unchanged':'No engine, thresholds, templates, images, family grouping, or status was changed.'
    }
    harmonic=next(f for f in decisions if f['family_id']=='AUX-RF-0301')
    summary['harmonic_sentinel']={
        'family_id':harmonic['family_id'],'decision':harmonic['policy_decision'],
        'member_count':harmonic['member_count'],'members':harmonic['member_identities'],
        'black_reason':harmonic['variant_status_reason']['black']['reason'],
        'white_reason':harmonic['variant_status_reason']['white']['reason'],
        'mask_evidence':'The saved machine report contains connected-component type/index and low-contrast ratio, but no exported component-mask coordinates or semantic text/wordmark classification. The pinned renderer treats reported chromatic components as protected; no safe recolour target can be established.'
    }
    (a.output_dir/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    (a.output_dir/'README.md').write_text(
        '# Auxiliary family contrast-policy pass\n\n'
        'Input is the accepted exception-family checkpoint `6ac15b98028ff344c1980cb4ea461a94d22894b1`. '
        'This pass classifies existing machine reasons under `docs/PICON-MASTER-QUALITY-PLAN.md`; it does not repeat SHA deduplication, render, change engine code, or modify PNGs.\n\n'
        f"- Engine-review families: {len(engine)}\n- Policy auto-fix candidates: 0\n- Human-review families: {len(remaining)}\n- Source-QC: {summary['source_qc_families']} families / {summary['source_qc_identities']} identities\n- Source-unresolved: {len(unresolved)} families\n"
        '- The existing engine already auto-fixes clearly isolated achromatic components. Remaining reasons identify protected chromatic and/or two-tone components, or source-QC holds. The report does not persist the mask geometry or semantic text identity needed to apply the plan’s text-aware exception safely.\n'
        '- Therefore no renderer call was made; output QC is not applicable. The prior reduced sheets remain in the parent checkpoint and are indexed by `remaining-review-sheets.json`.\n'
    )
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    print('parts',{'decisions':decision_parts,'remaining':remaining_parts,'source_unresolved':unresolved_parts})

if __name__=='__main__': main()
