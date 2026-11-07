"""Read exact immutable evidence into runner temp, never into package payloads."""
import argparse,hashlib,urllib.request
from pathlib import Path
PREFIX='https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/'
SPECS=[('snapshot.json','2322e554ea89b024db8c184ed193e5be40c8a996',5618333,'e97f6edfbea8c020e137f58b6e2b493aeb0123edaf179acd5defac9dfd4b13ee'),('final.json','890c9edb644d676f5b33855268f39aefbad65be8',7088290,'5caa5d293c351c73e161fa1cbc5ff252949a2605a517e1086d8949c644d0f593')]
def main():
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);a=p.parse_args();a.directory.mkdir(parents=True,exist_ok=True)
    for name,commit,count,digest in SPECS:
        f=a.directory/name
        raw=f.read_bytes()if f.exists()else urllib.request.urlopen(PREFIX+commit+'/picons/radio-world/staging/zeno-primary-20261107/checkpoint/source-review-rows.json',timeout=90).read(count+1)
        assert len(raw)==count and hashlib.sha256(raw).hexdigest()==digest
        if not f.exists():f.write_bytes(raw)
        print('Verified frozen evidence:',name,count,digest)
if __name__=='__main__':main()
