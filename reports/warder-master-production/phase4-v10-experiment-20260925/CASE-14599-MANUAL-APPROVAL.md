# Case #14599 WHITE — manual visual decision

Štefan confirmed the right-hand candidate on 2026-09-25: “beriem ten pravy”. He also clarified that this picon had already been corrected earlier. This record preserves that history and records the exact right-hand image confirmed today so the isolated test branch matches the confirmed output.

- Case: #14599 — МИР
- Destination: `picons/80.0e/orion-express/white/1_0_1_2C4_CD_1_3200000_0_0_0.png`
- Source transparent PNG SHA256: `152a0d7d31a4f4dd4e69ea0016ce61e5b7b059a98c607dc9e7680098a004e667`
- Previously present WHITE output SHA256: `4dd3c038f0a28e25e2993422cedc3d3769f30020d97730403ef1b1b07c0cbe6a`
- Confirmed right-hand candidate SHA256: `23d3fcc477141c824fb10d72d2098f69d8f0caa0552a7c147581df94c8f35256`
- Candidate: 220×132 RGBA; central text is black; colored ring is preserved. Candidate generation changed 993 source pixels; the rendered output differs from the old branch PNG at 797 pixels. Alpha and protected chromatic pixels are unchanged.
- Manual decision: confirmed exact displayed right-hand candidate for this individual WHITE output.
- Automated status remains `REVIEW`; this does not approve the algorithm or a full-catalog rebuild.
- Applied only to `phase4-v10-component-mask-test`. No change to `main` or `warder-master-production`.

The prior correction/approval is not reopened here. The test branch had retained a Phase 3 baseline, so this commit synchronizes its file with the image Štefan confirmed today.
