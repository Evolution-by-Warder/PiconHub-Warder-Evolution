from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from threading import Thread
from PIL import Image,ImageDraw
import tempfile,subprocess,sys,json,base64,gzip,hashlib,io,collections

def png(label):
 im=Image.new('RGBA',(240,100),'navy');ImageDraw.Draw(im).text((10,35),label,fill='white');out=io.BytesIO();im.save(out,'PNG');return out.getvalue()
known=png('Known Fixture Radio');new=png('New Fixture Radio');hits=collections.Counter()
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  hits[self.path]+=1;data={'/known.png':known,'/new.png':new,'/unsafe.svg':b'<svg xmlns="http://www.w3.org/2000/svg"><image href="https://example.invalid/external.png"/></svg>'}[self.path];self.send_response(200);self.end_headers();self.wfile.write(data)
 def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=Thread(target=server.serve_forever,daemon=True);thread.start();base=f'http://127.0.0.1:{server.server_port}'
rows=[]
for ref,name,country,path in [('new-ref','Known Fixture Radio','GB','known.png'),('wrong-name','Another Station','GB','known.png'),('wrong-country','Known Fixture Radio','US','known.png'),('candidate','New Fixture Radio','GB','new.png'),('already-saved','New Fixture Radio','GB','new.png'),('unsafe-svg','Unsafe Fixture Radio','GB','unsafe.svg')]:rows.append(dict(reference=ref,name=name,country=country,url='http://example.invalid/stream/'+ref,group='Fixture group',station_id=ref,favicon_urls=[base+'/'+path],homepages=[]))
hash_known=hashlib.sha256(known).hexdigest();seed={'project':'Radio plugin','catalogue_snapshot':'fixture','ready_references':['already-saved'],'reviewed_source_hashes':[hash_known],'approved_graphics':{hash_known+'|GB|knownfixtureradio':{'reference':'previous-approved-reference','render_fingerprint':'previous-nine-png-fingerprint'}},'queue':rows}
with tempfile.TemporaryDirectory(prefix='radio-artwork-test-') as tmp:
 root=Path(tmp);p=root/'seed.b64';p.write_bytes(base64.b64encode(gzip.compress(json.dumps(seed).encode())));out=root/'result';subprocess.run([sys.executable,str(Path(__file__).parent/'recover_radio_catalogue_artwork.py'),'--seed',str(p),'--output',str(out),'--workers','4'],check=True,stdout=subprocess.DEVNULL);state=json.loads((out/'discovery-state.json').read_text())['stations'];assert 'already-saved' not in state
 assert state['new-ref']['status']=='reuse_verified_graphic_pending_import';assert state['new-ref']['approved_graphic_reference']=='previous-approved-reference';assert state['new-ref']['expected_render_fingerprint']=='previous-nine-png-fingerprint'
 assert state['candidate']['status']=='candidate_catalogue_artwork_needs_visual_identity'
 for ref in ['wrong-name','wrong-country','unsafe-svg']:assert state[ref]['status']=='blocked_no_new_usable_catalogue_artwork'
 for row in rows:
  if row['reference'] not in state:continue
  for key in ['name','url','group','reference']:assert row[key]==state[row['reference']][key]
 assert hits['/known.png']==1 and hits['/new.png']==1 and hits['/unsafe.svg']==1
server.shutdown();print('Passed: exact approved-source/name/country reuse; wrong identity blocked; novel image candidate only; seed preserved; unsafe SVG blocked; URL cache single fetch; receiver identity unchanged.')
