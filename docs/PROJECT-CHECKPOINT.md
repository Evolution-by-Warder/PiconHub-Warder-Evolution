# PiconHub Warder Evolution — PROJECT CHECKPOINT

Updated: 2026-09-15
Purpose: durable recovery checkpoint so the project can be resumed exactly after loss of chat/context.

## V10 approval and resume addendum — 2026-09-25

This dated status supersedes older immediate-resume instructions in the historical checkpoint below. Its architecture, locked graphics, and MASTER rules remain binding.

- Pass 9: 52/52 approved and closed; Batches 1–12 closed (per the 2026-09-17 approval record).
- Batch 13: 12/12 visually approved on 2026-09-25.
- Corrected WHITE outputs: #3021, #3032, #3072, #3096. Approved as displayed without further edits: #3009, #3010, #3011, #3027, #3028, #3029, #3030, #3031.
- The four approved WHITE PNGs and their approval audit were applied to this test branch in commit `185f6be3499cf7bc147d20fee86a3ca624bab77d`.
- No full-catalog rebuild or merge to `main` has been performed. `main` remains unchanged.
- User visual selection (2026-09-25): keep the middle-column CURRENT WHITE outputs for #14716, #3163, #3133, and the PASS control; reject the scratch prototype alternatives. No PNG changed. Full paths: `reports/warder-master-production/phase4-v10-experiment-20260925/USER-VISUAL-SELECTION.md`.
- Scratch adjacency-guard-v2 regression (2026-09-25): #3163 and #3133 detected as unsafe and left REVIEW with 0 changed pixels; #14716 stayed REVIEW via V9 fallback; PASS control stayed PASS. All four composites were pixel-identical to the selected current WHITE outputs. This is limited fixture evidence, not V10 or production approval. Report: `reports/warder-master-production/phase4-v10-experiment-20260925/ADJACENCY-GUARD-V2-REGRESSION.md`.
- Case #15551 WHITE output manually approved by Štefan on 2026-09-25: use the V10 test candidate with black text and the red “+”. Exact duplicate #4860 has the same source SHA256, current output SHA256, and candidate PNG SHA256; the identical approved PNG bytes were reused at `picons/16.0e/total-tv/white/1_0_1_557_75FB_16E_A00000_0_0_0.png`. Approval and both per-case audit rows are in `reports/warder-master-production/phase4-v10-experiment-20260925/CASE-15551-MANUAL-APPROVAL.md` and `.csv`; candidate SHA256 `d4db70d1df947b5f76c56cf1c66b70e2b941ca8b390c1f38a19002a4c92844d8`. The V6 classifier still marks both samples REVIEW due to two-tone components. This is manual approval of these two byte-identical outputs, not algorithm or production rebuild approval.
- Expanded v4 WHITE/BLACK scratch regression (2026-09-25): #14716, #3163, #3133, #3172, #3174, #12062 remained REVIEW and the PASS control remained PASS. Six of seven composites matched current outputs; #12062 differed in 93 displayed pixels (115 source achromatic pixels recolored). Alpha and protected chromatic pixels remained unchanged. No AUTO-FIXED case was demonstrated. Fixture-limited evidence only, not production approval. Report: `reports/warder-master-production/phase4-v10-experiment-20260925/ADJACENCY-GUARD-V4-BW-REGRESSION.md`.
- Expanded v7 P1 WHITE scratch regression (2026-09-25): five additional cases (#628, #7352, #220, #858, #13193) remained REVIEW; alpha and protected chromatic pixels were unchanged, and the PASS control stayed unchanged. Existing fixture outputs/statuses remained stable. This is fixture-limited safety evidence only, not production approval. Report and audit: `reports/warder-master-production/phase4-v10-experiment-20260925/ADJACENCY-GUARD-V7-P1-REGRESSION.md` and `.../ADJACENCY-GUARD-V7-P1-REGRESSION-AUDIT.csv`.
- P1 mixed-logo screen (2026-09-25): the contact-fraction test covered 24 additional fixtures; all remained REVIEW, preservation checks passed, and the PASS control stayed unchanged. After seeing the focused images, Štefan clarified that “stredne” approved both #10085 and #6019. Their exact V10 candidates are manually approved and applied on this isolated test branch; their automatic status remains REVIEW. #6216: Štefan selected the right-hand V10 WHITE candidate and it is manually approved and applied on this test branch (candidate SHA256 `1428dd0e3da0f968837a30cc05876b11d84c1d24d4feffe5b3b4eb16ff82766c`). #14408: Štefan selected the middle-column CURRENT WHITE output; it remains unchanged. Both automatic classifications remain REVIEW. The case-level decisions and comparison evidence are recorded at `reports/warder-master-production/phase4-v10-experiment-20260925/CASE-6216-14408-MANUAL-VISUAL-DECISIONS.md` and `.csv`. This approves only the exact #6216 image, not V10 generally or a production rebuild. Case-level approval record, audit, and both comparison images: `reports/warder-master-production/phase4-v10-experiment-20260925/CASE-10085-6019-MANUAL-APPROVAL.md`, `.csv`, `CASE-10085-MANUAL-APPROVAL.jpg`, and `CASE-6019-MANUAL-APPROVAL.jpg`. This does not approve the algorithm or a production rebuild. Original screen report and audit: `reports/warder-master-production/phase4-v10-experiment-20260925/ADJACENCY-GUARD-P1-24-CASE-SCREEN.md` and `.../ADJACENCY-GUARD-P1-24-CASE-SCREEN-AUDIT.csv`.
- P1 manual visual selections (2026-09-25): Štefan selected the right-hand V10 WHITE candidates for #6099 and #7191; both exact PNGs are manually approved and applied only on `phase4-v10-component-mask-test`. Candidate SHA256 values are #6099 `37ba4c88b4bdb7115bac11e4744df4a5c4beb101126eb3a2368b9b749cb8761b` and #7191 `1420bd9a0c62ae6f087c6024f4cc9ad2a8e77216cff1879be99dc3c4740f2359`. Both automatic statuses remain REVIEW. Their case audit, decision record, and focused comparisons are `reports/warder-master-production/phase4-v10-experiment-20260925/CASE-6099-7191-MANUAL-APPROVAL.md`, `.csv`, `CASE-6099-MANUAL-APPROVAL.jpg`, and `CASE-7191-MANUAL-APPROVAL.jpg`. No algorithm or production rebuild is approved.
- P1 manual visual decision (2026-09-25): #13015 was corrected from its own original transparent source using the frozen V9 fit/render and white MASTER, then manually corrected per Štefan's direction: the second glyph's white dot and stem are black where it meets the globe. Štefan approved the right-hand corrected candidate on 2026-09-25; exact WHITE SHA256 `38a7c762af0645529fbf9e61c5cfff3648950e28d8431ad03958aa792baf0f27`. The orange globe pixels and source alpha are unchanged. Automatic status remains REVIEW; approval applies to this case only. #1856: Štefan selected the middle/current WHITE output; it remains unchanged. Decision audit and focused comparisons: `reports/warder-master-production/phase4-v10-experiment-20260925/CASE-13015-1856-MANUAL-DECISIONS.md`, `.csv`, `CASE-13015-MANUAL-CORRECTION.jpg`, and `CASE-1856-CURRENT-RETAINED.jpg`. This is a case-level approval, not V10 or production approval.
- P1 manual visual decisions (2026-09-25, corrected after user rejection): #10943's earlier candidate `b9a2e1468c5ed7a235ea784c03ed343507f6056d77e5c364fe4731a7bcf11fed` was rejected because it colored the silver `O` bezel where `W` letters should be black. The next candidate was visually checked and an isolated black speck at the `O`/`W` junction was removed by restoring 9 source pixels to their original bezel colors. Current WHITE candidate was rebuilt from the untouched original transparent source: upper `S`, `H`, and `W` are black; the red button and complete silver bezel are preserved; lower `RADYO` remains the frozen V9-rendered black baseline. Štefan approved this exact WHITE candidate on 2026-09-25 (SHA256 `1f410dc5330e8fdfa043a1af341ae2019f34639af84b44ece540e4cde32d6392`). Its automatic status remains REVIEW; this is a case-level approval only. #4926: the last `L` in lower `CHANNEL` remains approved exactly as recorded (WHITE SHA256 `36a2e9553aaffa9e27b10b20d49691b993733808073c612921ea45b04dfc9b62`). Both automatic statuses remain REVIEW. Case audit and focused comparison: `reports/warder-master-production/phase4-v10-experiment-20260925/CASE-10943-4926-MANUAL-DECISIONS.md`, `.csv`, `CASE-10943-MANUAL-CORRECTION.jpg`, and `CASE-4926-MANUAL-CORRECTION.jpg`. No algorithm or production rebuild is approved.
- Next gate: continue isolated V10 regression work on the test branch; ambiguous or unsafe samples remain REVIEW. The failed component-mask prototype is not approved, and full-catalog rebuild still requires successful isolated regression evidence and an explicitly approved production path.
- Do not repeat the visual review or regeneration of Batches 1–13. Continue the Phase 4 V10 workflow on the isolated test branch using the approved records and existing V10 test specification.

Approval audit path: `reports/warder-master-production/phase4-v10-approved-batch13/APPROVAL-AUDIT.csv`.

---

## Current project state

PiconHub Warder Evolution is **ACTIVE / IN DEVELOPMENT**. Current `main` contains the reorganized runtime picon catalog, completed guarded Vhannibal transparent import, authoritative BLACK/WHITE master templates, migration tooling, and the master quality plan.

## LOCKED — approved graphics and structure

Existing approved PiconHub graphics, UI layout, element dimensions, coordinates/positions, panel composition, provider artwork, MASTER templates and established repository/runtime structure are **LOCKED**. ChatGPT, Work, automation or a future recovery session must NOT independently redesign, redraw, regenerate, resize, reposition, reorganize, rename, replace or otherwise "improve" them.

New work must adapt to the already approved graphics and structure — the approved graphics/structure must not be changed merely to accommodate new work. Any intentional change to approved graphics, layout, dimensions, coordinates, provider artwork or structural organization requires **Štefan's explicit approval first**. No inferred permission and no silent optimization.

This LOCK does not prevent the separately planned QC of transparent picons or the approved future BLACK/WHITE production process; those operations must follow the exact QC/master rules documented below and in `docs/PICON-MASTER-QUALITY-PLAN.md` and must not be used as permission to redesign the PiconHub UI or repository architecture.

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

QC categories: PASS / AUTO-FIXED / REVIEW / ERROR-SKIP.

## V8 / V9 checkpoint — 2026-09-15

The component-mask visual development reached **V8**. The approved preview is `UKAZKA_LOG_V8_COMPONENT_MASK.png`; Štefan explicitly approved V8 with **„toto je už OK“**. V8 is therefore the current approved algorithm/rule baseline and must NOT be silently retuned while preparing the representative test set.

Binding detailed rules are in `docs/PICON-MASTER-QUALITY-PLAN.md`; the rules checkpoint used for this phase is commit `c93714ad1c1ed570a4e95b770d4425664a0cdf1d`.

The immediate next task is **V9 — representative QC/sample test of the approved V8 logic on multiple real transparent picons from the repository**. V9 should present reviewable samples as `TRANSPARENT → BLACK → WHITE` and cover the representative visual categories required by the MASTER Quality Plan. Any case that cannot be safely separated/edited by the approved component-mask rules must be marked `REVIEW`, never guessed.

Work started on V9 on 2026-09-15. The repository tree at the rules checkpoint was inspected and real transparent picons were located, including `picons/0.8w/digi-hu/transparent/`. The immutable MASTER templates were also re-confirmed in the checkpoint. No MASTER template, V8 rule, runtime picon or repository architecture was modified during this inspection.

For local pixel-level V9 processing, Štefan downloaded and uploaded the current repository ZIP to the ChatGPT conversation as `PiconHub-Warder-Evolution-main.zip`. The processing runtime then repeatedly failed with an internal `TransportTimeoutError` before the ZIP could be unpacked/analyzed. This is the current pause point; it is **not** a failure of the repository ZIP and does not authorize changing the method or rules.

### Exact resume point after the pause

1. Use the already supplied `PiconHub-Warder-Evolution-main.zip` if it remains available; otherwise obtain the current repository ZIP again.
2. Unpack/read it locally without modifying source PNGs or MASTER templates.
3. Select a representative set of real `transparent` picons covering the MASTER-plan categories.
4. Run the frozen V8 logic against BLACK and WHITE MASTERs and prepare the V9 visual review sheet `TRANSPARENT → BLACK → WHITE`.
5. Classify ambiguous/unsafe component masks as `REVIEW`; do not guess or alter V8 to make a sample pass.
6. Štefan visually approves/rejects V9 samples. Only after representative approval freeze the Warder Evolution MASTER standard.
7. Then hand the large complete-catalog BLACK/WHITE rebuild to Work on a controlled working branch with QC/audit/report and approval before merge to `main`.

## Before full batch — mandatory sample approval

Do not launch the whole catalog immediately. First prepare a representative test set containing at least light/white logo, dark/black logo, colored/multicolored logo, text wordmark, separated text/graphics, text in colored badge/box, adjacent components with antialias boundary, fine/small text, sharp and soft source, low contrast on WHITE and BLACK, wide and tall logo.

Štefan + ChatGPT define and visually approve the rules/samples first. Only after approval are those rules frozen for the full production run.

## Division of work for full production

Chat/Štefan + ChatGPT define visual/QC rules, approve representative samples, decide ambiguous aesthetic cases and review final results. Work executes the large multi-stage operation over thousands of files using only frozen approved rules, validates outputs and creates the audit/report and controlled branch/PR. Work must NOT invent aesthetic rules and must NOT auto-approve REVIEW cases.

## Git safety for the full catalog phase

Do not perform the mass rewrite uncontrolled directly on `main`. Required approach: working branch → QC + generation → audit/report → verify counts/architecture → review samples and REVIEW cases → merge to `main` only after successful validation/approval. Transparent sources must not disappear.

## Future module — Orbit Watch / Satellite Change Monitor

After catalog normalization and the Warder Evolution quality standard are completed and approved, build the already planned regular automatic satellite-change monitoring system. Detection/preparation may be automatic but production `main` remains approval-gated. Orbit Watch must obey the locked architecture, MASTERs and QC rules and must not silently redesign or rewrite approved graphics. Private maintainer e-mail notifications are intended for actionable changes or monitoring failures; secrets/recipient configuration must never be committed publicly.

## Chocholousek migration state

Chocholousek migration tooling/plans exist under `migration/chocholousek`, and backup material exists in private Trezor under `ChocholousekPicons/`. Keep migration/archive mechanics separate from runtime `picons/` and separate from Vhannibal unless an explicit future step connects them.

## UI project state

PiconHub UI is also still in development. The main design checkpoint is 1672×941. The `VYBERTE PROVIDERA` section has exactly 6 panels. Approved provider artwork exists for Skylink, Magio Sat, ANTIK Sat, freeSAT and Telly; their established order/coordinates must be preserved when continuing UI work. Do not redesign or reposition approved provider assets without explicit approval.

## Recovery rule

If chat/context is lost: read this file and `docs/PICON-MASTER-QUALITY-PLAN.md` first, inspect current `main`, and continue from these checkpoints. Never infer architecture from obsolete history. Preserve all LOCKED graphics/layout/structure unless Štefan explicitly approves a change. The final MASTER templates are accepted exactly as stored. **Immediate resume task: V9 representative test from the uploaded/current repository ZIP using frozen V8, then Štefan approval; only afterward hand the complete-catalog rebuild to Work.** Orbit Watch remains the planned subsequent maintenance phase.