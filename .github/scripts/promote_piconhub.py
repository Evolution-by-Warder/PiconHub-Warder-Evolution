"""Promote frozen plugin bytes without rebuilding or changing the update feed."""
import hashlib
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

REPOSITORY = 'Evolution-by-Warder/PiconHub-Warder-Evolution'


def validate(record, feed, release, package):
    item = feed['release']
    for key in ('version', 'tag', 'url', 'sha256', 'bytes'):
        if record['release'][key] != item[key]:
            raise ValueError('Production record differs from verified feed: '+key)
    expected_tag = 'v'+item['version']
    filename = 'enigma2-plugin-extensions-piconhub-warder-evolution_'+item['version']+'_all.ipk'
    expected_url = 'https://github.com/'+REPOSITORY+'/releases/download/'+expected_tag+'/'+filename
    if item['tag'] != expected_tag or item['url'] != expected_url:
        raise ValueError('Unexpected package identity')
    if (release['tag_name'] != expected_tag or release['draft']
            or release['target_commitish'] != record['source_commit']):
        raise ValueError('Release does not match frozen source')
    assets = {a['name']:a for a in release['assets']}
    asset = assets[filename]
    if (asset['size'] != item['bytes'] or asset['digest'] != 'sha256:'+item['sha256']
            or len(package) != item['bytes'] or hashlib.sha256(package).hexdigest() != item['sha256']):
        raise ValueError('Production package integrity check failed')


def main():
    root = Path(__file__).resolve().parents[2]
    record = json.loads((root/'plugin/production.json').read_text())
    feed = json.loads((root/'plugin/update/stable.json').read_text())
    token = os.environ['GITHUB_TOKEN']
    def api(path, payload=None):
        raw = json.dumps(payload).encode() if payload is not None else None
        request = Request('https://api.github.com/repos/'+REPOSITORY+path, data=raw,
                          method='PATCH' if payload is not None else 'GET',
                          headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json',
                                   'Content-Type':'application/json','User-Agent':'PiconHub-production'})
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    release = api('/releases/tags/'+record['release']['tag'])
    with urlopen(record['release']['url'], timeout=30) as response:
        package = response.read(record['release']['bytes']+1)
    validate(record, feed, release, package)
    result = api('/releases/'+str(release['id']), {'draft':False,'prerelease':False,'make_latest':'true'})
    if result['draft'] or result['prerelease']:
        raise ValueError('Production release promotion failed')
    print('Production release verified and promoted:', result['html_url'])


if __name__ == '__main__':
    main()
