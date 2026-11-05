"""Exercise actual batch HTTP parsing and refusal of mismatched station identities."""
import json,threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import parse_qs,urlsplit
from refresh_radio_metadata import verified_new_icons,api_batch

p=dict(name='Example Radio',name_aliases=['Example FM'],countrycode='SK',source_ids=['radio-browser:station-1'],url='https://stream.example/one',aliases=[],stream_variants=[])
r=dict(stationuuid='station-1',name='Example Radio',countrycode='SK',url='https://stream.example/one',url_resolved='',favicon='https://logo.example/new.png')
assert len(verified_new_icons(p,[r],set()))==1
for change in [dict(stationuuid='station-2'),dict(name='Other Station'),dict(countrycode='CZ'),dict(url='https://stream.example/other'),dict(favicon='file:///tmp/image.png')]:
 assert not verified_new_icons(p,[dict(r,**change)],set())
assert not verified_new_icons(p,[r],{r['favicon']})
assert len(verified_new_icons(p,[dict(r,url='http://stream.example/one')],set()))==1
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_GET(self):
  parsed=urlsplit(self.path);assert parsed.path=='/json/stations/byuuid'
  assert parse_qs(parsed.query)['uuids']==['station-1']
  body=json.dumps([r]).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(body)
server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
response=api_batch(['station-1'],['http://127.0.0.1:'+str(server.server_port)]);server.shutdown();server.server_close()
assert response['rows']==[r] and not response['errors']
print('Metadata refresh checks passed: real HTTP batch request, exact UUID/name/country/stream binding, new icon only, transport upgrade, mismatches refused.')
