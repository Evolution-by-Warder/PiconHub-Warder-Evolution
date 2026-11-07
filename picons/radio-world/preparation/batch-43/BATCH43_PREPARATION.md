Batch43 preparation only — no producer export or country build is asserted complete.

The immutable baseline is PR68 commit `b99fe072f36d03871cc9c0e7546a5fc9294846a0`; index SHA256 `8dfc9b924bc2c144997c1333840364ae12a2c7497baa2bcf02a9e9c5ef633d70`,219 countries,119 available,12 complete,2870 covered country references. The public baseline was fetched independently and its exact SHA/counts verified.

Planned source scopes are113 Zeno +25 primary +3 independently reviewed contrast repairs. These are expectations, not existing source pins or claimed completed outputs. Actual pinned producer selections and their final nine-variant ledgers must exist before preparation runs. No placeholder selection/configuration, PNG, ZIP or fictional source commit is supplied here.

From the shared workspace, after the actual exports pass their producer byte/pixel/visual gates:

```bash
python continuation/quality-tools/prepare43.py \
  --source "$ZENO_SELECTION:$ZENO_LEDGER" --expected-source-count 113 \
  --source "$PRIMARY_SELECTION:$PRIMARY_LEDGER" --expected-source-count 25 \
  --source "$CONTRAST_SELECTION:$CONTRAST_LEDGER" --expected-source-count 3
```

`--source SELECTION:LEDGER` and `--expected-source-count` repeat in matching order. Every count must match actual files and their sum must equal `--expected-total` (default141). Any changed reviewed scope requires explicit operator counts/total. Expected output instances are computed only after real files validate;141×9=1269 is not claimed rendered/built. Expected candidate coverage is baseline2870 plus the validated unique selection count.

Use `--history-root`, `--config-template`, `--baseline` and `--stage` to run outside the workspace layout. A repository checkout defaults to `picons/radio-world/staging` and `picons/radio-world/catalog/countries.json`; the workspace defaults to `continuation/output/.../staging` and `continuation/results-42-reviewed/countries.proposed.json`. The checked-in preparation script finds the unchanged visual_gate.py under `picons/radio-world/tools`.

Admission is closed until all required inputs validate: actual source commit hashes, safe parent asset_root paths (without trailing verified-assets), exact station identity, all nine SHA256/bytes/Gitblob triples, no duplicate references, exact per-source final approvals, every historical ledger, and source/identity holds. Actual v3 metadata-only source_holds are preserved; no fake PNG fingerprints are invented. Existing unequal prepared files are refused, and all validation happens before writing the output stage.

Historical ledger inventory is explicit: source-ledger-reviewed-20261107 (700), visual-review-34-36 (898), batches39,40,41,42, plus new43. workflow43-reviewed.yml is a template; it is deliberately outside `.github/workflows` on the preparation checkpoint branch. Root owns activation and the real work/radio-world-batch43-reviewed-history-20261107 branch. Every one of the three full visual_gate calls and the full candidate audit_png_admission call includes all seven exact ledger paths and is immediately preceded by an exact7path/file-presence assertion. No partial history gate remains. Checkout includes batch42 explicitly. The workflow runs15 existing v3 regressions, the unchanged importer, actual64MiB ZIP limits, preservation of earlier PNGs, independent10332 protected production-variant preservation, and full-candidate admission.

The downloader remains Radio0.1.9.2 commit `b7384bfdb55621beaf183ca6d40e9dedacaecdb9`. Replay covers all available candidate countries, TRANSPARENT/WHITE/BLACK at220×132, repeat-zero-ZIP behavior and user-data preservation. No IPK, production merge or main write is performed. Existing source ZIPs are read/preserved; only approved affected unions may produce new country archives when root later activates the workflow.

Local validation:12 preparation regression tests passed against the real, existing singleton6 immutable fixture (this validates the generic loader only; it does not admit those old sources into batch43). They cover unpinned inputs, mismatched counts, duplicate references, unsafe asset roots, incorrect nine-key inventories, noninteger byte counts, no writes on missing/count-incomplete inputs, all four full-history gate/admission calls, and bash syntax of every YAML run block. The unchanged15 visual_gate tests passed with the scratch fixture root adapted in memory. No positive batch43 build was run because its three actual source exports were not ready.

For local test replay, `test_prepare43.py` uses the existing singleton6 fixture path or `WARDER_PREP43_SELECTION_FIXTURE`; it does not fabricate source pins. `batch43-template-proof.json` records exact code hashes and completed test scope. Source producer approvals must still be checked separately before preparing an actual selection.
