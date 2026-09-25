# Case #15551 WHITE — manual visual approval

Date: 2026-09-25
Branch: `phase4-v10-component-mask-test`

Štefan approved the far-right V10 test candidate, specifying black text and preservation of the red “+”, for #15551. Before reusing it elsewhere, #4860 was verified as an exact duplicate: source SHA256, existing WHITE output SHA256, and candidate PNG SHA256 are identical. The same approved PNG bytes are therefore applied to #4860 as a duplicate asset.

- Transparent source: `picons/9.0e/ote/transparent/1_0_1_46E_8_AA_5A0000_0_0_0.png`
- Source SHA256: `2a072ef2f098c1de9e03f2bf4e8b9155e95539a2623786bf7f9d0929338f8191`
- Previous WHITE output SHA256: `121a378a80c5cdc5a30ee7cdf005de81d5b3adc7c5c354a0bdc6f04914c8d993`
- Approved WHITE output: `picons/9.0e/ote/white/1_0_1_46E_8_AA_5A0000_0_0_0.png`
- Approved PNG SHA256: `d4db70d1df947b5f76c56cf1c66b70e2b941ca8b390c1f38a19002a4c92844d8`
- Git blob SHA: `7d08c6d4252733cfed8ff51a836e80451b284402`
- Verified duplicate path: `picons/16.0e/total-tv/white/1_0_1_557_75FB_16E_A00000_0_0_0.png` (source: `picons/16.0e/total-tv/transparent/1_0_1_557_75FB_16E_A00000_0_0_0.png`; source SHA256 identical to #15551)
- Dimensions/mode: 220×132 RGBA
- Alpha unchanged: yes
- Protected chromatic pixels unchanged: yes
- Difference from previous output: 296 pixels

The V6 automated check classified this case as REVIEW because four small two-tone components remain ambiguous. The user's visual decision is recorded as a manual approval; the automatic classification remains REVIEW. No algorithm-wide or full-catalog production approval is implied. Only the two byte-identical WHITE outputs above are affected; generator, MASTER, and `main` are unchanged.
