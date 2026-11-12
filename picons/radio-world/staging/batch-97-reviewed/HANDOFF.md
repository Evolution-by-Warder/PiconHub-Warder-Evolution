# Radio batch 97 complete

Independent audit **PASS**. 4056 / 35,560 references, 31504 remaining, 37080 PNG entries and 134 / 219 countries.

This batch added 28 references (IT +27, LV +1) and 252 PNG entries across the nine required variants. 252 variants were rendered from 28 official originals. 0 PNG entries reused exact artwork bytes. Previously approved PNGs rerendered: 0.

Official station pages of Radio 105, Radio Monte Carlo, R101 and Virgin Radio supplied 27 exact Mediaset audio routes and station-specific player images. The displayed image URL embeds the original artwork URL. Two exact routes now carry a different brand: R101 Christmas instead of the listed R101 main service, and Baila Baila instead of New Music Friday. The other 58 uncovered catalogue routes had no unique exact match in the four current station directories. See official-source-evidence.json for all deferred cases. In Latvia, EHR tied Latviešu hiti to the exact legacy AAC route in the description of its official Top 20 show, using the same station ID as its current FM catalogue. The original SVG from the FM catalogue supplied the station logo.

[GitHub Actions audit](https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/actions/runs/43213100436)

- Audit checkpoint `b6d4ded4ae8da0901706f0c8f8c7649db456763b`
- Audited build `dd6678e32310a14aabc14ff9f939f6291895fa1f`
- Actual ZIP payload `a7494487fc4d912dfdc4899cf60c09cb2661211c`
- Immutable manifests `2fb04ab87d3a29dbc50bb38e3055d3f4b4a563f1`

The separate readback job downloaded and audited 18 actual GitHub ZIPs. The maximum archive was 14,567,180 bytes (limit 33,554,432). It verified SHA-256, CRC, complete member inventories, RGBA, dimensions, source alpha and exact per-reference PNG bytes. It verified 1,044 previous entries inside the changed packages and 217 unchanged country descriptors. The prior candidate inventory and all 31,329 current production PNG entries were preserved. Configuration retains all 923 blocked references and the historical decisions.

The pinned PR21 downloader `fe573248f3d9e0a8d21acf5696f44b4c02e6fdb7` passed all three 220×132 styles on these immutable packages with no failures. The replay kept the local user file. Hardware was outside the replay scope.

[Draft PR #68](https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/pull/68) remains unmerged. All writes are on the draft work branch, its existing payload branch or the Radio register work branch.

## Continue 98

Continue with other official catalogues. EHR’s standard player sources did not provide exact matches for remaining legacy URLs. Seek named publisher links or direct redirects for those references; stream numbers alone are insufficient. Initial public pages for Radio Pakistan and Vatican Radio returned HTTP 403 from the work environment. Use an alternative official source if available.

Use this batch's `countries.proposed.json` and the recorded payload manifest commit as the baseline. Batches 1–97 are complete. Details for open cases and source checks are in `results/next-source-observations.json`.
