#!/usr/bin/env python3
"""Prepare batch43 from actual immutable reviewed exports; no rendering, ZIPs or publishing."""
import argparse
import copy
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE if (HERE/'visual_gate.py').is_file() else HERE.parents[1]/'tools'))
from visual_gate import read, merge_ledgers, validate_selection, identity_blocks

ROOT = Path('continuation/output/picons/radio-world/staging') if Path('continuation/output').is_dir() else Path('picons/radio-world/staging')
BASE = 'https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/'
PARENT = 'b99fe072f36d03871cc9c0e7546a5fc9294846a0'
BASELINE_SHA = '8dfc9b924bc2c144997c1333840364ae12a2c7497baa2bcf02a9e9c5ef633d70'
HISTORY = ['source-ledger-reviewed-20261107/visual-ledger.json.gz', 'visual-review-34-36/decisions.json.gz', *[f'batch-{n}-reviewed/visual-ledger.json.gz' for n in (39, 40, 41, 42)]]
VARIANTS = {f'{size}/{style}' for size in ('50x30', '220x132', '400x240') for style in ('transparent', 'white', 'black')}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def packed(value):
    return gzip.compress((json.dumps(value, ensure_ascii=False, separators=(',', ':'))+'\n').encode(), mtime=0)


def source_pair(value):
    parts = value.split(':')
    if len(parts) != 2 or not all(parts):
        raise argparse.ArgumentTypeError('Use SELECTION:LEDGER (local paths without colons)')
    return tuple(map(Path, parts))


def validate_source(path, expected):
    data = read(path)
    rows = data['entries'] if isinstance(data, dict) else data
    require(type(expected) is int and expected > 0 and len(rows) == expected, f'Unexpected source count: {path}: actual={len(rows)}, expected={expected}')
    require(len({r['ref'] for r in rows}) == len(rows), f'Duplicate source references: {path}')
    for row in rows:
        require(isinstance(row.get('source_commit'), str) and re.fullmatch('[0-9a-f]{40}', row['source_commit']), 'Unpinned source: '+row['ref'])
        root = row.get('asset_root', '')
        require(isinstance(root, str) and bool(root) and 'pending' not in root.lower(), 'Pending asset root')
        relative = PurePosixPath(root)
        require(bool(relative.parts) and not relative.is_absolute() and '..' not in relative.parts and '\\' not in root and relative.parts[-1] != 'verified-assets', 'asset_root must be safe parent staging path; importer appends verified-assets/SHA.png')
        require(isinstance(row.get('station'), dict) and all(isinstance(row['station'].get(k), str) and row['station'][k] for k in ('name', 'url', 'group')), 'Missing exact station identity')
        require(set(row['variants']) == VARIANTS, 'Expected all nine exact variants')
        for value in row['variants'].values():
            require(isinstance(value, list) and len(value) == 3 and isinstance(value[0], str) and re.fullmatch('[0-9a-f]{64}', value[0]) and type(value[1]) is int and value[1] > 0 and isinstance(value[2], str) and re.fullmatch('[0-9a-f]{40}', value[2]), 'Unpinned PNG SHA256/bytes/Gitblob triple')
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', action='append', type=source_pair, required=True, metavar='SELECTION:LEDGER', help='Repeat once per real pinned producer export')
    parser.add_argument('--expected-source-count', action='append', type=int, required=True, help='Exact count in matching --source order; planned43 counts are113,25,3, not completed outputs')
    parser.add_argument('--expected-total', type=int, default=141, help='Reviewed scope expectation, never a fabricated completed count')
    parser.add_argument('--parent', default=PARENT)
    parser.add_argument('--baseline', type=Path, default=Path('continuation/results-42-reviewed/countries.proposed.json') if Path('continuation/results-42-reviewed/countries.proposed.json').is_file() else Path('picons/radio-world/catalog/countries.json'))
    parser.add_argument('--expected-baseline-sha256', default=BASELINE_SHA)
    parser.add_argument('--history-root', type=Path, default=ROOT)
    parser.add_argument('--config-template', type=Path)
    parser.add_argument('--stage', type=Path, default=ROOT/'batch-43-reviewed')
    args = parser.parse_args(argv)
    require(len(args.source) == len(args.expected_source_count), 'Each --source needs one --expected-source-count in matching order')
    require(all(n > 0 for n in args.expected_source_count) and sum(args.expected_source_count) == args.expected_total, 'Expected source counts must sum to exact reviewed scope')
    require(re.fullmatch('[0-9a-f]{40}', args.parent), 'Parent must be immutable commit')
    baseline_raw = args.baseline.read_bytes()
    require(sha(baseline_raw) == args.expected_baseline_sha256, 'Baseline SHA256 differs')
    baseline = json.loads(baseline_raw)['countries']
    require(len(baseline) == len({r['id'] for r in baseline}) == 219, 'Baseline country inventory differs')
    baseline_count = sum(r['picons'] for r in baseline)
    require(baseline_count == 2870 and sum(bool(r['release']) for r in baseline) == 119 and sum(r['status'] == 'complete' for r in baseline) == 12, 'Baseline must remain verified42:2870/119/12')
    rows, sources = [], []
    for (selection, ledger), expected in zip(args.source, args.expected_source_count):
        entries = validate_source(selection, expected)
        # Each producer must have its own exact nine-variant review, before unions.
        validate_selection(entries, read(ledger))
        rows.extend(entries)
        sources.append(dict(selection=str(selection), ledger=str(ledger), actual_references=len(entries), expected_references=expected, selection_sha256=sha(selection.read_bytes()), ledger_sha256=sha(ledger.read_bytes()), source_commits=sorted({r['source_commit'] for r in entries})))
    require(len(rows) == len({r['ref'] for r in rows}) == args.expected_total, 'Cross-producer duplicate or unexpected reference count')
    require({r['country'] for r in rows} <= {r['id'] for r in baseline}, 'Source country absent from the219-country index')
    historical = [args.history_root/name for name in HISTORY]
    require(all(f.is_file() for f in historical), 'Missing historical ledger; never prepare with a partial history')
    ledger_paths = [pair[1] for pair in args.source]
    new_ledger = merge_ledgers(ledger_paths)
    require(validate_selection(rows, new_ledger) == len(rows), 'Merged source reviews differ')
    combined = merge_ledgers(historical + ledger_paths)
    validate_selection(rows, combined)
    template = args.config_template or args.history_root/'batch-42-reviewed/configuration.json'
    cfg = copy.deepcopy(read(template))
    cfg.update(batch='43-reviewed', references=len(rows), parent_candidate=args.parent, expected_coverage=baseline_count+len(rows), selection_filename='selection.json.gz', visual_ledger_filename='visual-ledger.json.gz')
    for key in ('source_ledger_commit', 'reuse_index'):
        cfg.pop(key, None)
    cfg['baseline_index'] = dict(url=BASE+args.parent+'/picons/radio-world/catalog/countries.json', bytes=len(baseline_raw), sha256=sha(baseline_raw))
    cfg['held_references'] = sorted(set(cfg['held_references']) | {ref for country, ref in identity_blocks(combined)})
    require(not set(cfg['held_references']) & {r['ref'] for r in rows}, 'Identity/source-held reference in selection')
    selection_raw = packed(dict(entries=rows))
    cfg['selection_sha256'] = sha(selection_raw)
    proof = dict(schema=1, status='prepared-locally-not-built-or-published', parent=args.parent, baseline_covered=baseline_count, baseline_available=119, baseline_complete=12, baseline_sha256=sha(baseline_raw), source_inputs=sources, actual_validated_references=len(rows), expected_scope=args.expected_total, expected_png_instances=9*len(rows), expected_coverage=cfg['expected_coverage'], protected_production_png_variant_entries=10332, active_prior_ledgers=[dict(path=str(f), sha256=sha(f.read_bytes())) for f in historical], metadata_only_source_holds=len(new_ledger.get('source_holds', [])), no_render_or_zip_or_publish_performed=True)
    writes = {'selection.json.gz': selection_raw, 'visual-ledger.json.gz': packed(new_ledger), 'configuration.json': (json.dumps(cfg, indent=2)+'\n').encode(), 'preparation-proof.json': (json.dumps(proof, indent=2)+'\n').encode()}
    # Do not silently replace an earlier prepared selection or its proofs.
    for name, raw in writes.items():
        target = args.stage/name
        require(not target.exists() or target.read_bytes() == raw, 'Refusing unequal existing preparation: '+str(target))
    args.stage.mkdir(parents=True, exist_ok=True)
    for name, raw in writes.items():
        target = args.stage/name
        if not target.exists():
            with target.open('xb') as handle:
                handle.write(raw)
    print(json.dumps(proof, indent=2))


if __name__ == '__main__':
    main()
