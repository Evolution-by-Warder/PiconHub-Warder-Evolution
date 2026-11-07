# Reproduce six reviewed singleton countries

The plan reproduces BT, CX, GW, MS, SM and KM, six references and 54 exact reviewed PNGs. MS uses the same untouched official badge for all backgrounds. SM uses the broadcaster's official monochromatic positive/negative exports; the native 33 antialias-alpha differences are documented in the evidence archive. WF and other held references are excluded.

The source producer uploads seven complete raw originals to the exact `originals[*].path` values and GW as four 300000/300000/300000/673-byte pieces under `original-parts/`. `original-parts-manifest.json` is authoritative for those four pieces. `reassemble_originals.py` verifies all eight originals against SHA-256, byte count and Git blob digest before reproducing artwork. Seven originals are active; the older MS wordmark is evidence only and absent from `render_sources.source_inventory`. Primary evidence is stored as 21 parts under `evidence-parts/` and checked by `verify_evidence_parts.py` against `evidence-parts.json` and the deterministic archive proof.

Place the plan and runner in the isolated `picons/radio-world/staging/singleton-completion-20261107/` staging directory. Run with Python and Pillow exactly 13.0.0:

```sh
python picons/radio-world/staging/singleton-completion-20261107/reproduce_on_github.py --plan picons/radio-world/staging/singleton-completion-20261107/reproduce-plan.json --output-root . --object-cache .
```

The runner reads originals exclusively from staged checkout files, checking SHA-256, byte count and Git blob digest. Renderer, verifier, masters and catalogue are pinned to main commit `8180aa0df6e185efad120338bc53ca04bc5e492a`. A read-only local Git cache is used when the pinned objects exist; otherwise exact pinned GitHub raw resources are loaded and checked. No live broadcaster/logo HTTP fetch occurs.

The unchanged renderer creates nine utility ZIPs only in a temporary directory. All 54 expected SHA-256, byte counts and Git blob digests must match before any destination files are written. Only new SHA-named PNG files under `verified-assets/` and `reproduction-proof.json` are persisted. Unequal existing destination bytes fail; equal existing files are retained.

`local-test-proof.json` and `local-reproduction-proof.json` record the separate temporary-directory test and identical repeat run. `primary-evidence.tar.gz` includes 109 primary evidence, review and provenance files; `evidence-archive-proof.json` records archive and per-member verification, deterministic ordering and zero timestamps/owners. Its SHA-256 is `82d4dedb9f7ba36aa891fd642e9dc5ff826ce5a53b24c40e0c84d1c67856d4db`.

This step reproduces reviewed artwork only. It does not modify production indices, existing ZIPs/PNGs, user data, downloader or IPK files. Downloader integration tests remain a separate root task.
