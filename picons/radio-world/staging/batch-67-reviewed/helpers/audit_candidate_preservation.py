"""Check every previously approved PNG against a new working candidate."""
import argparse, concurrent.futures, hashlib, json, re, urllib.request
from pathlib import Path

BASE = 'https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/'
SIZES = ('50x30', '220x132', '400x240')
STYLES = ('transparent', 'white', 'black')

def get(entry):
    assert re.fullmatch('[0-9a-f]{40}', entry['commit'])
    assert entry['url'].startswith(BASE + entry['commit'] + '/')
    with urllib.request.urlopen(entry['url'], timeout=60) as response:
        body = response.read(entry['bytes'] + 1)
    assert len(body) == entry['bytes']
    assert hashlib.sha256(body).hexdigest() == entry['sha256']
    return json.loads(body)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline', type=Path, required=True)
    p.add_argument('--candidate', type=Path, required=True)
    p.add_argument('--baseline-commit', required=True)
    p.add_argument('--baseline-sha256', required=True)
    p.add_argument('--expected-references', type=int, required=True)
    p.add_argument('--expected-pngs', type=int, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    raw = a.baseline.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == a.baseline_sha256
    assert re.fullmatch('[0-9a-f]{40}', a.baseline_commit)
    old = {r['id']: r for r in json.loads(raw)['countries']}
    new = {r['id']: r for r in json.loads(a.candidate.read_bytes())['countries']}
    assert len(old) == len(new) == 219 and old.keys() == new.keys()
    assert sum(r['picons'] for r in old.values()) == a.expected_references
    for code, before in old.items():
        after = new[code]
        assert all(before[k] == after[k] for k in ('name', 'collection', 'stations')), code
        assert after['picons'] >= before['picons'], code
        if before['release']:
            assert after['release'], code
    entries = {r['release']['url']: r['release'] for table in (old, new)
               for r in table.values() if r['release']}
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        manifests = dict(zip(entries, pool.map(get, entries.values())))
    seen = set()
    protected = 0
    checks = []
    for code, row in old.items():
        if not row['release'] or row['collection'] in seen:
            continue
        seen.add(row['collection'])
        before = manifests[row['release']['url']]
        after = manifests[new[code]['release']['url']]
        assert before['collection'] == after['collection'] == row['collection']
        count = 0
        for size in SIZES:
            for style in STYLES:
                first = before['packages'][size][style]['files']
                second = after['packages'][size][style]['files']
                assert first.items() <= second.items(), (code, size, style)
                count += len(first)
        protected += count
        checks.append(dict(country=code, collection=row['collection'], protected_pngs=count))
    assert protected == a.expected_pngs, (protected, a.expected_pngs)
    proof = dict(schema=1, status='pass', baseline_commit=a.baseline_commit,
                 baseline_index_sha256=a.baseline_sha256,
                 baseline_references=a.expected_references,
                 protected_approved_png_variant_entries=protected,
                 candidate_references=sum(r['picons'] for r in new.values()),
                 manifests_verified=len(manifests), checks=checks,
                 scope='Every prior approved filename and SHA256 retained in all nine variants, including aliases')
    a.output.write_text(json.dumps(proof, indent=2) + '\n')
    print(json.dumps({k: v for k, v in proof.items() if k != 'checks'}))

if __name__ == '__main__':
    main()
