#!/usr/bin/env python3
"""Read-only Vhannibal November 2026 audit. No upstream archives are redistributed."""
import collections,datetime,hashlib,io,json,pathlib,re,urllib.request,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=ROOT/"reports/vhannibal-nov2026"
URL="https://www.vhannibal.net/download_setting.php?action=download&id="
def get(id):
 req=urllib.request.Request(URL+str(id),headers={"User-Agent":"Mozilla/5.0 (compatible; Warder-Reference-Audit/1.0)","Referer":"https://www.vhannibal.net/"})
 with urllib.request.urlopen(req,timeout=90) as response:return response.read()
def members(data,depth=0):
 with zipfile.ZipFile(io.BytesIO(data)) as z:
  for name in z.namelist():
   if name.endswith("/"):continue
   blob=z.read(name)
   if name.lower().endswith(".zip") and depth<2:
    yield from members(blob,depth+1)
   else:yield name,blob
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 local=collections.defaultdict(list)
 for p in (ROOT/"picons").glob("**/*.png"):
  if p.parent.name in ("transparent","black","white"):local[p.name.upper()].append(p)
 print("Local PNG references",len(local),flush=True)
 info={}
 for id,label in [(1,"vhannibal-picon-motor"),(5,"vhannibal-motor-settings")]:
  try:
   data=get(id);h=hashlib.sha256(data).hexdigest()
   records=list(members(data))
   info[label]={"source_url":URL+str(id),"sha256":h,"bytes":len(data),"files":len(records),"sample":[n for n,_ in records[:12]]}
   if label=="vhannibal-picon-motor":picons=records
   else:settings=records
   print(label,len(records),flush=True)
  except Exception as e:
   info[label]={"error":str(e)[:400]}
 if "picons" not in locals():
  (OUT/"audit.json").write_text(json.dumps({"status":"SOURCE_UNAVAILABLE","sources":info},indent=2)+"\n")
  raise RuntimeError("Official picon source unavailable; no comparison possible")
 names={}
 for name,data in picons:
  base=pathlib.PurePosixPath(name).name.upper()
  if base.endswith(".PNG") and re.match(r"^1_0_[0-9A-F_]+\.PNG$",base):
   names.setdefault(base,(name,data))
 added=sorted(set(names)-set(local))
 shared=sorted(set(names)&set(local))
 changed=[]
 for name in shared:
  source=hashlib.sha256(names[name][1]).hexdigest()
  if not any(hashlib.sha256(p.read_bytes()).hexdigest()==source for p in local[name] if p.parent.name=="transparent"):
   changed.append(name)
 missing_styles={name:sorted({"transparent","black","white"}-{p.parent.name for p in paths}) for name,paths in local.items() if len({p.parent.name for p in paths})<3}
 result={"status":"AUDIT_ONLY_NO_PUBLICATION","date":"2026-11-04","sources":info,"source_picon_references":len(names),"local_references":len(local),"source_new_references":len(added),"source_existing_references":len(shared),"existing_different_source_bytes":len(changed),"local_missing_styles":len(missing_styles),"new_references":added,"different_source_bytes":changed,"missing_styles":missing_styles}
 (OUT/"audit.json").write_text(json.dumps(result,indent=2)+"\n")
 lines=["# Vhannibal November 2026 vs Warder PiconHub","","> Comparison only. No picons have been added, overwritten or published.","",f"- Source references: {len(names)}",f"- Already named in PiconHub: {len(shared)}",f"- New service-reference filenames: {len(added)}",f"- Same reference, different PNG bytes: {len(changed)} (not necessarily outdated)",f"- Existing Warder references lacking all three styles: {len(missing_styles)}","","## First 100 new references","",*["- "+x for x in added[:100]],"","## First 100 differing source images","",*["- "+x for x in changed[:100]],"","See audit.json for full lists. Existing artwork must not be replaced without visual review."]
 (OUT/"audit.md").write_text("\n".join(lines)+"\n")
 print("AUDIT",len(added),len(changed),flush=True)
if __name__=="__main__":main()
