# V10 manual corrections — cases #10943 and #4926

Date: 2026-09-25  
Branch: `phase4-v10-component-mask-test`

Štefan requested these exact case-level edits to the WHITE outputs:

| Case | Manual edit | Previous/current WHITE SHA256 | Result WHITE SHA256 | User acceptance | Automatic status |
|---|---|---|---|---|---|
| #10943 | Upper `SHOW` letters black; correct the near-white left stroke of `W` at its contact with the circle; preserve the red `O` outline and central button | `f4f65320d9a13f5f88b5378b28d942d11cbcb4f63d30a8ae8ca11dbc641ebd73` | `b9a2e1468c5ed7a235ea784c03ed343507f6056d77e5c364fe4731a7bcf11fed` | Correction requested; no separate acceptance recorded | REVIEW |
| #4926 | Recolor only the final `L` of lower `CHANNEL` text to black | `b50a7a289c07ed47feb14c8866a6734151bf0b34ad6b66e14667e2ed1beedfed` | `36a2e9553aaffa9e27b10b20d49691b993733808073c612921ea45b04dfc9b62` | Štefan accepted this exact output on 2026-09-25 | REVIEW |

Both edits were regenerated from each case's own original transparent source using the frozen V9 fit/render and exact WHITE MASTER; the reconstructed baseline matched the previous/current output. For #10943, 4,957 achromatic source pixels were recolored, including 4,929 from the requested `SHOW` treatment and 28 near-white pixels on the `W` stroke at the circle contact (4,832 output pixels differ from the prior/current output). The red `O` outline and central red button are preserved; source alpha and chromatic source pixels are unchanged. For #4926, 302 source pixels in the last `L` only were recolored (278 output pixels differ); source alpha and chromatic pixels were preserved. #7564 shares #4926's transparent-source SHA256 but was not changed by this decision.

Focused comparisons: `CASE-10943-MANUAL-CORRECTION.jpg` shows current, the initial `SHOW` correction with the original circle outline, and the W-stroke correction. `CASE-4926-MANUAL-CORRECTION.jpg` shows current beside the corrected and accepted result. These manual edits do not change automatic status, approve the algorithm, or authorize a production rebuild.
