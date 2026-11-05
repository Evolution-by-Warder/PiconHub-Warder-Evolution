from strict_catalogue_ocr import identity,same_owner
assert identity('WXYZ 91.3 FM','WXYZ')
assert not identity('WXYZ 91.3 FM','WABC')
assert not identity('WXYZ FM','WXYZ',country='DE')
assert not identity('CLUB 90s','CLUB',country='CA')
assert not identity('WQXR Q2 New York Public Radio','WQXR',country='US')
assert identity('WXYZ HD2','WXYZ HD2',country='US')
assert identity('Antenne Unna','Antenne Unna')
assert not identity('Antenne Unna','Antenne Bayern')
assert not identity('Best Radio Music','Best Music Radio')
assert not identity('Antenne Unna','PayPal Antenne Unna')
row={'source':{'url':'https://cdn.unna.de/logo.png','final_url':'https://cdn.unna.de/logo.png'},'homepages':['https://www.unna.de/']}
assert same_owner(row)
row['source']['final_url']='https://evilunna.de/logo.png';assert not same_owner(row)
row={'source':{'url':'https://tunein.com/logo.png','final_url':'https://tunein.com/logo.png'},'homepages':['https://tunein.com/']};assert not same_owner(row)
print('PASS exact callsign, full brand, generic/platform rejection, source ownership, deceptive domain rejection')

import tempfile,hashlib,io
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from strict_catalogue_ocr import check
with tempfile.TemporaryDirectory() as folder:
 base=Path(folder);root=base/'output';root.mkdir();im=Image.new('RGBA',(480,150));ImageDraw.Draw(im).text((10,12),'WXYZ',font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',100),fill='white');b=io.BytesIO();im.save(b,'PNG');raw=b.getvalue();sha=hashlib.sha256(raw).hexdigest();(base/'original.png').write_bytes(raw)
 row=dict(name='WXYZ 91.3 FM',country='US',reference='test-reference',url='https://example.test/live',station_id='test-id',homepages=['https://example.test/'],source=dict(url='https://example.test/logo.png',final_url='https://example.test/logo.png',sha256=sha,path='original.png'),catalogue_evidence=dict(catalogue_station_id='test-id',exact_receiver_reference='test-reference',exact_receiver_stream='https://example.test/live'))
 masters={'transparent':Image.new('RGBA',(220,132)),'white':Image.new('RGBA',(220,132),'white'),'black':Image.new('RGBA',(220,132),'black')}
 actual=check(row,base,root,masters);assert actual['status']=='ready_strict_catalogue_wordmark_and_owned_image_host',actual
 assert len(actual['renders'])==9
 row['catalogue_evidence']['exact_receiver_stream']='https://other.test/live';assert check(row,base,root,masters)['status']=='pending_exact_programme_evidence'
print('PASS actual white transparent wordmark OCR,9 PNG variants and mismatched stream rejection')
