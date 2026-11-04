"""Add reviewed station artwork to the approved Warder variants, preserving old PNGs."""
import argparse
import csv
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
from urllib.request import urlopen
import zipfile
from PIL import Image

ROOT = Path('picons/IPTV-SK-CZ')
SOURCES = ROOT / 'sources/warder-radio-20261104'
REPOSITORY = 'Evolution-by-Warder/PiconHub-Warder-Evolution'
SHA = lambda raw: hashlib.sha256(raw).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def png(image):
    output = io.BytesIO()
    image.save(output, format='PNG')
    return output.getvalue()


def archive(files):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as z:
        for name, raw in sorted(files.items()):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            z.writestr(info, raw)
    return output.getvalue()


def build(base_folder=None):
    plan = json.loads((SOURCES / 'plan.json').read_text())
    release_raw = (ROOT / 'catalog/release.json').read_bytes()
    assert SHA(release_raw) == plan['base_release_sha256'], 'Base release changed'
    release = json.loads(release_raw)
    masters = {}
    for style, digest in plan['master_sha256'].items():
        raw = Path('plugin/artwork/templates/picons', style + '-sablona.png').read_bytes()
        assert SHA(raw) == digest, 'Approved Warder master changed'
        master = Image.open(io.BytesIO(raw)).convert('RGBA')
        assert master.size == (220, 132)
        masters[style] = master
    prepared = {}
    for entry in plan['artwork']:
        raw = (SOURCES / entry['path']).read_bytes()
        assert SHA(raw) == entry['sha256'], 'Source artwork changed'
        source_raw = raw
        original = Image.open(io.BytesIO(raw)).convert('RGBA')
        original.thumbnail((192, 104), Image.Resampling.LANCZOS)
        for style in ('black', 'white', 'transparent'):
            logo = original
            if entry.get('white_monochrome') and style == 'white':
                # Reviewed complete monochrome symbol; preserve every alpha pixel.
                assert all(pixel[:3] == (255, 255, 255) for pixel in
                           Image.open(io.BytesIO(source_raw)).convert('RGBA').get_flattened_data() if pixel[3])
                logo = Image.new('RGBA', original.size, (0, 0, 0, 0))
                logo.putalpha(original.getchannel('A'))
                assert logo.getchannel('A').tobytes() == original.getchannel('A').tobytes()
            image = masters[style].copy() if style != 'transparent' else Image.new('RGBA', (220, 132))
            image.alpha_composite(logo, ((220 - logo.width) // 2, (132 - logo.height) // 2))
            for resolution in release['packages']:
                size = tuple(map(int, resolution.split('x')))
                variant = image if size == image.size else image.resize(size, Image.Resampling.LANCZOS)
                raw = png(variant)
                assert SHA(raw) == entry['render_sha256'][resolution][style], 'Reviewed render changed'
                prepared[(entry['slug'], resolution, style)] = raw

    def variant(task):
        resolution, style, entry = task
        name = 'iptv-sk-cz-' + style + '-' + resolution + '.zip'
        if base_folder:
            raw = (base_folder / name).read_bytes()
        else:
            with urlopen(entry['url'], timeout=30) as response:
                raw = response.read(entry['bytes'] + 1)
        assert len(raw) == entry['bytes'] and SHA(raw) == entry['sha256']
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            assert len(z.infolist()) == len(entry['files']) == 294
            files = {n: z.read(n) for n in z.namelist()}
        assert {n: SHA(b) for n, b in files.items()} == entry['files']
        old = dict(files)
        for alias in plan['aliases']:
            assert alias['target'] not in files
            files[alias['target']] = old[alias['source']]
        for source in plan['artwork']:
            for station in source['stations']:
                assert station['target'] not in files
                files[station['target']] = prepared[(source['slug'], resolution, style)]
        assert len(files) == 316
        assert all(files[name] == data for name, data in old.items())
        size = tuple(map(int, resolution.split('x')))
        for data in files.values():
            with Image.open(io.BytesIO(data)) as image:
                assert image.format == 'PNG' and image.size == size
                image.verify()
        output = archive(files)
        metadata = dict(resolution=resolution, bytes=len(output), sha256=SHA(output),
                        files={n: SHA(b) for n, b in sorted(files.items())})
        return resolution, style, metadata, output

    tasks = [(size, style, entry) for size, styles in release['packages'].items() for style, entry in styles.items()]
    results = list(ThreadPoolExecutor(3).map(variant, tasks))
    assert len({tuple(r[2]['files']) for r in results}) == 1
    return plan, release, results


def check_receiver(release, results):
    import importlib.util
    import sys
    from types import ModuleType, SimpleNamespace
    root = Path('plugin/src/Plugins/Extensions/WarderPiconHub').resolve()
    package = ModuleType('warder_picon_check'); package.__path__ = [str(root)]
    sys.modules[package.__name__] = package
    sync = ModuleType('warder_picon_check.warder_skin_sync')
    sync.UPDATE_MODE_SYNC_TV = 'sync-tv'
    sync.UPDATE_MODE_SYNC_TV_RADIO = 'sync-radio'
    sync.UPDATE_MODE_INCREMENTAL = 'incremental'
    sys.modules[sync.__name__] = sync
    spec = importlib.util.spec_from_file_location('warder_picon_check.warder_iptv', root / 'warder_iptv.py')
    iptv = importlib.util.module_from_spec(spec); spec.loader.exec_module(iptv)
    manifest = json.dumps(release).encode()
    verified = iptv.read_manifest(lambda url: io.BytesIO(manifest))
    for resolution, style, entry, body in results:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ready = root / 'ready'; ready.mkdir()
            unrelated = ready / 'unrelated.png'; unrelated.write_bytes(b'keep')
            preferences = dict(update_mode=iptv.sync.UPDATE_MODE_INCREMENTAL,
                               resolution=resolution, style=style, destination=str(ready))
            queue, job = iptv.plan(verified, preferences, str(root))
            stage = SimpleNamespace(queue=queue, ready=ready, hashes={}, upstream=set())
            path = root / 'package.zip'; path.write_bytes(body)
            iptv.unpack(stage, path, job, lambda: None)
            assert len(stage.hashes) == 316 and unrelated.read_bytes() == b'keep'
            assert all(SHA((ready / n).read_bytes()) == digest for n, digest in entry['files'].items())
    return dict(engine='warder_iptv.py', variants=9, files_per_variant=316,
                previous_files_preserved=294, unrelated_picon_preserved=True,
                physical_receiver_test=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-folder', type=Path)
    parser.add_argument('--output', type=Path, default=Path('/tmp/warder-radio-picons'))
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()
    plan, release, results = build(args.base_folder)
    release.update(version=plan['version'], reference_files_per_variant=316)
    for size, style, entry, body in results:
        name = 'iptv-sk-cz-' + style + '-' + size + '.zip'
        (args.output / 'packages').mkdir(parents=True, exist_ok=True)
        (args.output / 'packages' / name).write_bytes(body)
        entry['url'] = ('https://raw.githubusercontent.com/' + REPOSITORY + '/' + plan['source_commit'] +
                        '/' + str(ROOT / 'packages' / name))
        release['packages'][size][style] = entry
    check = check_receiver(release, results)
    old_stations = json.loads((ROOT / 'catalog/stations.json').read_text())['stations']
    names = set(results[0][2]['files'])
    release['picon_stations'] = sum(s['picon_filename'] in names for s in old_stations)
    release['missing_artwork'] = len(old_stations) - release['picon_stations']
    proof = dict(schema=1, status='verified', version=plan['version'], source_graphics=6,
                 new_references=22, reviewed_profile_aliases=15, warder_master_sha256=plan['master_sha256'],
                 receiver_engine=check, original_station_counts=dict(stations=len(old_stations),
                 with_picons=release['picon_stations'], missing=release['missing_artwork']))
    write_json(args.output / 'release.json', release)
    write_json(args.output / 'proof.json', proof)
    print(json.dumps(proof))
    if not args.publish:
        return
    assert os.environ.get('GITHUB_REF_NAME') == 'radio/warder-picons-20261104'
    baseline = plan['source_commit']
    assert git('ls-remote', 'origin', 'refs/heads/main').split()[0] == baseline, 'Main advanced'
    assert git('diff', baseline, '--', str(ROOT / 'catalog/release.json')) == ''
    targets = []
    for size, style, entry, body in results:
        path = ROOT / 'packages' / ('iptv-sk-cz-' + style + '-' + size + '.zip')
        path.write_bytes(body); targets.append(str(path))
    git('config', 'user.name', 'Warder release automation')
    git('config', 'user.email', 'warder-release@users.noreply.github.com')
    git('add', *targets)
    git('commit', '-m', 'Prepare 22 reviewed radio picon references in all nine Warder variants')
    payload = git('rev-parse', 'HEAD')
    git('push', 'origin', 'HEAD:refs/heads/radio/warder-picons-20261104')
    for size, style, entry, body in results:
        entry['url'] = entry['url'].replace(baseline, payload)

    def verify(task):
        _, _, entry, _ = task
        with urlopen(entry['url'], timeout=30) as response:
            raw = response.read(entry['bytes'] + 1)
        assert len(raw) == entry['bytes'] and SHA(raw) == entry['sha256']
    list(ThreadPoolExecutor(3).map(verify, results))
    release['payload_commit'] = payload
    proof.update(payload_commit=payload, all_nine_public_archives_verified=True)
    check_receiver(release, results)
    write_json(ROOT / 'catalog/release.json', release)
    write_json(ROOT / 'catalog/warder-radio-picons-20261104.json', proof)
    readme = ROOT / 'README.md'
    text = readme.read_text()
    text = text.replace('Picony pokrývajú 278 položiek, 294 súborov',
                        'Picony pokrývajú 282 položiek pôvodného bouquetu, 316 súborov')
    text = text.replace('Zvyšných 43 položiek', 'Zvyšných 39 položiek')
    text += ('\nDoplnenie 4. novembra 2026: 6 overených grafických predlôh a 15 prepojení existujúcich '
             'piconov na aktuálne označenia staníc. Všetkých 294 predchádzajúcich PNG v každom variante '
             'zostalo bez zmeny. Použité sú pôvodné schválené Warder šablóny. Aktuálny katalóg má picony '
             'pre 88 z 89 slovenských a 210 z 250 českých položiek; zvyšné logá alebo identity ešte '
             'vyžadujú overenie. Počty pôvodného 321-položkového bouquetu sa od aktuálneho katalógu líšia. '
             '[Ukážka 1](sources/warder-radio-20261104/Warder-radio-picony-1.png), '
             '[ukážka 2](sources/warder-radio-20261104/Warder-radio-picony-2.png), '
             '[pokrytie a nevyriešené položky](sources/warder-radio-20261104/coverage.json), '
             '[overenie publikácie](catalog/warder-radio-picons-20261104.json). '
             'Nové IPK pre tieto dáta netreba; obnovte IPTV rádiá SK/CZ v PiconHube.\n')
    readme.write_text(text)
    missing = ROOT / 'catalog/missing-artwork.csv'
    with missing.open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.reader(stream))
    covered = {(r['country'], r['name']) for a in plan['artwork'] for r in a['stations']}
    rows = rows[:1] + [r for r in rows[1:] if tuple(r[:2]) not in covered]
    assert len(rows) - 1 == release['missing_artwork']
    with missing.open('w', encoding='utf-8-sig', newline='') as stream:
        csv.writer(stream).writerows(rows)
    git('add', str(ROOT / 'catalog/release.json'), str(ROOT / 'catalog/warder-radio-picons-20261104.json'), str(missing), str(readme))
    git('commit', '-m', 'Activate verified Warder radio picons while retaining every previous PNG [skip ci]')
    git('push', 'origin', 'HEAD:refs/heads/radio/warder-picons-20261104')
    assert git('ls-remote', 'origin', 'refs/heads/main').split()[0] == baseline, 'Main advanced before activation'
    git('push', '--force-with-lease=refs/heads/main:' + baseline, 'origin', 'HEAD:refs/heads/main')
    print('Activated:', git('rev-parse', 'HEAD'))


if __name__ == '__main__':
    main()
