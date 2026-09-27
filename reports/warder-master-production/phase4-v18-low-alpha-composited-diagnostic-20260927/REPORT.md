# Phase 4 — #14700 Low-Alpha Composited-Color Diagnostic

**Scope: measurement only. No classifier, threshold, mask, or candidate was changed.**

## Integrity checks

- Branch checkpoint recorded: `4e84d3ddb370c89addb5b39258d5f718c8d7618a`.
- WHITE MASTER SHA256: `c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589` — PASS.
- Frozen #14700 ownership population: 300 px (40 safe reference, 252 raw-RGB rejected, 7 other ambiguous, 1 protected/other).
- #14607 negative control: 6/6 still within a frozen protected neighborhood; safe ownership remains 0.

## Composition and measurements

C_out = (alpha/255)*C_source + (1-alpha/255)*C_WHITE_MASTER_RGB; float64; no intermediate rounding. MASTER uses its actual RGB at each pixel coordinate, including non-255 textured values.
Raw pixel RGB is compared to directly adjacent preconfirmed group support. For a fixed-pair comparison, support is selected by spatial distance (then y/x tie-break) independent of color. The CSV also stores every direct support pair, the minimum RGB/composited distance across that set, source/master values, and the alpha/composited values needed to recompute the results. Luminance uses inverse sRGB companding and linear Rec.709; distances use float64, with no pre-rounding.

Premultiplied RGB is recorded as `alpha/255 * source RGB` and is not used as an ownership test. Hypothetical dark-target values apply `(16,16,16)` at unchanged alpha only in numeric arrays; no candidate PNG is emitted.

## Distributions

The following metrics are descriptive, not fitted thresholds. See `SUMMARY.json` for min/median/mean/p75/p90/p95/max and all alpha-band breakdowns.

### #14700 SAFE REFERENCE (n=40)
- `raw_distance_to_local_support_min_Linf`: `{"n":40,"min":0.0,"median":0.0,"mean":2.9,"p75":1.25,"p90":12.0,"p95":13.199999999999989,"max":17.0}`
- `raw_distance_to_fixed_nearest_support_Linf`: `{"n":40,"min":0.0,"median":2.5,"mean":71.875,"p75":188.0,"p90":213.1,"p95":215.05,"max":233.0}`
- `composited_distance_to_fixed_nearest_support_Linf`: `{"n":40,"min":0.7372549019607675,"median":6.4156862745098096,"mean":9.473431372549024,"p75":13.332352941176481,"p90":20.85647058823532,"p95":25.45568627450981,"max":48.29411764705881}`
- `composited_distance_min_over_direct_support_Linf`: `{"n":40,"min":0.0,"median":2.543137254901964,"mean":3.770098039215687,"p75":5.937254901960799,"p90":7.827450980392164,"p95":8.661960784313758,"max":13.529411764705856}`
- `distance_reduction_fixed_support_Linf`: `{"n":40,"min":-10.807843137254906,"median":-0.9862745098039198,"mean":62.40156862745098,"p75":173.06666666666666,"p90":193.4776470588235,"p95":197.40372549019605,"max":199.48235294117646}`
- `composited_luminance_difference_to_fixed_support`: `{"n":40,"min":0.32644182976591196,"median":9.37850921455481,"mean":12.519441890004947,"p75":14.519567807982114,"p90":26.88567046707791,"p95":32.16473554531896,"max":75.72743570514008}`
- `premultiplied_RGB_magnitude_l2`: `{"n":40,"min":0.0,"median":0.0,"mean":1.370357844811847,"p75":0.0,"p90":6.873864381410603,"p95":8.605235953368664,"max":13.6933899139563}`
- `premultiplied_distance_to_fixed_support_L2`: `{"n":40,"min":0.0,"median":0.8558368696222688,"mean":81.11767506907333,"p75":224.17831717022358,"p90":249.6795609437108,"p95":258.6148834027468,"max":324.4368895040291}`
- `hypothetical_dark_target_visible_RGB_delta_Linf`: `{"n":40,"min":0.06274509803921546,"median":0.470588235294116,"mean":0.9898039215686261,"p75":1.1450980392156822,"p90":2.5317647058823582,"p95":3.5815686274509733,"max":6.149019607843144}`
- `hypothetical_dark_target_visible_luminance_delta`: `{"n":40,"min":0.10117034957931992,"median":0.7619644739382494,"mean":1.5173571853159342,"p75":1.6471778839783582,"p90":3.7172075649855207,"p95":5.448824350548955,"max":9.619392770166144}`

### #14700 RGB REJECTED (n=252)
- `raw_distance_to_local_support_min_Linf`: `{"n":252,"min":20.0,"median":194.0,"mean":172.1468253968254,"p75":216.0,"p90":255.0,"p95":255.0,"max":255.0}`
- `raw_distance_to_fixed_nearest_support_Linf`: `{"n":252,"min":31.0,"median":208.0,"mean":184.7420634920635,"p75":217.0,"p90":255.0,"p95":255.0,"max":255.0}`
- `composited_distance_to_fixed_nearest_support_Linf`: `{"n":252,"min":0.003921568627447414,"median":15.743137254901981,"mean":18.085714285714293,"p75":28.05490196078432,"p90":37.11999999999996,"p95":43.86882352941172,"max":72.07450980392159}`
- `composited_distance_min_over_direct_support_Linf`: `{"n":252,"min":0.003921568627447414,"median":12.213725490196097,"mean":14.693588546529728,"p75":22.37254901960784,"p90":32.145882352941186,"p95":37.024705882352926,"max":51.823529411764696}`
- `distance_reduction_fixed_support_Linf`: `{"n":252,"min":16.78823529411767,"median":182.71176470588236,"mean":166.6563492063492,"p75":196.20588235294116,"p90":246.26862745098038,"p95":251.5435294117647,"max":254.99607843137255}`
- `composited_luminance_difference_to_fixed_support`: `{"n":252,"min":0.006821444637580498,"median":18.916099265864162,"mean":24.67948385400956,"p75":39.266822508095416,"p90":53.98969147184497,"p95":66.92877987948542,"max":106.87697865778586}`
- `premultiplied_RGB_magnitude_l2`: `{"n":252,"min":0.0,"median":1.7286546295148206,"mean":2.9286644957422405,"p75":5.191058155625547,"p90":8.558368696222688,"p95":10.310796572115905,"max":13.856406460551018}`
- `premultiplied_distance_to_fixed_support_L2`: `{"n":252,"min":0.0,"median":246.20932420688888,"mean":166.03119843056342,"p75":271.4225500802052,"p90":316.6209253304232,"p95":354.8372598644945,"max":397.183023421922}`
- `hypothetical_dark_target_visible_RGB_delta_Linf`: `{"n":252,"min":0.06274509803921546,"median":1.0980392156862706,"mean":1.6658730158730162,"p75":2.4666666666666828,"p90":3.623529411764707,"p95":4.538039215686293,"max":7.247058823529414}`
- `hypothetical_dark_target_visible_luminance_delta`: `{"n":252,"min":0.10318769285390772,"median":1.7230819624281253,"mean":2.641551382602802,"p75":3.5846060843941885,"p90":5.7123080379691435,"p95":6.881236599978507,"max":12.084059216975902}`

### #14700 OTHER AMBIGUOUS (n=7)
- `raw_distance_to_local_support_min_Linf`: `{"n":7,"min":0.0,"median":0.0,"mean":0.0,"p75":0.0,"p90":0.0,"p95":0.0,"max":0.0}`
- `raw_distance_to_fixed_nearest_support_Linf`: `{"n":7,"min":0.0,"median":0.0,"mean":12.142857142857142,"p75":0.0,"p90":34.00000000000003,"p95":59.49999999999994,"max":85.0}`
- `composited_distance_to_fixed_nearest_support_Linf`: `{"n":7,"min":0.0,"median":1.1999999999999886,"mean":1.4106442577030773,"p75":1.6529411764705912,"p90":2.4031372549019645,"p95":2.964313725490199,"max":3.5254901960784366}`
- `composited_distance_min_over_direct_support_Linf`: `{"n":7,"min":0.0,"median":0.9882352941176578,"mean":1.249859943977587,"p75":1.4274509803921518,"p90":2.2180392156862756,"p95":2.6403921568627444,"max":3.0627450980392155}`
- `distance_reduction_fixed_support_Linf`: `{"n":7,"min":-3.5254901960784366,"median":-0.9882352941176293,"mean":10.732212885154066,"p75":-0.4274509803921518,"p90":33.33960784313728,"p95":58.34431372549014,"max":83.34901960784313}`
- `composited_luminance_difference_to_fixed_support`: `{"n":7,"min":0.0,"median":1.54614146648899,"mean":1.7279492412229485,"p75":2.4600734890971694,"p90":3.2838854666948185,"p95":3.7804938453719092,"max":4.277102224049003}`
- `premultiplied_RGB_magnitude_l2`: `{"n":7,"min":0.0,"median":0.0,"mean":0.7423074889580903,"p75":0.8660254037844386,"p90":2.424871130596429,"p95":2.94448637286709,"max":3.4641016151377544}`
- `premultiplied_distance_to_fixed_support_L2`: `{"n":7,"min":0.0,"median":0.0,"mean":0.4948716593053935,"p75":0.8660254037844386,"p90":1.7320508075688772,"p95":1.7320508075688772,"max":1.7320508075688772}`
- `hypothetical_dark_target_visible_RGB_delta_Linf`: `{"n":7,"min":0.06274509803921546,"median":0.1882352941176464,"mean":0.47338935574229674,"p75":0.5,"p90":1.23686274509804,"p95":1.5556862745098037,"max":1.874509803921569}`
- `hypothetical_dark_target_visible_luminance_delta`: `{"n":7,"min":0.10575242617821345,"median":0.31009557071183735,"mean":0.7888580432814365,"p75":0.8288055735525859,"p90":2.0549928848176027,"p95":2.5886185233996275,"max":3.122244161981655}`

### #14700 PROTECTED / OTHER (n=1)
- `raw_distance_to_local_support_min_Linf`: `{"n":1,"min":195.0,"median":195.0,"mean":195.0,"p75":195.0,"p90":195.0,"p95":195.0,"max":195.0}`
- `raw_distance_to_fixed_nearest_support_Linf`: `{"n":1,"min":195.0,"median":195.0,"mean":195.0,"p75":195.0,"p90":195.0,"p95":195.0,"max":195.0}`
- `composited_distance_to_fixed_nearest_support_Linf`: `{"n":1,"min":8.705882352941217,"median":8.705882352941217,"mean":8.705882352941217,"p75":8.705882352941217,"p90":8.705882352941217,"p95":8.705882352941217,"max":8.705882352941217}`
- `composited_distance_min_over_direct_support_Linf`: `{"n":1,"min":8.705882352941217,"median":8.705882352941217,"mean":8.705882352941217,"p75":8.705882352941217,"p90":8.705882352941217,"p95":8.705882352941217,"max":8.705882352941217}`
- `distance_reduction_fixed_support_Linf`: `{"n":1,"min":186.29411764705878,"median":186.29411764705878,"mean":186.29411764705878,"p75":186.29411764705878,"p90":186.29411764705878,"p95":186.29411764705878,"max":186.29411764705878}`
- `composited_luminance_difference_to_fixed_support`: `{"n":1,"min":5.813574016283667,"median":5.813574016283667,"mean":5.813574016283667,"p75":5.813574016283667,"p90":5.813574016283667,"p95":5.813574016283667,"max":5.813574016283667}`
- `premultiplied_RGB_magnitude_l2`: `{"n":1,"min":1.397575755756941,"median":1.397575755756941,"mean":1.397575755756941,"p75":1.397575755756941,"p90":1.397575755756941,"p95":1.397575755756941,"max":1.397575755756941}`
- `premultiplied_distance_to_fixed_support_L2`: `{"n":1,"min":184.34568212743997,"median":184.34568212743997,"mean":184.34568212743997,"p75":184.34568212743997,"p90":184.34568212743997,"p95":184.34568212743997,"max":184.34568212743997}`
- `hypothetical_dark_target_visible_RGB_delta_Linf`: `{"n":1,"min":0.7372549019607959,"median":0.7372549019607959,"mean":0.7372549019607959,"p75":0.7372549019607959,"p90":0.7372549019607959,"p95":0.7372549019607959,"max":0.7372549019607959}`
- `hypothetical_dark_target_visible_luminance_delta`: `{"n":1,"min":0.8931894517597243,"median":0.8931894517597243,"mean":0.8931894517597243,"p75":0.8931894517597243,"p90":0.8931894517597243,"p95":0.8931894517597243,"max":0.8931894517597243}`

### #14607 PROTECTED NEGATIVE CONTROL (n=6)
- `raw_distance_to_local_support_min_Linf`: `{"n":6,"min":14.0,"median":88.0,"mean":110.33333333333333,"p75":173.75,"p90":211.5,"p95":221.75,"max":232.0}`
- `raw_distance_to_fixed_nearest_support_Linf`: `{"n":6,"min":14.0,"median":88.0,"mean":110.33333333333333,"p75":173.75,"p90":211.5,"p95":221.75,"max":232.0}`
- `composited_distance_to_fixed_nearest_support_Linf`: `{"n":6,"min":16.73333333333335,"median":28.350980392156856,"mean":29.330065359477143,"p75":36.08921568627453,"p90":39.08431372549023,"p95":39.45588235294122,"max":39.8274509803922}`
- `composited_distance_min_over_direct_support_Linf`: `{"n":6,"min":16.73333333333335,"median":28.350980392156856,"mean":29.330065359477143,"p75":36.08921568627453,"p90":39.08431372549023,"p95":39.45588235294122,"max":39.8274509803922}`
- `distance_reduction_fixed_support_Linf`: `{"n":6,"min":-2.7333333333333485,"median":54.16274509803921,"mean":81.0032679738562,"p75":143.63823529411764,"p90":185.62745098039215,"p95":196.6254901960784,"max":207.62352941176468}`
- `composited_luminance_difference_to_fixed_support`: `{"n":6,"min":28.567475025268664,"median":40.89624583518673,"mean":43.33028640806835,"p75":52.452759165609734,"p90":56.74772457269415,"p95":57.74238354324022,"max":58.73704251378629}`
- `premultiplied_RGB_magnitude_l2`: `{"n":6,"min":0.9882352941176471,"median":1.8621038351569876,"mean":2.098583873401881,"p75":2.742156862745098,"p90":3.073504734205393,"p95":3.114178669935541,"max":3.1548526056656887}`
- `premultiplied_distance_to_fixed_support_L2`: `{"n":6,"min":1.011764705882353,"median":3.548542512363027,"mean":6.790601037149588,"p75":11.314136519526034,"p90":14.68255205644997,"p95":15.09335999603043,"max":15.504167935610887}`
- `hypothetical_dark_target_visible_RGB_delta_Linf`: `{"n":6,"min":0.7372549019607959,"median":1.339215686274514,"mean":1.587581699346411,"p75":2.3500000000000085,"p90":2.649019607843144,"p95":2.6970588235294173,"max":2.7450980392156907}`
- `hypothetical_dark_target_visible_luminance_delta`: `{"n":6,"min":0.0845001965479355,"median":0.7311888281058145,"mean":0.8056761883923874,"p75":1.387650928869057,"p90":1.5102180612143457,"p95":1.533367707230525,"max":1.5565173532467043}`

## Alpha-gradient evidence

Unique-owner paths analyzed: 299; composited luminance monotone: 240; non-monotone: 59; no measurable path: 0. Each row's path records core/attachment/perimeter RGBA, alpha, actual master RGB, raw and composited luminance, and per-step RGB/luminance changes. This is source-topology inspection only; no chaining was used.

The source-fit composite was compared numerically with CURRENT WHITE: max channel delta 4.0000, median 0.0000, p95 0.0000. This checks alignment of the source-derived fitted grid and the master pixel coordinates.

## Negative control and conclusion

#14607’s six low-alpha pixels retain protected proximity in every row, regardless of their composited values. The classifier’s protected precedence is unchanged.

**Diagnostic category: `MIXED`.** Compare the fixed-pair and best-direct-support distributions for the 252 raw-RGB rejects against the 40 safe reference and six #14607 protected controls. Any improved composited continuity is descriptive evidence only. No threshold or status was altered; all 252 remain rejected, the 40 remain reference-only, ambiguous groups stay ambiguous, #14607 remains protected, and #14700 remains REVIEW. Candidate = none; production writes = 0.

## Visualizations

- A: `diagnostics/14700-raw-vs-composited.jpg` — source on WHITE MASTER, raw-RGB rejects, raw distance and composited distance.
- B: `diagnostics/14700-population-classes.jpg` — safe reference, 252 rejected, other ambiguous/outlier.
- C: `diagnostics/14700-aa-edge-representatives.jpg` — representative edge crops: source RGB, composited on MASTER, hypothetical dark-target composite.
