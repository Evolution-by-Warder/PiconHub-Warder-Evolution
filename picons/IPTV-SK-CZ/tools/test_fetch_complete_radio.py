import gzip,json,unittest
from urllib.parse import parse_qs,urlsplit
from fetch_complete_radio import get,laut,radio_browser

class Response:
    def __init__(self,data,url='https://api.laut.fm/a',encoding=None):
        self.data=data;self.url=url;self.headers={'Content-Encoding':encoding}
    def read(self,n):return self.data[:n]
    def __enter__(self):return self
    def __exit__(self,*a):pass

class CompleteSourceTests(unittest.TestCase):
    def test_gzip_limit_and_redirect_validation(self):
        payload=gzip.compress(json.dumps({'data':'a'*10000}).encode())
        with self.assertRaises(ValueError):get('https://api.laut.fm/a',1000,lambda *a,**k:Response(payload,encoding='gzip'))
        self.assertEqual(get('https://api.laut.fm/a',20000,lambda *a,**k:Response(payload,encoding='gzip'))['data'],'a'*10000)
        with self.assertRaises(ValueError):get('https://api.laut.fm/a',20000,lambda *a,**k:Response(b'[]',url='http://api.laut.fm/a'))
    def test_unstable_pages_reconciled_with_name_inventory(self):
        names=['station'+str(i) for i in range(5001)];calls=[]
        def request(url,*args):
            calls.append(url);p=urlsplit(url)
            if p.path=='/station_names':return names
            if p.path.startswith('/stations/'):
                return [{'name':n,'active':True} for n in p.path.split('/')[-1].split(',')]
            offset=int(parse_qs(p.query)['offset'][0]);batch=names[offset:offset+1000]
            if offset==1000:batch[0]=names[0] # repeated row displaces station1000
            return {'items':[{'name':n,'active':True} for n in batch],'offset':offset,'total':len(names),'next_offset':offset+len(batch) if offset+len(batch)<len(names) else None}
        rows,report=laut(request,lambda n:None)
        self.assertEqual({r['name'] for r in rows},set(names))
        self.assertEqual(report['page_duplicates'],1);self.assertEqual(report['named_recoveries'],1)
        self.assertEqual(len(calls),8)
    def test_unrequested_batch_row_rejected(self):
        names=['station'+str(i) for i in range(5001)]
        def request(url,*args):
            p=urlsplit(url)
            if p.path=='/station_names':return names
            if p.path.startswith('/stations/'):return [{'name':'not-requested','active':True}]
            return {'items':[],'offset':0,'total':len(names),'next_offset':None}
        with self.assertRaisesRegex(ValueError,'Unexpected'):laut(request,lambda n:None)
    def test_pagination_loop_rejected(self):
        def request(url,*args):
            if url.endswith('/station_names'):return ['station'+str(i) for i in range(5001)]
            return {'items':[{'name':'station0'}],'offset':0,'total':5001,'next_offset':0}
        with self.assertRaisesRegex(ValueError,'pagination'):laut(request,lambda n:None)
    def test_radio_browser_mirror_fallback_and_duplicate_guard(self):
        calls=[]
        def request(url):
            calls.append(url)
            if 'de1.' in url:raise OSError('offline')
            if url.endswith('/json/countries'):return [{'name':str(i)} for i in range(200)]
            return [{'stationuuid':str(i)} for i in range(10001)]
        rows,countries,report=radio_browser(request)
        self.assertEqual(len(rows),10001);self.assertEqual(report['server'],'de2.api.radio-browser.info')
        self.assertEqual(len(calls),3)
        with self.assertRaises(RuntimeError):radio_browser(lambda url:[{'stationuuid':'same'}]*10001)

if __name__=='__main__':unittest.main()
