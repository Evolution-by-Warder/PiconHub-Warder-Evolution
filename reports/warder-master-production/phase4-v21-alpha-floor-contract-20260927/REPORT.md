# V21 — Frozen alpha-floor semantics / edit-mask contract audit

**Audited branch HEAD:** `37d466f398b1fc1f518c68e50072fbdc9e36817f`  
**Phase 3 code checkpoint:** `e9b503d76eae3c3c7d7763df4909039a55d3edb8`  
**Outcome: A — frozen V9 whole-component edits include subthreshold visible pixels, with an important qualification.**

The Phase 3 generator uses `OPAQUE_ALPHA=32` to select pixels used for component classification and material/contrast statistics. It does **not** use `alpha >= 32` as the edit-mask boundary. Components are formed from every fitted pixel with `alpha > 0`; when a safe achromatic component needs contrast correction, RGB is changed on the entire component. Thus alpha 1–31 members of an accepted component are recolored with it. If classification protects a component, its visible 1–31 members are included in that protected component too.

The qualification: V9 contains **no separate per-pixel low-alpha ownership classifier** and does not demand raw-RGB, one-hop, or AA-continuity proof for each alpha 1–31 pixel. Its operational assignment is the full alpha-connected component. The later #14700 gate added a stronger proof requirement.

## Direct answers

1. **Original technical meaning of `OPAQUE_ALPHA=32`:** sample floor for the `solid`/material set. If a component has pixels at alpha ≥32, only those feed achromatic, two-tone, and contrast fractions. If it has none, code falls back to the whole component. The name is not an edit-alpha cutoff. Docs do not explain why 32 was selected.
2. **Alpha 1–31:** visible (`alpha > 0`) and part of the 8-connected component. Omitted from classification samples only when the component has at least one alpha ≥32 pixel. Not globally excluded from the edit mask and not globally unowned. A corrected component recolors them; a protected component leaves them untouched.
3. **V9 requirement:** safe separation of the complete component being edited. The executable component covers all visible pixels, including alpha 1–31 antialias. There is no separate per-pixel low-alpha proof.
4–5. **Was #14700’s separate ownership proof frozen V9?** No. Explicit gate marking touching alpha<32 perimeter pixels REVIEW first appears in `6b336f74a6d717a39ac04084b2f4399f92842ccb` (isolated #14700 final-gate commit). The one-hop ownership diagnostic follows in `34dbb53a8291419c1061f602710dc36d263cef19`. Both are later safeguards.
6–7. **Is #14700 M0 complete under V9 mask semantics?** No, not as the same full visible connected component: the prior audit identified 300 visible alpha<32 pixels directly on the proposed wordmark perimeter. In Phase 3 code, directly connected visible pixels are part of the component and included if it is accepted for recolor. No V9 branch excludes alpha<32 from edits. This observation does **not** approve #14700 or establish that its full V9 component is a safe logical wordmark.

## Three distinct pixel classes

- **Visible pixel:** after `fit_logo`, alpha > 0. Participates in connected-component labeling.
- **Material/classification pixel:** normally alpha ≥32 within the component. If none exist, fallback sample is the full component.
- **Protected/uneditable pixel:** V9 protection is assigned to an unsafe component (`protected |= component`), not all low-alpha pixels globally. In the safe contrast-correction branch, those same alpha 1–31 pixels are part of the RGB edit mask.

The plan’s phrase “protected colored component … including edges and antialias pixels” refers to preserving a **protected colored brand component** (including chromatic/transition AA) against edits. It does not declare every achromatic alpha<32 edge protected or require a separate ownership classifier for it.

## First appearance of the later gate

Commit `6b336f74a6d717a39ac04084b2f4399f92842ccb` (“Add isolated #14700 final candidate gate”) builds a ring around the grouped mask, selects visible pixels with alpha <32, and turns any contact into `low_alpha_perimeter_ownership: REVIEW` and `edit_mask_complete: REVIEW`. Its result was recorded in `e57b44a4aaf3baf92bfb470eec28e82edc2df6b2`. Commit `34dbb53a8291419c1061f602710dc36d263cef19` then added the one-hop attribution experiment (40 safe, 259 ambiguous, 1 protected/other).

This is the first explicit **proof-of-ownership** gate found in the audited #14700 lineage. V9 already included alpha 1–31 in the complete visible-component mask; it did not individually prove their ownership.

## #14700 assessment, performed last

Prior Phase 4 evidence records M0 = 1,224 pixels (1,070 solid/core + 154 preconfirmed tonal attachments) and 300 directly adjacent visible alpha<32 perimeter pixels. M0 is not the same as the full V9 visible-component edit mask: leaving those 300 outside differs from V9’s whole-component assignment. V9 did not require the later raw-RGB or one-hop evidence for them; V9 assigned visible alpha-connected members together. This audit does not rerun generation, certify the full #14700 component as a safe wordmark, or authorize any edit. Keep #14700 at REVIEW.

No generator, template, source, MASTER, or production picon was modified. No candidate was created. #14599 was not accessed.
