# Auxiliary Provider/Satellite production architecture

Status: architecture implementation on auxiliary-production-architecture-20261008.
This is not a production publication and contains no approved auxiliary PNGs.

## Isolation boundary

Channel picons keep their existing identity and path contract:

    picons/<orbital-position>/<provider-folder>/{transparent,black,white}/<service-reference>.png

The auxiliary catalog is a separate root, outside picons:

- auxiliary/provider-logo/black/<filename>.png
- auxiliary/provider-logo/white/<filename>.png
- auxiliary/satellite-logo/black/<filename>.png
- auxiliary/satellite-logo/white/<filename>.png

The canonical key is exactly provider-logo::<filename> or
satellite-logo::<filename>. These keys are not service references, registry
IDs, provider-folder names, or orbital positions. In particular,
satellite-logo::150W.png does not imply an orbital mapping.

No auxiliary code is imported by rebuild_master_catalog.py,
validate_source(), or the channel renderer. No fallback into the channel
catalog is defined.

## Manifest contract, schema version 1

The deterministic JSON document has only these top-level fields:

- schema_version: integer 1
- approved_candidate_checkpoint: immutable 40-character Git commit SHA
- entries: non-empty array sorted by case-folded identity key

Each entry has exactly:

- identity: namespaced auxiliary key
- kind: provider-logo or satellite-logo
- filename: original basename, unchanged
- black: path and lowercase SHA256
- white: path and lowercase SHA256
- transparent_source_sha256: pinned source digest
- qc_status: PASS
- visual_approval_provenance: non-empty checkpoint/review reference

Asset paths are derived from kind, variant, and filename; callers cannot
choose arbitrary roots. There are no channel, service-reference, provider
folder, registry-ID, or orbital-position fields. Optional metadata is omitted
until a concrete consumer requirement exists.

The implementation is in tools/auxiliary_catalog.py:
build_manifest() emits the canonical shape and ordering;
canonical_manifest_bytes() produces stable JSON bytes.

## Fail-closed validation

verify_candidate_archives() requires the exact four approved candidate
archives, caller-supplied immutable archive SHA pins, exact archive member
sets, valid ZIP CRCs, safe paths, no symlinks, and exact per-member SHA256s.
The expected members are derived from the namespaced manifest entries.

validate_publication() is the single publication gate: it first verifies the
candidate archives, then calls validate_manifest() on the staged root.
validate_manifest() verifies:

- unique case-insensitive identity keys and target paths
- correct domain/filename identity binding
- exact auxiliary target path for each variant
- 220×132 RGBA PNG decode and exact SHA256
- complete BLACK/WHITE pair
- no symlinks, missing files, or orphan files in the auxiliary asset tree
- no target path collision with supplied channel paths
- no channel-only identity fields
- deterministic manifest order

load_catalog() validates the JSON and staged tree before returning the lookup
index. lookup_auxiliary(catalog, kind, filename, variant) only accepts the two
auxiliary kinds and black/white. It returns the exact auxiliary path or None;
it performs no case-insensitive aliasing, variant fallback, channel lookup, or
satellite/orbital inference.

## Publication flow

1. Read the pinned source and candidate archives already committed under
   reports/warder-master-production/.
2. Verify their immutable checkpoint, archive pins, and per-PNG hashes.
3. Build the deterministic manifest; do not rerender or alter the approved PNGs.
4. Stage the 346 files only under auxiliary/ on an isolated publication
   staging branch.
5. Run archive and staged-tree validation from a clean checkout.
6. Review manifest, hashes, exact changed paths, and channel-tree non-change.
7. Only a separately authorized later step may merge/publicize the auxiliary
   catalog. Runtime consumption is a separate integration and is not provided
   by this repository change.

There is no direct unzip-to-production step. The existing channel rebuild is
not an auxiliary publisher: it removes existing channel BLACK/WHITE files,
validates the service-reference path, and rewrites channel outputs.

## Rollback

The architecture-only branch can be discarded without touching production.
For a future staged asset import, rollback removes only the versioned auxiliary
manifest and the isolated auxiliary/ tree from that staging commit. No
channel picons, transparent masters, channel IDs, or external legacy fallback
directories are modified.

## Current scope and limits

This branch adds only the catalog contract, its tests, and this document. It
does not contain the 346 approved BLACK/WHITE PNGs or a production manifest,
does not alter the current channel catalog, and does not implement a FullHDGlass
or other runtime consumer.
