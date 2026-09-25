# V10 manual corrections — cases #10943 and #4926

Date: 2026-09-25  
Branch: `phase4-v10-component-mask-test`

Štefan requested these exact case-level edits to the WHITE outputs:

| Case | Manual edit | Previous/current WHITE SHA256 | Result WHITE SHA256 | User acceptance | Automatic status |
|---|---|---|---|---|---|
| #10943 | Rebuild from original transparent source; upper `S`, `H`, and `W` black; preserve the red `O` button and complete silver bezel | `b9a2e1468c5ed7a235ea784c03ed343507f6056d77e5c364fe4731a7bcf11fed` | `1f410dc5330e8fdfa043a1af341ae2019f34639af84b44ece540e4cde32d6392` | Correction requested; awaiting visual review | REVIEW |
| #4926 | Recolor only the final `L` of lower `CHANNEL` text to black | `b50a7a289c07ed47feb14c8866a6734151bf0b34ad6b66e14667e2ed1beedfed` | `36a2e9553aaffa9e27b10b20d49691b993733808073c612921ea45b04dfc9b62` | Štefan accepted this exact output on 2026-09-25 | REVIEW |

Both edits were regenerated from each case's own original transparent source using the frozen V9 fit/render and exact WHITE MASTER; the reconstructed baseline matched the previous/current output. For #10943, the rejected candidate was replaced by a fresh render from the original transparent source and immutable WHITE MASTER. Only upper `S`, `H`, and `W` lettering is manually recolored; the red button, full silver `O` bezel, source alpha, and source file remain unchanged. The final manual source mask covers 6,264 pixels; the corrected composite differs from the rejected candidate in 1,128 output pixels. A later visual check found and removed one isolated black speck by restoring 9 source pixels at the `O`/`W` boundary; this follow-up changed 29 output pixels from the prior candidate. The lower `RADYO` output is unchanged. For #4926, 302 source pixels in the last `L` only were recolored (278 output pixels differ); source alpha and chromatic pixels were preserved. #7564 shares #4926's transparent-source SHA256 but was not changed by this decision.

Focused comparison: `CASE-10943-MANUAL-CORRECTION.jpg` shows the rejected current image beside the fresh-source candidate, with the `O` bezel preserved. `CASE-4926-MANUAL-CORRECTION.jpg` shows current beside the corrected and accepted result. These manual edits do not change automatic status, approve the algorithm, or authorize a production rebuild.
