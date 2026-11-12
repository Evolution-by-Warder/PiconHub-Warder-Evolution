# Radio batch 96 complete

Independent audit **PASS**. 4028 / 35,560 references, 31532 remaining, 36828 PNG entries and 133 / 219 countries.

This batch added 90 references (RO +35, RU +38, SG +17) and 810 PNG entries across the nine required variants. 765 variants were rendered from 85 official originals. 45 PNG entries reused exact artwork bytes. Previously approved PNGs rerendered: 0.

The Radio Clasic player objects supplied 35 exact Romanian routes and channel artwork. The Radio Record station API supplied 38 exact Russian routes and individual channel symbols. Mediacorp's published stream and logo fields supplied 17 exact Singaporean references, including five standard/HQ pairs sharing one logo per station. The former 938 Now route is currently published by CNA938, with the rebrand corroborated by CNA. The Radio Record X-mas Party reference remains open because its exact route now carries Party 24/7. See official-source-evidence.json for source URLs, digests and the deferred case.

[GitHub Actions audit](https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/actions/runs/43211925667)

- Audit checkpoint `acd61e4e7b6678a56431cd628df694827b83a958`
- Audited build `e23b445599e1de1caa7bece2ebec333fdda5e43f`
- Actual ZIP payload `52412a026cb46f38e599e1dd88503938c0c544ca`
- Immutable manifests `b3b09ddba93bc8f3ff19689f7b4e1f9da355ed73`

The separate readback job downloaded and audited 27 actual GitHub ZIPs. The maximum archive was 9,204,720 bytes (limit 33,554,432). It verified SHA-256, CRC, complete member inventories, RGBA, dimensions, source alpha and exact per-reference PNG bytes. It verified 1,044 previous entries inside the changed packages and 216 unchanged country descriptors. The prior candidate inventory and all 31,329 current production PNG entries were preserved. Configuration retains all 923 blocked references and the historical decisions.

The pinned PR21 downloader `fe573248f3d9e0a8d21acf5696f44b4c02e6fdb7` passed all three 220×132 styles on these immutable packages with no failures. The replay kept the local user file. Hardware was outside the replay scope.

[Draft PR #68](https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/pull/68) remains unmerged. All writes are on the draft work branch, its existing payload branch or the Radio register work branch.

## Continue 97

Batch 97 checks official Mediaset pages for Radio 105, Virgin Radio, Radio Monte Carlo and R101. The direct HTML audio route and station-specific art must agree; hold retired streams or ambiguous station labels for new publisher evidence.

Use this batch's `countries.proposed.json` and the recorded payload manifest commit as the baseline. Batches 1–96 are complete. Details for open cases and source checks are in `results/next-source-observations.json`.
