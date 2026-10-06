#!/usr/bin/env python3
"""Reduce the accepted auxiliary run's human-review workload.

Reads only the pinned machine report, its existing candidate PNGs and the
legacy ZIP inputs. It does not render, alter, or approve candidate assets.
"""
import collections
import hashlib
import json
import math
import os
import re
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(os.environ.get('AUX_REVIEW_CHECKPOINT_ROOT', '/tmp/piconhub-review-checkpoint'))
RUN = ROOT / 'reports/warder-master-production/auxiliary-ingress-run-2026-10-06'
REPORT = RUN / 'machine-report.jsonl'
ZIPROOT = Path(os.environ.get('AUX_REVIEW_SOURCE_ZIP_DIR', '/tmp/warder-test202-source'))
OUT = Path(os.environ.get('AUX_REVIEW_OUTPUT_DIR', '/tmp/auxiliary-exception-reduction'))
OUT.mkdir(parents=True, exist_ok=True)

def read_rows():
    return [json.loads(line) for line in REPORT.open()]

def safe_component_reason(row):
    parts = []
    for variant in ('black', 'white'):
        v = row[variant]
        if v['status'] in ('REVIEW', 'HOLD'):
            parts.append((variant, v['status'], v.get('reason')))
    return parts

def primary_category(row):
    if row['final_status'] == 'SOURCE-UNRESOLVED':
        present = {k for k in ('black', 'white') if row['source'].get(k)}
        if present == {'black', 'white'}:
            return 'I_SOURCE_UNRESOLVED_BW'
        if present == {'black'}:
            return 'J_SOURCE_UNRESOLVED_BLACK_ONLY'
        return 'K_SOURCE_UNRESOLVED_OTHER'
    reasons = [row[v].get('reason') or '' for v in ('black', 'white')
               if row[v]['status'] in ('REVIEW', 'HOLD')]
    lowered = ' | '.join(reasons).lower()
    if row['source_qc_status'] in ('SOURCE-REVIEW', 'SOURCE-FAIL') or row['transparent']['status'] in ('REVIEW', 'HOLD', 'FAIL'):
        return 'G_SOURCE_QC_ALPHA_BACKGROUND'
    if row.get('geometry_status') not in ('PRESERVED_NATIVE_CANVAS', 'NOT_APPLICABLE'):
        return 'F_GEOMETRY_PLACEMENT_SAFE_FIT'
    if row['black']['status'] in ('REVIEW', 'HOLD') and row['white']['status'] in ('REVIEW', 'HOLD'):
        return 'C_BLACK_AND_WHITE_CONTRAST'
    if 'two-tone achromatic component' in lowered:
        return 'D_COMPONENT_MASK_AMBIGUOUS'
    if 'chromatic component' in lowered:
        return 'E_MIXED_CHROMATIC_UNSAFE_RECOLOUR'
    if row['black']['status'] in ('REVIEW', 'HOLD'):
        return 'A_DARK_LOW_CONTRAST_ON_BLACK'
    if row['white']['status'] in ('REVIEW', 'HOLD'):
        return 'B_LIGHT_LOW_CONTRAST_ON_WHITE'
    return 'H_OTHER_ENGINE_REVIEW'

def category_tags(row):
    """Overlapping machine-cause tags; artwork families remain hash-exact."""
    primary = primary_category(row)
    if primary.startswith('I_') or primary.startswith('J_') or primary.startswith('K_'):
        return [primary]
    if primary.startswith('G_') or primary.startswith('F_') or primary.startswith('H_'):
        return [primary]
    tags=[]
    b=row['black']; w=row['white']
    br=b.get('reason') or ''; wr=w.get('reason') or ''
    if b['status']=='REVIEW' and w['status']=='REVIEW': tags.append('C_BLACK_AND_WHITE_CONTRAST')
    if 'two-tone achromatic component' in br.lower() or 'two-tone achromatic component' in wr.lower():
        tags.append('D_COMPONENT_MASK_AMBIGUOUS')
    if 'chromatic component' in br.lower() or 'chromatic component' in wr.lower():
        tags.append('E_MIXED_CHROMATIC_UNSAFE_RECOLOUR')
    if b['status']=='REVIEW' and 'achromatic component' in br.lower() and 'two-tone achromatic component' not in br.lower():
        tags.append('A_DARK_LOW_CONTRAST_ON_BLACK')
    if w['status']=='REVIEW' and 'achromatic component' in wr.lower() and 'two-tone achromatic component' not in wr.lower():
        tags.append('B_LIGHT_LOW_CONTRAST_ON_WHITE')
    return tags or ['H_OTHER_ENGINE_REVIEW']

def group_key(row):
    # Exact identity-relevant hashes and exact status/reason tuples only.
    # No grouping by filename, provider, or fuzzy reason wording.
    cat = primary_category(row)
    if row['final_status'] == 'SOURCE-UNRESOLVED':
        return ('SOURCE-UNRESOLVED', cat,
                row['source'].get('black', {}).get('sha256'),
                row['source'].get('white', {}).get('sha256'))
    return ('ENGINE-REVIEW', cat,
            row['source'].get('transparent', {}).get('sha256'),
            row['transparent'].get('status'), row['transparent'].get('reason'),
            row['transparent'].get('output_sha256'),
            row['black'].get('status'), row['black'].get('reason'), row['black'].get('output_sha256'),
            row['white'].get('status'), row['white'].get('reason'), row['white'].get('output_sha256'))

def exact_reason_inventory(rows):
    inv = {}
    fields = {
        'source_status_reason': lambda r: (r.get('source_qc_status'), r.get('geometry_status'), r.get('geometry_reason')),
        'transparent_status_reason': lambda r: (r['transparent'].get('status'), r['transparent'].get('reason')),
        'black_status_reason': lambda r: (r['black'].get('status'), r['black'].get('reason')),
        'white_status_reason': lambda r: (r['white'].get('status'), r['white'].get('reason')),
        'final_status_reason': lambda r: (r.get('final_status'), r.get('final_reason')),
    }
    for field, get in fields.items():
        c = collections.Counter(get(r) for r in rows)
        inv[field] = [{'status': k[0], 'reason': k[1], 'extra': k[2] if len(k) > 2 else None, 'count': n}
                      for k, n in sorted(c.items(), key=lambda item: (str(item[0][0]), str(item[0][1]), str(item[0][2:]))) ]
    return inv

def source_archive(row, variant):
    source = row.get('source', {}).get(variant)
    if not source:
        return None
    p = source.get('path', '')
    archive_name, member = p.split(':', 1)
    archive = ZIPROOT / archive_name
    if not archive.exists():
        raise FileNotFoundError(archive)
    return archive, member

def extract_source(row, variant, temp_dir):
    item = source_archive(row, variant)
    if not item:
        return None
    archive, member = item
    key = row['source'][variant]['sha256']
    dest = temp_dir / f'{key}.png'
    if not dest.exists():
        with zipfile.ZipFile(archive) as zf:
            data = zf.read(member)
        if hashlib.sha256(data).hexdigest() != key:
            raise ValueError(f'source SHA mismatch {row["stable_identity"]} {variant}')
        dest.write_bytes(data)
    return dest

def candidate_path(row, variant):
    rel = row[variant].get('output_path')
    if not rel:
        return None
    return ROOT / rel

def file_dim(path):
    if not path or not path.exists(): return None
    with Image.open(path) as im: return [*im.size, im.mode]

def load_font(size):
    for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf'):
        if Path(p).exists(): return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def fit_preview(path, size=(220,132), bg=(230,230,230,255)):
    canvas = Image.new('RGBA', size, bg)
    if path and Path(path).exists():
        with Image.open(path) as im:
            im = im.convert('RGBA')
            im.thumbnail(size, Image.Resampling.LANCZOS)
            canvas.alpha_composite(im, ((size[0]-im.width)//2, (size[1]-im.height)//2))
    else:
        d = ImageDraw.Draw(canvas); d.rectangle((0,0,size[0]-1,size[1]-1), outline=(160,30,30,255), width=2)
        d.text((12,55),'NO SOURCE',font=load_font(18),fill=(160,30,30,255))
    return canvas.convert('RGB')

def wrap_text(draw, text, font, max_width):
    words = str(text or '').split()
    lines=[]; line=''
    for w in words:
        trial=(line+' '+w).strip()
        if draw.textbbox((0,0),trial,font=font)[2] <= max_width: line=trial
        else:
            if line: lines.append(line)
            line=w
    if line: lines.append(line)
    return lines

def main():
    rows = read_rows()
    if len(rows) != 1604: raise RuntimeError(f'expected 1604 report rows, got {len(rows)}')
    exception_rows = [r for r in rows if r['final_status'] in ('REVIEW','SOURCE-UNRESOLVED')]
    if len(exception_rows) != 1431: raise RuntimeError(f'expected 1431 exceptions, got {len(exception_rows)}')
    inventory = exact_reason_inventory(rows)
    (OUT/'reason-inventory.json').write_text(json.dumps(inventory, ensure_ascii=False, indent=2)+'\n')
    reason_count = sum(len(v) for v in inventory.values())

    groups=collections.defaultdict(list)
    for r in exception_rows: groups[group_key(r)].append(r)
    sorted_groups=sorted(groups.items(), key=lambda kv:(str(kv[0][0]), str(kv[0][1]), str(kv[0][2:])))
    families=[]; mapping=[]
    for i,(key,members) in enumerate(sorted_groups,1):
        fid=f'AUX-RF-{i:04d}'
        members=sorted(members,key=lambda r:(r['domain'],r['identity_filename'].casefold(),r['identity_filename']))
        rep=members[0]; cat=primary_category(rep)
        family={
            'family_id':fid,'case_type':key[0],'category':cat,'categories':category_tags(rep),
            'engine_reason':safe_component_reason(rep) if key[0]=='ENGINE-REVIEW' else 'No approved transparent source; source-unresolved grouping is exact legacy SHA pair.',
            'member_count':len(members),
            'provider_count':sum(r['domain']=='provider-logo' for r in members),
            'satellite_count':sum(r['domain']=='satellite-logo' for r in members),
            'representative_identity':rep['stable_identity'],
            'representative_filename':rep['identity_filename'],
            'representative_review_id':rep['review_id'],
            'representative_source_sha256':rep.get('source',{}).get('transparent',{}).get('sha256'),
            'source_sha256':{v:rep.get('source',{}).get(v,{}).get('sha256') for v in ('transparent','black','white')},
            'output_sha256':{v:rep.get(v,{}).get('output_sha256') for v in ('transparent','black','white')},
            'variant_status_reason':{v:{'status':rep[v].get('status'),'reason':rep[v].get('reason')} for v in ('transparent','black','white')},
            'member_identities':[r['stable_identity'] for r in members],
            'member_review_ids':[r['review_id'] for r in members],
            'key_sha256':hashlib.sha256(json.dumps(key,ensure_ascii=False,separators=(',',':')).encode()).hexdigest(),
        }
        families.append(family)
        for r in members:
            mapping.append({'stable_identity':r['stable_identity'],'review_id':r['review_id'],'domain':r['domain'],'filename':r['identity_filename'],'original_final_status':r['final_status'],'family_id':fid,'category':cat,'categories':'|'.join(category_tags(r)),'representative':r is rep})

    # Extract legacy source images from the already-fetched source ZIPs only.
    extracted=OUT/'source-cache'; extracted.mkdir(exist_ok=True)
    byid={r['stable_identity']:r for r in rows}
    for f in families:
        r=byid[f['representative_identity']]
        for variant in ('transparent','black','white'):
            f.setdefault('source_dimensions',{})[variant]=file_dim(extract_source(r,variant,extracted))
            cp=candidate_path(r,variant)
            f.setdefault('output_dimensions',{})[variant]=file_dim(cp)
            if cp and not cp.exists(): raise FileNotFoundError(cp)

    (OUT/'family-manifest.json').write_text(json.dumps(families,ensure_ascii=False,indent=2)+'\n')
    with (OUT/'identity-family-map.csv').open('w') as f:
        f.write('stable_identity,review_id,domain,filename,original_final_status,family_id,category,categories,representative\n')
        import csv
        w=csv.DictWriter(f,fieldnames=['stable_identity','review_id','domain','filename','original_final_status','family_id','category','categories','representative'])
        # Header already emitted above; write records only.
        for x in sorted(mapping,key=lambda x:x['stable_identity']): w.writerow(x)

    # Exact duplicate evidence for all exception source/output hashes.
    hash_index=collections.defaultdict(list)
    for r in exception_rows:
        for kind,variant in [('source',v) for v in ('transparent','black','white')]+[('output',v) for v in ('transparent','black','white')]:
            obj=r.get(kind,{}).get(variant,{}) if kind=='source' else r.get(variant,{})
            sha=obj.get('sha256') if kind=='source' else obj.get('output_sha256')
            if sha: hash_index[(kind,variant,sha)].append(r['stable_identity'])
    dupes=[{'kind':k,'variant':v,'sha256':sha,'member_count':len(ids),'members':sorted(set(ids))}
           for (k,v,sha),ids in sorted(hash_index.items()) if len(set(ids))>1]
    (OUT/'duplicate-hash-families.json').write_text(json.dumps(dupes,ensure_ascii=False,indent=2)+'\n')

    # Reduced review sheets: up to 4 family panels per page, one representative each.
    font=load_font(22); small=load_font(16); tiny=load_font(13)
    panel_w,panel_h=1500,450; cols,rows_per=2,2; gap=32
    sheet_dir=OUT/'reduced-review-sheets'; sheet_dir.mkdir(exist_ok=True)
    sheets=[]
    for start in range(0,len(families),4):
        batch=families[start:start+4]
        page=Image.new('RGB',(cols*panel_w+(cols+1)*gap, rows_per*panel_h+(rows_per+1)*gap),(248,248,248))
        draw=ImageDraw.Draw(page)
        for j,f in enumerate(batch):
            x=gap+(j%cols)*(panel_w+gap); y=gap+(j//cols)*(panel_h+gap)
            rep=byid[f['representative_identity']]
            draw.rounded_rectangle((x,y,x+panel_w,y+panel_h),radius=12,fill='white',outline=(70,90,120),width=2)
            head=f"{f['family_id']}  |  {f['category']}  |  members {f['member_count']} (P {f['provider_count']} / S {f['satellite_count']})"
            draw.text((x+16,y+12),head,font=font,fill=(20,35,55))
            draw.text((x+16,y+43),f"{f['representative_identity']}  [{rep['review_id']}]",font=small,fill=(30,30,30))
            labels=('SOURCE / LEGACY TRANSPARENT','ENGINE TRANSPARENT','ENGINE BLACK','ENGINE WHITE')
            variants=('transparent','transparent','black','white')
            cellw=panel_w//4
            for k,(lab,var) in enumerate(zip(labels,variants)):
                px=x+k*cellw+12; py=y+78
                draw.text((px,py),lab,font=tiny,fill=(45,45,45))
                if k==0 or f['case_type']=='SOURCE-UNRESOLVED':
                    p=extract_source(rep,var,extracted)
                else:
                    p=candidate_path(rep,var)
                thumb=fit_preview(p,(cellw-24,132),bg=(250,250,250,255) if var=='white' else ((20,20,20,255) if var=='black' else (220,220,220,255)))
                page.paste(thumb,(px,py+23))
                if f['case_type']=='SOURCE-UNRESOLVED':
                    status=('MISSING SOURCE' if k==0 else 'NO OUTPUT') if var=='transparent' else f"LEGACY {var.upper()}"
                    sha=rep.get('source',{}).get(var,{}).get('sha256') or '—'
                elif k==0:
                    status=f"SOURCE QC {rep['source_qc_status']}"
                    sha=rep.get('source',{}).get(var,{}).get('sha256') or '—'
                else:
                    status=rep[var].get('status') or 'NO OUTPUT'
                    sha=rep[var].get('output_sha256') or '—'
                draw.text((px,py+159),status,font=tiny,fill=(150,25,25) if ('REVIEW' in status or 'HOLD' in status) else (30,80,40))
                draw.text((px,py+178),f"SHA {sha[:14]}…",font=tiny,fill=(80,80,80))
            # Machine reasons, exact as stored.
            reason='; '.join(f"{v.upper()}: {rep[v].get('reason')}" for v in ('black','white') if rep[v].get('reason'))
            lines=wrap_text(draw,reason,small,panel_w-32)
            if len(lines)>3: lines=lines[:3]+['[Exact full reason: family-manifest.json]']
            for n,line in enumerate(lines): draw.text((x+16,y+330+n*18),line,font=small if n<3 else tiny,fill=(70,40,40))
        fn=f'reduced-review-{start//4+1:03d}.png'
        # Palette compression is only for this composite review sheet. It
        # never changes candidate PNGs or the source assets.
        page.quantize(colors=256,method=Image.Quantize.FASTOCTREE).save(sheet_dir/fn,optimize=True)
        sheets.append({'file':f'reduced-review-sheets/{fn}','family_ids':[f['family_id'] for f in batch]})

    bycat=collections.defaultdict(lambda:{'families':0,'identities':0})
    for f in families:
        for category in f['categories']:
            c=bycat[category]; c['families']+=1; c['identities']+=f['member_count']
    for empty_category in ('A_DARK_LOW_CONTRAST_ON_BLACK','B_LIGHT_LOW_CONTRAST_ON_WHITE','F_GEOMETRY_PLACEMENT_SAFE_FIT','H_OTHER_ENGINE_REVIEW'):
        bycat[empty_category]
    category_summary={k:{**v,'reduction_percent':round((1-v['families']/v['identities'])*100,2) if v['identities'] else 0.0} for k,v in sorted(bycat.items())}
    summary={
        'input_checkpoint':'71957fdfdc2ad7deac4908ae3dff2ee588330b73',
        'total_identities':len(rows),'total_exceptions':len(exception_rows),
        'review_identities':sum(r['final_status']=='REVIEW' for r in exception_rows),
        'source_unresolved_identities':sum(r['final_status']=='SOURCE-UNRESOLVED' for r in exception_rows),
        'unique_machine_reason_entries_by_field':{k:len(v) for k,v in inventory.items()},
        'unique_machine_reasons_total_across_fields':reason_count,
        'review_families':sum(f['case_type']=='ENGINE-REVIEW' for f in families),
        'source_unresolved_families':sum(f['case_type']=='SOURCE-UNRESOLVED' for f in families),
        'total_unique_human_review_families':len(families),
        'category_summary':category_summary,
        'reduction_vs_1431_exceptions_percent':round((1-len(families)/1431)*100,2),
        'review_sheet_count':len(sheets),'review_sheet_family_coverage':sum(len(s['family_ids']) for s in sheets),
        'review_sheets':sheets,
        'grouping_policy':'Exact source/output SHA and exact engine status/reason signature. SOURCE-UNRESOLVED groups require exact same legacy Black and White SHA pair, or exact Black SHA for black-only. No fuzzy-name grouping; no status changes; no rendering.',
        'harmonic_sentinel':None,
        'hellasat_regression':None,
    }
    harmonic=next(r for r in rows if r['identity_filename']=='HARMONIC.png' and r['domain']=='provider-logo')
    hf=next(f for f in families if harmonic['stable_identity'] in f['member_identities'])
    harmonic_equiv=[r for r in exception_rows if r['final_status']=='REVIEW' and r['source'].get('transparent',{}).get('sha256')==harmonic['source']['transparent']['sha256'] and safe_component_reason(r)==safe_component_reason(harmonic)]
    summary['harmonic_sentinel']={'family_id':hf['family_id'],'family_member_count':hf['member_count'],'exact_same_source_and_reason_count':len(harmonic_equiv),'machine_reason':safe_component_reason(harmonic),'review_id':harmonic['review_id']}
    hellasat=next(r for r in rows if r['identity_filename']=='300W.png' and r['domain']=='satellite-logo')
    summary['hellasat_regression']={'result':'PASS' if hellasat.get('hellasat_geometry_sentinel',{}).get('result')=='PASS' and hellasat.get('hellasat_geometry_sentinel',{}).get('source_sha256')==hellasat.get('hellasat_geometry_sentinel',{}).get('output_sha256') and hellasat.get('geometry_status')=='PRESERVED_NATIVE_CANVAS' else 'FAIL','family_id':next((f['family_id'] for f in families if hellasat['stable_identity'] in f['member_identities']),None),'geometry_status':hellasat['geometry_status'],'source_sha256':hellasat['hellasat_geometry_sentinel']['source_sha256'],'output_sha256':hellasat['hellasat_geometry_sentinel']['output_sha256'],'independent_review_reason':safe_component_reason(hellasat)}
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    (OUT/'README.md').write_text(
        '# Auxiliary exception reduction\n\n'
        'Derived from the accepted checkpoint `71957fdfdc2ad7deac4908ae3dff2ee588330b73`. '
        'This is a read-only clustering of its saved report, candidate PNGs and legacy source ZIPs. '
        'No rendering, candidate editing, approval, publication, or engine changes were performed.\n\n'
        f"- Exceptions: {summary['total_exceptions']} (REVIEW {summary['review_identities']}; SOURCE-UNRESOLVED {summary['source_unresolved_identities']})\n"
        f"- Exact reason entries across five inventory fields: {reason_count}\n"
        f"- Review families: {summary['review_families']}\n- Source-unresolved families: {summary['source_unresolved_families']}\n"
        f"- Total human-review families: {summary['total_unique_human_review_families']}\n"
        f"- Reduced sheets: {summary['review_sheet_count']} pages, covering {summary['review_sheet_family_coverage']} representative families\n"
        f"- HARMONIC: {hf['family_id']} ({hf['member_count']} identities)\n- HELLASAT geometry: {summary['hellasat_regression']['result']}\n\n"
        'Files: `reason-inventory.json`, `family-manifest.json`, `identity-family-map.csv`, `duplicate-hash-families.json`, `summary.json`, and `reduced-review-sheets/`.\n'
    )
    print(json.dumps({k:v for k,v in summary.items() if k not in ('review_sheets','category_summary')},ensure_ascii=False,indent=2))
    print('CATEGORY SUMMARY')
    for k,v in sorted(bycat.items()): print(k,v['identities'],v['families'],category_summary[k]['reduction_percent'])

if __name__=='__main__': main()
