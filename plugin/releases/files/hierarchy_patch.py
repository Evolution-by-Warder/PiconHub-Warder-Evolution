# -*- coding: utf-8 -*-
from __future__ import print_function
import re
from . import plugin as p

POS_RE = re.compile(r'_(\d+(?:\.\d+)?)([ew])$', re.I)
FAVORITES = ('skylink_23.5e','magiosat_0.8w','antiksat_16.0e','freesat_0.8w','telly_0.8w')
FAV_LABELS = {'skylink_23.5e':'★ Skylink  •  23.5E','magiosat_0.8w':'★ MagioSat  •  0.8W','antiksat_16.0e':'★ AntikSAT  •  16.0E','freesat_0.8w':'★ freeSAT  •  0.8W','telly_0.8w':'★ Telly  •  0.8W'}
_old_defs=p._server_package_defs
_old_resolve=p.PiconHubStyleUpdateEngine._resolve_entries
_old_load=p.load_settings

def migrated_load():
 data=_old_load(); changed=[]
 for key in data.get('packages',[]):
  low=str(key or '').lower().strip()
  changed.append('full_'+low[4:] if low.startswith('sat_') else key)
 data['packages']=list(dict.fromkeys(changed)); return data

def _parts(key,label):
 m=POS_RE.search(str(key or ''))
 if not m or float(m.group(1))==0.0: return None
 slug=str(key)[:m.start()].lower()
 if not slug or slug=='satellite': return None
 deg=float(m.group(1)); direction=m.group(2).upper(); pos='%s%s'%(m.group(1),direction)
 provider=re.sub(r'\s+\d+(?:\.\d+)?°?[EW]\s*$','',str(label or key),flags=re.I).strip()
 if not provider: provider=slug.replace('-',' ').replace('_',' ').title()
 return deg,direction,pos,provider

def hierarchical_defs(settings):
 try:
  eng=p.PiconHubStyleUpdateEngine(settings,timeout=5); cat=eng._fetch_json(settings.get('catalog_url') or p.DEFAULT_CATALOG_URL); groups={}; present=set()
  for item in cat.get('packages') or []:
   if not isinstance(item,dict): continue
   key=str(item.get('id') or item.get('package') or '').strip(); q=_parts(key,item.get('name') or key)
   if not q: continue
   deg,direction,pos,provider=q; present.add(key); groups.setdefault((deg,direction,pos),[]).append((provider.lower(),key,provider))
  out=[]
  for key in FAVORITES:
   if key in present: out.append((key,FAV_LABELS[key]))
  for deg,direction,pos in sorted(groups,key=lambda x:(x[0],0 if x[1]=='E' else 1)):
   out.append(('full_'+pos.lower(),'%s  FULL'%pos))
   for _s,key,provider in sorted(groups[(deg,direction,pos)]): out.append((key,'----- %s'%provider))
  if out: return out
 except Exception as e: print('[PiconHub] hierarchy load error:',e)
 return _old_defs(settings)

def expanded_resolve(self):
 original=list(self.active_packages)
 try:
  cat=self._fetch_json(self.catalog_url); ids=[]
  for item in cat.get('packages') or []:
   if isinstance(item,dict):
    key=str(item.get('id') or item.get('package') or '').strip()
    if key: ids.append(key)
  expanded=[]
  for wanted in original:
   low=str(wanted or '').lower().strip()
   if low.startswith('full_'): suffix='_'+low[5:]; expanded += [x for x in ids if x.lower().endswith(suffix)]
   elif low.startswith('sat_'): suffix='_'+low[4:]; expanded += [x for x in ids if x.lower().endswith(suffix)]
   else: expanded.append(wanted)
  self.active_packages=list(dict.fromkeys(expanded)); return _old_resolve(self)
 finally: self.active_packages=original

p.load_settings=migrated_load
p._server_package_defs=hierarchical_defs
p.PiconHubStyleUpdateEngine._resolve_entries=expanded_resolve
