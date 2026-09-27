# V22 — Full V9 alpha-visible component reconstruction

**Branch:** `phase4-v10-component-mask-test`  
**Starting HEAD:** `b1232993ad4f7be6c55546542b698b3fd3fcd773`  
**Phase 3 executable checkpoint:** `e9b503d76eae3c3c7d7763df4909039a55d3edb8`  
**Outcome: D — COMPONENT STRUCTURE DIFFERENT THAN ASSUMED**

## Finding

The previously confirmed #14700 M0 mask is **not contained in one V9 `alpha > 0` component**. Under the exact Phase 3 fit and eight-connected labeling it intersects three separate components, labels **4, 12, and 13**, with 488, 155, and 581 M0 pixels respectively. All 1,224 M0 pixels are visible and accounted for; none is label 0. Therefore the requested “whole V9 component containing the wordmark” does not exist as a single component. Per the test instruction, this audit stops short of treating the three-component set as one logical component and reports each V9 component independently.

The three M0-bearing components contain 1,865 visible pixels as a **set union, not one component**. Their solid samples total 1,070 pixels; the remaining 795 visible pixels have alpha 1–31. The separately frozen 300-pixel low-alpha perimeter is reproduced exactly and lies in those same three labels. The set union has another 341 subthreshold visible pixels beyond M0 and those 300 perimeter pixels. The full pixel inventory is in `14700-COMPONENT-PIXELS.csv`.

The frozen V9 chromatic material is elsewhere: 957 `alpha >= 32`, channel-spread `>18` pixels, all in V9 component 1. There is no `alpha > 0` path from any M0-bearing component to that material. Thus V9 connectivity **does not join the M0 wordmark pixels to the chromatic symbol/material** in this fitted image. The semantic role of the 341 extra low-alpha pixels cannot be decided by V9’s solid-material classifier; they are listed with their exact alpha, RGB, spread, and membership rather than assigned new ownership.

## Exact Phase 3 code path used

The audit imported `tools/rebuild_master_catalog.py` from commit `e9b503d76eae3c3c7d7763df4909039a55d3edb8` (local fixture SHA256 `f931d3eb703021fa90d6c7934e6902cd1ecb49dd7a8e69e087072a9bf00d1722`). The implementation is reproduced directly:

1. `fit_logo` crops the nonzero-alpha bbox, proportionally fits it inside the 220×132 canvas with 8-pixel side margins, resizes with LANCZOS when needed, then centers it. For #14700: source alpha bbox `[3,43,218,90]`, scale `0.9488372093`.
2. `visible = alpha > 0`.
3. `ndimage.label(visible, structure=np.ones((3,3), dtype=np.uint8))` gives 17 components.
4. For each component, sample mask is `component & (alpha >= 32)`; the source code falls back to the full component only if this sample is empty. None of components 4, 12, or 13 needs fallback.
5. On that sample, V9 calculates channel spread, achromatic fraction (`spread <=18`; required `>=0.985`), linear Rec.709 luminance, two-tone (`dark <=64` and `light >=192`, each `>=0.03`), and contrast against the actual MASTER under the sample. Contrast needs fixing when the weak-contrast share is `>=0.08` at ratio `<2.50`.
6. If achromatic and not two-tone, V9 may recolor the **entire visible component** RGB to its frozen target. Otherwise it protects the component and may emit a REVIEW reason. Alpha is not changed.

This replay does not substitute later topology, ownership, or grouping experiments for the frozen Phase 3 code.

## #14700: M0 and the three V9 components

| V9 label | Visible px | Bbox `[x0,y0,x1,y1)` | M0 px | Known 300-ring px | Other visible px outside M0+ring | alpha 1–31 | alpha ≥32 | Solid achromatic / chromatic | WHITE dark / light fraction | WHITE weak fraction | V9 WHITE branch |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 4 | 814 | `[82,55,139,76]` | 488 | 144 | 182 | 384 | 430 | 430 / 0 | 23.26% / 40.93% | 80.70% | PROTECTED; two-tone REVIEW |
| 12 | 225 | `[63,57,81,76]` | 155 | 42 | 28 | 97 | 128 | 128 / 0 | 26.56% / 39.06% | 73.44% | PROTECTED; two-tone REVIEW |
| 13 | 826 | `[140,57,210,76]` | 581 | 114 | 131 | 314 | 512 | 512 / 0 | 17.19% / 39.65% | 88.67% | PROTECTED; two-tone REVIEW |

All three solid samples are 100% achromatic under the frozen channel-spread rule. All three independently meet the frozen dark and light fractions and therefore independently trip the frozen two-tone condition. On WHITE, their material weak-contrast fractions exceed the frozen 8% material rule, so the generator emits one REVIEW reason per component and preserves them. No part of any of these three components is recolored by the WHITE run.

On BLACK, the same three components are still two-tone and remain protected; their weak-contrast shares are 7.67%, 4.69%, and 5.08%, below the 8% reason threshold. The image-level BLACK run is nevertheless REVIEW because separate chromatic component 1 has 77.5% weak-contrast material.

## Full visible set, M0 difference, and alpha bands

The 300 coordinates from the earlier low-alpha ownership audit exactly match the independently recomputed visible subthreshold ring around M0. Each has `0 < alpha <32`, and the 300 split across V9 labels 4/12/13 is 144/42/114.

M0 contains 1,070 pixels at alpha ≥32 plus 154 at alpha 1–31. The 300 known perimeter pixels are all outside M0. The component-set union has 795 pixels at alpha 1–31 and 1,070 at alpha ≥32. Of the 341 visible pixels outside M0 and the known 300 ring, all 341 are subthreshold with channel spread 0; there are no additional alpha≥32 material pixels outside M0 in these three components.

The single earlier `PROTECTED / OTHER` record is `(x=109,y=73)`, RGBA `(0,63,63,4)`, channel spread 63. It is in perimeter ring and V9 component 4. It is **not sampled** by the V9 classifier because alpha 4 is below 32; it therefore does not change component 4’s achromatic/two-tone statistics. It is not connected to the external V9 chromatic material component 1. Its later “protected/other” label is a Phase 4 evidence label, not the frozen V9 component class.

Set comparison:

- `M0 − (components 4∪12∪13) = 0` pixels.
- `(components 4∪12∪13) − M0 = 641` pixels: 300 known low-alpha perimeter + 341 other visible subthreshold pixels.

## Frozen V9 executable result versus documented safety intent

**Executable Phase 3 result:** the classifier processes labels 4, 12, and 13 as separate units. Each is achromatic by its solid sample but two-tone, so each whole component is protected; their WHITE low-contrast shares cause REVIEW. It does not see a single complete wordmark component. The separate colored material is component 1 and also remains separate/protected when the relevant branch says so.

**Safety intent:** V9’s whole-component operation is only suitable when that component is a safely separable logical element. This audit does not establish that labels 4/12/13 individually are a complete logical wordmark; indeed the M0 evidence spans three IDs. Nor does the executable code provide a semantic test that those separate component IDs collectively form a complete wordmark. Thus the code’s pixel connectivity and the later logical-wordmark grouping model are not interchangeable. Outcome D is the factual structural result; it is not authorization to join the components or recolor them.

## Historical Phase 3 output check

Exact frozen replay from the pinned generator is pixel-identical to the Phase 3 stored output for #14700 WHITE and BLACK. The current branch files at `b123299...` are also byte-for-byte identical to the Phase 3 checkpoint for #14700 source, WHITE, BLACK, WHITE MASTER, #14607/#14611 source and variants, Digi Slovakia source and variants, and both genuine-two-tone controls’ source and variants.

- #14700 WHITE: `REVIEW`, 69 changed pixels elsewhere in the image, 3,187 protected pixels. Reasons are components 4/12/13, with 80.7%, 73.4%, 88.7% weak contrast respectively. The three M0-bearing components themselves changed 0 pixels.
- #14700 BLACK: `REVIEW`, 54 changed pixels elsewhere, 3,187 protected pixels. Reason: chromatic component 1 at 77.5% weak contrast. The three M0-bearing components themselves changed 0 pixels.

The original V9 result on the M0-bearing components is therefore preservation/REVIEW due to component-level two-tone detection. It is not a recolor of their `alpha<32` perimeter.

## Controls

- **#14607/#14611:** fitted source bytes, WHITE output bytes, and BLACK output bytes are pairwise identical at both Phase 3 and current branch checkpoints. Frozen replay produces 28 visible components and `REVIEW`; WHITE changes 0 pixels, BLACK changes 64 elsewhere. Multiple chromatic and two-tone component reasons remain. This is a duplicate regression control; no reconstruction was repeated.
- **Digi Slovakia:** frozen replay is `PASS`, changed pixels 0 on both variants, and pixel-identical to stored Phase 3 outputs.
- **Genuine two-tone control 1 (Neosat):** frozen V9 reports `REVIEW` for two-tone component 1 on WHITE and BLACK; no pixels changed. Replay is pixel-identical to historical outputs.
- **Genuine two-tone control 2 (Demirören Medya):** frozen V9 reports `REVIEW` for two-tone component 1 on WHITE and BLACK; 1 / 18 unrelated pixels are changed elsewhere in the respective whole images. Replay is pixel-identical to historical outputs.
- **#14599:** not accessed.

## Conclusion

**Outcome D — COMPONENT STRUCTURE DIFFERENT THAN ASSUMED.** There is no single V9 `alpha>0` component containing M0; there are three, and they are separated from V9 chromatic material component 1. Frozen V9 independently labels all three M0-bearing components two-tone and preserves them on WHITE. This explains the executable historical decision without assuming that the 3-component set is one complete logical wordmark. No candidate was generated; no source, MASTER, template, or production picon was written.

Artifacts: `FULL-V9-COMPONENT-AUDIT.csv`, `CONNECTIVITY-AUDIT.csv`, `DECISION-REPLAY.csv`, `14700-COMPONENT-PIXELS.csv`, `SUMMARY.json`, and `tools/phase4_v22_full_v9_component_reconstruction.py`.

## Frozen content classes and limits of semantic assignment

The frozen V9 classifier has only the `alpha >=32` material sample and the component-level achromatic/chromatic decision; it has no distinct `true chromatic AA`, badge, or per-pixel ownership class. Accordingly:

- Within labels 4/12/13, the 1,070 sampled material pixels are all achromatic by frozen V9 (`spread <=18`). There are 0 sampled chromatic pixels in those labels.
- The known 300 perimeter pixels are all subthreshold. Of these, 299 have channel spread 0; coordinate `(109,73)` has spread 63. This one is the Phase 4 `PROTECTED / OTHER` record and is not V9 material.
- The other 341 visible pixels in those labels outside M0 plus known perimeter are all alpha 1–31 and have spread 0. The frozen code does not identify whether they are AA, an unrelated visible fragment, or another subthreshold transition; no ownership is assigned here.
- Frozen chromatic material is 957 pixels in component 1, outside labels 4/12/13. The source image shows a separate colored emblem there. There is no path linking it to M0 in `alpha>0` eight-connectivity. No chromatic material, colored badge/background, or unrelated solid visible fragment is established inside the three M0-bearing labels by the frozen material sample.

This is a code-classification description, not a new semantic segmentation. In particular, “chromatic AA” cannot be inferred from V9’s component/material output alone.

## Hashes and reproducibility inputs

| Item | SHA256 |
|---|---|
| #14700 transparent source | `9fa6f6a84bb9e1a98802e638f94d0f693757697648d1167d1b9f3f31fb7724c3` |
| #14700 current / Phase 3 WHITE | `e2b1eaf5cdad1acf3b251c7d5173a7bf0066ca3ea1a6eff9a60bd8aa02c76916` |
| #14700 current / Phase 3 BLACK | `1427d20873cb77f3bd659c79855956ade5a0f808e6dd33cccb1d94ef2ae895ad` |
| WHITE MASTER | `c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589` |
| BLACK MASTER | `61e69f7fc46e340453bf74ccd7af6ac9d8eba9f8e232884659e1ea99f6abf3fe` |
| #14607/#14611 transparent source (both byte-identical) | `edec07adb8a121d7c856271543549717aff4d253f0302fd2d83a909481b2d24c` |

The audit script expects a fixture directory containing the pinned generator as `rebuild_master_catalog.py` plus the exact transparent sources, stored WHITE/BLACK outputs, and master PNGs listed by the script. Retrieve the source generator and picons at the Phase 3 commit or use the byte-identical current-branch snapshots verified above. Run:

```sh
python tools/phase4_v22_full_v9_component_reconstruction.py --fixtures /path/to/v22-fixtures --out /path/to/v22-results
```

The script writes only to the supplied `--out` directory. The map PNG is a diagnostic overlay of the M0-bearing component **set**, not a candidate or recolor.
