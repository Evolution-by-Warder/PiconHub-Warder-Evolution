# 02-ORIGINALS inventory and active queue review

Date: 2026-10-14. This checkpoint records an owner-provided five-volume archive and an owner-provided Windows workspace snapshot. It contains aggregate evidence only; no PNG, raw per-item PC report, credential, or local absolute path is committed.

## Source inventory

The five canonical split volumes passed SHA-256 verification. The joined ZIP passed CRC validation. All 190,435 PNG entries decoded successfully in a read-only pass: 28,008 PiconHub, 148,466 OpenATV8, and 13,961 Vhannibal. PiconHub contains 9,336 complete transparent/black/white triplets. 190,335 images are 220×132. Four source files are fully transparent; their common content is the separate `ilsole24ore tv` QA hold.

Raw content hashes yield 22,811 duplicate groups with 150,382 extra file observations. Decoded pixel hashes yield 22,825 groups with 150,442 extra observations. These identify repeated files/pixels only; they do not prove service identity or approval.

OpenATV schema-3 contains four package-hash directories matching the SRP light/dark and utf8snp light/dark styles. Vhannibal's archive digest is recorded in the JSON checkpoint. A read-only PiconHub path-catalog comparison against production matched 39 satellite subtrees by entry counts and two commutative path fingerprints; PNG bytes were not compared and production was not modified.

## Actual active review queue

The latest owner-provided workspace run has 9,932 tasks: 4,054 identity, 5,877 artwork, and 1 technical QA. Each identity and artwork task has a distinct service-reference key inside its lane; there are zero exact duplicate same-service tasks to remove. 3,533 artwork tasks have one candidate pixel fingerprint and 2,344 have multiple candidate fingerprints; every task differs from its Master artwork in the report's pixel comparison.

Identical visual evidence recurs across services (345 artwork evidence buckets, covering 585 extra rows; 651 identity-signature buckets, covering 1,146 extra rows). These are useful visual triage buckets only. They are not a safe common approval scope because service references differ. No additional active task was automatically removed. The earlier 8,079 style-only identity checks and 2,902 duplicate-file observations were already suppressed by the Factory with no approval created.

The PC's local snapshot reported 3,386 Master reference matches but failed validation with `Fetched Git Warder Master snapshot failed validation`. Those matches are therefore not used to suppress tasks. The Git identity registry and approval ledger contain no verified identity/approval evidence for this queue. An empty ledger is not approval evidence. No Warder ID or approval was created.

## Diagnostic delivery defect

The engine imported `retry_review_evidence_exports` from `factory_diagnostics_retry`; that function actually lives in `review_evidence_upload`. The ImportError prevented both diagnostic upload paths. The 60-second scheduler then repeated the same failure. The fix imports the function from its actual module, stores per-file SHA retry counts atomically, limits automatic retries to three, pauses automatic polling after failure, preserves local reports, and reserves retry reset for explicit user action.

## Evidence and limitations

The machine-readable counterpart is `originals-and-queue-audit-20261014.json`; it records the five volume hashes, archive counts, anonymized queue counts, and the owner workspace snapshot SHA-256. Full item-level review reports and detailed inventory remain outside Git because the former contain local file paths and the latter is a bulky derived listing.

This audit does not create approvals, merge services by artwork, alter Warder IDs, or modify any production data. `ilsole24ore tv` remains blocked for separate QA.
