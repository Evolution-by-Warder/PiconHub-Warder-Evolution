import tempfile,threading,io
from pathlib import Path
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from PIL import Image,ImageDraw,ImageFont
import final_logo_pass as p
assert not p.identity('WXYZ 90.1',{'titles':['WXYZ Radio']},'University College')
assert p.identity('WXYZ 90.1',{'titles':['WXYZ Radio']},'WXYZ')
assert not p.identity('Moody Radio WXYZ',{'titles':['Moody Radio WXYZ']},'Moody Uplift')
assert p.identity('Radio Tessera',{'titles':['Radio Tessera']},'TESSERA RADIO')
assert not p.identity('Radio Tessera',{'titles':['Other broadcaster']},'TESSERA')
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',52);im=Image.new('RGBA',(360,120),'white');ImageDraw.Draw(im).text((10,15),'WXYZ',font=font,fill='black');buf=io.BytesIO();im.save(buf,'PNG');good=buf.getvalue();other=Image.new('RGBA',(120,80),'red');b=io.BytesIO();other.save(b,'PNG');bad=b.getvalue()
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  data=good if self.path=='/fourth-logo.png' else bad;self.send_response(200);self.send_header('Content-Type','image/png');self.end_headers();self.wfile.write(data)
 def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start();base='http://127.0.0.1:'+str(server.server_port)
with tempfile.TemporaryDirectory() as folder:
 root=Path(folder);masters={'transparent':Image.new('RGBA',(220,132))}
 for style in p.PINS:masters[style]=Image.open(Path(__file__).resolve().parents[1]/'snapshot-files/templates'/(style+'.png')).convert('RGBA')
 page=dict(url=base+'/station',final_url=base+'/station',titles=['WXYZ 90.1 Radio'],image_urls=[base+'/bad1.png',base+'/bad2.png',base+'/bad3.png'],named_logos={base+'/fourth-logo.png':'WXYZ station logo'},original_html_sha256='a'*64)
 result=p.discover(dict(name='WXYZ 90.1',reference='4097:0:2:1:2:3:0:0:0:0'),[page],{p.SHA(bad)},root,masters);assert result['status']=='ready_verified_exact_brand_and_recorded_page',result;assert len(result['renders'])==9
 for v,a in result['renders'].items():
  raw=(root/a['path']).read_bytes();assert p.SHA(raw)==a['sha256'];assert Image.open(io.BytesIO(raw)).size==tuple(map(int,v.split('/')[0].split('x')))
server.shutdown();print('PASS: fourth-image discovery, false brand rejection, exact callsign, actual HTTP fetching, OCR, all nine variants')
