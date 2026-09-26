# Original V10 mixed-logo failures — color-class topology regression

Date: 2026-09-26  
Branch: `phase4-v10-component-mask-test`  
Branch HEAD checked before work: `b8b708ffb1af68065f08e708f18a610e22e5a89b`

## Scope

Tested only the original review-index cases #14607, #14611, #14700, #14593, and cautious probe #14597, plus the Digi Slovakia PASS control. Review-index paths came from `reports/warder-master-production/phase3-clean-rebuild/contact-sheets/all-review-index.csv.gz`. The already closed #14599 МИР was not opened or modified.

The user-requested comparison format is in `COMPARISON-SHEET.jpg` and the per-case files. Because no safe repair was accepted, each CANDIDATE panel is the byte-identical CURRENT WHITE fallback.

## Frozen method and safety checks

The experiment uses V9 constants: alpha 32, achromatic RGB delta 18, achromatic fraction 98.5%, contrast ratio 2.50, material fraction 8%, and two-tone fraction 3%. The target dark value is `(16,16,16)`. Solid achromatic cores use 4-connectivity; solid chromatic cores use 8-connectivity. The chromatic core and its visible 8-neighbor AA/boundary ring are protected. Low-alpha pixels are ambiguous and never editable. A separate core is eligible only when it is exterior-connected through ambiguous low-alpha/transparent topology, so text enclosed by a filled badge is not treated as text on the MASTER.

No rectangular or positional masks are used. A case is rejected as a whole if only a fragment of its contrast-relevant wordmark can be separated. The exact frozen WHITE MASTER hash was verified as `c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589`. Every candidate layer passed source-alpha-after-fit equality, protected chromatic equality, and protected AA/boundary equality. All edit-mask/protected intersections are zero.

## Results

| Case | Source / duplicate | Achromatic cores | Locally separable before case gate | Rejected/ambiguous | Changed core pixels | Candidate vs CURRENT pixels | Result |
|---|---|---:|---:|---:|---:|---:|---|
| #14607 ПРОДВИЖЕНИЕ | SHA256 `edec07adb8a121d7c856271543549717aff4d253f0302fd2d83a909481b2d24c` | 58 | 0 | 58 hit protected boundary | 0 | 0 | REVIEW |
| #14611 ПРОДВИЖЕНИЕ | byte-identical source and CURRENT WHITE to #14607; candidate reused, not recomputed | 58 | 0 | 58 hit protected boundary | 0 | 0 | REVIEW |
| #14700 УДМУРТИЯ | unique source | 19 | 0 | 9 hit protected boundary; 10 were two-tone | 0 | 0 | REVIEW |
| #14593 STAR CINEMA | unique source | 14 | 1 | 9 hit protected boundary; 4 were two-tone | 0 | 0 | REVIEW |
| #14597 РУССКИЙ БЕСТСЕЛЛЕР | cautious gold/brand probe | 224 | 0 | 224 hit protected boundary | 0 | 0 | REVIEW |
| Digi Slovakia PASS | required control | 0 | 0 | 0 | 0 | 0 | PASS |

For #14593, one 54-pixel core was locally separable, but 13 other contrast-relevant cores were not. The case-level completeness guard rejected the partial mask, so no part of the wordmark was recolored. For #14597, no gold/brand pixels or boundary pixels changed.

The #14607/#14611 pair was confirmed byte-identical: source SHA256 `edec07…b2d24c`, CURRENT WHITE SHA256 `06f73c…928089`, and candidate SHA256 `06f73c…928089`. #14611 is only a duplicate regression check.

The PASS control stayed byte-identical to CURRENT WHITE. It had 0 changed pixels, as required.

## Conclusion

The conservative color-class topology guard did not produce a safe, complete repair for these original failures. The protected-boundary and two-tone checks rejected the relevant cores; #14593's only locally separable fragment was rejected because the rest of the wordmark could not be separated. All cases remain `REVIEW`, except the unchanged PASS control. The comparison images show the unmodified CURRENT WHITE fallback as the candidate. No production picons, transparent sources, MASTERs, plugin, skin, Phase 3 checkpoint, or `main` were changed. No rebuild or production application is authorized by this test.

## Artifacts

- `tools/phase4_original_failures_color_topology.py` — reproducible isolated runner; refuses output inside `picons/`.
- `AUDIT.csv` and `SUMMARY.json` — source/current/candidate hashes, duplicate mapping, component decisions, pixel counts, and invariants.
- `COMPARISON-SHEET.jpg` — SOURCE | CURRENT WHITE | CANDIDATE for all requested cases, duplicate pair grouped once.
- `CASE-14607-COMPARISON.jpg`, `CASE-14700-COMPARISON.jpg`, `CASE-14593-COMPARISON.jpg`, `CASE-14597-COMPARISON.jpg`, `CASE-pass-COMPARISON.jpg` — focused comparisons.
