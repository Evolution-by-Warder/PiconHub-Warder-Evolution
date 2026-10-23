"""One explicit owner-authorized allowlist; never infer deletions from version age."""
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def validate_target(target, release):
    if (type(target['id']) is not int or target['id'] != release['id']
            or not target['tag'].startswith('factory-v') or target['tag'] != release['tag_name']
            or 'FACTORY' not in release['name'].upper()):
        raise ValueError('Release is not an authorized Factory target')
    names = {a['name'] for a in release['assets']}
    if names != set(target['assets']) or any('.ipk' in name.lower() for name in names):
        raise ValueError('Target assets changed or contain a receiver package')


def main():
    record = json.loads((Path(__file__).resolve().parents[1]/'factory-removal.json').read_text())
    repository = record['repository']
    if repository != 'Evolution-by-Warder/PiconHub-Warder-Evolution':
        raise ValueError('Unexpected repository')
    token = os.environ['GITHUB_TOKEN']
    def api(path, method='GET', payload=None, missing_ok=False):
        request = Request('https://api.github.com/repos/'+repository+path,
                          data=json.dumps(payload).encode() if payload is not None else None,
                          method=method,headers={'Authorization':'Bearer '+token,
                              'Accept':'application/vnd.github+json','Content-Type':'application/json',
                              'User-Agent':'PiconHub-authorized-Factory-cleanup'})
        try:
            with urlopen(request,timeout=30) as response:
                data=response.read()
                return json.loads(data) if data else None
        except HTTPError as exc:
            if missing_ok and exc.code==404:return None
            raise
    keep = set(record['keep_plugin_release_ids'])
    latest = api('/releases/'+str(record['latest']['id']))
    if latest['tag_name']!=record['latest']['tag'] or latest['id'] not in keep:
        raise ValueError('Latest is not an approved receiver release')
    pending=[]
    # Validate the entire explicit plan before deleting anything.
    for target in record['remove']:
        if target['id'] in keep:raise ValueError('Deletion overlaps retained plugin releases')
        release=api('/releases/'+str(target['id']),missing_ok=True)
        if release is not None:
            validate_target(target,release);pending.append(target)
    for target in pending:
        api('/releases/'+str(target['id']),method='DELETE')
        print('Removed Factory release:',target['tag'])
    for release_id in keep:
        api('/releases/'+str(release_id))
    api('/releases/'+str(latest['id']),method='PATCH',
        payload={'draft':False,'prerelease':False,'make_latest':'true'})
    print('All',len(keep),'receiver plugin releases retained; Latest:',latest['tag_name'])


if __name__=='__main__':main()
