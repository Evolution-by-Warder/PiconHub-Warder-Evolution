# Existing Master approval evidence migration

The `master-approval-evidence.json` file is local-only and optional. The
Factory never generates it from PNG presence, filenames, service references,
pixel similarity, a review click, or `FINALIZED_LOCALLY`. The repository's
current review ledger distinguishes `APPROVED_FOR_REVIEW` from final QA and
Master approval; neither status by itself proves that an artwork was approved
into the Master.

## Evidence source status

The current repository contains no Master approval archive or canonical Warder
ID registry. A supplied Factory workspace ZIP was integrity-checked and
contained reports/logs only; it had no `03-REGISTRY` files, no review-decision
ledger, and no approval history. It therefore proves no historical approval.
Migration counts must remain unverified until the user's local evidence is
processed.

## Read-only migration tool

Run from the Python source directory on a copy of local evidence. The default
operation creates only the requested local audit report:

```powershell
python master_approval_migration.py `
  --master-index "D:\WARDER-PICON-FACTORY\08-REPORTS\warder-master-index-<run>.json" `
  --master-commit "<exact 40-character Master snapshot commit>" `
  --evidence "D:\WARDER-PICON-FACTORY\05-QA\<approval-audit>.json" `
  --report "D:\WARDER-PICON-FACTORY\08-REPORTS\approval-migration-audit.json"
```

The packaged one-file executable exposes the same tool with
`WARDER-PICON-FACTORY.exe --migrate-master-approvals` followed by the same
arguments. The normal GUI/startup path is unchanged.

The tool classifies each service as `VERIFIED`, `PARTIAL`, `NO_EVIDENCE`,
`CONFLICT`, or `NEW`. A usable historical record must explicitly identify a
Master approval (`master_approved: true` or a Master approval event type),
assert `identity_verified: true` and `artwork_approved: true`, contain an
approval record reference, match the exact Master commit, and carry current
variant SHA-256 values. If a source record supplies `evidence_sha256`, it must
match the canonical JSON hash of that record excluding the digest field.
Conflicts, stale hashes, old commits, duplicated contradictory approvals,
missing records, and legacy review-only decisions fail closed.

After reviewing the audit report and preserving its source evidence, the
operator may request a separate local manifest write:

```powershell
python master_approval_migration.py `
  --master-index "D:\WARDER-PICON-FACTORY\08-REPORTS\warder-master-index-<run>.json" `
  --master-commit "<exact 40-character Master snapshot commit>" `
  --evidence "D:\WARDER-PICON-FACTORY\05-QA\<approval-audit>.json" `
  --report "D:\WARDER-PICON-FACTORY\08-REPORTS\approval-migration-audit.json" `
  --write-manifest "D:\WARDER-PICON-FACTORY\03-REGISTRY\master-approval-evidence.json"
```

The manifest write is atomic, local-only, and refuses to replace an existing
file. The operator must review it before Factory consumes it. It must not be
uploaded to GitHub or included in diagnostics. Current Master/Registry files
are never written by this migration.
