"""Build a usable, identity-neutral catalog of unique OpenATV artwork.

This is deliberately separate from the service-reference production tree.
"""
from collections import defaultdict
from pathlib import Path
import hashlib
import json
import os
import shutil
import tempfile

from PIL import Image


def build_openatv_catalog(rows, output_root, *, excluded_hashes=()):
    """Materialize one PNG per distinct station-name/content pair, never overwrite.

    A station name is not a service reference. Source bytes are preserved exactly.
    A failed/empty asset can be excluded by its SHA-256. All paths stay under
    the designated catalog root, and no input file is ever modified.
    """
    output_root = Path(output_root)
    catalog = output_root / 'OPENATV-NAME-CATALOG'
    catalog.mkdir(parents=True, exist_ok=True)
    excluded = set(excluded_hashes)
    grouped = defaultdict(list)
    for row in rows:
        src = Path(str(row.get('candidate_source', '')))
        parts = str(src).replace('\\', '/').casefold().split('/')
        if 'source-ingest' not in parts or 'openatv8' not in parts:
            continue
        sha = row.get('candidate_sha256')
        if not sha or sha in excluded or not src.is_file():
            continue
        name = src.name.casefold()
        if not name.endswith('.png'):
            continue
        grouped[(name, sha)].append(src)
    entries = []
    station_index = defaultdict(list)
    created = reused = skipped = 0
    for (name, sha), sources in sorted(grouped.items()):
        # SHA-based basename is safe on Windows, avoids collisions and long paths.
        # Full SHA ensures deterministic uniqueness across runs.
        station_key = hashlib.sha256(name.encode('utf-8')).hexdigest()[:20]
        target_dir = catalog / station_key
        target_dir.mkdir(exist_ok=True)
        target = target_dir / (sha + '.png')
        if target.exists():
            if _digest(target) == sha:
                reused += 1
            else:
                # Never replace an unexpected existing file.
                skipped += 1
                continue
        else:
            source = next((p for p in sources if _digest(p) == sha), None)
            if source is None:
                skipped += 1
                continue
            try:
                with Image.open(source) as im:
                    im.load()
                    if im.format != 'PNG' or im.convert('RGBA').getchannel('A').getbbox() is None:
                        skipped += 1
                        continue
            except (OSError, ValueError):
                skipped += 1
                continue
            fd, tmp_name = tempfile.mkstemp(prefix='.staging-', suffix='.png', dir=target_dir)
            os.close(fd)
            try:
                shutil.copyfile(source, tmp_name)
                if _digest(Path(tmp_name)) != sha:
                    raise ValueError('Source changed during catalog copy')
                os.replace(tmp_name, target)
                created += 1
            finally:
                if os.path.exists(tmp_name):
                    os.unlink(tmp_name)
        entry = {'station_filename': name, 'sha256': sha,
                 'relative_path': target.relative_to(output_root).as_posix(),
                 'service_reference': None, 'identity_verified': False}
        entries.append(entry)
        station_index[name].append({'sha256': sha, 'relative_path': entry['relative_path']})
    # A station is the unit of triage, not each repeated PNG variant.
    # Keep all artwork variants but never promote a filename to an authoritative ID.
    stations = [{'station_filename': name, 'artwork_count': len(artworks),
                 'artworks': artworks, 'service_reference': None,
                 'identity_verified': False} for name, artworks in sorted(station_index.items())]
    manifest = {'schema': 2, 'policy': 'NAME_CATALOG_ONLY; NO_SERVICE_ID_ASSIGNMENT',
                'station_count': len(stations), 'stations': stations,
                'artworks': len(entries), 'created': created, 'reused': reused,
                'skipped': skipped, 'entries': entries}
    manifest_path = catalog / 'catalog.json'
    fd, tmp_name = tempfile.mkstemp(prefix='.catalog-', suffix='.json', dir=catalog)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(manifest, stream, ensure_ascii=False, indent=2)
        os.replace(tmp_name, manifest_path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
    return manifest


def _digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()
