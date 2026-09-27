# V25 — Manual approval and controlled #14700 WHITE apply

**Status:** V24 right-hand candidate manually approved by the user on 2026-09-27.  
**Selection:** “pravy je dobry” — dark УДМУРТИЯ wordmark is correct and legible on WHITE MASTER; the red symbol remains preserved.

## Exact approved artifact

- Candidate path: `reports/warder-master-production/phase4-v24-single-rule-replay-20260927/14700-V24-DIAGNOSTIC-WHITE-CANDIDATE.png`
- Candidate SHA256: `fbc6fd6a6532d2f13fa3d1a1f39ea400f7ec260838c4070acacdab04194d9164`
- Comparison path: `reports/warder-master-production/phase4-v24-single-rule-replay-20260927/14700-SOURCE-CURRENT-V24-CANDIDATE.png`
- The comparison's right-hand 220×132 panel was pixel-compared with the candidate RGB and matches exactly.
- Existing Phase3/V24 audit specifies WHITE output path: `picons/80.0e/orion-express/white/1_0_1_32D_CE_1_3200000_0_0_0.png`.

## Pre-apply checks

| Check | Result |
|---|---|
| Current WHITE SHA256 | `e2b1eaf5cdad1acf3b251c7d5173a7bf0066ca3ea1a6eff9a60bd8aa02c76916` |
| V24 approved candidate SHA256 | `fbc6fd6a6532d2f13fa3d1a1f39ea400f7ec260838c4070acacdab04194d9164` |
| Transparent source SHA256 | `9fa6f6a84bb9e1a98802e638f94d0f693757697648d1167d1b9f3f31fb7724c3` |
| WHITE master/template SHA256 | `c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589` |
| Target components | V9 visible components 4, 12, 13 |
| Target RGB | `(16,16,16)` |
| RGB changes outside components 4/12/13 | 0 |
| Chromatic component 1 changed pixels | 0 |
| Source-layer alpha | Bit-identical per V24 audit |
| Candidate output alpha vs CURRENT WHITE | Bit-identical |
| Candidate regenerated | No |

The approved PNG is the final WHITE MASTER-composited picon. Its output alpha follows the rendered master and is not expected to equal the transparent source alpha. The V24 invariant is that the fitted logo layer's alpha remains bit-identical while only selected RGB is recolored; V24 records `source_layer_alpha_equal=true`. The rendered candidate's alpha matches CURRENT WHITE pixel-for-pixel.

## Approval ledger

Appended one row to the existing `reports/warder-master-production/phase4-v10-approved-batch13/APPROVAL-AUDIT.csv` using its existing columns. The accompanying report preserves the approval date and user note.

## Apply and post-apply verification

The WHITE output at the exact path above is replaced byte-for-byte with the already approved V24 PNG. No candidate was regenerated. The V24 artifact itself remains unchanged.

V25 apply commit: `1b9a2a9bc599849500eade7a440c07f47afa4948`. Applied WHITE SHA256 is exactly the approved candidate SHA256: `fbc6fd6a6532d2f13fa3d1a1f39ea400f7ec260838c4070acacdab04194d9164`; the prior WHITE SHA256 was `e2b1eaf5cdad1acf3b251c7d5173a7bf0066ca3ea1a6eff9a60bd8aa02c76916`. The commit audit verifies exactly one changed picon path. BLACK, transparent source, WHITE MASTER/template, all other picons, and all regression-control outputs remain unchanged. A post-apply narrow replay confirmed #14700 BLACK unchanged, both genuine two-tone controls `two-tone=true` with 0 editable pixels, and replay-identical controls. The narrow replay results: both genuine-two-tone controls stay protected; #14607/#14611 remain REVIEW; #14593 remains REVIEW; #14597 remains cautious REVIEW; Digi Slovakia remains PASS/0 changes. #14599 was not accessed.

This approval is specific to #14700 WHITE. It does not authorize generator changes, global topology-aware rollout, other picon edits, full rebuild, or main-branch integration.
