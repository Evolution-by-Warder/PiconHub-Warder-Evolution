import os, sys, sqlite3, hashlib, zipfile, shutil, threading, queue, json, time, traceback, urllib.request, urllib.error, tempfile, io, subprocess
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
from master_registry import index_master_tree, classify_candidate, is_master_path
from workspace_paths import resolve_root, workspace_paths, read_only_preflight, verify_required_directories

ROOT=resolve_root()
_WORKSPACE=workspace_paths(ROOT)
APP=_WORKSPACE['app']
DATA=_WORKSPACE['data']
INBOX=_WORKSPACE['inbox']
ORIGINALS=_WORKSPACE['originals']
OUTPUT=_WORKSPACE['output']
FINAL_PICONS=_WORKSPACE['final']
EXCEPTIONS=_WORKSPACE['exceptions']
REPORTS=_WORKSPACE['reports']
REGISTRY=_WORKSPACE['registry']
MASTER_ROOT=_WORKSPACE['master_root']
LOGS=_WORKSPACE['logs']
APP_DATA=_WORKSPACE['app_data']
DB=_WORKSPACE['db']
SOURCE_STATE=_WORKSPACE['source_state']
SOURCE_MANIFEST=_WORKSPACE['source_manifest']
SOURCE_INGEST=_WORKSPACE['ingest']
# Cancellation is cooperative: downloads and atomic writes finish their
# current bounded operation, while no new candidate work is scheduled.
class ScanCancelled(Exception):
 pass

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
 # A substantial opaque black logo plate is part of the source artwork.
 # Protect its entire rectangle, including white/chrome letters inside it.
 dark=[a>=240 and max(r,g,b)<=65 for r,g,b,a in pixels]
 dark_seen=bytearray(width*height)
 for start in range(len(pixels)):
  if not dark[start] or dark_seen[start]:
   continue
  stack=[start]
  dark_seen[start]=1
  component=[]
  left=right=start%width
  top=bottom=start//width
  while stack:
   pos=stack.pop()
   component.append(pos)
   x,y=pos%width,pos//width
   left=min(left,x);right=max(right,x)
   top=min(top,y);bottom=max(bottom,y)
   for nx,ny in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
    if 0<=nx<width and 0<=ny<height:
     idx=ny*width+nx
     if dark[idx] and not dark_seen[idx]:
      dark_seen[idx]=1
      stack.append(idx)
  area=(right-left+1)*(bottom-top+1)
  if len(component)>=180 and right-left>=18 and bottom-top>=9 and len(component)/area>=0.35 and any(
      pixels[yy*width+xx][3]>=240 and min(pixels[yy*width+xx][:3])>=180
      for yy in range(top,bottom+1) for xx in range(left,right+1)):
   for yy in range(top,bottom+1):
    protected[yy*width+left:yy*width+right+1]=bytes([1])*(right-left+1)
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
 # Multi-tone neutral metallic ink is a gradient, not flat lettering.
 # Preserve relative silver highlights and shadows on the white template.
 gray_tones={round((r+g+b)/3/12)*12 for i,(r,g,b,a) in enumerate(pixels)
             if a>=128 and not protected[i] and max(r,g,b)-min(r,g,b)<=22}
 metallic=(background=='white' and sum(1 for i,(r,g,b,a) in enumerate(pixels) if a>=128 and not protected[i] and max(r,g,b)-min(r,g,b)<=22)>=100 and len(gray_tones)>=5
           and max(gray_tones)-min(gray_tones)>=65
           and max(gray_tones)>=205)
 result=list(pixels)
 changed=False
 ink=(30,30,30) if background=='white' else (238,238,238)
 for i,(r,g,b,a) in enumerate(pixels):
  if protected[i] or a<96 or max(r,g,b)-min(r,g,b)>35:
   continue
  low=(min(r,g,b)>=135) if background=='white' else (max(r,g,b)<=145)
  if metallic and background=='white':
   # One monotone mapping for the entire neutral metallic gradient.
   # Do not turn individual highlights into black patches.
   result[i]=(round(r*0.58),round(g*0.58),round(b*0.58),a)
   changed=True
  elif low:
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
   # Dark blue lettering can be above 0.18 luminance yet disappear
   # against the black template. Large chromatic brand plates remain
   # protected by the connected-component mask above.
   if luminance>=0.32:
    continue
   target=min(1.0,value*0.46/max(luminance,0.03))
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

RENDER_REVISION = "plate-aware-v17"

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
 def __init__(self,emit,cancel_event=None,preflight=None):
  self.emit=emit
  self.cancel_event=cancel_event or threading.Event()
  # A cached GUI preflight is useful for status, but can become stale while a
  # mounted workspace changes. Re-inventory immediately before any write.
  preflight=read_only_preflight(ROOT)
  structure_ok, findings=verify_required_directories(ROOT)
  if not preflight.ok or not structure_ok:
   raise PermissionError('Read-only preflight neprešiel; zápis zablokovaný: '+ '; '.join(findings or preflight.findings[-2:]))
  for p in (APP,APP_DATA,INBOX,SOURCE_INGEST,ORIGINALS,REGISTRY,MASTER_ROOT,OUTPUT,FINAL_PICONS,EXCEPTIONS,REPORTS,LOGS):p.mkdir(parents=True,exist_ok=True)
  self.log_path=LOGS/('factory-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.log')
  # Both source and packaged EXE consult the same signed-by-policy manifest
  # authority. The EXE never attempts to install the Python-only ZIP in place.
  from factory_auto_update import fetch, validate_manifest, version_tuple
  try:
   from factory_auto_update import MANIFEST_URL
   current=version_tuple(installed_factory_version())
   update=validate_manifest(json.loads(fetch(MANIFEST_URL)),current)
   if update:
    self.log('Overená novšia Factory: '+update['version']+'; samostatný EXE sa neprepisuje počas behu.')
  except (OSError,ValueError,KeyError,TypeError) as exc:
   self.log('Kontrola manifestu nedostupná ('+type(exc).__name__+'); pokračujem lokálne.')
  self.db=sqlite3.connect(str(DB))
  self.db.execute('CREATE TABLE IF NOT EXISTS files (path TEXT PRIMARY KEY, sha256 TEXT, size INTEGER, modified_ns INTEGER, status TEXT, last_run TEXT)')
  self.db.execute('CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, scanned INTEGER, changed INTEGER, duplicates INTEGER, exceptions INTEGER, created INTEGER)')
  self.db.commit()
  self.legacy_db=None
  legacy_db_path=APP_DATA/'factory.sqlite3'
  if legacy_db_path.is_file() and legacy_db_path.resolve()!=DB.resolve():
   try:
    self.legacy_db=sqlite3.connect(legacy_db_path.resolve().as_uri()+'?mode=ro',uri=True)
    self.legacy_db.execute('SELECT 1 FROM files LIMIT 1').fetchone()
   except sqlite3.Error:
    if self.legacy_db is not None:self.legacy_db.close()
    self.legacy_db=None
 def cached_file(self,columns,path):
  """Use canonical state first, then query the old app database read-only."""
  columns=columns if isinstance(columns,str) else ','.join(columns)
  row=self.db.execute(f'SELECT {columns} FROM files WHERE path=?',(path,)).fetchone()
  if row is None and self.legacy_db is not None:
   try:row=self.legacy_db.execute(f'SELECT {columns} FROM files WHERE path=?',(path,)).fetchone()
   except sqlite3.Error:row=None
  return row
 def log(self,msg):
  line=datetime.now().astimezone().isoformat(timespec='seconds')+' '+str(msg)
  with self.log_path.open('a',encoding='utf-8') as stream:
   stream.write(line+'\n');stream.flush()
  self.emit('log',msg)
 def check_cancelled(self):
  if self.cancel_event.is_set():
   raise ScanCancelled('Používateľ bezpečne zastavil beh Factory')
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
    dest=MASTER_ROOT/commit/Path(*parts)
    key='github:'+rel
    old=self.cached_file('sha256',key)
    if dest.exists():
     if not dest.is_file() or dest.stat().st_size!=int(e.get('size') or 0):
      raise RuntimeError('Registry snapshot path already exists with different content; refusing overwrite: '+str(dest))
     # Validate even if the previous process stopped before checkpointing.
     h=hashlib.sha1(); h.update(('blob '+str(dest.stat().st_size)+'\0').encode('ascii'))
     with open(dest,'rb') as previous:
      for piece in iter(lambda:previous.read(1048576),b''):h.update(piece)
     if h.hexdigest()!=e.get('sha'):
      raise RuntimeError('Registry snapshot SHA mismatch; existing file preserved: '+str(dest))
     if not old or old[0]!=e.get('sha'):
      self.db.execute('INSERT OR REPLACE INTO files VALUES (?,?,?,?,?,?)',(key,e.get('sha'),dest.stat().st_size,0,'SOURCE_SYNC',datetime.now().isoformat()))
     skipped+=1;continue
    jobs.append((e,dest,key))
   self.db.commit()
   self.log(f'PiconHub: {len(entries)} PNG, už uložených {skipped}, na stiahnutie {len(jobs)}.')
   if not jobs:
    self.master_paths=master_paths
    atomic_json(_WORKSPACE['master_paths'],{'commit':commit,'paths':master_paths})
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
    atomic_json(_WORKSPACE['master_paths'],{'commit':commit,'paths':master_paths})
   else:
    self.log('Warder Master checkpoint nemenil som, pretože nie všetky aktuálne PNG sa overili.')
  except Exception as e:
   self.log('ZDROJ NEDOSTUPNÝ: PiconHub ('+str(e)+')')
 def scan(self):
  run=datetime.now().strftime('%Y%m%d-%H%M%S-%f'); stats=dict(scanned=0,changed=0,duplicates=0,exceptions=0,created=0)
  self.log('Začínam spracovanie '+run)
  self.fetch_sources()
  self.check_cancelled()
  if not hasattr(self,'master_paths'):
   try:
    master_paths_file=_WORKSPACE['master_paths']
    if not master_paths_file.is_file() and (APP_DATA/'master-current-paths.json').is_file():
     master_paths_file=APP_DATA/'master-current-paths.json'
    saved=json.loads(master_paths_file.read_text(encoding='utf-8'))
    self.master_paths=saved.get('paths',[]);self.master_commit=saved.get('commit')
   except (OSError,ValueError,AttributeError):self.master_paths=[]
  self.emit('stage','3/5 · Importujem lokálne ZIP archívy')
  if not PIL_OK:self.log('Pillow nie je dostupný: grafické varianty sa nevytvoria; iba inventarizácia.')
  # Safe, bounded, atomic import; originals never overwritten.
  for archive in sorted(INBOX.rglob('*.zip')):
   self.check_cancelled()
   try:
    result=import_png_zip(archive,ORIGINALS)
    self.log(f'Archív {archive.name}: import {result["imported"]}, preskočené {result["skipped"]}')
   except Exception as e:
    stats['exceptions']+=1
    self.log('CHYBA archívu '+archive.name+': '+str(e))
  # The three requested peer sources are integrated into the same resumable
  # ingestion tree. Each source owns its checkpoint and failure isolation.
  self.sync_peer_sources(stats)
  self.check_cancelled()
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
      notify=lambda key,state:self.log(f'{key}: {state}'), state_dir=DATA, originals_dir=ORIGINALS,
      legacy_state_dir=APP_DATA)
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
  master_root=MASTER_ROOT/getattr(self,'master_commit','') if getattr(self,'master_commit',None) else MASTER_ROOT
  registry={'schema':1,'authority':'PiconHub-Warder-Evolution/warder-master-production',
            'service_count':0,'asset_count':0,'rejected_paths':0,'services':{},'conflicts':[]}
  if master_root.is_dir():
   try:
    master_cache_path=_WORKSPACE['master_cache']
    legacy_cache=APP_DATA/'master-registry-cache.json'
    read_cache=master_cache_path if master_cache_path.is_file() else legacy_cache
    previous_cache=json.loads(read_cache.read_text(encoding='utf-8')) if read_cache.is_file() else {}
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
  output_cache_path=_WORKSPACE['output_cache']
  try:
   legacy_cache=APP_DATA/'output-cache.json'
   read_cache=output_cache_path if output_cache_path.is_file() else legacy_cache
   output_cache=json.loads(read_cache.read_text(encoding='utf-8')).get('items',{})
   if not isinstance(output_cache,dict):output_cache={}
  except (OSError,ValueError,AttributeError):output_cache={}
  candidates=[]
  for base in (ORIGINALS,INBOX,SOURCE_INGEST/'originals'):
   for p in base.rglob('*'):
    self.check_cancelled()
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
    self.check_cancelled()
    stats['scanned']+=1
    try:
     st=p.stat();rel=str(p)
     old=self.cached_file(('sha256','size','modified_ns','status'),rel)
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
  # Real-data verification: use the actual PNG paths from this run, not synthetic examples.
  # One bounded evidence archive per run; never mutate source files or Master Registry.
  try:
   from live_png_test import build_live_test
   live_result=build_live_test(
    collision_path, output_path=REPORTS/('warder-live-png-test-'+run+'.zip'), limit=10)
   stats['live_png_test']=live_result['summary']
   self.log('LIVE PNG TEST: '+str(live_result['cases'])+' reálnych kolízií; '+
            str(live_result['summary'])+'; dôkazy: '+live_result['output'])
  except ValueError as exc:
   self.log('LIVE PNG TEST: bez vhodných kolízií alebo neplatný report: '+str(exc))
  except Exception as exc:
   stats['live_png_test_error']=type(exc).__name__+': '+str(exc)[:200]
   self.log('LIVE PNG TEST NEÚSPEŠNÝ: '+stats['live_png_test_error'])

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
     self.check_cancelled()
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
  review_path=EXCEPTIONS/('review-queue-'+run+'.json')
  # Pixel equivalence is artwork evidence only; never a service identity approval.
  from artwork_pixel_groups import candidate_pixel_digests
  review_pixel_digests=candidate_pixel_digests(registry_matches,OUTPUT)
  review_queue=apply_decisions(build_review_queue(qa_issues,hashes,collisions,registry_matches,
                                                   pixel_digests=review_pixel_digests),
                               _WORKSPACE["ledger_path"],_WORKSPACE["legacy_ledger"])
  if PIL_OK and master_root.is_dir():
   from artwork_pixel_groups import master_artwork_pixel_digests, attach_master_pixel_comparisons
   master_pixels=master_artwork_pixel_digests(registry,master_root,REGISTRY/'openatv-pixel-evidence-cache.json')
   master_comparisons=attach_master_pixel_comparisons(review_queue,master_pixels,review_pixel_digests)
   stats['master_artwork_pixel_comparisons']=master_comparisons
   self.log('QA Master RGBA zhody (len evidencia, bez schvalenia): '+str(master_comparisons))
  save_review_queue(review_path,review_queue)
  from qa_backlog_diagnostics import explain_review_backlog
  backlog=explain_review_backlog(review_queue)
  backlog_path=REPORTS/('qa-backlog-causes-'+run+'.json')
  atomic_json(backlog_path,backlog)
  from review_batch import artwork_review_batch
  batch_path=REPORTS/('artwork-review-batch-10-'+run+'.json')
  atomic_json(batch_path,artwork_review_batch(review_queue,limit=10))
  self.log('QA grafika: prvych 10 stabilnych kontrolnych ID (bez schvalenia): '+str(batch_path))
  stats['qa_backlog_causes']=backlog['pending_by_reason']
  stats['qa_pending_by_workstream']=backlog['pending_by_workstream']
  stats['qa_pending_review_tasks']=backlog['pending_review_tasks']
  stats['qa_grouping_savings']=backlog['grouping_savings']
  self.log('QA PREČO ZOSTÁVAJÚ: '+str(backlog['pending_by_reason'])+'; report: '+str(backlog_path))
  self.log('QA ÚSPORA ZOSKUPENÍM: '+str(backlog['grouping_savings']))
  stats['review_queue_items']=review_queue['count']
  stats['review_workstreams']=review_queue.get('workstream_counts', {})
  self.log('QA pracovné fronty: '+', '.join(f'{name}={count}' for name,count in review_queue.get('workstream_counts', {}).items()))
  self.log(f'Výnimky na rozhodnutie: {review_queue["count"]}; vizuálne upozornenia sú evidované osobitne v QA reporte: {review_path}')
  # End-of-run read-only integrity gate: source content must still match its ID.
  integrity=audit_artifacts(hashes,OUTPUT,source_hashes_verified=False)
  integrity_path=REPORTS/('integrity-'+run+'.json')
  atomic_json(integrity_path,integrity)
  stats['integrity_issues']=integrity['issue_count']
  self.log(f'Integrita: {integrity["checked"]} zdrojov, {integrity["issue_count"]} problémov; report: {integrity_path}')
  # Only locally staged NEW identities with one unambiguous artwork and clean QA.
  # No Master Registry writes or semantic approvals are performed.
  self.check_cancelled()
  from factory_finalization import finalize_new_candidates
  integrity_blocked={issue['sha256'] for issue in integrity['issues']}
  new_candidate_shas={row.get('candidate_sha256') for row in registry_matches if row.get('classification')=='NEW'}
  unique_shas=set(unique)
  verified_for_finalization={sha for sha in new_candidate_shas if sha in unique_shas and sha not in qa_issues and sha not in integrity_blocked and _output_signature(sha) is not None and (sha in qa_targets or (current_signatures.get(sha) is not None and sha not in qa_targets))}
  finalized=finalize_new_candidates(registry_matches,qa_issues,OUTPUT,FINAL_PICONS,verified_shas=verified_for_finalization)
  stats['new_candidate_finalization']=finalized
  self.log('Lokálne finálne NEW-CANDIDATES: '+str(finalized))
  self.db.execute('INSERT INTO runs VALUES (?,?,?,?,?,?)',(run,stats['scanned'],stats['changed'],stats['duplicates'],stats['exceptions'],stats['created']))
  self.db.commit()
  report=REPORTS/('report-'+run+'.json')
  stats['installed_factory_version']=installed_factory_version()
  stats['final_picons_on_disk']=final_picon_counts(FINAL_PICONS)
  report.write_text(json.dumps({'run':run,'stats':stats,'pillow':PIL_OK,'master_commit':getattr(self,'master_commit',None),'note':'PiconHub production snapshot is read-only. Vhannibal, OpenATV 8 and Chocholousek are checked as candidate sources. Optional additional feeds require a verified source-manifest.json. Identity matching uses exact service-reference filenames; no Warder IDs, production assets or GitHub content are changed.'},ensure_ascii=False,indent=2),encoding='utf-8')
  self.emit('done',(stats,str(report)))

 def sync_peer_sources(self,stats):
  """Discover and import current releases without ranking source artwork."""
  workspace=SOURCE_INGEST
  workspace.mkdir(parents=True,exist_ok=True)
  results={}
  self.emit('stage','3/5 · Kontrolujem Vhannibal a OpenATV 8')
  try:
   from vhannibal_source import sync_vhannibal
   result=sync_vhannibal(workspace,state_dir=DATA,originals_dir=ORIGINALS,legacy_state_dir=APP_DATA)
   results['vhannibal']=result
   self.log(f'Vhannibal: {result["status"]}; import {result.get("imported",0)}, preskočené {result.get("skipped",0)}.')
  except Exception as exc:
   results['vhannibal']={'status':'unavailable','error':str(exc)[:300]}
   stats['source_errors']=stats.get('source_errors',0)+1
   self.log('Vhannibal nedostupný/nezmenený checkpoint zachovaný: '+str(exc)[:300])
  try:
   from openatv_feed import discover_current,download_package,naming_inventory
   from ipk_import import import_png_ipk, IMPORT_SCHEMA
   state_path=DATA/'openatv8-state.json'
   legacy_state=APP_DATA/'openatv8-state.json'
   read_state=state_path if state_path.is_file() else legacy_state
   state=json.loads(read_state.read_text(encoding='utf-8')) if read_state.is_file() else {}
   current=discover_current()
   families=naming_inventory(current['packages'])
   # A matching feed index is not sufficient: previously skipped or absent SRP
   # archives must still be imported before the checkpoint is considered complete.
   missing=[]
   schema_root=ORIGINALS/'openatv8'/('schema-'+str(IMPORT_SCHEMA))
   for package in current['packages']:
    archive=workspace/'archives'/'openatv8'/(package['sha256']+'.ipk')
    extracted=schema_root/package['sha256']
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
     extracted=schema_root/package['sha256']
     outcome=import_png_ipk(archive,schema_root)
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
  try:
   from chocholousek_source import sync_chocholousek
   try:
    choice=json.loads(_WORKSPACE['chocho_positions'].read_text(encoding='utf-8'))
    positions=choice.get('positions',[]) if isinstance(choice,dict) else []
   except (OSError,ValueError,TypeError):
    positions=[]
   result=sync_chocholousek(workspace,selected_positions=positions,state_dir=DATA,originals_dir=ORIGINALS,
                            legacy_state_dir=APP_DATA)
   results['chocholousek']=result
   if result['status']=='selection_required':
    self.log('Chocholousek: zdroj je dostupný; vyber aktívne pozície v Nastaveniach (bez automatického odhadu).')
   else:
    self.log(f'Chocholousek: {result["status"]}; archívy {result.get("downloaded",0)}, import {result.get("imported_png",0)} PNG.')
  except Exception as exc:
   results['chocholousek']={'status':'unavailable','error':str(exc)[:300]}
   stats['source_errors']=stats.get('source_errors',0)+1
   self.log('Chocholousek nedostupný/bez zmeny checkpointu: '+str(exc)[:300])
  stats['peer_sources']=results
  stats['peer_source_imports']=sum(int(r.get('imported',r.get('imported_png',0)) or 0)
                                    for r in results.values() if isinstance(r,dict))

def installed_factory_version(app_dir=None):
 """Read the installed build marker, never the latest GitHub version."""
 from factory_build_info import bundled_metadata_path
 location = Path(app_dir) if app_dir is not None else bundled_metadata_path('.factory-version.json').parent
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
  from factory_build_info import build_commit, executable_path
  self.build_commit=build_commit()
  self.executable_path=executable_path()
  self.root=tk.Tk();self.root.title('WARDER PICON FACTORY — '+self.installed_version);self.root.geometry('1480x930');self.root.minsize(1200,760)
  try:
   dpi=float(self.root.winfo_fpixels('1i'))
   self.root.tk.call('tk','scaling',max(1.0,min(2.25,dpi/72.0)))
  except (tk.TclError,ValueError,TypeError):pass
  self._configure_style()
  self.workspace_ready=False
  self._automatic_run_started=False
  self.preflight_result=None
  self._final_counts_running=False
  self._final_counts_refresh_pending=False
  self.final_counts_ready=False
  self.events=queue.Queue();self.running=False;self.export_running=False;self.started_at=None
  self.cancel_event=threading.Event();self.close_requested=False
  self.root.protocol('WM_DELETE_WINDOW',self.on_close)
  self._delivery_lock=threading.Lock()
  from factory_workspace import FactoryWorkspace
  self.workspace=FactoryWorkspace(self,self.root,_WORKSPACE)
  self.status.set('Read-only preflight · kontrolujem 13 adresárov; zápisy zostávajú zablokované')
  self.root.after(100,self.poll)
  self.root.after(350,self._load_saved_review_counts)
  self.run_preflight()
  if os.environ.get("WARDER_GUI_SMOKE_TEST") == "1":
   self.root.after(200, self._signal_smoke_ready)
 def _configure_style(self):
  style=ttk.Style(self.root)
  try:style.theme_use('vista' if os.name=='nt' else 'clam')
  except tk.TclError:pass
  style.configure('.',font=('Segoe UI',11))
  style.configure('TLabel',padding=(2,3))
  style.configure('TButton',padding=(14,9),font=('Segoe UI',11,'bold'))
  style.configure('TNotebook.Tab',padding=(17,11),font=('Segoe UI',11,'bold'))
  style.configure('Treeview',rowheight=32,font=('Segoe UI',11))
  style.configure('Treeview.Heading',font=('Segoe UI',11,'bold'),padding=(8,9))
  style.configure('TLabelframe',padding=8)
 def log_workspace_change(self,path):
  self.output.insert('end','Pracovný koreň uložený: '+str(path)+' · dáta sa nemenia; reštart načíta nové cesty.\n')
  self.output.see('end')
 def restart(self):
  if self.running or self.export_running:
   from tkinter import messagebox
   messagebox.showwarning('Aplikácia pracuje','Počkaj na dokončenie aktívnej úlohy pred reštartom.',parent=self.root)
   return
  command=[sys.executable]
  if not getattr(sys,'frozen',False):command.append(str(Path(__file__).resolve()))
  command.extend(sys.argv[1:])
  subprocess.Popen(command,cwd=str(Path(sys.executable).resolve().parent))
  self.root.destroy()
 def run_preflight(self):
  if self.running or self.export_running:
   self.status.set('Preflight sa nedá obnoviť počas aktívneho zápisu');return
  self.workspace_ready=False
  self.status.set('Read-only preflight · inventarizujem existujúci workspace')
  def worker():
   try:self.emit('preflight_done',read_only_preflight(ROOT,progress=lambda current,total,name:self.emit('preflight_progress',(current,total,name))))
   except Exception as exc:self.emit('preflight_error',type(exc).__name__+': '+str(exc)[:300])
  threading.Thread(target=worker,name='factory-read-only-preflight',daemon=True).start()
 def _load_saved_review_counts(self):
  try:
   from review_ui import latest_review
   from review_queue import load_review_queue
   path=latest_review(EXCEPTIONS,REPORTS)
   if path is None:
    self.counts_status.set('Čakajúce úlohy: bez uloženého reportu')
    return
   data=load_review_queue(path)
   lanes=data.get('workstream_counts',{})
   self.counts_status.set('Čakajúce úlohy: '+str(data['count'])+
    ' | Identita: '+str(lanes.get('IDENTITY_VERIFICATION',0))+
    ' | Grafika: '+str(lanes.get('ARTWORK_REVIEW',0))+
    ' | Technické QA: '+str(lanes.get('TECHNICAL_QA',0)))
  except (OSError,ValueError,KeyError,TypeError) as exc:
   self.counts_status.set('Čakajúce úlohy: report nedostupný ('+type(exc).__name__+')')
 def _refresh_production_counts(self):
  if self._final_counts_running:
   self._final_counts_refresh_pending=True
   return
  self._final_counts_refresh_pending=False
  self._final_counts_running=True
  def worker():
   try:self.emit('final_counts_done',final_picon_counts(FINAL_PICONS))
   except Exception as exc:self.emit('final_counts_error',type(exc).__name__+': '+str(exc)[:240])
  threading.Thread(target=worker,name='factory-final-output-counts',daemon=True).start()
 def _signal_launcher_ready(self):
  marker = os.environ.get("WARDER_FACTORY_GUI_READY_FILE")
  if marker:
   Path(marker).write_text("GUI_READY\n", encoding="utf-8")
 def _signal_smoke_ready(self):
  if self.preflight_result is None:
   self.root.after(100,self._signal_smoke_ready);return
  if not self.final_counts_ready:
   self.root.after(100,self._signal_smoke_ready);return
  if self.workspace._source_refreshing:
   self.root.after(100,self._signal_smoke_ready);return
  if not self.preflight_result.ok:
   raise RuntimeError('GUI smoke: read-only workspace preflight failed: '+', '.join(self.preflight_result.missing))
  expected={'Zdroje','Master Registry','Kandidáti','Grafický motor','QA',
            'Finalizácia','Nastavenia','Diagnostika'}
  tabs={self.workspace.notebook.tab(tab,'text') for tab in self.workspace.notebook.tabs()}
  missing=expected-tabs
  if missing:
   raise RuntimeError('GUI smoke: missing workspace panels: '+', '.join(sorted(missing)))
  source_inventory=[self.workspace.source_tree.item(row,'values') for row in self.workspace.source_tree.get_children()]
  inbox=next((row for row in source_inventory if row and row[0]=='Lokálny inbox'),None)
  if inbox is None or inbox[2] != '1 ZIP · 0 PNG':
   raise RuntimeError('GUI smoke: dashboard/source inventory counters are not reading the synthetic workspace: '+repr(inbox))
  if not self.workspace.kpi_vars['queue'].get().startswith('0 '):
   raise RuntimeError('GUI smoke: review counter did not read the persisted empty queue')
  if not self.workspace.kpi_vars['final'].get().startswith('0 '):
   raise RuntimeError('GUI smoke: final-output counter is not reading the actual output folder')
  pending=list(self.root.winfo_children())
  while pending:
   widget=pending.pop()
   pending.extend(widget.winfo_children())
   if isinstance(widget,ttk.Button) and not widget.cget('command'):
    raise RuntimeError('GUI smoke: button without action: '+str(widget))
  marker = os.environ.get("WARDER_GUI_SMOKE_READY_FILE")
  if marker:
   import json
   payload={"status":"GUI_READY","build_commit":self.build_commit,
            "executable_path":self.executable_path,"data_root":str(ROOT),
            "preflight":"ok" if self.preflight_result and self.preflight_result.ok else "blocked",
            "tabs":sorted(tabs)}
   Path(marker).write_text(json.dumps(payload,ensure_ascii=False)+"\n", encoding="utf-8")
  if os.environ.get("WARDER_GUI_SMOKE_TEST") == "1":
   self.root.after(150, self.root.destroy)
 def open_review(self):
  if not self.workspace_ready:return
  from review_ui import ReviewWindow
  ReviewWindow(self.root, EXCEPTIONS, _WORKSPACE['ledger_path'], OUTPUT, legacy_report_dir=REPORTS, master_root=MASTER_ROOT)
 def open_reports(self):
  if not self.workspace_ready:
   self.status.set('Reporty sa neotvárajú, kým read-only preflight neprejde');return
  if os.name=='nt':os.startfile(str(REPORTS))
  elif sys.platform=='darwin':subprocess.Popen(['open',str(REPORTS)])
  else:subprocess.Popen(['xdg-open',str(REPORTS)])
 def export_pending(self):
  from tkinter import messagebox
  target=ROOT.parent/'WARDER-PICONS-PENDING.zip'
  if not self.workspace_ready:
   messagebox.showwarning('Preflight required','Export je zablokovaný, kým nie je overená pôvodná štruktúra.',parent=self.root);return
  if self.running or self.export_running:
   messagebox.showwarning('Factory pracuje','Export je dostupný až po dokončení behu.',parent=self.root);return
  if target.exists():
   messagebox.showwarning('ZIP už existuje','Najskôr presuň alebo premenuj existujúci '+str(target),parent=self.root);return
  self.export_running=True
  self.status.set('Balím čakajúce PNG do D:\\WARDER-PICONS-PENDING.zip ...')
  def worker():
   try:
    from factory_pending_export import export_pending
    result=export_pending(EXCEPTIONS,OUTPUT,target,ledger_path=_WORKSPACE['ledger_path'],
                          legacy_report_dir=REPORTS,legacy_ledger_path=_WORKSPACE['legacy_ledger'])
    self.emit('export_done',result)
   except Exception as exc:self.emit('export_error',str(exc))
  threading.Thread(target=worker,daemon=True).start()
 def request_cancel(self):
  if not self.running:
   self.status.set('Žiadny spracovateľský beh nie je aktívny');return
  self.cancel_event.set()
  self.status.set('Zastavujem bezpečne · dokončujem aktuálne sťahovanie alebo atómový zápis')
  self.emit('log','Požiadavka na zastavenie prijatá. Dokončí sa aktuálna bezpečná operácia; nič sa nefinalizuje čiastočne.')
 def on_close(self):
  if self.running or self.export_running:
   from tkinter import messagebox
   if not messagebox.askyesno('Bezpečné ukončenie',
       'Prebieha spracovanie alebo export. Požiadať o bezpečné zastavenie a zavrieť okno po dokončení aktuálnej operácie?',parent=self.root):
    return
   self.close_requested=True
   if self.running:self.request_cancel()
   else:self.status.set('Export prebieha · aplikácia sa zavrie po jeho bezpečnom dokončení')
   return
  self.root.destroy()
 def _close_when_ready(self):
  if self.close_requested and not self.running and not self.export_running:
   self.close_requested=False
   self.root.after_idle(self.root.destroy)
 def configure_github(self):
  from tkinter import messagebox
  from factory_github_credentials import load_token
  if not self.workspace_ready:
   messagebox.showwarning('Preflight required','Diagnostika zostane lokálna, kým sa neoverí existujúca adresárová štruktúra.',parent=self.root);return
  if load_token(_WORKSPACE['github_credentials']):
   messagebox.showinfo('GitHub prenos','Existujúce prihlásenie je dostupné. Odosielam čakajúce reporty bez nového skenovania.',parent=self.root)
   threading.Thread(target=self._send_diagnostics,args=(None,),daemon=True).start()
   return
  import shutil,subprocess
  gh=shutil.which('gh')
  if not gh:
   messagebox.showwarning('GitHub prenos','GitHub CLI (gh) nie je nainštalované. Automatické prihlásenie vyžaduje GitHub CLI; neodoslané dáta zostávajú lokálne.',parent=self.root)
   return
  if not messagebox.askyesno('GitHub prenos','Otvoriť jednorazové bezpečné prihlásenie cez GitHub CLI? GitHub si autorizáciu zapamätá pre ďalšie spustenia.',parent=self.root):
   return
  def login_worker():
   try:
    # gh handles the browser/device flow and stores the credential in its own
    # credential manager. Never capture or log the access token.
    creationflags=getattr(subprocess,'CREATE_NEW_CONSOLE',0)
    result=subprocess.run([gh,'auth','login','--hostname','github.com','--web','--git-protocol','https','--scopes','repo'],
                          timeout=300,creationflags=creationflags,check=False)
    if result.returncode==0:
     self.emit('diagnostics','GitHub prihlásenie dokončené; odosielam čakajúce dáta.')
     self._send_diagnostics(None)
    else:self.emit('diagnostics','GitHub prihlásenie nedokončené; dáta zostali lokálne.')
   except (OSError,subprocess.TimeoutExpired):
    self.emit('diagnostics','GitHub prihlásenie sa nepodarilo; dáta zostali lokálne.')
  threading.Thread(target=login_worker,daemon=True).start()
 def _scheduled_delivery(self):
  # Retry in small bounded batches while the GUI is open. A failed or slow
  # request cannot block Tk, and the delivery lock prevents overlap.
  if not self.running:
   threading.Thread(target=self._send_diagnostics,args=(None,),daemon=True).start()
  self.root.after(60000,self._scheduled_delivery)
 def _resume_pending_delivery(self):
  # A restart must NOT rescan 162k PNG merely to retry GitHub delivery.
  self.status.set('Pripravené · obnovujem čakajúce odosielanie bez skenovania')
  threading.Thread(target=self._send_diagnostics,args=(None,),daemon=True).start()
 def _send_diagnostics(self,report_path):
  if not self._delivery_lock.acquire(blocking=False):
   self.emit('diagnostics','prenos už prebieha; druhý paralelný prenos nespúšťam')
   return
  try:
   from factory_github_credentials import load_token
   token=load_token(_WORKSPACE['github_credentials'])
   if not token:
    self.emit('diagnostics','prihlásenie nedostupné; reporty a PNG ponechané lokálne')
    return
   os.environ['WARDER_DIAGNOSTICS_TOKEN']=token
   from factory_diagnostics_retry import retry_reports
   results=retry_reports(REPORTS,_WORKSPACE['diagnostics_cache'],limit=5)
   sent=sum(item['status']=='sent' for item in results)
   failures=[item['report']+': '+item['status'] for item in results if item['status']!='sent']
   message=('potvrdené odoslanie '+str(sent)+'/'+str(len(results))+'; '+('; '.join(failures) if failures else 'všetky prijaté'))
   self.emit('diagnostics',message)
   from factory_png_evidence import upload_png_evidence
   evidence=upload_png_evidence(EXCEPTIONS,state_path=APP_DATA/'png-evidence-delivered.json',max_attempts=20,legacy_report_dir=REPORTS)
   if evidence['attempted'] or evidence.get('errors'):
    self.emit('diagnostics','PNG dôkazy: '+str(evidence['sent'])+'/'+str(evidence['attempted'])+'; stav '+evidence['status']+'; chyby: '+', '.join(evidence.get('errors',[])[:3]))
  except Exception as exc:
   self.emit('diagnostics','prenos nedokončený ('+type(exc).__name__+'); lokálne dáta zachované')
  finally:
   self._delivery_lock.release()
 def _record_failed_run(self):
  # A failed run must reach the same bounded, allowlisted GitHub telemetry
  # pipeline as a successful scan. Never upload tracebacks or local paths.
  from datetime import timezone
  now=datetime.now(timezone.utc)
  run=now.strftime('%Y%m%d-%H%M%S-%f')
  report=REPORTS / ('report-'+run+'.json')
  payload={'run':run,'created_utc':now.isoformat(),
           'stats':{'source_errors':1,'installed_factory_version':self.installed_version}}
  REPORTS.mkdir(parents=True,exist_ok=True)
  atomic_json(report,payload)
  threading.Thread(target=self._send_diagnostics,args=(str(report),),daemon=True).start()
 def emit(self,k,v):self.events.put((k,v))
 def start(self):
  if self.running or self.export_running:return
  if not self.workspace_ready:
   from tkinter import messagebox
   messagebox.showwarning('Zápisové operácie zablokované',
    'Read-only preflight nepotvrdil kompletnú pôvodnú štruktúru D:\\WARDER-PICON-FACTORY. Aplikácia nič nevytvorí, nepresunie ani neprepíše. Otvor Nastavenia → Preflight a pozri diagnostiku.',parent=self.root)
   return
  self.cancel_event.clear();self.close_requested=False
  self.running=True;self.started_at=time.monotonic();self.status.set('1/5 · Začínam synchronizáciu')
  def worker():
   factory=None
   try:
    factory=Factory(self.emit,self.cancel_event,self.preflight_result);factory.scan()
   except ScanCancelled as exc:self.emit('cancelled',str(exc))
   except Exception:self.emit('error',traceback.format_exc())
   finally:
    if factory is not None:
     try:factory.db.close()
     except Exception:pass
     if factory is not None and factory.legacy_db is not None:
      try:factory.legacy_db.close()
      except Exception:pass
  threading.Thread(target=worker,daemon=True).start()
 def poll(self):
  if self.running:
   last=getattr(self,'_last_progress_at',self.started_at)
   if last is not None:
    idle=int(time.monotonic()-last)
    if idle>=30:
     stage=getattr(self,'_current_stage','spracovanie')
     self.status.set('PRACUJE / ČAKÁ NA OPERÁCIU · bez nového priebehu '+str(idle)+' s · posledná fáza: '+str(stage))
  try:
   pending_logs=[]
   while True:
    k,v=self.events.get_nowait()
    if k=='log':
     pending_logs.append(str(v))
     if len(pending_logs)>=256:
      self.output.insert('end','\n'.join(pending_logs)+'\n')
      pending_logs.clear()
     continue
    if pending_logs:
     self.output.insert('end','\n'.join(pending_logs)+'\n')
     self.output.see('end')
     pending_logs.clear()
    if k=='stage':
     self._current_stage=str(v)
     self._last_progress_at=time.monotonic()
     self.status.set(v)
    elif k=='progress':
     self.bar['maximum']=max(1,v[1]);self.bar['value']=v[0]
     self._last_progress_at=time.monotonic()
     self._last_progress=v
    elif k=='done':
     s,path=v;self.status.set('Hotovo · '+str(s['scanned'])+' PNG · QA opravené '+str(s.get('qa_repaired',0))+' · zostáva '+str(s.get('qa_review','?'))+' výnimiek.')
     self.output.insert('end','\nREPORT: '+path+'\n');self.running=False;self.gallery.reload()
     if self.started_at is not None:
      seconds=int(time.monotonic()-self.started_at)
      self.output.insert('end',f'TRVANIE: {seconds//60} min {seconds%60} s\n')
     # Report counts are already verified by the completed scan; show them
     # immediately while the independent on-disk recount runs in background.
     disk=s.get('final_picons_on_disk') or {}
     if isinstance(disk,dict) and 'total' in disk:
      self.production_label.configure(text='Lokálne kandidátske PNG podľa reportu: '+str(disk['total'])+' (transparentné '+str(disk.get('transparent',0))+', čierne '+str(disk.get('black',0))+', biele '+str(disk.get('white',0))+') · overujem disk')
      if hasattr(self.workspace,'kpi_vars'):
       self.workspace.kpi_vars['final'].set(str(disk['total'])+' lokálnych kandidátskych PNG (neschválené)')
     self._refresh_production_counts()
     self.workspace.refresh_all()
     final=s.get('new_candidate_finalization',{})
     self.output.insert('end','FINÁLNE NEW-CANDIDATES: '+str(final.get('copied',0))+
       ' PNG zapísaných, '+str(final.get('already_present',0))+
       ' existujúcich trojíc, '+str(final.get('conflicts',0))+
       ' konfliktov, '+str(final.get('qa_blocked',0))+
       ' zablokovaných QA, '+str(final.get('invalid',0))+' neplatných.\n')
     threading.Thread(target=self._send_diagnostics,args=(path,),daemon=True).start()
     lanes=s.get('review_workstreams',{})
     self.counts_status.set('Čakajúce úlohy: '+str(s.get('review_queue_items','?'))+' | Identita: '+str(lanes.get('IDENTITY_VERIFICATION','?'))+' | Grafika: '+str(lanes.get('ARTWORK_REVIEW','?'))+' | Technické QA: '+str(lanes.get('TECHNICAL_QA','?')))
     self.output.insert('end','VERZIA: '+self.installed_version+' | Tento beh: '+str(s.get('changed',0))+' zmenených zdrojov, '+str(s.get('created',0))+' vytvorených záznamov, '+str(s.get('qa_repaired',0))+' QA opráv, '+str(s.get('review_queue_items',0))+' čaká na posúdenie.\n')
     self._close_when_ready()
    elif k=='cancelled':
     self.running=False;self.status.set('Beh bezpečne zastavený · čiastočné výstupy zostali obnoviteľné')
     self.output.insert('end','ZASTAVENÉ: '+v+'\n')
     self._close_when_ready()
    elif k=='diagnostics':
     self.output.insert('end','GITHUB DIAGNOSTIKA: '+v+'\n')
    elif k=='source_inventory_done':
     self.workspace.show_sources(v)
    elif k=='source_inventory_error':
     self.workspace.source_inventory_error(v)
    elif k=='final_counts_done':
     self._final_counts_running=False;self.final_counts_ready=True
     counts=v
     self.production_label.configure(text='Lokálne kandidátske PNG (nie publikované): '+str(counts['total'])+' (transparentné '+str(counts['transparent'])+', čierne '+str(counts['black'])+', biele '+str(counts['white'])+', ostatné '+str(counts['other'])+')')
     if hasattr(self,'workspace') and hasattr(self.workspace,'kpi_vars'):
      self.workspace.kpi_vars['final'].set(f"{counts['total']:,} lokálnych kandidátskych PNG (neschválené)".replace(',',' '))
     if self._final_counts_refresh_pending:self._refresh_production_counts()
    elif k=='final_counts_error':
     self._final_counts_running=False;self.final_counts_ready=True
     self.production_label.configure(text='Lokálny výstup sa nepodarilo spočítať: '+v)
     if hasattr(self,'workspace') and hasattr(self.workspace,'kpi_vars'):
      self.workspace.kpi_vars['final'].set('Počítanie zlyhalo · pozri Diagnostiku')
     if self._final_counts_refresh_pending:self._refresh_production_counts()
    elif k=='preflight_progress':
     current,total,name=v
     self.status.set('Read-only preflight · '+str(current)+'/'+str(total)+' · '+name+' · kontrolujem súbory')
    elif k=='preflight_done':
     self.preflight_result=v;self.workspace_ready=bool(v.ok)
     self.workspace.show_preflight(v)
     self.workspace.update_runtime_identity(v)
     if v.ok:
      # Confirm a pending update only after the workspace preflight succeeds.
      self._signal_launcher_ready()
      self.status.set('Preflight úspešný · 13 kategórií prečítaných · zápisové operácie povolené')
      if os.environ.get('WARDER_GUI_SMOKE_TEST')!='1':
       self.root.after(150,self._resume_pending_delivery)
       self.root.after(60000,self._scheduled_delivery)
       # Begin the normal production pipeline only after read-only preflight
       # validates the existing D: workspace. Never auto-approve review items.
       if not self._automatic_run_started:
        self._automatic_run_started=True
        self.root.after(500,self.start)
     else:
      self.status.set('Zápisy zablokované · preflight: '+(', '.join(v.missing) or 'chyba čítania'))
      self.output.insert('end','READ-ONLY PREFLIGHT FAILED\n'+'\n'.join(v.findings)+'\n')
      self.output.see('end')
    elif k=='preflight_error':
     self.workspace_ready=False;self.preflight_result=None
     self.workspace.update_runtime_identity(None,error=v)
     self.status.set('Preflight zlyhal · všetky zápisy zostávajú zablokované')
     self.output.insert('end','PREFLIGHT ERROR: '+v+'\n');self.output.see('end')
    elif k=='export_done':
     self.export_running=False
     self.status.set('Export dokončený: '+v['path'])
     self.output.insert('end','EXPORT: '+str(v)+'\n')
     self._close_when_ready()
    elif k=='export_error':
     self.export_running=False
     self.status.set('Export zlyhal');self.output.insert('end','EXPORT CHYBA: '+v+'\n')
     self._close_when_ready()
    elif k=='error':
     self.status.set('Chyba spracovania');self.output.insert('end',v);self.running=False
     try:self._record_failed_run()
     except (OSError,ValueError,TypeError) as exc:
      self.output.insert('end','\nDiagnostika chyby sa nedala uložiť: '+type(exc).__name__+'\n')
     self._close_when_ready()
  except queue.Empty:pass
  if pending_logs:
   self.output.insert('end','\n'.join(pending_logs)+'\n')
   self.output.see('end')
  self.root.after(100,self.poll)
if __name__=='__main__':
 multiprocessing.freeze_support()
 try:
  App().root.mainloop()
 except Exception:
  detail=traceback.format_exc()
  try:
   # A startup crash must not trigger another potentially hours-long scan.
   # Verify only the existing top-level layout before writing a local log.
   if verify_required_directories(ROOT)[0]:
    startup_log=_WORKSPACE['startup_log']
    startup_log.parent.mkdir(parents=True,exist_ok=True)
    startup_log.write_text(detail,encoding='utf-8')
  except OSError:
   pass
  try:
   from tkinter import messagebox
   messagebox.showerror('WARDER PICON FACTORY','Aplikácia sa nepodarila spustiť. Read-only preflight: '+str(ROOT)+'\nDiagnostika (iba po úspešnom preflightu):\n'+str(_WORKSPACE['startup_log']))
  except Exception:
   pass
  raise
