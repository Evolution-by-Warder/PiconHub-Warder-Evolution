# V10 manual corrections — cases #10943 and #4926

Date: 2026-09-25  
Branch: `phase4-v10-component-mask-test`

Štefan requested these exact case-level edits to the WHITE outputs:

| Case | Manual edit | Previous/current WHITE SHA256 | Result WHITE SHA256 | Automatic status |
|---|---|---|---|---|
| #10943 | Upper `SHOW` letters black; leave central red `O`/button untouched | `f4f65320d9a13f5f88b5378b28d942d11cbcb4f63d30a8ae8ca11dbc641ebd73` | `14ed7e6cc8b66bc09f66def59f0564cc16a8eba99c8af3fd7ac98e647ee9de30` | REVIEW |
| #4926 | Recolor only the final `L` of lower `CHANNEL` text to black | `b50a7a289c07ed47feb14c8866a6734151bf0b34ad6b66e14667e2ed1beedfed` | `36a2e9553aaffa9e27b10b20d49691b993733808073c612921ea45b04dfc9b62` | REVIEW |

Both edits were regenerated from each case's own original transparent source using the frozen V9 fit/render and exact WHITE MASTER; the reconstructed baseline matched the previous/current output. #10943 recolored 4,929 achromatic source pixels in `SHOW` (4,804 output pixels differ from the prior output); the central red `O`/button and all source chromatic pixels were preserved. #4926 recolored 302 source pixels in the last `L` only (278 output pixels differ); source alpha and chromatic pixels were preserved. #7564 shares #4926's transparent-source SHA256 but was not changed by this decision.

Focused comparisons: `CASE-10943-MANUAL-CORRECTION.jpg` and `CASE-4926-MANUAL-CORRECTION.jpg` show the current output beside the corrected result. These manual edits do not change automatic status, approve the algorithm, or authorize a production rebuild.
