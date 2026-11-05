"""Acquire untried catalogue-supplied artwork; reuse only an exact approved graphic/identity match."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
import argparse,base64,gzip,json,io,re,subprocess,time
from radio_source_helpers import fetch,dump,SHA,norm,push_checkpoint

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--seed',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--workers',type=int,default=32);ap.add_argument('--checkpoint-size',type=int,default=100);ap.add_argument('--commit',action='store_true');args=ap.parse_args();assert 1<=args.workers<=32
 raw=gzip.decompress(base64.b64decode(args.seed.read_bytes()));seed=json.loads(raw);root=args.output;root.mkdir(parents=True,exist_ok=True);state_path=root/'discovery-state.json';state=json.loads(state_path.read_text()) if state_path.exists() else {'schema':1,'project':'Radio plugin','input_sha256':SHA(raw),'production_changed':False,'stations':{}}
 assert state['input_sha256']==SHA(raw)
 done=set(seed['ready_references']);reviewed=set(seed['reviewed_source_hashes']);cache=seed['approved_graphics'];queue=[]
 for r in seed['queue']:
  if r['reference'] in done:continue
  prior=state['stations'].get(r['reference'])
  if prior and prior['status'] in ('reuse_verified_graphic_pending_import','candidate_catalogue_artwork_needs_visual_identity','blocked_no_new_usable_catalogue_artwork'):continue
  queue.append(r);state['stations'][r['reference']]=dict(r,status='pending_catalogue_artwork')
 def acquire(row):
  row=dict(row);errors=[]
  for url in row['favicon_urls']:
   try:
    body,final=fetch(url);digest=SHA(body);identity=digest+'|'+row['country']+'|'+norm(row['name']);reuse=cache.get(identity)
    if digest in reviewed and not reuse:continue
    rasterized=None
    if b'<svg' in body[:2000].lower():
     svg=body.decode('utf-8',errors='strict')
     if re.search(r'<(?:image|script)\b|(?:href|xlink:href)\s*=\s*["\x27](?!#)',svg,re.I):raise ValueError('SVG contains resources requiring separate verification')
     if any(not u.strip().strip('"\x27').startswith('#') for u in re.findall(r'url\(([^)]+)\)',svg,re.I)):raise ValueError('SVG resource URL requires separate verification')
     import cairosvg
     rasterized=cairosvg.svg2png(bytestring=body,output_width=640,unsafe=False);im=Image.open(io.BytesIO(rasterized))
    else:im=Image.open(io.BytesIO(body))
    if im.width<96 or im.height<48 or max(im.size)>8192 or im.width*im.height>16000000:continue
    im.load();rgba=im.convert('RGBA')
    if not rgba.getchannel('A').getbbox():continue
    path=root/'originals'/(digest+'.img');path.parent.mkdir(exist_ok=True);path.write_bytes(body);source=dict(url=url,final_url=final,path=str(path.relative_to(root)),sha256=digest,bytes=len(body),dimensions=list(im.size),format='SVG' if rasterized else im.format)
    if rasterized:
     p=root/'rasterized'/(SHA(rasterized)+'.png');p.parent.mkdir(exist_ok=True);p.write_bytes(rasterized);source['frozen_svg_raster']=dict(path=str(p.relative_to(root)),sha256=SHA(rasterized),cairosvg_version=cairosvg.__version__)
    evidence=dict(catalogue_snapshot=seed['catalogue_snapshot'],catalogue_station_id=row['station_id'],exact_receiver_reference=row['reference'],exact_receiver_stream=row['url'],catalogue_supplied_image_url=url,current_homepage_not_confirmed=True)
    
    if row.get('metadata_refresh_evidence_by_url'):
     evidence.pop('catalogue_supplied_image_url');evidence.update(row['metadata_refresh_evidence_by_url'][url])
    row.update(source=source,catalogue_evidence=evidence)
    if reuse:row.update(status='reuse_verified_graphic_pending_import',approved_graphic_reference=reuse['reference'],expected_render_fingerprint=reuse['render_fingerprint'],verification='Exact source SHA256, full normalized receiver name and catalogue country match an already saved approved graphic. Import must verify and copy the original nine saved PNG bytes; no new programme alias is inferred.')
    else:row.update(status='candidate_catalogue_artwork_needs_visual_identity',verification=('New image URL returned by the original source UUID after exact name, country and stream checks.' if row.get('metadata_refresh_evidence_by_url') else 'Image URL supplied by the uniquely matched frozen catalogue programme; recovered after an earlier transient network failure.')+' Visual identity still requires review; no confirmed current homepage is claimed.')
    return row
   except Exception as e:errors.append(str(e)[:160])
  row.update(status='blocked_no_new_usable_catalogue_artwork',errors=errors);return row
 def checkpoint(event):
  counts={v:sum(r['status']==v for r in state['stations'].values()) for v in sorted({r['status'] for r in state['stations'].values()})};state.update(counts=counts,last_event=event,updated_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()));dump(state_path,state)
  dump(root/'reuse-ready.json',[r for r in state['stations'].values() if r['status']=='reuse_verified_graphic_pending_import'])
  with (root/'discovery-journal.jsonl').open('a') as f:f.write(json.dumps({'event':event,'time':state['updated_utc'],'counts':counts})+'\n')
  print(event,counts,flush=True)
  if args.commit:
   subprocess.run(['git','add','--',str(root)],check=True)
   if subprocess.run(['git','diff','--cached','--quiet']).returncode:subprocess.run(['git','commit','--quiet','-m','Save catalogue-provided Radio artwork: '+event],check=True);push_checkpoint()
 checkpoint('catalogue_artwork_recovery_started')
 for offset in range(0,len(queue),args.checkpoint_size):
  with ThreadPoolExecutor(args.workers) as pool:
   for row in pool.map(acquire,queue[offset:offset+args.checkpoint_size]):state['stations'][row['reference']]=row
  checkpoint(f'artwork_{min(offset+args.checkpoint_size,len(queue))}_of_{len(queue)}')
 checkpoint('catalogue_artwork_recovery_complete_with_explicit_unresolved_items')
if __name__=='__main__':main()
