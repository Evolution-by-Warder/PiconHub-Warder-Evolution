Batch42 is a local template. No assets, ZIPs, GitHub refs, or production files were changed by this preparation.

Run after both producer exports are immutable and complete, from the workspace root:

```bash
python continuation/quality-tools/prepare42.py \
  --laut-selection continuation/laut-api-batch/github-results/selection.json.gz \
  --laut-ledger continuation/laut-upload/visual-ledger.json.gz \
  --singleton-selection PATH_TO_PINNED_SINGLETON_SELECTION.json.gz \
  --singleton-ledger PATH_TO_SINGLETON_VISUAL_LEDGER.json.gz
```

The wrapper defaults to parent673062395da2f49cf2c739a16c605eedc9553480, verifies baseline index SHA85f17a3022d770a31dd1cd2fcf53ba19a6681d4c7ec0a0133ebe56e59a14fd30 and actual2429 coverage. It requires435laut+6singleton rows; these are expected producer counts, not completed integration results. `--parent` and `--expected-baseline-sha256` permit an explicitly reviewed canonical successor.

Outputs are under continuation/output/picons/radio-world/staging/batch-42-reviewed/: deterministic selection.json.gz, combined new visual-ledger.json.gz (including actual v3 metadata-only source_holds), configuration.json and preparation-proof.json. No PNG fingerprint is invented for source-only holds. The wrapper rejects pending source pins, missing9variants, duplicate refs, prior negative exact artwork, unresolved source holds, unexpected counts, and changed baseline bytes. Expected coverage is calculated2429+actual validated rows, never asserted as a completed result.

Use continuation/quality-tools/workflow42-reviewed.yml for the working-branch workflow only. Keep current quality-tools/saved_artwork_import.py, visual_gate.py, test_visual_gate.py, audit_png_admission.py and stable replay_downloader.py. Workflow runs the15regressions, exact selection gate against all700+898+39+40+41+newlaut/singleton ledgers, importer byte checks, historical preservation, complete candidate admission audit retaining10332production PNG variant entries, and unchanged stable downloader replay across all available countries. New ZIPs are made only for affected country/variant unions; existing source ZIPs are never rebuilt. Runtime importer enforces actual64MiB ZIP limit.

Independent DE400WHITE conservative preflight is batch42-de-white400-preflight.json:347newDErefs, existing package26,508,614bytes + new rawPNG32,697,581bytes +1MiB contingency =60,254,771bytes, below67,108,864bytes by6,854,093bytes. No existing ZIP fetched/recreated/recompressed. This estimate does not replace the runtime actual ZIP size assertion.

Validation performed locally: prepare42.py --help/import succeeded; existing15visual_gatev3 regression tests passed using the actual saved898 ledger with its local test data root adjusted in memory. Initial unadjusted scratch-layout test invocation could not locate its staging directory and executed0tests; no implementation change was needed.
