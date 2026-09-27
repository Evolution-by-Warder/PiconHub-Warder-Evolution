# V21 — Alpha-floor and edit-mask contract

## Finding

At the executable level, `OPAQUE_ALPHA=32` is a **classification/material sampling floor**, not an edit-mask cutoff. The written documents do not explain why 32 was chosen or define a separate alpha<32 ownership class. The component-mask rule requires safe separation of the complete logical component; Phase 3 operationalizes it as all 8-connected fitted pixels with alpha > 0.

**Outcome A, qualified:** if an accepted component needs recoloring, its visible alpha 1–31 members are included and recolored with it. If unsafe, those same members are protected with the component. There is no separate per-pixel low-alpha proof in V9.

## Terms

| Term | Frozen V9 meaning |
|---|---|
| Visible pixel | Fitted image alpha > 0; used for labels. |
| Material/core sample | Per component alpha ≥32; if none, fallback to the whole component. Used for color/tone/contrast statistics. |
| Edit mask | Full `component` label when safe achromatic contrast correction is required. RGB changes, alpha does not. |
| Protected/uneditable | Full visible component in unsafe branch; not a global alpha<32 mask. |

## Code-path trace

Source: `tools/rebuild_master_catalog.py` at Phase 3 commit `e9b503d76eae3c3c7d7763df4909039a55d3edb8`.

| Stage | Code operation | Alpha 1–31 |
|---|---|---|
| Fit | A-channel bbox; crop; optional LANCZOS resize; RGBA canvas | Downstream alpha is fitted/resampled, not necessarily source-byte-identical. |
| Visible | `visible = alpha > 0` | Included. |
| Components | 8-connected `ndimage.label(visible,...)` | Included in connected component. |
| Material | `solid = component & (alpha >= 32)`; if empty, `solid = component` | Omitted from stats if any ≥32; included by fallback if none. |
| Classification | Achromatic, two-tone and contrast stats consume `solid` | No independent low-alpha ownership test. |
| Protected | Unsafe branch: `protected |= component` | Whole visible component, including 1–31, remains untouched. |
| Edit | Safe + contrast-needed: `work[..., :3][component] = target` | Whole component RGB is assigned, including 1–31; no alpha write. |
| Render | `Image.alpha_composite(master, logo)` | Existing fitted alpha determines rendered contribution. |

The `solid` sample mask and `component` edit/protection mask are different.

## Documents and commits

- Quality plan at Phase 3 (lines 61–63, 76–80) says a complete logical component must be safely separated; overlap with a protected colored component including its edges/AA means REVIEW. It has no `OPAQUE_ALPHA`, `alpha<32`, or low-alpha ownership clause.
- `5de71aaf9a7b3f9ce2f66a6663aec328006922be`: text-aware whole-wordmark adaptation.
- `ecc876abaec441430413766582e0541a09cb81b8`: text in a colored badge/background remains part of the protected colored element with AA/transition pixels.
- `c93714ad1c1ed570a4e95b770d4425664a0cdf1d`: exact component masks; overlap with protected colored component is REVIEW.
- Phase 3 `summary.json` records `opaque_alpha: 32` as a value only.

These define complete-component separation and protected colored-component integrity; none treats alpha<32 achromatic AA as globally excluded or requires separate per-pixel ownership evidence.

## Later #14700 low-alpha gate

The first explicit gate is commit `6b336f74a6d717a39ac04084b2f4399f92842ccb`, `tools/phase4_14700_final_candidate_gate.py`. It selects visible alpha<32 pixels in the proposed group’s neighboring perimeter and makes any contact REVIEW; it also marks edit-mask completeness REVIEW. Commit `e57b44a4aaf3baf92bfb470eec28e82edc2df6b2` records the result. Commit `34dbb53a8291419c1061f602710dc36d263cef19` adds the separate one-hop attribution diagnostic.

This Phase 4 proof-of-ownership gate is stricter than V9 component assignment. It is not an original V9 alpha-floor rule.

## #14700, evaluated last

Prior evidence: M0 is 1,224 px (1,070 core + 154 preconfirmed tonal attachments); 300 visible alpha<32 pixels directly contact its perimeter. Those 300 would be included in the same alpha-connected component under V9’s visible mask if directly 8-connected to the group. If accepted, the old edit operation would recolor them too.

M0 is not identical to the full V9 visible-component edit mask. The historical generator did not demand raw-RGB or one-hop ownership proof for the 300; it assigned connected visible members together. This is not a finding that the entire #14700 component is safe. No generation was rerun and production status remains REVIEW.

## Answers

1. 32 is the normal material/classification sample floor.
2. Alpha 1–31 are visible; not globally excluded/protected. They join whole-component edit/protection.
3. Safe separation applies to the complete component; no separate low-alpha proof exists.
4. The #14700 complete-low-alpha proof was not frozen V9.
5. It first appears as a separate gate at `6b336f74a6d717a39ac04084b2f4399f92842ccb`.
6. M0 is not the full V9 visible-component mask when 300 adjacent visible pixels are left out.
7. Inclusion follows from `alpha > 0` labeling and `work[..., :3][component] = target`, not a separate alpha<32 branch.
