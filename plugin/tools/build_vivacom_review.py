from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json,hashlib
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/"picons/13.0e/vivacom"
MAST=ROOT/"plugin/artwork/templates/picons"
OUT=ROOT/"review/vivacom-20261103"
CHANNELS=[
("Diema Sport HD","19","130","2648","19"),
("Diema Sport 2","1","14A","2648","19"),
("Diema Sport 3","1","145","2648","19"),
("MAX Sport 1","1","13AC","2710","19"),
("MAX Sport 2","1","13AD","2710","19"),
("MAX Sport 3","1","139","2648","19"),
("MAX Sport 4","19","138A","2710","19"),
("Ring HD","1","140","2648","19"),
("Nova sport Bulgaria","1","D0","25E4","16")]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def make():
 OUT.mkdir(parents=True,exist_ok=True)
 masters={s:Image.open(MAST/(s+"-sablona.png")).convert("RGBA") for s in ("white","black")}
 assert all(x.size==(220,132) for x in masters.values())
 records=[]
 canvas=Image.new("RGB",(820,9*190+90),(220,226,234))
 draw=ImageDraw.Draw(canvas)
 draw.text((18,12),"VIVACOM 13E  |  WARDER ARTWORK REVIEW  |  NOT RELEASED",fill=(10,18,35))
 for col,style in enumerate(("transparent","white","black")):draw.text((200+col*205,46),style.upper(),fill=(20,25,40))
 for idx,(name,typ,sid,tsid,oldtype) in enumerate(CHANNELS):
  src=BASE/"transparent"/f"1_0_{oldtype}_{sid}_{tsid}_D5_820000_0_0_0.png"
  assert src.is_file(),str(src)
  logo=Image.open(src).convert("RGBA")
  assert logo.size==(220,132),str(src)
  # The approved transparent original is the only artwork source.
  # Alpha-composite it on the untouched frozen MASTER backgrounds.
  ref=f"1_0_{typ}_{sid}_{tsid}_13E_820000_0_0_0.png"
  draw.text((12,100+idx*190),name,fill=(20,25,40))
  for col,style in enumerate(("transparent","white","black")):
   im=logo.copy() if style=="transparent" else Image.alpha_composite(masters[style].copy(),logo)
   dest=OUT/style/ref
   dest.parent.mkdir(exist_ok=True)
   im.save(dest)
   canvas.paste(im.convert("RGB"),(160+col*215,120+idx*190))
   draw.rectangle((159+col*215,119+idx*190,381+col*215,253+idx*190),outline=(130,145,165),width=1)
   records.append(dict(name=name,style=style,reference=ref,sha256=digest(dest),source=str(src),output=str(dest)))
 canvas.save(OUT/"review-sheet.png")
 (OUT/"review-manifest.json").write_text(json.dumps({"status":"OWNER_APPROVAL_REQUIRED","master_sha256":{s:digest(MAST/(s+"-sablona.png")) for s in masters},"picons":records},indent=2)+"\n")
 print("REVIEW ONLY",len(records),"PNG images",flush=True)
if __name__=="__main__":make()
