# V10 manual visual decisions — cases #6216 and #14408

Date: 2026-09-25  
Branch: `phase4-v10-component-mask-test`

Štefan selected the **right-hand image** for #6216 and the **middle-column CURRENT** image for #14408.

| Case | User selection | Transparent source | Previous/current WHITE SHA256 | Selected WHITE SHA256 | V10 status | Result |
|---|---|---|---|---|---|---|
| #6216 | Right-hand V10 candidate | `picons/19.2e/tsa/transparent/1_0_2_18F6_3F4_1_C00000_0_0_0.png` | `60f6c922b1d2c5995ec28fa57ab978e4b0bed64d46149de170c99ac3af573fab` | `1428dd0e3da0f968837a30cc05876b11d84c1d24d4feffe5b3b4eb16ff82766c` | REVIEW | Exact candidate manually approved and applied to WHITE on this test branch |
| #14408 | Middle-column CURRENT | `picons/80.0e/harmonic/transparent/1_0_1_22_14_1113_3200000_0_0_0.png` | `5934af2ceb6e44be81aa49cb2d084e5ad2fa0970a932ec2d72f70ca131f57172` | `5934af2ceb6e44be81aa49cb2d084e5ad2fa0970a932ec2d72f70ca131f57172` | REVIEW | Current WHITE retained; no PNG write |

For #6216, the selected PNG is 220×132 RGBA. Candidate SHA256 is `1428dd0e3da0f968837a30cc05876b11d84c1d24d4feffe5b3b4eb16ff82766c`; Git blob SHA is `48a07d798e307a7e79fdd572d3f20c0288c2b569`. The regression audit recorded 9,743 changed source pixels, 1,498 pixels different from the current output, unchanged alpha, and unchanged protected chromatic pixels.

The focused #6216 comparison is preserved as `CASE-6216-14408-MANUAL-VISUAL-DECISIONS.jpg`; the focused #14408 comparison is preserved as `CASE-14408-MANUAL-VISUAL-DECISION.jpg`. The automatic classifier remains REVIEW for both cases. These are case-specific visual decisions; they do not approve V10 as an algorithm or a full-catalog rebuild.
