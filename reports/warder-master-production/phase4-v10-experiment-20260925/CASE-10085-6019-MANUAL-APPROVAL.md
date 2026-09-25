# V10 manual visual approval — cases #10085 and #6019

Date: 2026-09-25
Branch: `phase4-v10-component-mask-test`

Štefan clarified that his earlier assessment “u oboch su stredne dobre” meant both shown V10 candidates were approved: “stredne som schvalil”. The exact candidates shown in the focused comparisons are applied to their WHITE outputs below.

| Case | Transparent source | Previous WHITE SHA256 | Approved WHITE SHA256 | Git blob SHA | V10 status | Difference from previous |
|---|---|---|---|---|---|---:|
| #10085 | `picons/36.0e/tv-provider/transparent/1_0_1_101_1_1_1682D43_0_0_0.png` | `52f297a5c1735851c40a22ac4682918dae8faffd8a95a07d875cda3d05e82461` | `7d69912ca6d30af83ef49aee2b0780f3214fb4192b9acc30ccc9718da804ca36` | `fd0116e675aaf868d0147e721753257aea13e238` | REVIEW (one two-tone component) | 7,345 px |
| #6019 | `picons/19.2e/ses/transparent/1_0_1F_109D_3EE_1_C00000_0_0_0.png` | `14efe2ca3d8593a316d238f66a0b58263b52052de1899aa8bac8d3dee05f5e74` | `dab34e7c9f837bee6cbf3a981bc9189d6ff53cfba450a24e8064ea9e98445a3b` | `480f4bcd3fb43c83b5e14f852f861000c66147a1` | REVIEW (one two-tone component) | 1,599 px |

Both candidates are 220×132 RGBA. The source-overlay alpha and protected chromatic pixels were preserved in the test assertions. The automatic status remains REVIEW; the user's visual approval is recorded as a case-level override.

The focused comparisons shown before approval are preserved as `CASE-10085-MANUAL-APPROVAL.jpg` and `CASE-6019-MANUAL-APPROVAL.jpg`. Per-case source hashes, pixel counts, and preservation assertions are in the accompanying CSV.

Only the two WHITE output paths above were changed. The duplicate #1009, #407, MASTER templates, generator, approved batches, and `main` were not changed by this approval. This does not approve the V10 algorithm or a full-catalog rebuild.
