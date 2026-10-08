# Auxiliary production staging (not published)

This branch stages the approved Provider/Satellite auxiliary workflow without changing production or the channel renderer.

## Entry points

- `python3 tools/auxiliary_ingress.py`: explicit auxiliary-only CLI, pinned to the transparent-source ZIP and the three approved centered candidate ZIPs.
- `python3 tools/test_auxiliary_ingress.py`: invokes that CLI in a temporary clean-report location and checks the complete 173-identity/346-PNG result, approvals, and output comparison.
- `python3 tools/test_warder_visual_qc.py`: helper, proof-case, approval invalidation, and production channel fixture regressions.

`tools/rebuild_master_catalog.py` is byte-identical to production baseline `b33644ada1ae61c1c0085ec753a20c48b1549e9a`. Auxiliary namespace and input paths do not use channel service-reference validation or channel output paths. No fallback directory is written or removed.

## Immutable inputs

The four ZIP input pins (Git blob SHA, file SHA-256, size) and two immutable template SHA-256 values are defined in `tools/auxiliary_ingress.py`. Individual transparent source and candidate output hashes are bound by the centering audit JSONL. Source provenance is PiconHub commit `db5eec9f1cdb7a4d587cb1bcdeebc6b3f0d51819`; candidate checkpoint `8bf726a3d7ba046f5bc531c8236b573963b7557a`; QC checkpoint `13dd00b5624c4b6659574cdddedd503edc18947`.

The source ZIP and three candidate ZIPs were reused from their existing immutable Git blob objects. Transparent sources and approved candidate PNGs are read-only inputs. The CLI does not regenerate, replace, or publish PNGs.

## Channel parity

`reports/auxiliary-staging/channel-parity.json` records a full independent rebuild comparison of all transparent channel inputs and BLACK/WHITE outputs. Channel PASS requires the same identity set and exact SHA-256 for every output in the original and staging builds.
