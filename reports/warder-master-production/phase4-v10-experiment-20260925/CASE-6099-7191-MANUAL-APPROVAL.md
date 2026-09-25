# V10 manual visual approval — cases #6099 and #7191

Date: 2026-09-25  
Branch: `phase4-v10-component-mask-test`

Štefan selected the **right-hand V10 candidate** for both picons. The exact displayed candidate PNGs were applied to their WHITE outputs on this isolated test branch.

| Case | Transparent source | Previous WHITE SHA256 | Approved WHITE SHA256 | Git blob SHA | V10 status | Pixels different from previous |
|---|---|---|---|---|---|---:|
| #6099 | `picons/19.2e/ses-astra/transparent/1_0_1F_183D_40B_1_C00000_0_0_0.png` | `94f8032c9f0c8dc845507c8eb9561ef256bb88fd7a0e675a6213ac87c9845e40` | `37ba4c88b4bdb7115bac11e4744df4a5c4beb101126eb3a2368b9b749cb8761b` | `57c01b108a777aa4162c9e229595c322e72d3f3f` | REVIEW (manual approval) | 11 |
| #7191 | `picons/23.5e/telekom-srbija/transparent/1_0_1_4E4D_CA5_3_EB0000_0_0_0.png` | `6a1b1a102def567285e56a5ac02b62a7248323df75fe7efba2667b69a74ffb73` | `1420bd9a0c62ae6f087c6024f4cc9ad2a8e77216cff1879be99dc3c4740f2359` | `04a9c274fdaed1a7e03d924f8827b8798459439d` | REVIEW (manual approval) | 49 |

Both approved PNGs are 220×132 RGBA. The source hashes match the P1 regression audit. Alpha and protected chromatic pixels remained unchanged in the fixture assertions. The automated classifier remains REVIEW for both; the user's approval applies to these two exact images only.

Focused comparisons are preserved as `CASE-6099-MANUAL-APPROVAL.jpg` and `CASE-7191-MANUAL-APPROVAL.jpg`. This does not approve the V10 algorithm or a full-catalog rebuild.
