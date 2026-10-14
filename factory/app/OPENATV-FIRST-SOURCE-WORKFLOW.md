# OpenATV first-source workflow

The active source order is OpenATV 8, Vhannibal, then Chocholousek. Factory synchronizes and scans only OpenATV until its source ledger entry is `COMPLETED` or `UNCHANGED`. Generic inbox archives and optional source manifests are deferred.

`factory/registry/source-processing-ledger.json` is the Git authority for source status. Per-PNG manifests under `factory/registry/source-manifests/openatv8/` contain only source-relative path, service reference when parseable, byte SHA-256, and decoded-pixel SHA-256. No PNG bytes, local absolute paths, credentials, or Windows user names are included. The run checkpoint is under `factory/app/diagnostic-checkpoints/`.

## First real OpenATV batch (2026-10-14)

The owner-provided five-part `02-ORIGINALS` archive passed ZIP CRC validation; combined SHA-256: `b58689171780485889506ef6dbae5f68e70fe48ece3fc536926d4b89fec87dab`. Its five part hashes are recorded in the source ledger. The supplied snapshot has four OpenATV schema-3 content-addressed packages and 148,466 PNG observations (618,394,106 PNG bytes); no upstream version/release ID was present.

An isolated run compared same-reference byte SHA against PiconHub production snapshot commit `f936138f49fd37c845939d1222d9589951bcae79`: 673 exact observations; 7,121 different-artwork observations for existing references; 19,526 new service references; 100,378 PNGs lacked a parsed service reference. These are technical matches only, not identity or approval.

The existing Factory renderer prepared 16,015 unique non-exact-master artwork triplets (48,045 PNG); all 16,015 passed triplet QA. One distinct fully transparent artwork was blocked, covering four source observations. Output bytes are isolated scratch artifacts and are not in Git. No Warder IDs or approvals were created. OpenATV remains `AWAITING_APPROVAL`; no later source was processed.

The application performs a one-time migration that deletes only a file matching the exact known 9,932-task queue fingerprint after recording filename and SHA-256 in `00-STATE/migrations/`. It preserves reports, registries, approvals, Master assets, originals, and any changed/new queue file. It runs after a successful workspace preflight. Since this Work session has no access to the user's D: drive, actual removal there remains unverified until the candidate is launched on that PC.
