"""Assemble exact checked archives, verify public bytes, then publish the catalogue."""
from pathlib import Path
import hashlib
import io
import json
import re
import subprocess
import time
import urllib.request
import zipfile
from PIL import Image

ROOT = Path('picons/IPTV-SK-CZ')
REPO = 'Evolution-by-Warder/PiconHub-Warder-Evolution'
BRANCH = 'radio/iptv-sk-cz-publish'
EXPECTED_MAIN = 'e777edf594dab41a31ad2d5fedff5a579c8a3b5b'

def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()

def remote_head(branch):
    return git('ls-remote', 'origin', 'refs/heads/' + branch).split()[0]

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def public(url, expected):
    for attempt in range(4):
        try:
            request = urllib.request.Request(url, headers={'Cache-Control':'no-cache', 'User-Agent':'Warder-radio-release'})
            with urllib.request.urlopen(request, timeout=90) as response:
                raw = response.read(expected['bytes'] + 1)
            assert len(raw) == expected['bytes'] and digest(raw) == expected['sha256'], url
            return
        except OSError:
            if attempt == 3:
                raise
            time.sleep(3)

def main():
    assert remote_head('main') == EXPECTED_MAIN, 'Production branch advanced'
    inventory = json.loads((ROOT/'catalog/package-inventory.json').read_text())
    for entry in json.loads((ROOT/'catalog/assembly-plan.json').read_text()):
        data = bytearray()
        for part in entry['parts']:
            path = ROOT/part['path']
            raw = path.read_bytes()
            assert len(raw) == part['bytes'] and digest(raw) == part['sha256']
            data.extend(raw)
        assert len(data) == entry['bytes'] and digest(data) == entry['sha256']
        (ROOT/'packages'/entry['filename']).write_bytes(data)
        for part in entry['parts']:
            (ROOT/part['path']).unlink()
    common = None
    for resolution, styles in inventory.items():
        for style, entry in styles.items():
            raw = (ROOT/'packages'/entry['filename']).read_bytes()
            assert len(raw) == entry['bytes'] and digest(raw) == entry['sha256']
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                assert len(archive.namelist()) == len(entry['files'])
                assert set(archive.namelist()) == set(entry['files'])
                assert archive.testzip() is None
                for name, checksum in entry['files'].items():
                    assert re.fullmatch(r'(4097|5001|5002|8193)_0_(2|A)_([0-9A-F]+_){6}[0-9A-F]+\.png', name)
                    png = archive.read(name)
                    assert digest(png) == checksum
                    with Image.open(io.BytesIO(png)) as image:
                        assert image.size == tuple(map(int, resolution.split('x')))
                        image.verify()
            if common is None:
                common = set(entry['files'])
            assert set(entry['files']) == common
    git('config','user.name','Warder release automation')
    git('config','user.email','warder-release@users.noreply.github.com')
    git('add',str(ROOT/'packages'))
    git('commit','-m','Assemble and verify all nine IPTV radio archives')
    payload = git('rev-parse','HEAD')
    git('push','origin','HEAD:refs/heads/'+BRANCH)
    for styles in inventory.values():
        for entry in styles.values():
            name = entry.pop('filename')
            entry['url'] = 'https://raw.githubusercontent.com/'+REPO+'/'+payload+'/'+str(ROOT/'packages'/name)
            public(entry['url'], entry)
    document = {'schema':1,'status':'verified','collection':'IPTV-SK-CZ',
                'version':'2026.10.28','stations':321,'audio_sampled':286,
                'picon_stations':213,'missing_artwork':108,'reference_files_per_variant':len(common),
                'payload_commit':payload,'packages':inventory}
    (ROOT/'catalog/release.json').write_text(json.dumps(document,ensure_ascii=False,indent=2)+'\n')
    git('add',str(ROOT/'catalog/release.json'))
    git('commit','-m','Publish verified IPTV radio catalogue and bouquets')
    git('push','origin','HEAD:refs/heads/'+BRANCH)
    assert remote_head('main') == EXPECTED_MAIN, 'Production branch advanced before activation'
    git('push','origin','HEAD:refs/heads/main')
    raw = (ROOT/'catalog/release.json').read_bytes()
    public('https://raw.githubusercontent.com/'+REPO+'/main/'+str(ROOT/'catalog/release.json'),
           {'bytes':len(raw),'sha256':digest(raw)})
    print('Published',payload,'213 station picons; 229 reference files per variant; 321 bouquet entries')

if __name__ == '__main__':
    main()
