# PiconHub Warder Evolution — PROJECT CHECKPOINT

Updated: 2026-09-15
Purpose: durable recovery checkpoint so the project can be resumed exactly after loss of chat/context.

## Current project state

PiconHub Warder Evolution is **ACTIVE / IN DEVELOPMENT**. Current `main` contains the reorganized runtime picon catalog, completed guarded Vhannibal transparent import, authoritative BLACK/WHITE master templates, migration tooling, and the master quality plan.

## Binding runtime architecture — NEVER CHANGE SILENTLY

The runtime picon tree is exactly:

`picons/<satellite-position>/<provider>/{transparent,white,black}/<service-reference>.png`

Rules:

- satellite position → provider → style,
- NO extra `satellite` directory,
- NO `Satellite 0`,
- NO color/style directories directly under satellite position,
- NO invented/generic provider merely to force an import,
- current style directory names are exactly `transparent`, `white`, `black`.

This architecture is a hard project decision. Do not reintroduce old structures.

## Completed catalog reorganization

The catalog was reorganized to the binding architecture above. Historical cleanup also removed the invalid Satellite 0E package/duplicate Magio entry. Do not use old historical paths as evidence of current runtime structure.

## Vhannibal import — completed guarded phase

Merged to `main` in commit:

`ac7fb19f1cf098d636e5ccdad0a065fbb92befbc`

Authoritative import result:

- source PNG: 13,903
- added transparent picons: **4,601**
- existing/preserved: **3,737**
- skipped unknown position/namespace: **420**
- skipped non-220×132: **117**
- skipped missing provider: **5,028**
- invalid filename: **0**

The import added only safely classified transparent picons. It did NOT fabricate BLACK/WHITE variants and did NOT overwrite existing service references.

Retained audit/import files:

- `migration/vhannibal/import_vhannibal.py`
- `migration/vhannibal/README.md`
- `migration/vhannibal/import-report.tsv`
- `migration/vhannibal/import-summary.txt`

The one-time Vhannibal workflow was removed before merge. Do not restore it as permanent runtime infrastructure without a new explicit reason.

### Unresolved Vhannibal sets

Still NOT imported and must not be guessed:

- 5,028 missing-provider picons,
- 420 unknown `EEEE0000` namespace/position cases,
- 117 non-220×132 cases.

Future work may investigate these using reliable metadata. Do not put them under a generic `vhannibal` provider and do not invent position/provider mappings. Do not resize the 117 nonstandard files automatically unless a deliberate rule is later approved.

## BLACK/WHITE MASTER templates — FINAL

Authoritative templates on `main`:

- `templates/picons/black-sablona.png`
- `templates/picons/white-sablona.png`

Added in commit:

`292fcbaa98a20bb95263a1ad60a489676aa64f06`

Both are 220×132 RGBA with alpha. These exact stored MASTER templates are FINAL and valid **as they are**. Do not repair, redraw, regenerate, recolor, deform or replace them with AI/approximate copies.

Original ZIP backups are stored in private Trezor:

- `backups/piconhub/master-templates/black-sablona.zip`
- `backups/piconhub/master-templates/white-sablona.zip`

Trezor backup commit: `7c2b2e6dbdaf3c5c4c3430c76ae691cf6fffa927`.

ZIP SHA256:

- black: `27fc4712d600b97572b03e7403f22a5185ea3faac4bd39df430163a6aa951abc`
- white: `4252701bd5142114e59849d06f20de42a248232f21e12eba5ba9080618c12080`

## New complete-catalog quality goal

The target is no longer merely to fill missing Vhannibal BLACK/WHITE variants. The intended next major phase is to bring the **complete PiconHub catalog** to a consistent Warder Evolution quality standard using the final MASTER templates.

Detailed plan is in:

`docs/PICON-MASTER-QUALITY-PLAN.md`

Current plan commit after confirming masters final:

`1ef2f4e56b63a13e98f8eb3432f50b3f83b173bb`

### Required pipeline

For each transparent source:

1. QC transparent source first: dimensions, RGBA/alpha, edge quality, sharpness, blur/resize artifacts and damage.
2. Do NOT sharpen everything. Apply only a gentle, controlled correction when QC proves it is needed; avoid halo/jagged edges/design changes.
3. Analyze logo/text contrast separately against BLACK and WHITE master backgrounds.
4. Prevent unreadable combinations such as white/light logo on WHITE or black/dark logo on BLACK.
5. Preserve original brand colors/design whenever possible; never use a crude global rule such as blindly turning all white logos black.
6. If contrast correction is necessary, use only a minimal pre-approved method. Ambiguous cases go to REVIEW, never to automatic guessing.
7. Generate BLACK and WHITE using the exact final masters.
8. Validate every result: 220×132, PNG/RGBA/alpha, correct position/provider/style path, identical service-reference filename, readable logo, clean edges, no unwanted design changes.

QC categories:

- PASS
- AUTO-FIXED (must be audited)
- REVIEW (manual decision required)
- ERROR/SKIP (reason required)

## Before full batch — mandatory sample approval

Do not launch the whole catalog immediately. First prepare a representative test set containing at least:

- light/white logo,
- dark/black logo,
- colored logo,
- fine/small text,
- already sharp high-quality transparent,
- soft/low-quality transparent suitable for controlled sharpening test,
- low-contrast case on WHITE,
- low-contrast case on BLACK.

Štefan + ChatGPT define and visually approve the rules/samples first. Only after approval are those rules frozen for the full production run.

## Division of work for full production

Chat/Štefan + ChatGPT:

- define visual/QC rules,
- approve representative samples,
- decide ambiguous aesthetic cases,
- review final reports/results.

Work:

- execute the large multi-stage operation over thousands of files,
- perform QC using only approved rules,
- generate BLACK/WHITE,
- validate outputs,
- create audit/report and working Git branch/PR.

Work must NOT invent aesthetic rules and must NOT auto-approve REVIEW cases.

## Git safety for the full catalog phase

Do not perform the mass rewrite uncontrolled directly on `main`.

Required approach:

1. working branch,
2. QC + generation,
3. audit/report,
4. verify counts and architecture,
5. review samples and all REVIEW cases,
6. merge to `main` only after successful validation/approval.

Transparent sources must not disappear. Existing BLACK/WHITE may be replaced by the new final-master standard only as part of the explicitly approved complete-catalog rebuild.

## Chocholousek migration state

Chocholousek migration tooling/plans exist under `migration/chocholousek`, and backup material exists in private Trezor under `ChocholousekPicons/`. Keep migration/archive mechanics separate from runtime `picons/` and separate from Vhannibal unless an explicit future step connects them.

## UI project state

PiconHub UI is also still in development. The main design checkpoint is 1672×941. The `VYBERTE PROVIDERA` section has exactly 6 panels. Approved provider artwork exists for Skylink, Magio Sat, ANTIK Sat, freeSAT and Telly; their established order/coordinates must be preserved when continuing UI work. Do not redesign or reposition approved provider assets without explicit approval.

## Recovery rule

If chat/context is lost: read this file and `docs/PICON-MASTER-QUALITY-PLAN.md` first, inspect current `main`, and continue from these checkpoints. Never infer architecture from obsolete history. The final MASTER templates are accepted exactly as stored. The immediate next major task is representative QC/sample-rule approval, then the complete-catalog BLACK/WHITE quality rebuild through Work on a controlled branch.
