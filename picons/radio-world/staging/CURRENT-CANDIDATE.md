# Current Warder Radio candidate · 2026-11-07

Production remains batch33 at `8180aa0df6e185efad120338bc53ca04bc5e492a`. No production merge or IPK release has been performed. PR67 and PR68 remain Draft by explicit instruction.

## Tested candidate through40

- Immutable tested checkpoint: `8c6caf04c608f8443969af66d1e39538bccc86f0`.
- Current working integration: PR68 branch `work/radio-world-batch38-contrast-pass1-history-20261107`; its canonical country index and release manifests reuse the exact tested Git blobs.
- Staging index: `picons/radio-world/staging/batch-40-reviewed/countries.proposed.json`.
- Index:219 countries,109 available;6 complete,103 partial,110 unavailable.
- Complete countries: SK,CZ,TD,GG,KI,LR.
- Coverage:2389 of35560 country references;33171 remain without an admitted candidate picon.
- Candidate archive inventory:22077 PNG variant entries including aliases; all10332 production entries preserved exactly.
- Every11745 additional PNG entry is bound to an exact approved nine-variant review.
- CI42372903860 passed: all109 available countries,324 public220x132 ZIP URLs,2388 exact installs+1 custom file/style,0 failures,repeat0ZIP,and settings/history/favourites preserved.
- Thirteen regression tests passed, including rejection of a repair with even one stale held variant. A held artwork can only be replaced by a separately reviewed exact nine-hash replacement.
- Language repair18:162 PNGs regenerated from exact official language originals and immutable MASTERs; CI42372359825 reproduced all162 local SHA256/bytes/Git blobs. Corrected source PNG commit:`40a534e2f316c3256759f0caef55f1867d2365de`; retain source branch `work/radio-replay18-source-20261107`.
- Batch39:334 admitted refs/3006PNG after732 actual visual and primary-identity reviews. Batch40:18 exact language repairs+27 vetted CDN reuses=45refs/405PNG.
- Independent legacy review34–36:all898 complete,530 admitted/368 held before the18 later language replacements. No legacy visual review remains pending.
- PR67 separately proposes219 admitted refs from34–35 (181 held),index219/81/1303; integration commit`0359575fa65c19c2b2172075ebe4e9c0e37bf0d5`.
- Exact alias audit across all2389 admitted country donors found0 additional country matches;89 HDF matches and64 historical extra PNG filenames are excluded from station counts.
- Physical receiver test was not performed.

## Continuation

The next source work is separate from this tested checkpoint:
- `continuation/world42`:40 accepted saved-artwork refs/21countries;31 held final candidates,2 source tenants excluded. Not yet integrated.
- `continuation/laut-api-batch`:889 new official laut.fm country station objects frozen from primary API,36countries. Source download, explicit country/default-image exclusions and visual review are in progress. No pending source is admitted by these counts.

Preserve all pinned working payload/source branches and immutable snapshots. In particular retain `work/radio-batch33-legacy-payload-20261106` at `3bd8ea5659eb4d21c913ab4edb090d890d646a39`. Do not regenerate existing ZIPs or use rejected render outputs as new inputs. New work must preserve all existing production PNG bytes.

Detailed Slovak journal: Radio-Warder-Evolution branch `work/radio-batch33-recovery-register-20261106`, `RADIO_PROGRESS.md`. No merge, publishing or new IPK without explicit approval.
