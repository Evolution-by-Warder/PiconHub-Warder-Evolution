# V10 manual corrections — cases #10943 and #4926

Date: 2026-09-25  
Branch: `phase4-v10-component-mask-test`

Štefan requested these exact case-level edits to the WHITE outputs:

| Case | Manual edit | Previous/current WHITE SHA256 | Result WHITE SHA256 | User acceptance | Automatic status |
|---|---|---|---|---|---|
| #10943 | Upper `SHOW` letters black; correct the achromatic white edge of the red `O` at its contact with `W`; leave the central red button untouched | `f4f65320d9a13f5f88b5378b28d942d11cbcb4f63d30a8ae8ca11dbc641ebd73` | `fccb5b8f137d2b38b66836c624d1f128572ac79ebe4af51be4e2fdf562ac90d5` | Correction requested; no separate acceptance recorded | REVIEW |
| #4926 | Recolor only the final `L` of lower `CHANNEL` text to black | `b50a7a289c07ed47feb14c8866a6734151bf0b34ad6b66e14667e2ed1beedfed` | `36a2e9553aaffa9e27b10b20d49691b993733808073c612921ea45b04dfc9b62` | Štefan accepted this exact output on 2026-09-25 | REVIEW |

Both edits were regenerated from each case's own original transparent source using the frozen V9 fit/render and exact WHITE MASTER; the reconstructed baseline matched the previous/current output. For #10943, 5,063 achromatic source pixels were recolored, including the upper `SHOW` and the small white edge at the red `O`/`W` contact; 4,938 output pixels differ from the prior/current output. The central red button and source chromatic pixels were preserved, and source alpha is unchanged. For #4926, 302 source pixels in the last `L` only were recolored (278 output pixels differ); source alpha and chromatic pixels were preserved. #7564 shares #4926's transparent-source SHA256 but was not changed by this decision.

Focused comparisons: `CASE-10943-MANUAL-CORRECTION.jpg` shows current, first correction, and the updated edge correction. `CASE-4926-MANUAL-CORRECTION.jpg` shows current beside the corrected and accepted result. These manual edits do not change automatic status, approve the algorithm, or authorize a production rebuild.
