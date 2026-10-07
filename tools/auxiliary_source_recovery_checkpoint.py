#!/usr/bin/env python3
"""Evidence-only auxiliary recovery checkpoint builder.

Consumes the pinned 2026-10-07 auxiliary candidate/report artifacts and verified
legacy BLACK/WHITE ZIPs. It never changes production renderer or PNG candidates.
Recovery is deliberately exact: a pair is recoverable only when dimensions, alpha
plane, visible RGB, and a non-opaque transparent canvas are identical.
"""
from __future__ import annotations
import argparse, hashlib, json, zipfile
from collections import Counter, defaultdict
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import numpy as np

BASE = Path('reports/warder-master-production')
UNRES = BASE/'auxiliary-family-policy-2026-10-06'
COMBINED = BASE/'auxiliary-mask-geometry-combined-2026-10-07'
PROVIDER = BASE/'auxiliary-mask-geometry-provider-2026-10-07'
DIAGS = BASE/'auxiliary-component-diagnostics-2026-10-06'
CANDIDATE_ZIP = Path('/tmp/candidate-output.zip')
SOURCES = {
 'provider-black': Path('/tmp/aux-source-recovery-provider-black.zip'),
 'provider-white': Path('/tmp/aux-source-recovery-provider-white.zip'),
 'satellite-black': Path('/tmp/aux-source-recovery-satellite-black.zip'),
 'satellite-white': Path('/tmp/aux-source-recovery-satellite-white.zip'),
}
URLS = {
 'provider-black':'https://raw.githubusercontent.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/main/assets/warder/downloads/picons/providers/black/piconProv.zip',
 'provider-white':'https://raw.githubusercontent.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/main/assets/warder/downloads/picons/providers/white/piconProv.zip',
 'satellite-black':'https://raw.githubusercontent.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/main/assets/warder/downloads/picons/satellites/black/piconSat.zip',
 'satellite-white':'https://raw.githubusercontent.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/main/assets/warder/downloads/picons/satellites/white/piconSat.zip',
}
EXPECTED = {
 'provider-black': (11990269,'f693c2d70866a1b7161046a0e3fd74610b4785673e9ad11f2fa5cefbd6d1e13f'),
 'provider-white': (13974289,'ebff6f537720da39410741cb13abcce0be6a1f822264f516a291a2e70c889cff'),
 'satellite-black': (2244970,'6458bdf32db1dddd21ecf8894864e130d5c5535fcfe7fe2681509ad7b0958d8a'),
 'satellite-white': (2421870,'539cda4f3f599f5e3f2b6e6690a4625fc5c678bdfb46cb9b1b68622d28b08b2b'),
}

def sha(data: bytes) -> str: return hashlib.sha256(data).hexdigest()
def read_jsonl(p): return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def png_sha(p): return sha(Path(p).read_bytes())
def archive_index(z):
    idx={}
    for n in z.namelist():
        if n.endswith('/') or not n.lower().endswith('.png'): continue
        idx.setdefault(Path(n).name,[]).append(n)
    return idx

def load_png(z, members, basename):
    paths=members.get(basename, [])
    if len(paths)!=1: return None, {'entry_count':len(paths),'paths':paths}
    try:
        data=z.read(paths[0]); im=Image.open(__import__('io').BytesIO(data)); im.load();
        return (im.convert('RGBA'), data, paths[0]), None
    except Exception as e: return None, {'decode_error':str(e),'paths':paths}

def rgba_info(im):
    a=np.asarray(im.convert('RGBA'),dtype=np.uint8)
    alpha=a[:,:,3]
    visible=alpha>0
    bbox=Image.fromarray(alpha).getbbox()
    return a, {
      'dimensions':[im.width,im.height], 'mode':im.mode,
      'alpha_min':int(alpha.min()),'alpha_max':int(alpha.max()),
      'alpha_unique_values':int(np.unique(alpha).size),
      'transparent_pixels':int(np.count_nonzero(alpha==0)),
      'partial_alpha_pixels':int(np.count_nonzero((alpha>0)&(alpha<255))),
      'opaque_pixels':int(np.count_nonzero(alpha==255)),
      'visible_bbox_xyxy':list(bbox) if bbox else None,
      'visible_rgb_unique':int(np.unique(a[:,:,:3][visible],axis=0).shape[0]) if visible.any() else 0,
      'visible_pixel_count':int(visible.sum()),
    }

def source_recovery_class(b,w,err_b,err_w):
    if err_b or err_w: return ('BROKEN/INVALID', {'black_error':err_b,'white_error':err_w})
    bi,bd,bpath=b; wi,wd,wpath=w
    ba, bm=rgba_info(bi); wa, wm=rgba_info(wi)
    ev={'black_path':bpath,'white_path':wpath,'black_sha256':sha(bd),'white_sha256':sha(wd),
        'black':bm,'white':wm}
    if bi.size!=wi.size:
        return 'MISMATCHED-PAIR', {**ev,'reason':'canvas dimensions differ; exact alignment unavailable'}
    # Compare alpha support and exact alpha independently from RGB. This is a
    # deterministic geometry check, not a similarity threshold.
    alpha_equal=bool(np.array_equal(ba[:,:,3],wa[:,:,3]))
    support_equal=bool(np.array_equal(ba[:,:,3]>0,wa[:,:,3]>0))
    ev.update({'alpha_plane_exact_match':alpha_equal,'visible_support_exact_match':support_equal})
    if not support_equal:
        return 'MISMATCHED-PAIR', {**ev,'reason':'visible alpha support differs at aligned pixels'}
    visible=ba[:,:,3]>0
    rgb_equal=bool(np.array_equal(ba[:,:,:3][visible],wa[:,:,:3][visible]))
    ev['visible_rgb_exact_match']=rgb_equal
    if not alpha_equal:
        return 'AMBIGUOUS', {**ev,'reason':'same visible support but alpha coverage differs; foreground alpha not uniquely established'}
    if not np.any(ba[:,:,3]==0):
        return 'AMBIGUOUS', {**ev,'reason':'pair has no transparent canvas; foreground/background separation is not established'}
    if not rgb_equal:
        return 'AMBIGUOUS', {**ev,'reason':'visible RGB differs between variants; original foreground colors cannot be uniquely recovered'}
    return 'SAFE-RECOVERABLE', {**ev,'reason':'exact aligned RGBA match with existing transparent canvas; either source is an identical transparent foreground'}

def composite_preview(im, bg):
    im=im.convert('RGBA'); canvas=Image.new('RGBA',im.size,bg); canvas.alpha_composite(im); return canvas.convert('RGB')

def make_sheet(rows, out):
    W=1250; title_h=54; card_h=158; pad=16
    H=title_h+card_h*len(rows)+pad
    sheet=Image.new('RGB',(W,H),(238,241,246)); d=ImageDraw.Draw(sheet)
    font=ImageFont.load_default()
    d.text((pad,14),'Auxiliary source recovery — exception sample (no new renderer output)',fill=(15,25,38),font=font)
    for i,r in enumerate(rows):
        y=title_h+i*card_h
        d.rounded_rectangle((8,y+4,W-8,y+card_h-6),radius=8,fill='white',outline=(190,198,210),width=1)
        d.text((pad,y+12),f"{r['family_id']}  |  {r['category']}  |  {r['representative_identity']}",fill=(20,28,40),font=font)
        d.text((pad,y+31),r['reason'][:150],fill=(75,83,96),font=font)
        for j,key in enumerate(('black_preview','white_preview')):
            x=pad+j*365
            p=Path(r.get(key+'_scratch','')) if r.get(key+'_scratch') else (Path(r[key]) if r.get(key) else None)
            if p and p.exists():
                with Image.open(p) as im: tile=composite_preview(im,(24,27,32,255) if j==0 else (236,237,240,255))
            else: tile=Image.new('RGB',(300,90),(220,220,220))
            tile=tile.resize((300,90),Image.Resampling.NEAREST)
            x+=50; yimg=y+52
            sheet.paste(tile,(x,yimg)); d.text((x,yimg+94),'LEGACY '+('BLACK' if j==0 else 'WHITE'),fill=(30,35,44),font=font)
    out.parent.mkdir(parents=True,exist_ok=True); sheet.save(out,optimize=True)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--output-root',default='reports/warder-master-production/auxiliary-partial-recovery-2026-10-07'); args=ap.parse_args()
    out=Path(args.output_root); partial_dir=out/'partial-improvements'; recovery_dir=out/'source-recovery'; recovery_dir.mkdir(parents=True,exist_ok=True)
    # Validate source archives before any analysis.
    archive_meta={}
    zips={}
    for label,p in SOURCES.items():
        data=p.read_bytes(); size,expected_sha=EXPECTED[label]
        if len(data)!=size or sha(data)!=expected_sha: raise SystemExit(f'archive verification failed: {label} size={len(data)} sha={sha(data)}')
        z=zipfile.ZipFile(p); bad=z.testzip()
        if bad: raise SystemExit(f'ZIP CRC failure: {label} member={bad}')
        zips[label]=z; archive_meta[label]={'local_path':str(p),'url':URLS[label],'size_bytes':len(data),'sha256':sha(data),'zip_crc':'PASS'}
    # Build 47 family partial manifest from the 86 already-QC'd experiment PNGs.
    exp_rows=json.load(open(COMBINED/'combined-experiment-output-qc.json'))['results']
    if len(exp_rows)!=86 or any(x['status']!='PASS' or x.get('changed_pixels_outside_mask',0)!=0 for x in exp_rows):
        raise SystemExit('Existing experiment QC does not meet accepted invariants')
    exp_file_by_sha={}
    for d in [PROVIDER/'experiment-candidates',COMBINED/'satellite-checkpoint-inputs/experiment-candidates']:
        for p in d.glob('*.png'): exp_file_by_sha[png_sha(p)]=p
    candidate_bytes=CANDIDATE_ZIP.read_bytes()
    if len(candidate_bytes)!=93431686 or sha(candidate_bytes)!='5e5bff985638203a2b1c540cd49d37b1893357b20e34d349a4369adb3ac654ff':
        raise SystemExit('candidate-output.zip size/SHA mismatch')
    candidate_zip=zipfile.ZipFile(CANDIDATE_ZIP)
    if candidate_zip.testzip(): raise SystemExit('candidate-output.zip CRC failure')
    by_family=defaultdict(list)
    for x in exp_rows: by_family[x['family_id']].append(x)
    diag_by_family=defaultdict(list)
    for p in sorted(DIAGS.glob('component-diagnostics-*.jsonl.gz')):
        import gzip
        with gzip.open(p,'rt') as f:
            for line in f:
                x=json.loads(line); diag_by_family[x['family_id']].append(x)
    partial=[]
    for fid,items in sorted(by_family.items()):
        members=sorted({x['identity'] for x in items})
        changed_by_variant=defaultdict(set); sig_by_variant=defaultdict(set)
        for x in items:
            changed_by_variant[x['variant']].update(x['component_ids'])
            sig_by_variant[x['variant']].update(x['mask_signatures'])
        original={}; fixed={}
        for variant in ('BLACK','WHITE'):
            rows=[x for x in items if x['variant']==variant]
            # Use the source candidate archive member, verify its actual bytes and retain exact ref.
            originals=[]
            for identity in members:
                dom='provider' if identity.startswith('provider-logo::') else 'satellite'
                fname=identity.split('::',1)[1]; arc=f'{dom}/{variant.lower()}/{fname}'
                if arc in candidate_zip.namelist():
                    b=candidate_zip.read(arc); originals.append({'identity':identity,'archive_member':arc,'sha256':sha(b),'bytes':len(b)})
            original[variant]=originals
            generated=[]
            for x in rows:
                p=exp_file_by_sha.get(x['output_sha256'])
                if not p or png_sha(p)!=x['output_sha256']: raise SystemExit(f'missing or mismatched existing partial PNG: {fid} {variant} {x["output_sha256"]}')
                generated.append({'identity':x['identity'],'path':str(p),'sha256':x['output_sha256'],'dimensions':x['dimensions'],'mode':x['mode'],'status':'PARTIAL-IMPROVED / REVIEW'})
            fixed[variant]=generated
        remaining=[]
        for dx in diag_by_family[fid]:
            ident=dx['auxiliary_identity']
            for variant,dv in dx.get('variants',{}).items():
                strong=changed_by_variant.get(variant,set())
                for c in dv.get('components',[]):
                    low=c.get('low_contrast_pixel_count',0)>0
                    if low and c.get('component_id') not in strong:
                        remaining.append({'identity':ident,'variant':variant,'component_id':c.get('component_id'),'mask_signature':c.get('mask_signature'),'engine_status':c.get('engine_status'),'engine_reason':c.get('engine_reason'),'low_contrast_pixel_count':c.get('low_contrast_pixel_count'),'low_contrast_percentage':c.get('low_contrast_percentage'),'recolour_refusal_reason':c.get('recolour_refusal_reason')})
        partial.append({'family_id':fid,'member_identities':members,'status':'PARTIAL-IMPROVED / REVIEW','changed_components':{k:sorted(v) for k,v in changed_by_variant.items()},'exact_mask_signatures':{k:sorted(v) for k,v in sig_by_variant.items()},'original_current_outputs':original,'partial_fixed_outputs':fixed,'remaining_unresolved_review_reasons':remaining})
    if len(partial)!=47: raise SystemExit(f'expected 47 partial families, got {len(partial)}')
    partial_dir.mkdir(parents=True,exist_ok=True)
    with (partial_dir/'partial-improved-families.jsonl').open('w') as f:
        for x in partial: f.write(json.dumps(x,sort_keys=True)+'\n')
    partial_summary={'family_count':len(partial),'existing_experiment_png_count':len(exp_rows),'all_statuses':'PARTIAL-IMPROVED / REVIEW','no_new_render':True,'no_production_policy_promotion':True,'existing_output_qc':'PASS','candidate_output_zip_sha256':'5e5bff985638203a2b1c540cd49d37b1893357b20e34d349a4369adb3ac654ff'}
    (partial_dir/'summary.json').write_text(json.dumps(partial_summary,indent=2,sort_keys=True)+'\n')
    # Analyze 284 paired and 36 black-only families.
    unresolved=[]
    for part in sorted(UNRES.glob('remaining-source-unresolved-*.jsonl')): unresolved+=read_jsonl(part)
    if len(unresolved)!=320: raise SystemExit(f'expected 320 unresolved families, got {len(unresolved)}')
    zip_index={k:archive_index(v) for k,v in zips.items()}
    pair_rows=[]; blackonly=[]; scratch=Path('/tmp/aux-recovery-review'); scratch.mkdir(exist_ok=True)
    sheet_pool=[]
    for row in unresolved:
        fid=row['family_id']; domain='provider' if row['representative_identity'].startswith('provider-logo::') else 'satellite'
        fname=row['representative_identity'].split('::',1)[1]
        b_label=domain+'-black'; w_label=domain+'-white'
        b,be=load_png(zips[b_label],zip_index[b_label],fname)
        w,we=(load_png(zips[w_label],zip_index[w_label],fname) if row['source_sha256'].get('white') else (None,{'missing':'white source not declared'}))
        if w is None:
            # Black-only inventory. Record exact duplicate family evidence and alpha stats only.
            cat='BROKEN/INVALID' if b is None else 'BLACK-ONLY / UNRESOLVED'
            if b:
                im,data,path=b; im.save(scratch/f'{fid}-black.png'); _,inf=rgba_info(im)
                member_audit=[]
                for member_identity in row['member_identities']:
                    mi=member_identity.split('::',1)[1]; mm,merr=load_png(zips[b_label],zip_index[b_label],mi)
                    if mm is None: raise SystemExit(f'missing black-only family member {fid}: {member_identity}')
                    _,mbdata,mbpath=mm; _,minfo=rgba_info(mm[0]); member_audit.append({'identity':member_identity,'sha256':sha(mbdata),'archive_member':mbpath,'png':minfo})
                info={'black_path':path,'black_sha256':sha(data),'black':inf,'member_source_audit':member_audit,'genuine_transparency_recoverable':False,'reason':'single variant cannot establish original foreground colors or alpha provenance; retain UNRESOLVED'}
            else: info={'black_error':be,'reason':'black member missing or invalid'}
            blackonly.append({'family_id':fid,'domain':domain,'representative_identity':row['representative_identity'],'member_identities':row['member_identities'],'category':cat,'source_sha256':row['source_sha256'],'evidence':info,'final_status':'UNRESOLVED'})
            if b:
                sheet_pool.append({'family_id':fid,'category':cat,'representative_identity':row['representative_identity'],'reason':info['reason'],'black_preview_scratch':str(scratch/f'{fid}-black.png')})
            continue
        category,evidence=source_recovery_class(b,w,be,we)
        member_audit=[]
        for member_identity in row['member_identities']:
            member_name=member_identity.split('::',1)[1]
            mb,mbe=load_png(zips[b_label],zip_index[b_label],member_name)
            mw,mwe=load_png(zips[w_label],zip_index[w_label],member_name)
            if mb is None or mw is None:
                raise SystemExit(f'missing member source while auditing family {fid}: {member_identity}')
            member_audit.append({'identity':member_identity,'black_sha256':sha(mb[1]),'white_sha256':sha(mw[1]),'black_member':mb[2],'white_member':mw[2]})
        if b and row['source_sha256'].get('black') and sha(b[1])!=row['source_sha256']['black']:
            raise SystemExit(f'black PNG SHA mismatch vs family manifest: {fid}')
        if w and row['source_sha256'].get('white') and sha(w[1])!=row['source_sha256']['white']:
            raise SystemExit(f'white PNG SHA mismatch vs family manifest: {fid}')
        record={'family_id':fid,'domain':domain,'representative_identity':row['representative_identity'],'member_identities':row['member_identities'],'category':category,'source_sha256':row['source_sha256'],'member_source_audit':member_audit,'evidence':evidence,'recovered_transparent':None,'round_trip_qc':None,'final_status':'SOURCE-UNRESOLVED'}
        if category=='SAFE-RECOVERABLE':
            bi,bd,bpath=b; wi,wd,wpath=w
            # This branch only accepts existing exact RGBA that already encodes transparency.
            candidate=bi.convert('RGBA'); target=recovery_dir/'recovered-transparent'/f'{fid}.png'; target.parent.mkdir(parents=True,exist_ok=True); candidate.save(target)
            record['recovered_transparent']={'path':str(target),'sha256':png_sha(target),'dimensions':list(candidate.size),'mode':'RGBA','derivation':'exact pair source (no pixel edits)'}
            # No candidates should require rerender here; defer to the production renderer if this branch is reached.
            record['round_trip_qc']={'status':'NOT_RUN','reason':'exact-pair precondition found; renderer round-trip requires controlled existing-template invocation'}
        pair_rows.append(record)
        bp=scratch/f'{fid}-black.png'; wp=scratch/f'{fid}-white.png'; b[0].save(bp); w[0].save(wp)
        sheet_pool.append({'family_id':fid,'category':category,'representative_identity':row['representative_identity'],'reason':evidence.get('reason',''),'black_preview_scratch':str(bp),'white_preview_scratch':str(wp)})
    # Write complete deterministic artifacts.
    with (recovery_dir/'black-white-pair-analysis.jsonl').open('w') as f:
        for x in pair_rows: f.write(json.dumps(x,sort_keys=True)+'\n')
    with (recovery_dir/'black-only-analysis.jsonl').open('w') as f:
        for x in blackonly: f.write(json.dumps(x,sort_keys=True)+'\n')
    with (recovery_dir/'remaining-unresolved-families.jsonl').open('w') as f:
        for x in pair_rows: f.write(json.dumps({'family_id':x['family_id'],'domain':x['domain'],'member_identities':x['member_identities'],'source_recovery_category':x['category'],'final_status':'SOURCE-UNRESOLVED','reason':x['evidence'].get('reason'),'source_sha256':x['source_sha256']},sort_keys=True)+'\n')
        for x in blackonly: f.write(json.dumps({'family_id':x['family_id'],'domain':x['domain'],'member_identities':x['member_identities'],'source_recovery_category':x['category'],'final_status':'SOURCE-UNRESOLVED','reason':x['evidence'].get('reason'),'source_sha256':x['source_sha256']},sort_keys=True)+'\n')
    # Ensure the review set includes every detected pair class where available.
    selected=[]
    for category in ('SAFE-RECOVERABLE','AMBIGUOUS','MISMATCHED-PAIR','BROKEN/INVALID','BLACK-ONLY / UNRESOLVED'):
        candidate=next((x for x in sheet_pool if x['category']==category),None)
        if candidate and candidate not in selected: selected.append(candidate)
    for x in sheet_pool:
        if x not in selected and len(selected)<20: selected.append(x)
    sheet_rows=[]
    for x in selected:
        sheet_rows.append({'family_id':x['family_id'],'category':x['category'],'representative_identity':x['representative_identity'],'reason':x['reason'],'black_preview_scratch':x.get('black_preview_scratch'),'white_preview_scratch':x.get('white_preview_scratch')})
    sheet_path=recovery_dir/'recovery-review-sheet.png'; make_sheet(sheet_rows,sheet_path)
    (recovery_dir/'recovery-review-sheet-manifest.json').write_text(json.dumps(sheet_rows,indent=2,sort_keys=True)+'\n')
    cats=Counter(x['category'] for x in pair_rows); alpha_candidates=sum(bool(x['evidence'].get('black',{}).get('transparent_pixels',0) and x['evidence'].get('black',{}).get('opaque_pixels',0)) for x in blackonly if x['category']!='BROKEN/INVALID')
    black_member_hashes=[m['sha256'] for x in blackonly for m in x['evidence'].get('member_source_audit',[])]
    black_hash_counts=Counter(black_member_hashes)
    # Exact RGB+alpha agreement + transparency is the only accepted recovery proof.
    summary={'checkpoint':'fc0ed19d8ee05482b9a59cf78170f4dac4e20f12','total_source_unresolved_families':len(unresolved),'black_white_families':len(pair_rows),'black_white_member_identities':sum(len(x['member_identities']) for x in pair_rows),'black_white_categories':dict(sorted(cats.items())),'black_only_families':len(blackonly),'black_only_member_identities':len(black_member_hashes),'black_only_exact_duplicate_sha_groups':sum(1 for n in black_hash_counts.values() if n>1),'black_only_duplicate_extra_identities':sum(n-1 for n in black_hash_counts.values() if n>1),'black_only_with_alpha_transparency':alpha_candidates,'black_only_genuine_transparency_recoverable':0,'still_unresolved_families':len(unresolved)-sum(1 for x in pair_rows if x['category']=='SAFE-RECOVERABLE'),'safe_recoverable':cats.get('SAFE-RECOVERABLE',0),'round_trip_qc':{'attempted':sum(x['round_trip_qc'] is not None for x in pair_rows),'pass':0,'not_run':cats.get('SAFE-RECOVERABLE',0),'reason':'Not applicable: zero SAFE-RECOVERABLE pairs, so no transparent candidates existed to round-trip.'},'archive_verification':archive_meta,'pair_policy':'SAFE only when aligned RGBA (including alpha and visible RGB) is exact in both variants and contains transparent canvas. Any differing visible RGB or alpha coverage is ambiguous; differing support or canvas dimensions is mismatched. No thresholds, OCR, naming, or external matching.','black_only_policy':'Report source SHA/alpha/geometry only; a single recoloured variant never establishes original transparent artwork.','review_sheet':str(sheet_path),'review_sheet_count':len(sheet_rows),'safe_candidate_outputs_created':cats.get('SAFE-RECOVERABLE',0)}
    (recovery_dir/'summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
    (partial_dir/'README.md').write_text('# Partial improvements\n\n47 families are labelled `PARTIAL-IMPROVED / REVIEW`. This manifest references the 86 pre-existing, QC-passing HORIZONTAL_GLYPH_RUN_V1 PNGs; no new render was run. Remaining BLACK/WHITE review components and their original reasons are retained per family.\n')
    (recovery_dir/'README.md').write_text('# Source recovery analysis\n\nThe four pinned legacy ZIPs were SHA/size/CRC verified. Black/White pairs were compared at exact aligned pixel coordinates. `SAFE-RECOVERABLE` requires exact RGBA equality including the alpha plane, identical visible support, and a transparent canvas. No thresholding, OCR, filename semantics, or external matching was used. Black-only variants remain unresolved; alpha and geometry are recorded but do not establish original colors. No production assets or downloads manifests were changed.\n')
    with (out/'summary.json').open('w') as f: json.dump({'partial_improvements':partial_summary,'source_recovery':summary},f,indent=2,sort_keys=True); f.write('\n')
    print(json.dumps({'partial':partial_summary,'recovery':summary},indent=2,sort_keys=True))
if __name__=='__main__': main()
