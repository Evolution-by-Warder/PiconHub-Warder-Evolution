# PiconHub Warder Evolution — PROJECT CHECKPOINT

Updated: 2026-09-15
Purpose: durable recovery checkpoint. This file applies ONLY to **PiconHub Warder Evolution**, not to the separate futuristic PiconHub project.

## FIRST: identify the project line

There are two independent PiconHub projects. Binding separation is documented in `docs/PICONHUB-PROJECT-LINES.md`; current parallel work plan is in `docs/PICONHUB-WORK-PLAN.md`.

- **PiconHub — original Warder project**: independent plugin with the new futuristic UI; version family `0.6.x / 0.7.x`.
- **PiconHub Warder Evolution — THIS repository**: modernization of the original s3n0/Chocholousek Picons Enigma2 plugin; version family `5.0.240904.x`.

Never mix their graphics, screenshots, UI/layout decisions, versions, packages, checkpoints or code assumptions. A screenshot/package from one line is not evidence for the other.

## Current state — Warder Evolution

PiconHub Warder Evolution is ACTIVE / IN DEVELOPMENT. Current tested plugin baseline recorded in the repository README is `5.0.240904.6`.

The complete-catalog BLACK/WHITE production phase is being handled on the controlled branch `warder-master-production`. Do not use that branch for unrelated plugin/UI work while production is active. No uncontrolled mass rewrite on `main`.

## V9 / MASTER quality standard — APPROVED AND FROZEN

Štefan visually approved V9 on 2026-09-15. The Warder Evolution MASTER rules are frozen. The approved rules commit is:

`1428a108c5a2d5cdd9725a35ca4cb2c43e703d6e`

Binding detailed rules are in `docs/PICON-MASTER-QUALITY-PLAN.md`.

Important V9 rule for mixed/colored logos: a white/very light logical text component directly on WHITE may be changed to dark/black only when a safe component mask isolates it; the reverse applies to dark text disappearing on BLACK. Protected colored components remain unchanged. If safe isolation cannot be guaranteed, classify REVIEW rather than guess.

QC classes: PASS / AUTO-FIXED / REVIEW / ERROR-SKIP.

## LOCKED — graphics and structure

For **PiconHub Warder Evolution**, approved original graphics, GUI structure/layout, dimensions, positions, provider artwork, MASTER templates and established repository/runtime structure are LOCKED. New functionality must adapt to them. Do not redesign, redraw, regenerate, resize, reposition, reorganize, rename or replace them without Štefan's explicit approval.

Do NOT import the futuristic UI, its provider-panel count, screenshots or layout decisions from the separate PiconHub project into Warder Evolution.

## Binding runtime picon architecture

Exactly:

`picons/<satellite-position>/<provider>/{transparent,white,black}/<service-reference>.png`

Hard rules:
- satellite position → provider → style;
- no extra `satellite` directory;
- no `Satellite 0`;
- no style directories directly under satellite position;
- no invented/generic provider merely to force an import;
- style names exactly `transparent`, `white`, `black`;
- preserve service-reference filenames.

## MASTER templates — FINAL

Authoritative files:
- `templates/picons/black-sablona.png`
- `templates/picons/white-sablona.png`

They are final 220×132 RGBA assets and must not be modified, regenerated, resized, recolored, redrawn or approximated.

Private Trezor backups:
- `backups/piconhub/master-templates/black-sablona.zip`
- `backups/piconhub/master-templates/white-sablona.zip`

Trezor commit: `7c2b2e6dbdaf3c5c4c3430c76ae691cf6fffa927`.

ZIP SHA256:
- black `27fc4712d600b97572b03e7403f22a5185ea3faac4bd39df430163a6aa951abc`
- white `4252701bd5142114e59849d06f20de42a248232f21e12eba5ba9080618c12080`

## Vhannibal guarded import — completed

Merged commit: `ac7fb19f1cf098d636e5ccdad0a065fbb92befbc`

Results:
- source PNG 13,903
- added transparent 4,601
- existing/preserved 3,737
- unknown position/namespace 420
- non-220×132 117
- missing provider 5,028
- invalid filename 0

Unresolved sets must not be guessed. No generic `vhannibal` provider and no automatic resize of the 117 nonstandard files without an approved rule.

Retained audit/import material is under `migration/vhannibal/`.

## Current work plan

Two PiconHub lines are developed separately and may proceed in parallel. The authoritative plan is `docs/PICONHUB-WORK-PLAN.md`.

For Warder Evolution now:
1. Work completes and audits BLACK/WHITE production on `warder-master-production` using only frozen V9 rules and original MASTERs.
2. Review counts, architecture, QC results, samples and REVIEW cases before any merge to `main`.
3. Continue s3n0 plugin modernization separately around the LOCKED graphics/structure; do not collide with the active production branch.
4. After catalog normalization and approval, Orbit Watch / satellite-change monitoring remains the planned later module.

For the separate original Warder PiconHub project, continue only from its own verified source/package/UI baseline. Its futuristic UI and `0.6.x / 0.7.x` artifacts stay in that project.

## Recovery rule

After any context loss, read in this order:
1. `docs/PICONHUB-PROJECT-LINES.md`
2. `docs/PICONHUB-WORK-PLAN.md`
3. this `docs/PROJECT-CHECKPOINT.md`
4. `docs/PICON-MASTER-QUALITY-PLAN.md`

First identify which PiconHub project is being discussed. Never infer one project's UI, versions or decisions from the other. For Warder Evolution preserve all LOCKED graphics/structure and frozen V9 MASTER rules unless Štefan explicitly approves a change.
