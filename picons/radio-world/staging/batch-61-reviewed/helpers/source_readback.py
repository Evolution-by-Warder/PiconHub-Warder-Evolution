import gzip,json,concurrent.futures,subprocess,hashlib,io,sys
from pathlib import Path
from PIL import Image
stage=Path(__file__).resolve().parents[1];rows=json.loads(gzip.decompress((stage/'selection.json.gz').read_bytes()))['entries']
def check(x):
 r,key,(h,n,b)=x;u='https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/'+r['source_commit']+'/'+r['asset_root']+'/verified-assets/'+h+'.png'
 p=subprocess.run(['curl','-fLsS','--max-time','40',u],capture_output=True);assert p.returncode==0;raw=p.stdout;assert len(raw)==n and hashlib.sha256(raw).hexdigest()==h and hashlib.sha1(b'blob '+str(n).encode()+b'\0'+raw).hexdigest()==b
 im=Image.open(io.BytesIO(raw));assert im.mode=='RGBA' and im.size==tuple(map(int,key.split('/')[0].split('x')));alpha=im.getchannel('A').getextrema();Image.open(io.BytesIO(raw)).verify()
 return dict(variant=key,url=u,sha256=h,bytes=n,git_blob=b,alpha_extrema=alpha)
with concurrent.futures.ThreadPoolExecutor(max_workers=4)as p:out=list(p.map(check,[(r,k,v)for r in rows for k,v in r['variants'].items()]))
(stage/'source-readback-proof.json').write_text(json.dumps(dict(status='pass',source_commits=sorted({r['source_commit']for r in rows}),unchanged_approved_PNGs=len(out),actual_readback=out),indent=2)+'\n');print('PASS',len(out),'original PNG byte bodies, dimensions, RGBA and alpha')
