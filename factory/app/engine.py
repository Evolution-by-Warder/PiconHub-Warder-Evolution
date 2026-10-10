import os, sys, sqlite3, hashlib, zipfile, shutil, threading, queue, json, time, traceback, urllib.request, urllib.error, tempfile, io
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
import multiprocessing
from collections import Counter
from hardening import import_png_zip
from identity_audit import audit_collision_records
from review_queue import build_review_queue, save_review_queue
from review_decisions import apply_decisions
from artifact_audit import audit_artifacts
from empty_source_resolution import empty_source_report, build_empty_source_exclusion
from qa_diagnostics import summarize
from source_registry import atomic_json
from report_housekeeping import cleanup_reports
from work_housekeeping import cleanup_interrupted_renders
from factory_update import check_factory_release
from master_registry import index_master_tree, classify_candidate, is_master_path

_DEFAULT_ROOT = 'D:/WARDER-PICON-FACTORY' if os.name == 'nt' else str(Path.home()/'WARDER-PICONS')
ROOT=Path(os.environ.get('WARDER_PICON_FACTORY_ROOT', _DEFAULT_ROOT)).expanduser()
APP=ROOT/'11-APP'/'WARDER-PICON-FACTORY'
DATA=ROOT/'11-APP'/'.factory-data'
INBOX=ROOT/'01-SOURCES'/'LOCAL-INBOX'
ORIGINALS=ROOT/'02-ORIGINALS'
OUTPUT=ROOT/'04-WORK'/'PICONS'
FINAL_PICONS=ROOT/'06-OUTPUT'/'PICONS'
EXCEPTIONS=ROOT/'05-QA'/'EXCEPTIONS'
REPORTS=ROOT/'08-REPORTS'
DB=DATA/'factory.sqlite3'
SOURCE_STATE=DATA/'sources.json'
SOURCE_MANIFEST=DATA/'source-manifest.json'
SOURCE_INGEST=DATA/'source-ingest'
# Only a known official Warder repository is enabled. No unverified third-party endpoints.
SOURCES=[('PiconHub-Warder-Evolution','https://api.github.com/repos/Evolution-by-Warder/PiconHub-Warder-Evolution/zipball/warder-master-production')]
MAX_DOWNLOAD=450_000_000
try:
 from PIL import Image, ImageOps
 PIL_OK=True
except ImportError:
 PIL_OK=False

def _contrast_variant_art(rgba, background):
 """Contrast neutral ink without recoloring lettering inside colored badges.

 Connected chromatic plate regions protect their entire bounding rectangle,
 including white counters and lettering separated from the colored pixels.
 """
 from PIL import Image
 if background not in ('white', 'black'):
  return rgba
 width,height=rgba.size
 pixels=list(rgba.getdata())
 colored=[a>=128 and max(r,g,b)-min(r,g,b)>=65 for r,g,b,a in pixels]
 protected=bytearray(width*height)
 seen=bytearray(width*height)
 for start in range(len(pixels)):
  if not colored[start] or seen[start]:
   continue
  seen[start]=1
  stack=[start]
  size=0
  left=right=start%width
  top=bottom=start//width
  while stack:
   pos=stack.pop()
   size+=1
   x,y=pos%width,pos//width
   left=min(left,x);right=max(right,x)
   top=min(top,y);bottom=max(bottom,y)
   for nx,ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
    if 0<=nx<width and 0<=ny<height:
     idx=ny*width+nx
     if colored[idx] and not seen[idx]:
      seen[idx]=1
      stack.append(idx)
  if size>=20 and right-left>=5 and bottom-top>=5:
   for y in range(top,bottom+1):
    protected[y*width+left:y*width+right+1]=bytes([1])*(right-left+1)
 # Protect entire white plaques on BOTH templates.  Their black lettering and
 # white matte are one artwork element; changing either destroys the logo.
 white=[a>=240 and min(r,g,b)>=235 for r,g,b,a in pixels]
 visited=bytearray(width*height)
 for start in range(len(pixels)):
  if not white[start] or visited[start]:
   continue
  visited[start]=1
  stack=[start]
  size=0
  left=right=start%width
  top=bottom=start//width
  while stack:
   pos=stack.pop()
   size+=1
   x,y=pos%width,pos//width
   left=min(left,x);right=max(right,x)
   top=min(top,y);bottom=max(bottom,y)
   for nx,ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
    if 0<=nx<width and 0<=ny<height:
     idx=ny*width+nx
     if white[idx] and not visited[idx]:
      visited[idx]=1
      stack.append(idx)
  # A white connected area is a plaque only when it encloses opaque
  # non-white artwork (e.g. black lettering). A plain white word is ink.
  enclosed_ink=False
  if size>=80 and right-left>=15 and bottom-top>=12:
   for yy in range(top,bottom+1):
    for xx in range(left,right+1):
     rr,gg,bb,aa=pixels[yy*width+xx]
     if aa>=128 and not white[yy*width+xx] and max(rr,gg,bb)<=185:
      enclosed_ink=True
      break
    if enclosed_ink:break
  if enclosed_ink:
   for y in range(top,bottom+1):
    protected[y*width+left:y*width+right+1]=bytes([1])*(right-left+1)
 result=list(pixels)
 changed=False
 ink=(30,30,30) if background=='white' else (238,238,238)
 for i,(r,g,b,a) in enumerate(pixels):
  if protected[i] or a<96 or max(r,g,b)-min(r,g,b)>35:
   continue
  low=(min(r,g,b)>=135) if background=='white' else (max(r,g,b)<=145)
  if low:
   result[i]=(*ink,a)
   changed=True
 if not changed:
  return rgba
 out=Image.new('RGBA',rgba.size)
 out.putdata(result)
 return out

def _adjust_low_contrast_color(rgba, background):
 """Adjust only isolated low-contrast chromatic ink, never colored plates.

 Large connected color fields and their enclosed lettering are brand artwork;
 recoloring individual pixels in those fields produces broken lettering.
 """
 from PIL import Image
 import colorsys
 if background not in ('white','black'):
  return rgba
 w,h=rgba.size
 pixels=list(rgba.getdata())
 chromatic=[a>=96 and max(r,g,b)-min(r,g,b)>=35 for r,g,b,a in pixels]
 visited=bytearray(len(pixels))
 protected=bytearray(len(pixels))
 for start in range(len(pixels)):
  if not chromatic[start] or visited[start]:
   continue
  stack=[start]
  visited[start]=1
  group=[]
  left=right=start%w
  top=bottom=start//w
  while stack:
   pos=stack.pop()
   group.append(pos)
   x,y=pos%w,pos//w
   left=min(left,x);right=max(right,x)
   top=min(top,y);bottom=max(bottom,y)
   for nx,ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
    if 0<=nx<w and 0<=ny<h:
     idx=ny*w+nx
     if chromatic[idx] and not visited[idx]:
      visited[idx]=1
      stack.append(idx)
  # Preserve substantial color plates, including lettering within their bounds.
  if len(group)>=100 and right-left>=10 and bottom-top>=8:
   for y in range(top,bottom+1):
    protected[y*w+left:y*w+right+1]=bytes([1])*(right-left+1)
 out=list(pixels)
 changed=False
 for i,(r,g,b,a) in enumerate(pixels):
  if protected[i] or not chromatic[i]:
   continue
  hue,saturation,value=colorsys.rgb_to_hsv(r/255,g/255,b/255)
  if saturation<0.32:
   continue
  luminance=(0.2126*r+0.7152*g+0.0722*b)/255
  if background=='white':
   if luminance<=0.70:
    continue
   target=min(value,value*0.57/max(luminance,0.01))
  else:
   if luminance>=0.18:
    continue
   target=min(1.0,value*0.36/max(luminance,0.03))
  nr,ng,nb=colorsys.hsv_to_rgb(hue,saturation,target)
  out[i]=(round(nr*255),round(ng*255),round(nb*255),a)
  changed=True
 if not changed:
  return rgba
 result=Image.new('RGBA',rgba.size)
 result.putdata(out)
 return result

def _outlined_variant(rgba, background, radius=2):
 """Contrast stroke behind mixed-colour artwork; never changes source pixels."""
 from PIL import Image, ImageFilter, ImageChops
 if background not in ('white','black'):
  return rgba
 alpha=rgba.getchannel('A')
 # A two-pixel outside stroke, clipped by the canvas; keep original alpha/RGB.
 expanded=alpha.filter(ImageFilter.MaxFilter(2*radius+1))
 ring=ImageChops.subtract(expanded,alpha)
 stroke=Image.new('RGBA',rgba.size,(22,22,22,0) if background=='white' else (242,242,242,0))
 stroke.putalpha(ring)
 stroke.alpha_composite(rgba)
 return stroke

def _has_contrast_outline(transparent, variant, background):
 """Only accept a visible contrasting ring outside the original alpha."""
 from PIL import ImageFilter, ImageChops
 alpha=transparent.getchannel('A')
 ring=ImageChops.subtract(alpha.filter(ImageFilter.MaxFilter(5)),alpha)
 points=list(ring.getdata())
 colors=list(variant.convert('RGB').getdata())
 active=[i for i,a in enumerate(points) if a>=128]
 if len(active)<20:return False
 if background=='white':
  return sum(max(colors[i])<=90 for i in active)/len(active)>=0.75
 return sum(min(colors[i])>=165 for i in active)/len(active)>=0.75

def _selective_light_stroke(rgba, background):
 """Outline only pale/dark lettering in multicolour logos; preserve red/blue art."""
 from PIL import Image, ImageFilter, ImageChops
 if background not in ('white','black'):
  return rgba
 pixels=list(rgba.getdata())
 if background=='white':
  selected=[a if min(r,g,b)>=210 and max(r,g,b)-min(r,g,b)<=30 else 0
            for r,g,b,a in pixels]
  ink=(24,24,24,0)
 else:
  selected=[a if (0.2126*r+0.7152*g+0.0722*b)<=85 else 0
            for r,g,b,a in pixels]
  ink=(242,242,242,0)
 if sum(v>=128 for v in selected)<20:
  return rgba
 mask=Image.new('L',rgba.size)
 mask.putdata(selected)
 # Stroke only outside the full artwork alpha: no destruction of colored pixels.
 ring=ImageChops.subtract(mask.filter(ImageFilter.MaxFilter(5)),rgba.getchannel('A'))
 if ring.getbbox() is None:
  return rgba
 stroke=Image.new('RGBA',rgba.size,ink)
 stroke.putalpha(ring)
 stroke.alpha_composite(rgba)
 return stroke

def _compose_variant(rgba, background):
 from PIL import Image
 if background=='transparent':
  return rgba
 template=Path(__file__).resolve().parent/'templates'/'picons'/(background+'-sablona.png')
 if not template.is_file():
  raise FileNotFoundError('Chýba originálna WARDER šablóna: '+str(template))
 with Image.open(template) as source:
  source.load()
  if source.size!=(220,132):
   raise ValueError('Nesprávne rozmery WARDER šablóny')
  canvas=source.convert('RGBA')
  canvas.putalpha(255)  # WARDER output variants must be opaque
 # Preserve already-legible brand colors; no unconditional stroke.
 art=_adjust_low_contrast_color(_contrast_variant_art(rgba,background),background)
 # Last resort: outline only remaining neutral, low-contrast pixels.
 # Never stroke all alpha or recolor brand-color regions.
 if background in ('white','black'):
  from PIL import Image, ImageFilter, ImageChops
  px=list(art.getdata())
  selected=[]
  for r,g,b,a in px:
   neutral=max(r,g,b)-min(r,g,b)<=22
   low=(min(r,g,b)>=205) if background=='white' else (max(r,g,b)<=72)
   selected.append(a if neutral and low else 0)
  if sum(a>=128 for a in selected)>=12:
   mask=Image.new('L',art.size)
   mask.putdata(selected)
   # One-pixel ring, excluding every original artwork pixel.
   ring=ImageChops.subtract(mask.filter(ImageFilter.MaxFilter(3)),art.getchannel('A'))
   if ring.getbbox():
    stroke=Image.new('RGBA',art.size,(26,26,26,0) if background=='white' else (240,240,240,0))
    stroke.putalpha(ring)
    stroke.alpha_composite(art)
    art=stroke
 canvas.alpha_composite(art)
 return canvas

RENDER_REVISION = "plate-aware-v15"

def render_png_task(args):
 # Independent process: Pillow decoding and PNG encoding use multiple CPU cores.
 path, output_dir, sha = args
 try:
  with Image.open(path) as im:
   im.verify()
  with Image.open(path) as im:
   if not (1 <= im.width <= 4096 and 1 <= im.height <= 4096):
    raise ValueError('Neštandardné rozmery')
   from artwork_preparation import extract_flat_edge_background
   raw=im.convert('RGBA')
   clean,extracted=extract_flat_edge_background(raw)
   rgba=_fit_canvas(clean)
  dest=Path(output_dir)/sha[:2]/sha
  dest.mkdir(parents=True,exist_ok=True)
  created=0
  for bgname,bg in [('transparent',None),('black',(0,0,0,255)),('white',(255,255,255,255))]:
   out=dest/(bgname+'.png')
   signature=dest/(bgname+'.template-sha256')
   revision_marker=dest/(bgname+'.render-revision')
   expected=None
   if bgname!='transparent':
    template=Path(__file__).resolve().parent/'templates'/'picons'/(bgname+'-sablona.png')
    expected=hashlib.sha256(template.read_bytes()).hexdigest()
   if out.exists() and (bgname=='transparent' or (revision_marker.is_file() and revision_marker.read_text(encoding='ascii').strip()==RENDER_REVISION)) and (expected is None or (signature.exists() and signature.read_text(encoding='ascii')==expected)):
    try:
     with Image.open(out) as existing:
      existing.verify()
     with Image.open(out) as existing:
      if existing.size == (220,132) and existing.mode == 'RGBA':
       continue
    except Exception: pass
   render=_compose_variant(_fit_canvas(raw) if bgname=='transparent' else rgba,bgname)
   tmp=out.with_name(out.name+'.'+str(os.getpid())+'.partial')
   try:
    render.save(tmp,format='PNG',compress_level=3)
    os.replace(tmp,out)
    if expected is not None:
     sig_tmp=signature.with_suffix('.partial')
     sig_tmp.write_text(expected,encoding='ascii')
     os.replace(sig_tmp,signature)
    rev_tmp=revision_marker.with_name(revision_marker.name+'.'+str(os.getpid())+'.partial')
    rev_tmp.write_text(RENDER_REVISION,encoding='ascii')
    os.replace(rev_tmp,revision_marker)
    created+=1
   finally:
    if tmp.exists():tmp.unlink()
  return (True,created,'')
 except Exception as e:
  return (False,0,str(e))

def _fit_canvas(rgba):
 """Center visible artwork in the plastic template safe area without distortion.

 Transparent input remains the reference artwork; derivative layout is based on
 the actual non-transparent bounds rather than source-image whitespace.
 """
 from PIL import Image
 rgba=rgba.convert('RGBA')
 bbox=rgba.getchannel('A').getbbox()
 canvas=Image.new('RGBA',(220,132),(0,0,0,0))
 if bbox is None:
  return canvas
 art=rgba.crop(bbox)
 safe_width,safe_height=196,108  # 12px horizontal and vertical padding
 scale=min(safe_width/art.width,safe_height/art.height,1.0 if rgba.size==(220,132) else float('inf'))
 size=(max(1,round(art.width*scale)),max(1,round(art.height*scale)))
 if art.size!=size:
  art=art.resize(size,Image.Resampling.LANCZOS)
 canvas.alpha_composite(art,((220-art.width)//2,(132-art.height)//2))
 return canvas

def _output_signature(sha):
 """Return cache signature only for outputs tied to CURRENT plastic templates.

 An old flat render or missing signature must never count as an unchanged
 output, even when the source PNG itself has not changed.
 """
 folder=OUTPUT/sha[:2]/sha
 result={}
 try:
  for name in ('transparent','black','white'):
   path=folder/(name+'.png')
   if not path.is_file():return None
   revision_marker=folder/(name+'.render-revision')
   if name!='transparent' and (not revision_marker.is_file() or revision_marker.read_text(encoding='ascii').strip()!=RENDER_REVISION):return None
   from PIL import Image as _Image
   with _Image.open(path) as _cached:
    _cached.verify()
   with _Image.open(path) as _cached:
    if _cached.size != (220,132) or _cached.mode != 'RGBA':return None
   st=path.stat()
   if st.st_size<=0:return None
   if name!='transparent':
    template=Path(__file__).resolve().parent/'templates'/'picons'/(name+'-sablona.png')
    expected=hashlib.sha256(template.read_bytes()).hexdigest()
    marker=folder/(name+'.template-sha256')
    if not marker.is_file() or marker.read_text(encoding='ascii').strip()!=expected:
     return None
    result[name+'_template_sha256']=expected
   result[name]=[st.st_size,st.st_mtime_ns]
  return result
 except (OSError,UnicodeError,ValueError):
  return None

def qa_png_task(args):
 """Read-only image QA. Never rewrites approved or existing variants."""
 sha, output_dir = args
 folder=Path(output_dir)/sha[:2]/sha
 try:
  from PIL import Image, ImageStat
  paths={name:folder/(name+'.png') for name in ('transparent','black','white')}
  issues=[]
  images={}
  for name,path in paths.items():
   if not path.is_file():
    issues.append('MISSING_'+name.upper());continue
   try:
    with Image.open(path) as im:
     im.load()
     if im.width!=220 or im.height!=132:
      issues.append('DIMENSIONS_'+name.upper())
     images[name]=im.convert('RGBA')
   except Exception:
    issues.append('CORRUPT_'+name.upper())
  if len(images)==3:
   dims={im.size for im in images.values()}
   if len(dims)!=1:issues.append('VARIANT_SIZE_MISMATCH')
   transparent=images['transparent']
   alpha=transparent.getchannel('A')
   bounds=alpha.getbbox()
   if not bounds:issues.append('FULLY_TRANSPARENT')
   else:
    import PIL.ImageChops as ImageChops
    # Check how many foreground pixels disappear on white/black background.
    # Pixel-level visibility only; not semantic logo legibility.
    a=transparent.getchannel('A')
    fg=transparent.convert('RGB')
    from PIL import Image as PImage
    # Downsample for speed; count pixels that differ visibly from each background.
    sample=transparent.copy()
    sample.thumbnail((256,256))
    rgba=list(sample.getdata())
    visible=sum(1 for r,g,b,al in rgba if al>=128)
    if visible>=20:
     nearwhite=sum(1 for r,g,b,al in rgba if al>=128 and min(r,g,b)>=238)
     nearblack=sum(1 for r,g,b,al in rgba if al>=128 and max(r,g,b)<=17)
     if nearwhite/visible>0.94:
      white_pixels=[rgb for rgb,(_,_,_,a) in zip(images['white'].getdata(),transparent.getdata()) if a>=128]
      if white_pixels and sum(min(r,g,b)>=238 for r,g,b,a in white_pixels)/len(white_pixels)>0.94 and not _has_contrast_outline(transparent,images['white'],'white'):
       issues.append('LOW_CONTRAST_WHITE')
     if nearblack/visible>0.94:
      black_pixels=[rgb for rgb,(_,_,_,a) in zip(images['black'].getdata(),transparent.getdata()) if a>=128]
      if black_pixels and sum(max(r,g,b)<=17 for r,g,b,a in black_pixels)/len(black_pixels)>0.94 and not _has_contrast_outline(transparent,images['black'],'black'):
       issues.append('LOW_CONTRAST_BLACK')
   # The solid background variants must not retain transparency.
   for name in ('black','white'):
    if images[name].getchannel('A').getextrema()!=(255,255):
     issues.append('NONOPAQUE_'+name.upper())
  return sha, issues
 except Exception as e:
  return sha,['QA_ERROR: '+str(e)[:180]]

def repair_variant_task(args):
 """Repair deterministic variant defects, backing up existing bytes before replacement.

 Never changes the transparent source art for low contrast or empty images.
 """
 source, output_dir, sha, reasons, backup_root = args
 allowed={'MISSING_TRANSPARENT','MISSING_BLACK','MISSING_WHITE',
          'CORRUPT_TRANSPARENT','CORRUPT_BLACK','CORRUPT_WHITE',
          'DIMENSIONS_TRANSPARENT','DIMENSIONS_BLACK','DIMENSIONS_WHITE',
          'VARIANT_SIZE_MISMATCH','NONOPAQUE_BLACK','NONOPAQUE_WHITE',
          'LOW_CONTRAST_WHITE','LOW_CONTRAST_BLACK'}
 if not reasons or not set(reasons).issubset(allowed):
  return False,0,'Requires human review'
 folder=Path(output_dir)/sha[:2]/sha
 try:
  with Image.open(source) as im:
   im.load()
   if not (1<=im.width<=4096 and 1<=im.height<=4096):
    raise ValueError('Invalid source dimensions')
   from artwork_preparation import extract_flat_edge_background
   raw=im.convert('RGBA')
   clean,extracted=extract_flat_edge_background(raw)
   rgba=_fit_canvas(clean)
  # No re-render of approved-looking, otherwise intact variants.
  affected=set()
  for reason in reasons:
   if reason=='VARIANT_SIZE_MISMATCH':
    affected.update(('transparent','black','white'))
   elif reason=='LOW_CONTRAST_WHITE':affected.add('white')
   elif reason=='LOW_CONTRAST_BLACK':affected.add('black')
   else:
    affected.add(reason.rsplit('_',1)[-1].lower())
  # Prepare and validate every requested derivative before changing any on-disk PNG.
  prepared={}
  for name in ('transparent','black','white'):
   if name not in affected:continue
   render=_compose_variant(rgba,name)
   if name in ('white','black') and 'LOW_CONTRAST_'+name.upper() in reasons:
    if _contrast_variant_art(rgba,name).tobytes()==rgba.tobytes():
     for radius in (2,3,4):
      candidate=_compose_variant(_outlined_variant(rgba,name,radius=radius),name)
      if _has_contrast_outline(rgba,candidate,name):
       render=candidate
       break
     else:
      return False,0,'Contrast outline cannot be verified safely'
   if render.size!=(220,132):
    return False,0,'Invalid prepared variant dimensions'
   prepared[name]=render
  # Stage all outputs before touching the work store; rollback on any commit failure.
  folder.mkdir(parents=True,exist_ok=True)
  staged={}
  originals={}
  committed=[]
  try:
   for name,render in prepared.items():
    out=folder/(name+'.png')
    tmp=out.with_name(out.name+'.'+str(os.getpid())+'.repair-partial')
    render.save(tmp,format='PNG',compress_level=3)
    with Image.open(tmp) as check:check.verify()
    staged[out]=tmp
    if name in ('black','white'):
     template=Path(__file__).resolve().parent/'templates'/'picons'/(name+'-sablona.png')
     sig=folder/(name+'.template-sha256')
     sig_tmp=sig.with_name(sig.name+'.'+str(os.getpid())+'.partial')
     sig_tmp.write_text(hashlib.sha256(template.read_bytes()).hexdigest(),encoding='ascii')
     staged[sig]=sig_tmp
   # Record pre-transaction bytes even for signatures, so rollback is complete.
   for dest in staged:
    originals[dest]=dest.read_bytes() if dest.exists() else None
   for dest in staged:
    if dest.suffix == '.png' and originals[dest] is not None:
     backup=Path(backup_root)/sha[:2]/sha/dest.name
     backup.parent.mkdir(parents=True,exist_ok=True)
     if not backup.exists():
      temp_backup=backup.with_name(backup.name+'.partial')
      try:
       with temp_backup.open('xb') as stream:
        stream.write(originals[dest]);stream.flush();os.fsync(stream.fileno())
       os.replace(temp_backup,backup)
      finally:
       temp_backup.unlink(missing_ok=True)
   for dest,tmp in staged.items():
    os.replace(tmp,dest)
    committed.append(dest)
  except Exception:
   for dest in reversed(committed):
    prior=originals[dest]
    if prior is None:
     dest.unlink(missing_ok=True)
    else:
     restore=dest.with_name(dest.name+'.rollback-partial')
     restore.write_bytes(prior)
     os.replace(restore,dest)
   raise
  finally:
   for tmp in staged.values():
    tmp.unlink(missing_ok=True)
  repaired=len(prepared)
  return True,repaired,''
 except Exception as exc:
  return False,0,str(exc)

def _legacy_ambiguous_cache_entry(entry):
 """Old QA results incorrectly classified safe recolor refusal as I/O failure."""
 return isinstance(entry,dict) and any(
  isinstance(reason,str) and reason.startswith(
   'AUTO_REPAIR_FAILED: Ambiguous artwork: no safe monochrome recolor')
  for reason in entry.get('issues',[]))

class Factory:
 def __init__(self,emit):
  self.emit=emit
  for p in (APP,DATA,INBOX,ORIGINALS,OUTPUT,FINAL_PICONS,EXCEPTIONS,REPORTS):p.mkdir(parents=True,exist_ok=True)
  interrupted=cleanup_interrupted_renders(OUTPUT, min_age_seconds=86400)
  self.log(f'Upratovanie nedokončených renderov: {len(interrupted["deleted"])} starých dočasných súborov.')
  release=check_factory_release()
  if release['status']=='available':
   self.log('Nová Factory na GitHub Releases: '+release['version']+' (inštalácia zatiaľ vyžaduje overený inštalátor).')
  elif release['status']=='offline_or_invalid':
   self.log('Kontrola aktualizácie nedostupná; pokračujem lokálne.')
  for error in interrupted['errors']:
   self.log('Upratovanie pracovných súborov: '+error)
  housekeeping=cleanup_reports(REPORTS,keep_runs=3)
  self.log(f'Upratovanie reportov: vymazaných {housekeeping["deleted"]} starých JSON; ponechané {housekeeping["retained_runs"]} behy.')
  for error in housekeeping['errors']:
   self.log('Upratovanie: nepodarilo sa vymazať '+error)
  self.db=sqlite3.connect(str(DB))
  self.db.execute('CREATE TABLE IF NOT EXISTS files (path TEXT PRIMARY KEY, sha256 TEXT, size INTEGER, modified_ns INTEGER, status TEXT, last_run TEXT)')
  self.db.execute('CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, scanned INTEGER, changed INTEGER, duplicates INTEGER, exceptions INTEGER, created INTEGER)')
  self.db.commit()
 def log(self,msg):self.emit('log',msg)
 def fetch_sources(self):
  # Bounded parallel download, pinned to one immutable production commit.
  from concurrent.futures import ThreadPoolExecutor, as_completed
  from urllib.parse import quote, urlsplit
  import random
  owner,repo,branch='Evolution-by-Warder','PiconHub-Warder-Evolution','warder-master-production'
  try:
   self.emit('stage','1/5 · Kontrolujem GitHub a zmeny zdroja');self.log('Zisťujem stav PiconHub cez GitHub API...')
   api=f'https://api.github.com/repos/{owner}/{repo}/branches/{branch}'
   request=urllib.request.Request(api,headers={'User-Agent':'Warder-Picon-Factory/1.0','Accept':'application/vnd.github+json'})
   with urllib.request.urlopen(request,timeout=75) as response:
    if urlsplit(response.url).hostname!='api.github.com':raise ValueError('Neočakávaný server API')
    payload=response.read(2_000_001)
    if len(payload)>2_000_000:raise ValueError('Branch metadata prekročili limit')
   branch_info=json.loads(payload)
   commit=branch_info.get('commit',{}).get('sha','')
   if len(commit)!=40 or any(c not in '0123456789abcdef' for c in commit):raise ValueError('Neplatný production commit')
   api=f'https://api.github.com/repos/{owner}/{repo}/git/trees/{commit}?recursive=1'
   request=urllib.request.Request(api,headers={'User-Agent':'Warder-Picon-Factory/1.0','Accept':'application/vnd.github+json'})
   with urllib.request.urlopen(request,timeout=75) as response:
    if urlsplit(response.url).hostname!='api.github.com':raise ValueError('Neočakávaný server API')
    payload=response.read(40_000_001)
    if len(payload)>40_000_000:raise ValueError('Zoznam súborov prekročil bezpečnostný limit')
   tree=json.loads(payload)
   if tree.get('truncated'):raise ValueError('Neúplný GitHub strom; synchronizácia zastavená')
   entries=[]
   for entry in tree.get('tree',[]):
    rel=entry.get('path','').replace('\\','/')
    parts=Path(rel).parts
    blob=entry.get('sha','')
    if (entry.get('type')=='blob' and rel.lower().endswith('.png') and len(parts)==5 and
        parts[0]=='picons' and parts[3] in ('transparent','black','white') and
        not rel.startswith('/') and all(p not in ('','.','..') and ':' not in p for p in parts) and
        isinstance(entry.get('size'),int) and 0<entry['size']<=30_000_000 and
        len(blob)==40 and all(ch in '0123456789abcdef' for ch in blob)):
     entries.append(entry)
   self.master_commit=commit
   master_paths=[e['path'].replace('\\','/') for e in entries]
   self.log(f'PiconHub production commit: {commit}; indexujem všetky štýly Warder Master.')
   jobs=[]; skipped=0
   for e in entries:
    rel=e['path'];parts=Path(rel.replace('\\','/')).parts
    if not parts or '..' in parts or any(':' in part for part in parts) or rel.startswith('/') or int(e.get('size') or 0)>30_000_000:continue
    dest=ORIGINALS/'github-piconhub'/Path(*parts)
    key='github:'+rel
    old=self.db.execute('SELECT sha256 FROM files WHERE path=?',(key,)).fetchone()
    if dest.is_file() and dest.stat().st_size==int(e.get('size') or 0):
     if old and old[0]==e.get('sha'):
      skipped+=1;continue
     # Validate previously downloaded files even when interrupted before database checkpoint.
     h=hashlib.sha1(); h.update(('blob '+str(dest.stat().st_size)+'\0').encode('ascii'))
     with open(dest,'rb') as previous:
      for piece in iter(lambda:previous.read(1048576),b''):h.update(piece)
     if h.hexdigest()==e.get('sha'):
      self.db.execute('INSERT OR REPLACE INTO files VALUES (?,?,?,?,?,?)',(key,e.get('sha'),dest.stat().st_size,0,'SOURCE_SYNC',datetime.now().isoformat()))
      skipped+=1;continue
    jobs.append((e,dest,key))
   self.db.commit()
   self.log(f'PiconHub: {len(entries)} PNG, už uložených {skipped}, na stiahnutie {len(jobs)}.')
   if not jobs:
    self.master_paths=master_paths
    atomic_json(DATA/'master-current-paths.json',{'commit':commit,'paths':master_paths})
    self.emit('progress',(1,1));self.log('Všetky zdrojové PNG sú aktuálne.');return
   self.emit('stage','2/5 · Paralelne sťahujem zmenené PNG');self.log('Spúšťam paralelné sťahovanie (32 spojení); bezpečnostné overenie každého PNG.')
   def download(job):
    e,dest,key=job;rel=e['path']
    url='https://raw.githubusercontent.com/'+quote(owner)+'/'+quote(repo)+'/'+quote(commit)+'/'+quote(rel,safe='/')
    last_error=None
    for attempt in range(3):
     tmp=None
     try:
      req=urllib.request.Request(url,headers={'User-Agent':'Warder-Picon-Factory/1.0'})
      with urllib.request.urlopen(req,timeout=50) as response:
       if urlsplit(response.url).hostname not in ('raw.githubusercontent.com','media.githubusercontent.com'):
        raise ValueError('Neoverený server sťahovania')
       if int(response.headers.get('Content-Length') or 0)>30_000_000:raise ValueError('Priveľký PNG')
       dest.parent.mkdir(parents=True,exist_ok=True)
       tmp=dest.with_name(dest.name+'.'+str(threading.get_ident())+'.partial')
       total=0;sha=hashlib.sha1()
       with open(tmp,'wb') as f:
        while True:
         chunk=response.read(1048576)
         if not chunk:break
         total+=len(chunk)
         if total>30_000_000:raise ValueError('PNG prekročil limit')
         f.write(chunk)
       if total!=int(e.get('size') or 0):raise ValueError('Nesprávna veľkosť PNG')
       with open(tmp,'rb') as f:
        if f.read(8)!=b'\x89PNG\r\n\x1a\n':raise ValueError('Neplatná PNG hlavička')
        f.seek(0)
        sha.update(('blob '+str(total)+'\0').encode('ascii'))
        for chunk in iter(lambda:f.read(1048576),b''):sha.update(chunk)
       if sha.hexdigest()!=e.get('sha'):raise ValueError('Git blob hash nesúhlasí')
       os.replace(tmp,dest)
       return (True,key,e.get('sha',''),total,'')
     except Exception as ex:
      last_error=str(ex)
      if attempt<2:time.sleep(0.6*(attempt+1)+random.random()*0.4)
     finally:
      if tmp is not None and tmp.exists():tmp.unlink()
    return (False,key,'',0,last_error)
   done=0;errors=0;batch=[]
   with ThreadPoolExecutor(max_workers=32) as pool:
    futures=[pool.submit(download,job) for job in jobs]
    for future in as_completed(futures):
     ok,key,sha,size,error=future.result();done+=1
     if ok:batch.append((key,sha,size,0,'SOURCE_SYNC',datetime.now().isoformat()))
     else:
      errors+=1
      if errors<=15:self.log('CHYBA '+key+': '+error)
     if len(batch)>=100:
      self.db.executemany('INSERT OR REPLACE INTO files VALUES (?,?,?,?,?,?)',batch)
      self.db.commit();batch.clear()
     if done%100==0 or done==len(jobs):
      self.emit('progress',(done,len(jobs)))
      self.log(f'Sťahovanie: {done}/{len(jobs)}; chyby {errors}; predtým uložených {skipped}.')
   if batch:
    self.db.executemany('INSERT OR REPLACE INTO files VALUES (?,?,?,?,?,?)',batch);self.db.commit()
   self.log(f'Synchronizácia ukončená: {done-errors} stiahnutých, {skipped} už uložených, {errors} chýb; commit {commit}.')
   if errors==0:
    self.master_paths=master_paths
    atomic_json(DATA/'master-current-paths.json',{'commit':commit,'paths':master_paths})
   else:
    self.log('Warder Master checkpoint nemenil som, pretože nie všetky aktuálne PNG sa overili.')
  except Exception as e:
   self.log('ZDROJ NEDOSTUPNÝ: PiconHub ('+str(e)+')')
 def scan(self):
  run=datetime.now().strftime('%Y%m%d-%H%M%S-%f'); stats=dict(scanned=0,changed=0,duplicates=0,exceptions=0,created=0)
  self.log('Začínam spracovanie '+run)
  self.fetch_sources()
  if not hasattr(self,'master_paths'):
   try:
    saved=json.loads((DATA/'master-current-paths.json').read_text(encoding='utf-8'))
    self.master_paths=saved.get('paths',[]);self.master_commit=saved.get('commit')
   except (OSError,ValueError,AttributeError):self.master_paths=[]
  self.emit('stage','3/5 · Importujem lokálne ZIP archívy')
  if not PIL_OK:self.log('Pillow nie je dostupný: grafické varianty sa nevytvoria; iba inventarizácia.')
  # Safe, bounded, atomic import; originals never overwritten.
  for archive in sorted(INBOX.rglob('*.zip')):
   try:
    result=import_png_zip(archive,ORIGINALS)
    self.log(f'Archív {archive.name}: import {result["imported"]}, preskočené {result["skipped"]}')
   except Exception as e:
    stats['exceptions']+=1
    self.log('CHYBA archívu '+archive.name+': '+str(e))
  # The three requested peer sources are integrated into the same resumable
  # ingestion tree. Each source owns its checkpoint and failure isolation.
  self.sync_peer_sources(stats)
  # Optional verified current-source manifest connects the tested ingestion
  # modules to the same one-run pipeline. Missing source configuration is
  # reported as unavailable; no URLs or checksums are guessed.
  if SOURCE_MANIFEST.is_file():
   try:
    from source_pipeline import ingest_current_sources
    from source_inventory import validate_manifest
    from urllib.parse import urlsplit
    source_manifest=json.loads(SOURCE_MANIFEST.read_text(encoding='utf-8'))
    verified_entries=validate_manifest(source_manifest)
    allowed_hosts={urlsplit(item['url']).hostname for item in verified_entries}
    source_result=ingest_current_sources(
      source_manifest, SOURCE_INGEST, allowed_hosts,
      notify=lambda key,state:self.log(f'{key}: {state}'))
    stats['external_source_archives']=len(source_result['processed'])
    stats['unchanged_sources']=source_result['unchanged']
   except Exception as e:
    stats['exceptions']+=1
    stats['external_source_error']=str(e)[:300]
    self.log('EXTERNÉ ZDROJE: manifest alebo synchronizácia zlyhali bezpečne: '+str(e))
  else:
   stats['external_source_archives']=0
   stats['external_source_error']='NOT_CONFIGURED'
  # Build a read-only snapshot index from the exact production files downloaded
  # above. It is the identity baseline; master assets are never sent through
  # the candidate renderer.
  master_root=ORIGINALS/'github-piconhub'
  registry={'schema':1,'authority':'PiconHub-Warder-Evolution/warder-master-production',
            'service_count':0,'asset_count':0,'rejected_paths':0,'services':{},'conflicts':[]}
  if master_root.is_dir():
   try:
    master_cache_path=DATA/'master-registry-cache.json'
    previous_cache=json.loads(master_cache_path.read_text(encoding='utf-8')) if master_cache_path.is_file() else {}
    registry=index_master_tree(master_root,previous_cache,allowed_paths=self.master_paths)
    atomic_json(master_cache_path,registry.pop('cache'))
   except Exception as e:
    stats['exceptions']+=1
    stats['master_registry_error']=str(e)[:300]
    self.log('WARDER MASTER index zlyhal; kandidáti nebudú automaticky prepojení: '+str(e))
  registry_path=REPORTS/('warder-master-index-'+run+'.json')
  atomic_json(registry_path,registry)
  stats['master_registry_services']=registry['service_count']
  stats['master_registry_conflicts']=len(registry['conflicts'])
  self.log(f'WARDER MASTER: {registry["service_count"]:,} service references, {registry["asset_count"]:,} súborov, {len(registry["conflicts"]):,} konfliktných štýlov.')
  self.emit('stage','4/5 · Overujem PNG a pripravujem varianty')
  hashes={}
  candidate_records=[]
  output_cache_path=DATA/'output-cache.json'
  try:
   output_cache=json.loads(output_cache_path.read_text(encoding='utf-8')).get('items',{})
   if not isinstance(output_cache,dict):output_cache={}
  except (OSError,ValueError,AttributeError):output_cache={}
  candidates=[]
  for base in (ORIGINALS,INBOX,SOURCE_INGEST/'originals'):
   for p in base.rglob('*'):
    if p.is_file() and p.suffix.lower()=='.png' and not is_master_path(p): candidates.append(p)
  total=len(candidates)
  self.log(f'Kontrola PNG: 0/{total}; Pillow: '+('dostupný' if PIL_OK else 'CHÝBA'))
  self.emit('progress',(0,max(1,total)))
  cpu=os.cpu_count() or 4
  workers=min(24,max(1,cpu-2))
  self.log(f'Paralelné PNG spracovanie: {workers} procesov z {cpu} logických CPU; limit rozpracovaných úloh {workers*3}.')
  self.emit('stage',f'4/5 · Paralelné PNG · {workers} procesov')
  # Parent process exclusively owns SQLite. Worker processes only decode/render PNG.
  pool=ProcessPoolExecutor(max_workers=workers) if PIL_OK else None
  pending={}
  completed=0
  def collect(done):
   nonlocal completed
   for fut in done:
    rel,sha,st=pending.pop(fut)
    try: ok,created,error=fut.result()
    except Exception as e:ok,created,error=False,0,str(e)
    stats['created']+=created
    status='VARIANTS_UNREVIEWED' if ok else 'EXCEPTION'
    if not ok:
     stats['exceptions']+=1
     if stats['exceptions']<=30:self.log('Výnimka '+Path(rel).name+': '+error)
    self.db.execute('INSERT OR REPLACE INTO files VALUES (?,?,?,?,?,?)',(rel,sha,st.st_size,st.st_mtime_ns,status,run))
    completed+=1
   if completed%250< len(done) or completed==total:
    self.db.commit()
    self.emit('progress',(completed,max(1,total)))
    self.emit('stage',f'4/5 · PNG {completed:,}/{total:,} · procesov {workers} · varianty {stats["created"]:,} · výnimky {stats["exceptions"]:,}')
    if completed%1000<len(done) or completed==total:
     self.log(f'PNG: {completed}/{total}; varianty {stats["created"]}; výnimky {stats["exceptions"]}.')
  try:
   for p in candidates:
    stats['scanned']+=1
    try:
     st=p.stat();rel=str(p)
     old=self.db.execute('SELECT sha256,size,modified_ns,status FROM files WHERE path=?',(rel,)).fetchone()
     if old and old[1]==st.st_size and old[2]==st.st_mtime_ns:
      sha=old[0]
     else:
      h=hashlib.sha256()
      with open(p,'rb') as f:
       for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
      sha=h.hexdigest();stats['changed']+=1
     candidate_records.append({'sha256':sha,'source':str(p)})
     if sha in hashes:
      stats['duplicates']+=1
      self.db.execute('INSERT OR REPLACE INTO files VALUES (?,?,?,?,?,?)',(rel,sha,st.st_size,st.st_mtime_ns,'DUPLICATE',run))
      completed+=1
     else:
      hashes[sha]=rel
      cached=output_cache.get(sha,{})
      current_signature=_output_signature(sha)
      if current_signature is not None and cached.get('signatures')==current_signature:
       self.db.execute('INSERT OR REPLACE INTO files VALUES (?,?,?,?,?,?)',(rel,sha,st.st_size,st.st_mtime_ns,'VARIANTS_UNREVIEWED',run))
       completed+=1
      elif pool:
       fut=pool.submit(render_png_task,(rel,str(OUTPUT),sha))
       pending[fut]=(rel,sha,st)
      else:
       self.db.execute('INSERT OR REPLACE INTO files VALUES (?,?,?,?,?,?)',(rel,sha,st.st_size,st.st_mtime_ns,'PILLOW_MISSING',run))
       completed+=1
    except Exception as e:
     stats['exceptions']+=1;completed+=1
     if stats['exceptions']<=30:self.log('CHYBA súboru '+str(p)+': '+str(e))
    if pool and len(pending)>=workers*3:
     done,_=wait(tuple(pending),return_when=FIRST_COMPLETED)
     collect(done)
    if completed%500==0:
     self.db.commit()
     self.emit('progress',(completed,max(1,total)))
     self.emit('stage',f'4/5 · PNG {completed:,}/{total:,} · procesov {workers} · varianty {stats["created"]:,}')
   while pending:
    done,_=wait(tuple(pending),return_when=FIRST_COMPLETED)
    collect(done)
  finally:
   if pool:pool.shutdown(wait=True)
  self.db.commit()
  self.emit('progress',(completed,max(1,total)))
  self.emit('stage',f'4/5 · PNG {completed:,}/{total:,} · hotovo')
  # Conservative identity audit: do not assume filenames are validated registry IDs.
  collisions=audit_collision_records(candidate_records)
  collision_path=REPORTS/('identity-collisions-'+run+'.json')
  collision_payload={'run':run,'collisions':collisions,'count':len(collisions),
    'note':'Filename-based candidates only; compare against authoritative Warder Master Registry before approval.'}
  collision_tmp=collision_path.with_suffix('.json.partial')
  collision_tmp.write_text(json.dumps(collision_payload,ensure_ascii=False,indent=2),encoding='utf-8')
  os.replace(collision_tmp,collision_path)
  stats['identity_collisions']=len(collisions)
  self.log(f'Identita: {len(collisions)} konfliktných kandidátnych service-ref; report: {collision_path}')
  registry_matches=[]
  for record in sorted(candidate_records,key=lambda item:(item['sha256'],item['source'])):
   registry_matches.append(classify_candidate(record['source'],record['sha256'],registry))
  from artwork_evidence import attach_artwork_evidence
  artwork_evidence_counts=attach_artwork_evidence(registry_matches,registry)
  from openatv_pixel_evidence import attach_pixel_evidence
  pixel_evidence_counts=attach_pixel_evidence(registry_matches,registry,master_root,DATA/'openatv-pixel-evidence-cache.json') if PIL_OK and master_root.is_dir() else {}
  from openatv_normalized_evidence import attach_normalized_evidence
  normalized_evidence_counts=attach_normalized_evidence(registry_matches,registry,master_root) if PIL_OK and master_root.is_dir() else {}
  from openatv_scaled_evidence import attach_scaled_evidence
  scaled_evidence_counts=attach_scaled_evidence(registry_matches,registry,master_root) if PIL_OK and master_root.is_dir() else {}
  from openatv_candidate_link import attach_name_candidates
  openatv_candidate_counts=attach_name_candidates(registry_matches)
  from openatv_crossname import attach_crossname_artwork_candidates
  crossname_counts=attach_crossname_artwork_candidates(registry_matches)
  self.log("OpenATV presné SHA zhody medzi rôznymi názvami (NEOVERENÉ): "+str(crossname_counts))
  from openatv_station_groups import group_openatv_stations
  openatv_station_groups=group_openatv_stations(registry_matches)
  station_summary={key:value for key,value in openatv_station_groups.items() if key != 'station_groups'}
  self.log('OpenATV skupiny staníc (nie jednotlivé PNG): '+str(station_summary))
  from openatv_catalog import build_openatv_catalog
  # Materialize unique original artwork in a separate non-production catalog.
  # The known empty source must never enter a usable artwork catalog.
  catalog=build_openatv_catalog(registry_matches,OUTPUT,excluded_hashes=())
  self.log('OpenATV katalóg unikátnych grafík: '+str(catalog['artworks'])+'; nových '+str(catalog['created'])+'; uložené v '+str(OUTPUT/'OPENATV-NAME-CATALOG'))
  from openatv_name_evidence import summarize_openatv_name_evidence
  openatv_name_evidence=summarize_openatv_name_evidence(registry_matches)
  from openatv_triage import build_openatv_triage
  triage=build_openatv_triage(registry_matches)
  triage_path=REPORTS/('openatv-triage-'+run+'.json')
  atomic_json(triage_path,triage)
  self.log('OpenATV triedenie bez duplicít a bez pridelenia ID: '+str(triage['summary'])+'; report: '+str(triage_path))
  match_path=REPORTS/('registry-matches-'+run+'.json')
  from registry_triage import summarize_registry_matches, service_reference_diagnostics, unmapped_filename_diagnostics, unmapped_asset_inventory
  from registry_triage import identity_level_triage
  identity_triage=identity_level_triage(registry_matches)
  identity_triage_path=REPORTS/('openatv-identity-triage-'+run+'.json')
  atomic_json(identity_triage_path,identity_triage)
  self.log('OpenATV SRP identita bez duplicít: '+str(identity_triage['reference_status_counts'])+'; '+str(identity_triage['unique_service_references'])+' unikátnych referencií; report: '+str(identity_triage_path))
  self.log('OpenATV SRP rozdiely podľa formátu/štýlu (diagnostika, bez schválenia): '+str(identity_triage['style_diagnostic_counts']))
  self.log('OpenATV SRP rozhodovacie kategórie (bez automatického schválenia): '+str(identity_triage['actionable_identity_counts']))
  match_breakdown=summarize_registry_matches(registry_matches)
  service_breakdown=service_reference_diagnostics(registry_matches)
  unmapped_evidence=unmapped_filename_diagnostics(registry_matches)
  match_payload={'schema':1,'unmapped_filename_diagnostics':unmapped_evidence,'unmapped_asset_inventory':unmapped_asset_inventory(registry_matches),'master_commit':getattr(self,'master_commit',None),'source_breakdown':match_breakdown,'openatv_identity_triage':identity_triage,'service_reference_breakdown':service_breakdown,
    'artwork_evidence_counts':artwork_evidence_counts,
    'pixel_evidence_counts':pixel_evidence_counts,
    'normalized_evidence_counts':normalized_evidence_counts,
    'scaled_evidence_counts':scaled_evidence_counts,
    'openatv_name_evidence':openatv_name_evidence,
    'openatv_candidate_counts':openatv_candidate_counts,
    'openatv_crossname_counts':crossname_counts,
    'openatv_station_summary':station_summary,
    'candidate_count':len(registry_matches),
    'identical':sum(1 for item in registry_matches if item['classification']=='IDENTICAL'),
    'review':sum(1 for item in registry_matches if item['classification']=='REVIEW'),
    'new':sum(1 for item in registry_matches if item['classification']=='NEW'),
    'unmapped':sum(1 for item in registry_matches if item['classification']=='UNMAPPED'),
    'evidence_linked':sum(1 for item in registry_matches if item['classification']=='EVIDENCE_LINKED'),
    'items':registry_matches,
    'policy':'EXACT_SERVICE_REFERENCE_ONLY; NO_WARDER_ID_ASSIGNMENT; NO_AUTOMATIC_MASTER_CHANGE'}
  atomic_json(match_path,match_payload)
  stats['registry_identical']=match_payload['identical']
  stats['registry_review']=match_payload['review']
  stats['registry_new']=match_payload['new']
  stats['registry_unmapped']=match_payload['unmapped']
  stats['registry_evidence_linked']=match_payload['evidence_linked']
  self.log(f'Porovnanie s Warder Master: {match_payload["identical"]:,} identických kandidátov; {match_payload["new"]:,} nových; {match_payload["review"]:,} rozdielov artworku; {match_payload["evidence_linked"]:,} s kandidátnou grafickou väzbou (NEOVERENÉ); {match_payload["unmapped"]:,} bez väzby (NEPOROVNANÉ). Report: {match_path}')
  self.log('OpenATV dekódované pixely – presná zhoda (NEOVERENÉ identity): '+str(pixel_evidence_counts))
  self.log('OpenATV presné logo bez priehľadných okrajov (NEOVERENÉ identity): '+str(normalized_evidence_counts))
  self.log('OpenATV zhodné logo po zmene mierky (NEOVERENÉ identity): '+str(scaled_evidence_counts))
  self.log('OpenATV/UTF8SNP presná grafická zhoda s Master (iba dôkaz, nie identita): '+str(artwork_evidence_counts))
  self.log('OpenATV kandidáti podľa zhodnej grafiky v skupine názvu (NEOVERENÉ identity): '+str(openatv_candidate_counts))
  self.log('OpenATV názvy: '+str(openatv_name_evidence['distinct_names'])+' unikátnych; '+str(openatv_name_evidence['name_categories'])+'; rozdielne varianty pri jednej referencii: '+str(openatv_name_evidence['single_ref_names_with_other_artwork_variants']))
  for origin,counts in sorted(match_breakdown.items()):
   self.log(f'  Zdroj {origin}: identické {counts["IDENTICAL"]:,}, nové {counts["NEW"]:,}, odlišné {counts["REVIEW"]:,}, graficky priradené {counts["EVIDENCE_LINKED"]:,}, nemapované {counts["UNMAPPED"]:,}')
  for origin,info in unmapped_evidence.items():
   self.log(f'  Neidentifikované {origin}: {info["count"]:,}; UTF8/názvy {info["utf8_names"]:,}; ostatné {info["other"]:,}; vzorky {", ".join(info["samples"][:5])}')
  for origin,counts in sorted(service_breakdown.items()):
   self.log(f'  Identita {origin}: {counts["distinct_service_references"]:,} unikátnych service-ref; '
            f'{counts["service_references_with_multiple_artworks"]:,} referencií s viacerými grafikami; '
            f'{counts["unrecognized_filenames"]:,} nerozpoznaných názvov.')
  # Phase 5: read-only QA on UNIQUE content hashes. Does not alter production.
  self.emit('stage','5/5 · Automatická QA existujúcich variantov')
  unique=list(hashes)
  current_signatures={sha:_output_signature(sha) for sha in unique}
  # Legacy cache stored safe-recolor refusals as blocking repair failures.
  # Recheck only those affected images so the current QA can recover the
  # original contrast advisory; do not silently erase a cached finding.
  legacy_ambiguous={sha for sha,entry in output_cache.items()
                    if _legacy_ambiguous_cache_entry(entry)}
  if legacy_ambiguous:
   self.log(f'QA cache migrácia: znovu preverím {len(legacy_ambiguous)} starých nejednoznačných opráv.')
  qa_issues={sha:list(entry.get('issues',[])) for sha,entry in output_cache.items()
              if sha in hashes and sha not in legacy_ambiguous and current_signatures[sha] is not None and isinstance(entry,dict)
              and entry.get('signatures')==current_signatures[sha] and entry.get('qa_schema') in (4,5) and entry.get('issues')}
  qa_targets=[sha for sha in unique if sha in legacy_ambiguous or current_signatures[sha] is None or
              output_cache.get(sha,{}).get('signatures')!=current_signatures[sha] or
              output_cache.get(sha,{}).get('qa_schema') not in (4,5)]
  qa_checked=0
  if not PIL_OK and qa_targets:
   raise RuntimeError('Pillow chýba: QA nemožno dokončiť ani bezpečne aktualizovať cache.')
  if PIL_OK and qa_targets:
   with ProcessPoolExecutor(max_workers=workers) as qa_pool:
    pending_qa={}
    iterator=iter(qa_targets)
    def enqueue():
     while len(pending_qa)<workers*3:
      try: sha=next(iterator)
      except StopIteration:break
      fut=qa_pool.submit(qa_png_task,(sha,str(OUTPUT)))
      pending_qa[fut]=sha
    enqueue()
    while pending_qa:
     done,_=wait(tuple(pending_qa),return_when=FIRST_COMPLETED)
     for fut in done:
      sha=pending_qa.pop(fut)
      try: _,issues=fut.result()
      except Exception as e:issues=['QA_ERROR: '+str(e)[:180]]
      qa_checked+=1
      if issues:qa_issues[sha]=issues
      else:qa_issues.pop(sha,None)
     if qa_checked%500< len(done) or qa_checked==len(qa_targets):
      self.emit('progress',(qa_checked,len(qa_targets)))
      self.emit('stage',f'5/5 · QA {qa_checked:,}/{len(qa_targets):,} nových/zmenených · problémy {len(qa_issues):,}')
      if qa_checked%2000<len(done) or qa_checked==len(qa_targets):
       self.log(f'QA: skontrolovaných {qa_checked}/{len(qa_targets)} zmenených sád; na preverenie {len(qa_issues)}.')
     enqueue()
  else:
   if not PIL_OK:self.log('QA nie je možné spustiť: Pillow chýba.')
   elif unique:self.log(f'QA cache: {len(unique)} nezmenených sád preskočených bez dekódovania.')
  # Auto-fix only objectively missing/corrupt variant files by rerendering
  # from the immutable original. Ambiguous identity/contrast stays in review.
  fixable={'MISSING_TRANSPARENT','MISSING_BLACK','MISSING_WHITE',
           'CORRUPT_TRANSPARENT','CORRUPT_BLACK','CORRUPT_WHITE',
           'DIMENSIONS_TRANSPARENT','DIMENSIONS_BLACK','DIMENSIONS_WHITE',
           'VARIANT_SIZE_MISMATCH','NONOPAQUE_BLACK','NONOPAQUE_WHITE',
          'LOW_CONTRAST_WHITE','LOW_CONTRAST_BLACK'}
  # A verified unchanged multicolour logo must not trigger the same rejected
  # recolour on every run. Reattempt only if its source or output changed.
  refused_cache={sha for sha,entry in output_cache.items()
                 if sha in hashes and isinstance(entry,dict)
                 and entry.get('contrast_repair_refused') is True
                 and entry.get('signatures')==current_signatures.get(sha)
                 and entry.get('source_sha256')==sha and entry.get('qa_schema')==5}
  repair_candidates=[sha for sha,issues in qa_issues.items()
                     if set(issues).issubset(fixable) and sha in hashes
                     and sha not in refused_cache]
  contrast_refused=set(refused_cache)
  if refused_cache:
   self.log(f'QA: {len(refused_cache)} nezmenených viacfarebných logotypov bezpečne ponechaných bez opakovaného prefarbovania.')
  repaired=0
  if repair_candidates and PIL_OK:
   self.emit('stage',f'5/5 · Bezpečne opravujem {len(repair_candidates)} sád')
   backup_root=EXCEPTIONS/'variant-backups'/run
   with ProcessPoolExecutor(max_workers=workers) as fix_pool:
    futures={fix_pool.submit(repair_variant_task,
              (hashes[sha],str(OUTPUT),sha,qa_issues[sha],str(backup_root))):sha
             for sha in repair_candidates}
    for fut in futures:
     sha=futures[fut]
     try: ok,changed,error=fut.result()
     except Exception as e:ok,changed,error=False,0,str(e)
     if ok:
      _,remaining=qa_png_task((sha,str(OUTPUT)))
      if not remaining:
       del qa_issues[sha];repaired+=1
      else:qa_issues[sha]=remaining
     else:
      # A complex multicolour logo is not corrupt: keep the original
      # low-contrast finding as an advisory, not a fabricated technical error.
      # Actual I/O/encoding failures remain blocking and retain their cause.
      if error == 'Ambiguous artwork: no safe monochrome recolor':
       contrast_refused.add(sha)
       qa_issues[sha]=[r for r in qa_issues[sha] if r in ('LOW_CONTRAST_WHITE','LOW_CONTRAST_BLACK')]
      else:
       qa_issues[sha]=sorted(set(qa_issues[sha]+['AUTO_REPAIR_FAILED: '+error[:150]]))
  stats['qa_repaired']=repaired
  stats['qa_checked']=qa_checked
  qa_triage=summarize(qa_issues)
  stats['qa_reasons']=qa_triage['reasons']
  stats['qa_blocking']=qa_triage['blocking_count']
  stats['qa_visual_advisory']=qa_triage['advisory_count']
  stats['qa_cache_hits']=len(unique)-len(qa_targets)
  stats['qa_cache_findings']=sum(1 for sha in qa_issues if sha not in qa_targets)
  self.log(f'QA cache: {stats["qa_cache_hits"]} overených nezmenených sád; {stats["qa_cache_findings"]} s uloženými nálezmi.')
  self.log('QA: technické problémy '+str(stats['qa_blocking'])+'; upozornenia na možný kontrast '+str(stats['qa_visual_advisory'])+'.')
  self.log('QA dôvody: '+str(stats['qa_reasons']))
  for reason, count in Counter(reason for issues in qa_issues.values() for reason in issues).most_common(12):
   self.log(f'QA DETAIL: {reason} = {count} sád; ukážka SHA: '+', '.join(sha[:12] for sha, issues in qa_issues.items() if reason in issues)[:150])
  self.log(f'QA autooprava: {repaired} opravených sád, {stats["qa_blocking"]} technických chýb, {stats["qa_visual_advisory"]} vizuálnych upozornení.')
  stats['qa_review']=stats['qa_blocking']
  self.emit('stage',f'5/5 · QA ukončená · skutočné nálezy {len(qa_issues):,} · vytváram reporty')
  # Cache is a flat sha->record mapping in memory; persist it inside one envelope.
  # Do not nest 'items' in itself: that invalidates the next run's QA cache.
  atomic_json(output_cache_path,{'schema':1,'items':{
      sha:{'signatures':_output_signature(sha),'qa_schema':5,'issues':qa_issues.get(sha,[]),
           'source_sha256':sha,'contrast_repair_refused':sha in contrast_refused and
           bool(set(qa_issues.get(sha,[])) & {'LOW_CONTRAST_WHITE','LOW_CONTRAST_BLACK'})}
      for sha in unique}})
  qa_path=REPORTS/('qa-'+run+'.json')
  qa_data={'run':run,'unique_png':len(unique),'checked':qa_checked,
           'needs_review':stats['qa_blocking'],'findings_total':len(qa_issues),'blocking_count':qa_triage['blocking_count'],
           'visual_advisory_count':qa_triage['advisory_count'],
           'auto_repaired':repaired,'reasons':stats['qa_reasons'],
           'issues':[{ 'sha256':sha,'reasons':reasons,'example_source':hashes.get(sha,'')}
                     for sha,reasons in sorted(qa_issues.items())],
           'note':'Len technická kontrola. Bez automatického schvaľovania identity alebo publikovania.'}
  tmp=qa_path.with_suffix('.json.partial')
  tmp.write_text(json.dumps(qa_data,ensure_ascii=False,indent=2),encoding='utf-8')
  os.replace(tmp,qa_path)
  self.log(f'QA hotová: {qa_checked} skontrolovaných PNG, {stats["qa_blocking"]} technických chýb a {stats["qa_visual_advisory"]} vizuálnych upozornení. Report: {qa_path}')
  # Fail closed: never present a transparent-only source as publication-ready.
  # Keep immutable inputs and existing output files intact; consumers can use
  # the explicit exclusion manifest to filter the publication candidate set.
  empty_report=empty_source_report(qa_issues,candidate_records,hashes)
  empty_report_path=REPORTS/('empty-source-'+run+'.json')
  atomic_json(empty_report_path,empty_report)
  exclusion=build_empty_source_exclusion(empty_report,OUTPUT)
  exclusion_path=REPORTS/('publication-exclusions-'+run+'.json')
  atomic_json(exclusion_path,exclusion)
  stats['empty_source_blocked']=empty_report['blocking_count']
  stats['publication_excluded_variant_paths']=len(exclusion['excluded_variant_paths'])
  if empty_report['blocking_count']:
   self.log(f'Prázdne PNG: {empty_report["blocking_count"]} zdrojových sád zablokovaných pre publikovanie; report: {empty_report_path}')
   self.log(f'Vylúčené výstupné varianty: {len(exclusion["excluded_variant_paths"])}; manifest: {exclusion_path}')
  # Stable per-exception review IDs, independent of run timestamps.
  review_path=REPORTS/('review-queue-'+run+'.json')
  review_queue=apply_decisions(build_review_queue(qa_issues,hashes,collisions,registry_matches), DATA/"review-decisions.json")
  save_review_queue(review_path,review_queue)
  stats['review_queue_items']=review_queue['count']
  stats['review_workstreams']=review_queue.get('workstream_counts', {})
  self.log('QA pracovné fronty: '+', '.join(f'{name}={count}' for name,count in review_queue.get('workstream_counts', {}).items()))
  self.log(f'Výnimky na rozhodnutie: {review_queue["count"]}; vizuálne upozornenia sú evidované osobitne v QA reporte: {review_path}')
  # End-of-run read-only integrity gate: source content must still match its ID.
  integrity=audit_artifacts(hashes,OUTPUT,source_hashes_verified=True)
  integrity_path=REPORTS/('integrity-'+run+'.json')
  atomic_json(integrity_path,integrity)
  stats['integrity_issues']=integrity['issue_count']
  self.log(f'Integrita: {integrity["checked"]} zdrojov, {integrity["issue_count"]} problémov; report: {integrity_path}')
  self.db.execute('INSERT INTO runs VALUES (?,?,?,?,?,?)',(run,stats['scanned'],stats['changed'],stats['duplicates'],stats['exceptions'],stats['created']))
  self.db.commit()
  report=REPORTS/('report-'+run+'.json')
  stats['installed_factory_version']=installed_factory_version()
  stats['final_picons_on_disk']=final_picon_counts(FINAL_PICONS)
  report.write_text(json.dumps({'run':run,'stats':stats,'pillow':PIL_OK,'master_commit':getattr(self,'master_commit',None),'note':'PiconHub production snapshot is read-only. Vhannibal and OpenATV 8 are checked and ingested; Chocholousek is disabled by user request. Optional additional feeds require a verified source-manifest.json. Identity matching uses exact service-reference filenames; no Warder IDs, production assets or GitHub content are changed.'},ensure_ascii=False,indent=2),encoding='utf-8')
  self.emit('done',(stats,str(report)))

 def sync_peer_sources(self,stats):
  """Discover and import current releases without ranking source artwork."""
  workspace=SOURCE_INGEST
  workspace.mkdir(parents=True,exist_ok=True)
  results={}
  self.emit('stage','3/5 · Kontrolujem Vhannibal a OpenATV 8')
  try:
   from vhannibal_source import sync_vhannibal
   result=sync_vhannibal(workspace)
   results['vhannibal']=result
   self.log(f'Vhannibal: {result["status"]}; import {result.get("imported",0)}, preskočené {result.get("skipped",0)}.')
  except Exception as exc:
   results['vhannibal']={'status':'unavailable','error':str(exc)[:300]}
   stats['source_errors']=stats.get('source_errors',0)+1
   self.log('Vhannibal nedostupný/nezmenený checkpoint zachovaný: '+str(exc)[:300])
  try:
   from openatv_feed import discover_current,download_package,naming_inventory
   from ipk_import import import_png_ipk, IMPORT_SCHEMA
   state_path=workspace/'openatv8-state.json'
   state=json.loads(state_path.read_text(encoding='utf-8')) if state_path.is_file() else {}
   current=discover_current()
   families=naming_inventory(current['packages'])
   # A matching feed index is not sufficient: previously skipped or absent SRP
   # archives must still be imported before the checkpoint is considered complete.
   missing=[]
   for package in current['packages']:
    archive=workspace/'archives'/'openatv8'/(package['sha256']+'.ipk')
    extracted=workspace/'originals'/'openatv8'/package['sha256']/package['sha256']
    if (not archive.is_file() or not extracted.is_dir() or
        not (extracted/'.warder-import-schema').is_file() or
        (extracted/'.warder-import-schema').read_text(encoding='ascii').strip()!=str(IMPORT_SCHEMA)):
     missing.append(package)
   changed=state.get('index_sha1')!=current['index_sha1']
   if not changed and not missing:
    results['openatv8']={'status':'unchanged','index_sha1':current['index_sha1'],
                         'packages':len(current['packages']),'naming_families':families}
   else:
    imported=skipped=downloaded=0
    for package in current['packages']:
     archive=workspace/'archives'/'openatv8'/(package['sha256']+'.ipk')
     if not archive.is_file():
      download_package(package,archive)
      downloaded+=1
     extracted=workspace/'originals'/'openatv8'/package['sha256']/package['sha256']
     if extracted.is_dir() and (not (extracted/'.warder-import-schema').is_file() or
         (extracted/'.warder-import-schema').read_text(encoding='ascii').strip()!=str(IMPORT_SCHEMA)):
      # Old import contains only regular logos. Move it aside until a new
      # complete atomic import succeeds; never delete source archives.
      backup=extracted.with_name(extracted.name+'.pre-srp-import')
      if backup.exists():
       import shutil
       shutil.rmtree(backup)
      extracted.rename(backup)
     outcome=import_png_ipk(archive,workspace/'originals'/'openatv8'/package['sha256'])
     imported+=outcome['imported'];skipped+=outcome['skipped']
    state={'schema':2,'index_sha1':current['index_sha1'],'packages':current['packages'],
           'checked_unix':int(time.time()),'imported_png':imported,'naming_families':families}
    atomic_json(state_path,state)
    results['openatv8']={'status':'updated','index_sha1':current['index_sha1'],
                         'downloaded':downloaded,'imported':imported,'skipped':skipped,
                         'naming_families':families}
   r=results['openatv8'];self.log(f'OpenATV 8: {r["status"]}; balíky {r.get("downloaded",0)}, import {r.get("imported",0)}.')
   self.log(f'OpenATV formáty feedu: SRP {families["srp"]["count"]}, UTF8SNP {families["utf8snp"]["count"]}; SRP prítomnosť je overená podľa názvu balíka.')
   if not families['srp']['count']:
    self.log('OpenATV UPOZORNENIE: feed neposkytol SRP balík; názvové PNG nemožno vydávať za SRP.')
  except Exception as exc:
   results['openatv8']={'status':'unavailable','error':str(exc)[:300]}
   stats['source_errors']=stats.get('source_errors',0)+1
   self.log('OpenATV 8 nedostupný/bez zmeny checkpointu: '+str(exc)[:300])
  # Chocholousek deliberately disabled by user request: no network probes or import.
  results['chocholousek']={'status':'disabled_by_user','downloaded':0,'imported':0}
  self.log('Chocholousek: vypnutý podľa zadania; bez kontroly siete a bez importu.')
  stats['peer_sources']=results
  stats['peer_source_imports']=sum(int(r.get('imported',r.get('imported_png',0)) or 0)
                                    for r in results.values() if isinstance(r,dict))

def installed_factory_version(app_dir=None):
 """Read the installed build marker, never the latest GitHub version."""
 location = Path(app_dir) if app_dir is not None else Path(__file__).resolve().parent
 try:
  value = json.loads((location / '.factory-version.json').read_text(encoding='utf-8'))['version']
  import re
  if isinstance(value, str) and re.fullmatch(r'factory-v\d+\.\d+\.\d+', value):
   return value
 except (OSError, ValueError, TypeError, KeyError):
  pass
 return 'neznáma verzia'


def final_picon_counts(folder):
 """Counts actual final PNG files; does not confuse work files with published ones."""
 folder = Path(folder)
 counts = {'transparent': 0, 'black': 0, 'white': 0, 'other': 0}
 if folder.is_dir():
  for file in folder.rglob('*.png'):
   try:
    variant = next((part for part in file.relative_to(folder).parts[:-1] if part.lower() in counts and part.lower() != 'other'), 'other')
    counts[variant] += 1
   except (OSError, ValueError):
    continue
 counts['total'] = sum(counts.values())
 return counts


class App:
 def __init__(self):
  self.installed_version=installed_factory_version()
  self.root=tk.Tk();self.root.title('WARDER PICON FACTORY — '+self.installed_version);self.root.geometry('900x550')
  self.events=queue.Queue();self.running=False
  frm=ttk.Frame(self.root,padding=18);frm.pack(fill='both',expand=True)
  ttk.Label(frm,text='WARDER PICON FACTORY',font=('Segoe UI',20,'bold')).pack(anchor='w')
  ttk.Label(frm,text='Automatické lokálne spracovanie bez zásahu do originálov a GitHubu').pack(anchor='w',pady=(0,12))
  self.version_label=ttk.Label(frm,text='Nainštalovaná verzia: '+self.installed_version);self.version_label.pack(anchor='w')
  self.production_label=ttk.Label(frm,text='Finálne uložené PNG: zisťujem...');self.production_label.pack(anchor='w')
  self._refresh_production_counts()
  self.status=tk.StringVar(value='Pripravujem...');ttk.Label(frm,textvariable=self.status,font=('Segoe UI',11)).pack(anchor='w')
  self.bar=ttk.Progressbar(frm,mode='determinate');self.bar.pack(fill='x',pady=12)
  self.work_area=ttk.Panedwindow(frm, orient='horizontal');self.work_area.pack(fill='both',expand=True)
  log_panel=ttk.Frame(self.work_area)
  self.output=tk.Text(log_panel,height=17,wrap='word',font=('Consolas',10));self.output.pack(fill='both',expand=True)
  self.work_area.add(log_panel,weight=45)
  from review_gallery import ReviewGallery
  self.gallery=ReviewGallery(self.work_area, REPORTS, DATA/'review-decisions.json', OUTPUT)
  self.work_area.add(self.gallery,weight=55)
  actions=ttk.Frame(frm);actions.pack(fill='x')
  ttk.Button(actions,text='Zobraziť iba nevyriešené výnimky',command=self.open_review).pack(side='left')
  ttk.Button(actions,text='Otvoriť priečinok reportov',command=self.open_reports).pack(side='left',padx=8)
  ttk.Label(frm,text=f'Zdrojové ZIP/PNG: {INBOX}  |  Rozpracované: {OUTPUT}  |  Finálne: {FINAL_PICONS}  |  Reporty: {REPORTS}').pack(anchor='w',pady=8)
  if os.environ.get("WARDER_GUI_SMOKE_TEST") != "1":
   self.root.after(150,self.start)
  self.root.after(100,self.poll)
  self.root.after(250,self._signal_launcher_ready)
  if os.environ.get("WARDER_GUI_SMOKE_TEST") == "1":
   self.root.after(200, self._signal_smoke_ready)
 def _refresh_production_counts(self):
  counts=final_picon_counts(FINAL_PICONS)
  self.production_label.configure(text='Finálne uložené PNG: '+str(counts['total'])+' (transparentné '+str(counts['transparent'])+', čierne '+str(counts['black'])+', biele '+str(counts['white'])+', ostatné '+str(counts['other'])+')')
 def _signal_launcher_ready(self):
  marker = os.environ.get("WARDER_FACTORY_GUI_READY_FILE")
  if marker:
   Path(marker).write_text("GUI_READY\n", encoding="utf-8")
 def _signal_smoke_ready(self):
  marker = os.environ.get("WARDER_GUI_SMOKE_READY_FILE")
  if marker:
   Path(marker).write_text("GUI_READY\n", encoding="utf-8")
 def open_review(self):
  from review_ui import ReviewWindow
  ReviewWindow(self.root, REPORTS, DATA/'review-decisions.json', OUTPUT)
 def open_reports(self):
  if os.name=='nt':os.startfile(str(REPORTS))
 def emit(self,k,v):self.events.put((k,v))
 def start(self):
  if self.running:return
  self.running=True;self.status.set('1/5 · Začínam synchronizáciu')
  def worker():
   try:Factory(self.emit).scan()
   except Exception:self.emit('error',traceback.format_exc())
  threading.Thread(target=worker,daemon=True).start()
 def poll(self):
  try:
   while True:
    k,v=self.events.get_nowait()
    if k=='stage':self.status.set(v)
    elif k=='log':self.output.insert('end',v+'\n');self.output.see('end')
    elif k=='progress':self.bar['maximum']=max(1,v[1]);self.bar['value']=v[0]
    elif k=='done':
     s,path=v;self.status.set('Hotovo · '+str(s['scanned'])+' PNG · QA opravené '+str(s.get('qa_repaired',0))+' · zostáva '+str(s.get('qa_review','?'))+' výnimiek.')
     self.output.insert('end','\nREPORT: '+path+'\n');self.running=False;self.gallery.reload()
     self._refresh_production_counts()
     self.output.insert('end','VERZIA: '+self.installed_version+' | Tento beh: '+str(s.get('changed',0))+' zmenených zdrojov, '+str(s.get('created',0))+' vytvorených záznamov, '+str(s.get('qa_repaired',0))+' QA opráv, '+str(s.get('review_queue_items',0))+' čaká na posúdenie.\n')
    elif k=='error':self.status.set('Chyba spracovania');self.output.insert('end',v);self.running=False
  except queue.Empty:pass
  self.root.after(100,self.poll)
if __name__=='__main__':
 multiprocessing.freeze_support()
 App().root.mainloop()
