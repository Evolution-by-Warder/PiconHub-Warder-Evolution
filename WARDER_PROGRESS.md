# WARDER RADIO

| Dávka | Nové referencie | PNG | ZIP | Audit |
| --- | ---: | ---: | ---: | --- |
| 95 | 5 | 45 | 9 | [PASS](https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/actions/runs/43210929605) |

# Radio batch 95 complete

Independent audit **PASS**. 3938 / 35,560 references, 31622 remaining, 36018 PNG entries and 132 / 219 countries.

This batch added 5 references (AR +5) and 45 PNG entries across the nine required variants. 45 variants were rendered from 5 official originals. 0 PNG entries reused exact artwork bytes. Previously approved PNGs rerendered: 0.

Radio Nacional Argentina published exact playback URLs for five accepted national services and original artwork for AM870, Clásica, Folklórica, Rock and RAE. The official RAE landing-page link supplies the RAE image because its pop-up player uses the common AM870 image. Thirty-eight regional references have exact publisher routes but no verified station-specific artwork, and six legacy port 7200 references have no exact official route. Their evidence is preserved in official-source-evidence.json.

[GitHub Actions audit](https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/actions/runs/43210929605)

- Audit checkpoint `06496353484d1581cc2e8c2953c44b995b8bb0fc`
- Audited build `e30a8f2186998f96eb419304e59d8915fd119631`
- Actual ZIP payload `9daf0dc1f5499c6fa09197df087548dc64f164f2`
- Immutable manifests `b7d5b621afee154e842283af97508c928877fcca`

The separate readback job downloaded and audited 9 actual GitHub ZIPs. The maximum archive was 3,262,698 bytes (limit 33,554,432). It verified SHA-256, CRC, complete member inventories, RGBA, dimensions, source alpha and exact per-reference PNG bytes. It verified 261 previous entries inside the changed packages and 218 unchanged country descriptors. The prior candidate inventory and all 31,329 current production PNG entries were preserved. Configuration retains all 923 blocked references and the historical decisions.

The pinned PR21 downloader `fe573248f3d9e0a8d21acf5696f44b4c02e6fdb7` passed all three 220×132 styles on these immutable packages with no failures. The replay kept the local user file. Hardware was outside the replay scope.

[Draft PR #68](https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/pull/68) remains unmerged. All writes are on the draft work branch, its existing payload branch or the Radio register work branch.

## Continue 96

Batch 96 uses exact player data and station artwork from Radio Record, Radio Clasic and Mediacorp. Keep the Argentine artwork and legacy port cases open for decisive publisher evidence.

Use this batch's `countries.proposed.json` and the recorded payload manifest commit as the baseline. Batches 1–95 are complete. Details for open cases and source checks are in `results/next-source-observations.json`.
