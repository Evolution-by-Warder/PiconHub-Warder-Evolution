"""Lossless, source-aware service-reference registry diagnostics.

Artwork differences are not identity conflicts. Never assign a Warder ID or
approve an artwork based on matching filenames alone.
"""
from collections import Counter, defaultdict
import ntpath
from pathlib import Path
import re

_SRP = re.compile(r"^[0-9a-fA-F]+(?:_[0-9a-fA-F]+){9}$")

def unmapped_filename_diagnostics(matches, sample_limit=12):
    """Bounded, source-aware evidence for unmapped PNGs; never guess IDs."""
    groups = defaultdict(lambda: {"count": 0, "service_ref_like": 0, "utf8_names": 0, "other": 0, "samples": []})
    for item in matches:
        if item.get("classification") != "UNMAPPED":
            continue
        source = str(item.get("candidate_source", ""))
        group = groups[origin_of(source)]
        group["count"] += 1
        stem = Path(source.replace("\\", "/")).stem
        if _SRP.fullmatch(stem):
            group["service_ref_like"] += 1
        elif stem and not re.fullmatch(r"[0-9a-fA-F_]+", stem):
            group["utf8_names"] += 1
        else:
            group["other"] += 1
        if len(group["samples"]) < sample_limit:
            group["samples"].append(Path(source.replace("\\", "/")).name)
    return dict(sorted(groups.items()))


def origin_of(source):
    parts = Path(str(source).replace('\\', '/')).parts
    if 'source-ingest' in parts:
        i = parts.index('source-ingest')
        if i + 2 < len(parts) and parts[i + 1] == 'originals':
            return parts[i + 2]
    return 'local-inbox'


def summarize_registry_matches(matches):
    counts = defaultdict(Counter)
    for item in matches:
        counts[origin_of(item.get('candidate_source', ''))][item.get('classification', 'REVIEW')] += 1
    return {origin: {key: counts[origin][key] for key in ('IDENTICAL', 'NEW', 'REVIEW', 'UNMAPPED', 'EVIDENCE_LINKED')}
            for origin in sorted(counts)}


def service_reference_diagnostics(matches):
    """Distinguish artwork *files* from distinct service identities.

    Never infer a new service identity from a different image or provider.
    """
    grouped = defaultdict(lambda: defaultdict(lambda: {'sha256': set(), 'sources': set(), 'classes': Counter()}))
    unrecognized = Counter()
    for item in matches:
        origin = origin_of(item.get('candidate_source', ''))
        ref = item.get('service_reference')
        if not ref:
            unrecognized[origin] += 1
            continue
        cell = grouped[origin][ref]
        if item.get('candidate_sha256'):
            cell['sha256'].add(item['candidate_sha256'])
        cell['sources'].add(item.get('candidate_source', ''))
        cell['classes'][item.get('classification', 'REVIEW')] += 1
    result = {}
    for origin, refs in sorted(grouped.items()):
        result[origin] = {
            'distinct_service_references': len(refs),
            'unrecognized_filenames': unrecognized[origin],
            'service_references_with_multiple_artworks': sum(len(v['sha256']) > 1 for v in refs.values()),
            'distinct_artwork_hashes': len({sha for v in refs.values() for sha in v['sha256']}),
            'service_references_by_class': {
                key: sum(any(c == key for c in v['classes']) for v in refs.values())
                for key in ('IDENTICAL', 'NEW', 'REVIEW', 'UNMAPPED', 'EVIDENCE_LINKED')},
        }
    for origin, count in sorted(unrecognized.items()):
        result.setdefault(origin, {'distinct_service_references': 0,
            'service_references_with_multiple_artworks': 0, 'distinct_artwork_hashes': 0,
            'service_references_by_class': {'IDENTICAL': 0, 'NEW': 0, 'REVIEW': 0, 'UNMAPPED': 0, 'EVIDENCE_LINKED': 0}})
        result[origin]['unrecognized_filenames'] = count
    return result


def unmapped_asset_inventory(matches, sample_limit=15):
    """Group source assets by exact basename, without inventing a service ID.

    A repeated UTF8SNP filename is not evidence of a unique service; keep
    original file paths and hashes available for later provenance matching.
    """
    grouped = defaultdict(lambda: defaultdict(list))
    for item in matches:
        if item.get('classification') != 'UNMAPPED':
            continue
        source = str(item.get('candidate_source', ''))
        grouped[origin_of(source)][ntpath.basename(source).casefold()].append(source)
    output = {}
    for origin, names in sorted(grouped.items()):
        repeats = sorted(((name, paths) for name, paths in names.items()),
                         key=lambda pair: (-len(pair[1]), pair[0]))
        output[origin] = {
            'unmapped_files': sum(map(len, names.values())),
            'distinct_filenames': len(names),
            'duplicate_filename_occurrences': sum(len(paths)-1 for paths in names.values()),
            'repeated_filenames': sum(len(paths)>1 for paths in names.values()),
            'examples': [{'filename': name, 'copies': len(paths)}
                         for name, paths in repeats[:sample_limit]],
            'identity_policy': 'NO_SERVICE_REFERENCE_INFERRED_FROM_FILENAME',
        }
    return output


# Package fingerprints confirmed by the 2026-10-10 SRP archive audit.
# These are source provenance labels, NOT identities or Warder approvals.
_OPENATV_PACKAGE_STYLES = {
    'bf8cb399d92f16682bb81639588894dbaed8f7bda7af3ecbc80cbc9a3b15e0ad': ('srp', 'dark'),
    'c3b149471e6b16edc5068481e8df14c8ef71bb0e1dcdf04cdd865c5143178e5a': ('srp', 'light'),
    'd0ac04daa1f655ecbb7e70968bd8e447762d229f2b589014a586ddb25005d87a': ('utf8snp', 'dark'),
    'b8e2583155877d6e35948f5b5025f59b41f3758c32d4480dda3eecd89be1da69': ('utf8snp', 'light'),
}


def _openatv_provenance(source, package_styles=None):
    mapping = _OPENATV_PACKAGE_STYLES if package_styles is None else package_styles
    parts = [part.casefold() for part in str(source).replace('\\', '/').split('/')]
    for part in parts:
        if part in mapping:
            return tuple(mapping[part])
    return ('unknown', 'unknown')


def identity_level_triage(matches, origin='openatv8', sample_limit=20, package_styles=None):
    """Group by SRP, package format and style; never silently approve artwork.

    SHA-256 is byte identity, not perceptual identity. Unknown provenance remains
    explicitly unresolved instead of being interpreted as a graphics conflict.
    """
    refs = defaultdict(lambda: {'hashes': set(), 'classes': set(), 'sources': set(),
                                'buckets': defaultdict(set)})
    named = defaultdict(lambda: {'hashes': set(), 'files': 0})
    for item in matches:
        if origin_of(item.get('candidate_source', '')) != origin:
            continue
        source = str(item.get('candidate_source', ''))
        ref = item.get('service_reference')
        sha = item.get('candidate_sha256')
        if ref and _SRP.fullmatch(str(ref)):
            cell = refs[ref]
            if sha:
                cell['hashes'].add(sha)
                cell['buckets'][_openatv_provenance(source, package_styles)].add(sha)
            cell['classes'].add(item.get('classification', 'UNMAPPED'))
            cell['sources'].add(source)
        else:
            name = ntpath.basename(source).casefold()
            cell = named[name]
            if sha:
                cell['hashes'].add(sha)
            cell['files'] += 1
    status = Counter()
    style_status = Counter()
    conflicts = []
    for ref, cell in sorted(refs.items()):
        classes = cell['classes']
        buckets = cell['buckets']
        known = {k: v for k, v in buckets.items() if 'unknown' not in k}
        unknown = buckets.get(('unknown', 'unknown'), set())
        if len(cell['hashes']) > 1:
            label = 'MULTIPLE_ARTWORKS_REVIEW'
            if unknown:
                style_label = 'UNKNOWN_PROVENANCE_REVIEW'
            elif any(len(hashes) > 1 for hashes in known.values()):
                style_label = 'SAME_STYLE_MULTIPLE_ARTWORKS_REVIEW'
            elif len(known) > 1:
                style_label = 'CROSS_STYLE_DIFFERENCE_ONLY'
            else:
                style_label = 'UNCLASSIFIED_MULTIPLE_ARTWORKS_REVIEW'
            conflicts.append({'service_reference': ref, 'artworks': len(cell['hashes']),
                              'observations': len(cell['sources']),
                              'style_status': style_label,
                              'per_package_style': [
                                  {'format': fmt, 'style': style, 'artwork_hashes': len(hashes)}
                                  for (fmt, style), hashes in sorted(buckets.items())]})
        elif 'REVIEW' in classes:
            label = 'MASTER_ARTWORK_REVIEW'
            style_label = 'SINGLE_ARTWORK_MASTER_REVIEW'
        elif 'IDENTICAL' in classes:
            label = 'MASTER_IDENTICAL'
            style_label = 'SINGLE_ARTWORK_MASTER_IDENTICAL'
        elif 'NEW' in classes:
            label = 'NOT_IN_MASTER'
            style_label = 'SINGLE_ARTWORK_NOT_IN_MASTER'
        else:
            label = 'OTHER'
            style_label = 'OTHER'
        status[label] += 1
        style_status[style_label] += 1
    # Actionable identity categories are separate from legacy diagnostics.
    # Expected cross-style differences are not manual artwork conflicts.
    actionable = Counter()
    for ref, cell in sorted(refs.items()):
        classes = cell['classes']
        buckets = cell['buckets']
        known = {k: v for k, v in buckets.items() if 'unknown' not in k}
        if len(cell['hashes']) > 1 and (buckets.get(('unknown', 'unknown')) or
                any(len(hashes) > 1 for hashes in known.values()) or not known):
            actionable['ARTWORK_VARIANTS_REVIEW'] += 1
        elif 'REVIEW' in classes:
            actionable['MASTER_ARTWORK_REVIEW'] += 1
        elif 'NEW' in classes and 'IDENTICAL' not in classes:
            actionable['NOT_IN_MASTER_CANDIDATE'] += 1
        elif 'IDENTICAL' in classes:
            actionable['MASTER_IDENTICAL_NO_ACTION'] += 1
        else:
            actionable['OTHER_UNRESOLVED'] += 1
    actionable['EXPECTED_CROSS_STYLE_NO_CONFLICT'] = style_status['CROSS_STYLE_DIFFERENCE_ONLY']
    return {
        'schema': 2, 'origin': origin,
        'unique_service_references': len(refs),
        'reference_observations': sum(len(v['sources']) for v in refs.values()),
        'reference_status_counts': dict(sorted(status.items())),
        'style_diagnostic_counts': dict(sorted(style_status.items())),
        'actionable_identity_counts': dict(sorted(actionable.items())),
        'distinct_named_artwork_filenames': len(named),
        'named_file_observations': sum(v['files'] for v in named.values()),
        'named_filename_artwork_conflicts': sum(len(v['hashes']) > 1 for v in named.values()),
        'reference_multiple_artwork_samples': conflicts[:sample_limit],
        'policy': 'READ_ONLY; CROSS_STYLE_IS_NOT_CONFLICT; MASTER_REVIEW_PRESERVED; UNKNOWN_IS_NOT_APPROVED; NO_MASTER_OVERWRITE',
    }
