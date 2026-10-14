Warning: truncated output (original token count: 30105)
Total output lines: 2234

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
   # Compress silver highlights while keeping existing dark chrome shadows.
   # Avoid the earlier heavy 42% global darkening and preserve tone ordering.
   def chrome_channel(v):
    return round(v*(0.90 if v<=125 else 0.90-0.22*(v-125)/130))
   result[i]=(chrome_channel(r),chrome_channel(g),chrome_channel(b),a)
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
 # Apply established contrast rules; do not outline whole logos merely because they are pale.
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

RENDER_REVISION = "plate-aware-v20-unified-clean-artwork"
QA_SCHEMA = 7

def render_png_task(args):
 # Independent process: Pillow decoding and PNG encoding use multiple CPU cores.
 path, output_dir, sha = args
 try:
  # The content-addressed cache must never accept a mismatched or malformed key.
  if not isinstance(sha,str) or len(sha)!=64 or any(c not in '0123456789abcdef' for c in sha):
   raise ValueError('INVALID_SOURCE_SHA256')
  digest=hashlib.sha256()
  with open(path,'rb') as source:
   for chunk in iter(lambda:source.read(1024*1024),b''):
    digest.update(chunk)
  if digest.hexdigest()!=sha:
   raise ValueError('SOURCE_SHA256_MISMATCH')
  with Image.open(path) as im:
   im.verify()
  with Image.open(path) as im:
   if not (1 <= im.width <= 4096 and 1 <= im.height <= 4096):
    raise ValueError('Neštandardné rozmery')
   from artwork_preparation import extract_flat_edge_background
   raw=im.convert('RGBA')
   # Reject empty artwork before creating a cache directory.
   if raw.getchannel('A').getbbox() is None:
    raise ValueError('FULLY_TRANSPARENT: source artwork contains no visible pixels')
   clean,extracted=extract_flat_edge_background(raw)
   if clean.getchannel('A').getbbox() is None:
    raise ValueError('EMPTY_AFTER_BACKGROUND_EXTRACTION: no visible artwork remains')
   rgba=_fit_canvas(clean)
  # Validate both plates before touching the output cache. A missing or
  # damaged plate must not leave a successful-looking transparent variant.
  for plate_name in ('black','white'):
   plate=Path(__file__).resolve().parent/'templates'/'picons'/(plate_name+'-sablona.png')
   with Image.open(plate) as template_image:
    template_image.verify()
   with Image.open(plate) as template_image:
    if template_image.size!=(220,132):
     raise ValueError('INVALID_WARDER_TEMPLATE: '+plate_name)
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
    expected=_template_sha256(bgname)
   if out.exists() and revision_marker.is_file() and revision_marker.read_text(encoding='ascii').strip()==RENDER_REVISION and (expected is None or (signature.exists() and signature.read_text(encoding='ascii')==expected)):
    try:
     with Image.open(out) as existing:
      existing.verify()
     with Image.open(out) as existing:
      if existing.size == (220,132) and existing.mode == 'RGBA':
       extrema=existing.getchannel('A').getextrema()
       if (bgname=='transparent' and extrema[1]>0) or (bgname!='transparent' and extrema==(255,255)):
        continue
    except Exception: pass
   # All three variants must use the same background-extracted artwork.
   # Using raw input for transparent left the original opaque background intact.
   render=_compose_variant(rgba,bgname)
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
  # A render is successful only when all three files are readable,
  # correctly sized, and the current render/template markers are present.
  if _output_signature_for_folder(dest) is None:
   raise ValueError('INCOMPLETE_RENDER_TRIPLET')
  return (True,created,'')
 except Exception as e:
  return (False,0,str(e))

def _output_signature_for_folder(folder):
 try:
  for name in ('transparent','black','white'):
   path=folder/(name+'.png')
   marker=folder/(name+'.render-revision')
   if not marker.is_file() or marker.read_text(encoding='ascii').strip()!=RENDER_REVISION:
    return None
   with Image.open(path) as im:
    im.verify()
   with Image.open(path) as im:
    if im.size!=(220,132) or im.mode!='RGBA':
     return None
    alpha=im.getchannel('A')
    if name=='transparent':
     if alpha.getbbox() is None:
      return None
    elif alpha.getextrema()!=(255,255):
     return None
   if name!='transparent':
    expected=_template_sha256(name)
    signature=folder/(name+'.template-sha256')
    if not signature.is_file() or signature.read_text(encoding='ascii').strip()!=expected:
     return None
  return True
 except (OSError,UnicodeError,ValueError):
  return None

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

def _template_sha256(name):
 """Cache immutable template bytes for the duration of a scan.

 The template fingerprint is invalidated when the file metadata changes,
 avoiding tens of thousands of redundant template reads during cache checks.
 """
 from functools import lru_cache
 template=Path(__file__).resolve().parent/'templates'/'picons'/(name+'-sablona.png')
 st=template.stat()
 return _cached_template_sha256(str(template),st.st_size,st.st_mtime_ns)

from functools import lru_cache
@lru_cache(maxsize=12)
def _cached_template_sha256(path,size,mtime_ns):
 return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def _hash_file_bytes(path):
 checksum=hashlib.sha256()
 with Path(path).open('rb') as stream:
  for block in iter(lambda:stream.read(1024*1024),b''):
   checksum.update(block)
 return checksum.hexdigest()

def _file_content_signature(path):
 """Hash bytes; metadata-only changes are accepted only after a matching re-read."""
 path=Path(path)
 before=path.stat()
 digest=_hash_file_bytes(path)
 after=path.stat()
 before_sig=(before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)
 after_sig=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns)
 if before_sig!=after_sig:
  verify_digest=_hash_file_bytes(path)
  verified=path.stat()
  if verify_digest!=digest or verified.st_size!=after.st_size:
   raise OSError('Output PNG content changed while hashing')
  after=verified
 return {'sha256':digest,'stat':[after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns]}

def _output_signature(sha):
 """Content signature for outputs tied to current templates and render rules.

 This deliberately hashes bytes without decoding. QA remains mandatory on a
 new/changed signature; unchanged bytes can reuse only matching QA-rule results.
 """
 folder=OUTPUT/sha[:2]/sha
 result={}
 try:
  for name in ('transparent','black','white'):
   path=folder/(name+'.png')
   if not path.is_file():return None
   revision_marker=folder/(name+'.render-revision')
   if not revision_marker.is_file() or revision_marker.read_text(encoding='ascii').strip()!=RENDER_REVISION:return None
   signature=_file_content_signature(path)
   if signature['stat'][2]<=0:return None
   result[name]=signature
   if name!='transparent':
    expected=_template_sha256(name)
    marker=folder/(name+'.template-sha256')
    if not marker.is_file() or marker.read_text(encoding='ascii').strip()!=expected:return None
    result[name+'_template_sha256']=expected
  return result
 except (OSError,UnicodeError,ValueError):
  return None


def _qa_signature_unchanged(before, after):
 """Compare content hashes and render-rule fingerprints, not timestamp metadata."""
 if not isinstance(before,dict) or not isinstance(after,dict):
  return False
 before_content={key:value.get('sha256') for key,value in before.items()
                 if isinstance(value,dict) and isinstance(value.get('sha256'),str)}
 after_content={key:value.get('sha256') for key,value in after.items()
                if isinstance(value,dict) and isinstance(value.get('sha256'),str)}
 before_rules={key:value for key,value in before.items() if key.endswith('_template_sha256')}
 after_rules={key:value for key,value in after.items() if key.endswith('_template_sha256')}
 required={'transparent','black','white'}
 return (set(before_content)==required and set(after_content)==required and
         before_content==after_content and before_rules==after_rules and
         set(before_rules)=={'black_template_sha256','white_template_sha256'})

def _qa_cache_entry_compatible(entry, current_signature, source_sha):
 """Reuse QA only for identical PNG bytes and unchanged QA/template rules."""
 if not isinstance(entry,dict) or current_signature is None:
  return False
 old=entry.get('signatures')
 if not isinstance(old,dict):
  return False
 old_content={key:value.get('sha256') for key,value in old.items()
              if isinstance(value,dict) and isinstance(value.get('sha256'),str)}
 new_content={key:value.get('sha256') for key,value in current_signature.items()
              if isinstance(value,dict) and isinstance(value.get('sha256'),str)}
 old_rules={key:value for key,value in old.items() if key.endswith('_template_sha256')}
 new_rules={key:value for key,value in current_signature.items() if key.endswith('_template_sha256')}
 required={'transparent','black','white'}
 return (entry.get('source_sha256')==source_sha and
         set(old_content)==required and set(new_content)==required and
         old_content==new_content and old_rules==new_rules and
         set(old_rules)=={'black_template_sha256','white_template_sha256'} and
         entry.get('qa_schema')==QA_SCHEMA and isinstance(entry.get('issues',[]),list))

def _record_repaired_sha(sha, repair_succeeded, remaining_issues, repaired_shas):
 """Track only repaired outputs that passed the immediate post-repair QA."""
 if repair_succeeded and not remaining_issues:
  repaired_…18105 tokens truncated… koreň uložený: '+str(path)+' · dáta sa nemenia; reštart načíta nové cesty.\n')
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
            "installed_version":self.installed_version,
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
   from factory_diagnostics_retry import retry_reports, retry_review_evidence_exports
   evidence_results=retry_review_evidence_exports(REPORTS,APP_DATA/'review-evidence-delivery.json',limit=5,token=token)
   for delivered in evidence_results:
    self.emit('diagnostics','review evidence '+delivered.get('report','')+': '+delivered.get('status','unknown')+
              (' · skupiny '+str(delivered.get('groups')) if delivered.get('status')=='sent' else ''))
   results=[]
   # Drain all pending reports in bounded batches, without rescanning PNG.
   while True:
    batch=retry_reports(REPORTS,_WORKSPACE['diagnostics_cache'],limit=5)
    results.extend(batch)
    if len(batch)<5 or any(item['status']!='sent' for item in batch):
     break
   sent=sum(item['status']=='sent' for item in results)
   failures=[item['report']+': '+item['status'] for item in results if item['status']!='sent']
   if not results:
    message='žiadne čakajúce reporty; nič nové sa neodoslalo'
   else:
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
  duration=max(0,int(time.monotonic()-self.started_at)) if self.started_at is not None else 0
  payload={'run':run,'created_utc':now.isoformat(),
           'stats':{'source_errors':1,'processing_failure':1,
                    'run_duration_seconds':duration,
                    'installed_factory_version':self.installed_version}}
  REPORTS.mkdir(parents=True,exist_ok=True)
  atomic_json(report,payload)
  threading.Thread(target=self._send_diagnostics,args=(str(report),),daemon=True).start()
 def emit(self,k,v):self.events.put((k,v))
 def _set_run_state(self,state,message):
  colors={'running':'#805500','success':'#176b2c','failed':'#b00020','cancelled':'#805500'}
  self.run_state=state
  self.status.set(message)
  label=getattr(self,'status_label',None)
  if label is not None:
   try:label.configure(foreground=colors.get(state,'#202020'))
   except Exception:pass
  if state=='failed' and hasattr(self,'bar'):
   self.bar['maximum']=1;self.bar['value']=0

 def start(self):
  if self.running or self.export_running:return
  if not self.workspace_ready:
   from tkinter import messagebox
   messagebox.showwarning('Zápisové operácie zablokované',
    'Read-only preflight nepotvrdil kompletnú pôvodnú štruktúru D:\\WARDER-PICON-FACTORY. Aplikácia nič nevytvorí, nepresunie ani neprepíše. Otvor Nastavenia → Preflight a pozri diagnostiku.',parent=self.root)
   return
  self.cancel_event.clear();self.close_requested=False
  self.running=True;self.started_at=time.monotonic();self._set_run_state('running','1/5 · Začínam synchronizáciu')
  self.bar['maximum']=1;self.bar['value']=0
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
     s,path=v;self._set_run_state('success','Hotovo · '+str(s['scanned'])+' PNG · QA opravené '+str(s.get('qa_repaired',0))+' · zostáva '+str(s.get('qa_review','?'))+' výnimiek.')
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
     self.running=False;self._set_run_state('cancelled','Beh bezpečne zastavený · čiastočné výstupy zostali obnoviteľné')
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
     self._set_run_state('failed','ZLYHANIE · beh nebol dokončený · posledný platný report a fronta zachované');self.output.insert('end',v);self.running=False
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
 if len(sys.argv)>1 and sys.argv[1]=='--migrate-master-approvals':
  # A source and one-file EXE entrypoint share the same conservative migrator.
  from master_approval_migration import main as migrate_master_approvals
  sys.exit(migrate_master_approvals(sys.argv[2:]))
 if os.environ.get('WARDER_RENDER_SMOKE')=='1':
  source=Path(os.environ['WARDER_RENDER_SOURCE'])
  target=Path(os.environ['WARDER_RENDER_TARGET'])
  sha=hashlib.sha256(source.read_bytes()).hexdigest()
  ok,count,error=render_png_task((str(source),str(target),sha))
  _,issues=qa_png_task((sha,str(target))) if ok else (sha,['RENDER_FAILED'])
  report={'ok':ok,'count':count,'error':error,'sha':sha,'qa_issues':issues}
  Path(os.environ['WARDER_RENDER_REPORT']).write_text(json.dumps(report),encoding='utf-8')
  sys.exit(0 if ok and not issues else 1)
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
