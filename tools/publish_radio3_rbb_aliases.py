#!/usr/bin/env python3
"""Preserve RBB radio3 approved HQ logo bytes for the broadcaster's LQ/MQ streams."""
import argparse, gzip, io, json, re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request,urlopen
from publish_warder_radio_approved_3 import SHA,RAW,archive,pack,pngcheck,readjson,writejson,remaining_entries
from publish_country_radio_picons import verify_receiver

ROOT=Path("picons/IPTV-DE")
SIZES=("50x30","220x132","400x240")
STYLES=("transparent","white","black")
HQ="4097_0_2_C634_62DF_ED_0_0_0_0.png"
ALIASES=(
 ("4097:0:2:4CD:9AC2:ED:0:0:0:0","radio 3 | rbb | LQ","http://www.rbbkultur.de/livemp3_s"),
 ("4097:0:2:F806:39F9:ED:0:0:0:0","radio 3 | rbb | MQ","http://www.rbbkultur.de/livemp3_m"),
)
NAMES=tuple(ref.replace(":","_")+".png" for ref,_,_ in ALIASES)
OLD="2026.11.04-2"
NEW="2026.11.04-3"

def package(sz,style):
 return ROOT/"packages"/("iptv-de-"+style+"-"+sz+".zip")

def old():
 release=readjson(ROOT/"catalog/release.json")
 plan=readjson(ROOT/"plan.json")
 assert (release["version"],release["stations"],release["reference_files_per_variant"])==(OLD,62,88)
 assert (plan["version"],plan["covered_stations"],plan["reference_files_per_variant"])==(NEW,64,90)
 entries=[a for a in plan["artwork"] if a["slug"]=="rbb-radio3-official-owner-approved"]
 assert len(entries)==1
 art=entries[0]
 assert art["stations"][0]["target"]==HQ and len(art["stations"])==3
 assert {(s["reference"],s["name"],s["stream_url"]) for s in art["stations"][1:]}==set(ALIASES)
 assert art["verified_bitrate_aliases"]["official_rbb_stream_list"]=="https://www.rbb-online.de/radio/frequenzen/livestreams.html"
 return release,art

def prepare():
 release,art=old()
 for sz in SIZES:
  for style in STYLES:
   meta=release["packages"][sz][style];path=package(sz,style);raw=path.read_bytes()
   assert SHA(raw)==meta["sha256"] and len(raw)==meta["bytes"]
   files=archive(raw)
   assert len(files)==88 and set(files)==set(meta["files"])
   assert all(SHA(b)==meta["files"][name] for name,b in files.items())
   assert HQ in files and all(name not in files for name in NAMES)
   img=files[HQ]
   assert SHA(img)==art["render_sha256"][sz][style]
   assert img==(ROOT/art["frozen_review_assets"][sz][style]).read_bytes()
   for name in NAMES:files[name]=img
   new=pack(files)
   assert archive(new)==files
   path.write_bytes(new)
   print("STAGED",sz,style,"88 -> 90 picons, all previous PNGs byte-identical")

def finalize(sha):
 assert re.fullmatch(r"[a-f0-9]{40}",sha)
 release,art=old()
 proofs={}
 for sz in SIZES:
  proofs[sz]={}
  for style in STYLES:
   meta=release["packages"][sz][style]
   before=meta["files"]
   raw=package(sz,style).read_bytes()
   files=archive(raw)
   assert set(files)==set(before)|set(NAMES)
   assert len(files)==90
   assert all(SHA(files[n])==v for n,v in before.items())
   assert all(files[n]==files[HQ] for n in NAMES)
   assert SHA(files[HQ])==art["render_sha256"][sz][style]
   digests={n:SHA(b) for n,b in sorted(files.items())}
   proofs[sz][style]={"previous_png_unchanged":88,"added_alias_hashes":{n:digests[n] for n in NAMES},
                      "package_sha256":SHA(raw),"bytes":len(raw)}
   meta.update(url=RAW+sha+"/"+str(package(sz,style)),bytes=len(raw),sha256=SHA(raw),files=digests)
 release.update(version=NEW,stations=64,reference_files_per_variant=90,payload_commit=sha)
 writejson(ROOT/"catalog/release.json",release)
 coverage=readjson(ROOT/"coverage.json")
 assert coverage["with_picons"]==62 and coverage["missing"]==3360
 coverage.update(with_picons=64,missing=3358)
 writejson(ROOT/"coverage.json",coverage)
 p=ROOT/"remaining.json.gz"
 obj,rows,key=remaining_entries(p.read_bytes())
 remaining=[s for s in rows if (s.get("reference") or s.get("service_reference")) not in {x[0] for x in ALIASES}]
 assert len(rows)-len(remaining)==2
 if key:obj[key]=remaining
 else:obj=remaining
 p.write_bytes(gzip.compress(json.dumps(obj,ensure_ascii=False,separators=(",",":")).encode(),compresslevel=9,mtime=0))
 readme=ROOT/"README.md"
 text=readme.read_text(encoding="utf-8")
 before="Current reviewed batch: 62 of 3422 catalogue stations, 88 references in every variant."
 after="Current reviewed batch: 64 of 3422 catalogue stations, 90 references in every variant."
 assert before in text
 readme.write_text(text.replace(before,after)+"\nWarder radio3 r3: two more officially documented bitrate references reuse the exact approved radio3 source image without recolouring. All 88 old PNGs/variant remain intact. Source: https://www.rbb-online.de/radio/frequenzen/livestreams.html\n",encoding="utf-8")
 writejson(ROOT/"catalog/radio3-bitrate-aliases-r3.json",dict(schema=1,status="verified",version=NEW,payload_commit=sha,
         source="https://www.rbb-online.de/radio/frequenzen/livestreams.html",
         rebrand="https://www.rbb-online.de/unternehmen/presse/presseinformationen/unternehmen/2024/20240214-aus-rbbkultur-wird-radio3-neuer-name-neuer-morgen-neue-stimmen.html",
         aliases=[dict(reference=a,name=b,stream_url=c) for a,b,c in ALIASES],
         old_pngs_preserved=True,new_references=2,files_per_variant=90,variants=proofs,
         receiver_hardware_tested=False))
 print("FINAL DE 64/3422 stations, 90 PNG per variant")

def verify():
 release=readjson(ROOT/"catalog/release.json")
 assert (release["version"],release["stations"],release["reference_files_per_variant"])==(NEW,64,90)
 coverage=readjson(ROOT/"coverage.json")
 assert (coverage["with_picons"],coverage["missing"])==(64,3358)
 assert len(remaining_entries((ROOT/"remaining.json.gz").read_bytes())[1])==3358
 proof=readjson(ROOT/"catalog/radio3-bitrate-aliases-r3.json")
 assert proof["payload_commit"]==release["payload_commit"]
 blobs={}
 for sz in SIZES:
  for style in STYLES:
   meta=release["packages"][sz][style]
   data=package(sz,style).read_bytes()
   assert meta["url"]==RAW+release["payload_commit"]+"/"+str(package(sz,style))
   assert SHA(data)==meta["sha256"] and len(data)==meta["bytes"]
   files=archive(data)
   assert set(files)==set(meta["files"]) and len(files)==90
   assert all(SHA(b)==meta["files"][n] for n,b in files.items())
   assert all(files[n]==files[HQ] for n in NAMES)
   for b in files.values():pngcheck(b,sz)
   blobs[package(sz,style).name]=data
 verify_receiver(release,blobs)
 print("PASS: 9 complete Warder packages, rbb alias identity, non-destructive native installer")

def public():
 release=readjson(ROOT/"catalog/release.json")
 def check(t):
  sz,style,meta=t
  with urlopen(Request(meta["url"],headers={"User-Agent":"WarderRadio3AliasChecker"}),timeout=40) as f:
   data=f.read(meta["bytes"]+1)
  assert len(data)==meta["bytes"] and SHA(data)==meta["sha256"]
  return sz,style
 tasks=[(sz,style,release["packages"][sz][style]) for sz in SIZES for style in STYLES]
 with ThreadPoolExecutor(max_workers=3) as ex:
  for sz,style in ex.map(check,tasks):print("PUBLIC VERIFIED",sz,style)

if __name__=="__main__":
 p=argparse.ArgumentParser();mx=p.add_mutually_exclusive_group(required=True)
 mx.add_argument("--prepare",action="store_true");mx.add_argument("--finalize",metavar="SHA")
 mx.add_argument("--verify",action="store_true");mx.add_argument("--public",action="store_true")
 a=p.parse_args()
 if a.prepare:prepare()
 elif a.finalize:finalize(a.finalize)
 elif a.verify:verify()
 else:public()
