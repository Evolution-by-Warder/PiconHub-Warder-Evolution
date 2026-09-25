# V10 manual decisions — cases #13015 and #1856

Date: 2026-09-25  
Branch: `phase4-v10-component-mask-test`

Štefan selected the **middle/current output** for #1856 and requested the correction to the **middle/current output** for #13015. After reviewing the comparison, Štefan approved the **right-hand corrected WHITE candidate** for #13015 on 2026-09-25.

| Case | Decision | Source SHA256 | Previous/current WHITE SHA256 | Result WHITE SHA256 | Git blob SHA | Automatic status |
|---|---|---|---|---|---|---|
| #13015 | Manually correct the second glyph's white dot and stem to black where they meet the globe | `c19edbff953b7c4b23e3b7ee8bf93e0e405984cc6ea0923cb54aad8faacbbb11` | `ba8253aec7cdfbeca3d5b0732ee1dac69f2365d43b48e72d00137f4b4cd0d2da` | `38a7c762af0645529fbf9e61c5cfff3648950e28d8431ad03958aa792baf0f27` | `7d5fb74bf321196762608bc45729296236cc5b93` | REVIEW |
| #1856 | Retain the middle/current output without changes | `d214870136a075840d559831b4f52ce1a94a7686c5c296fe723859d64e327b09` | `8b2912c4c3afbd7c5a632e76019c0d5937f3aee999deb4aacc68a354a9f16c0e` | `8b2912c4c3afbd7c5a632e76019c0d5937f3aee999deb4aacc68a354a9f16c0e` | unchanged | REVIEW |

For #13015, reconstruction from the original transparent source through the frozen V9 fit/render and exact WHITE MASTER was pixel-identical to the previous/current output before the manual edit. Only the two achromatic components identified as the second glyph (dot and stem; 997 source pixels) were recolored to black. The rendered output differs from previous in 994 pixels. Source alpha and all chromatic globe pixels were preserved. Final PNG is 220×132 RGBA.

Focused evidence: `CASE-13015-MANUAL-CORRECTION.jpg` shows original/current/corrected output and a magnified detail; `CASE-1856-CURRENT-RETAINED.jpg` shows original/current/V10 candidate. No algorithm-wide approval or production rebuild is implied.


Štefan's visual approval applies to this exact #13015 corrected WHITE PNG (SHA256 `38a7c762af0645529fbf9e61c5cfff3648950e28d8431ad03958aa792baf0f27`) only. Its automatic status remains REVIEW; no algorithm-wide or production rebuild approval is implied.
