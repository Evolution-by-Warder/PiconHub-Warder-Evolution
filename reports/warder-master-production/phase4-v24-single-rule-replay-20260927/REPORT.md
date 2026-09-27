# V24 — Complete frozen safety-gate replay / single-rule substitution

**Outcome: A — ALL SAFETY GATES CLEAR / DIAGNOSTIC CANDIDATE GENERATED.**

**Starting HEAD:** `bcff65e01476d01aea4766066a886b93dccdccf4`  
**Phase 3 generator:** `e9b503d76eae3c3c7d7763df4909039a55d3edb8`  
**V23 topology implementation:** `bcff65e01476d01aea4766066a886b93dccdccf4` (tool blob `dd66e2e96c15c1ee425222bf7898aabd45756b6a`; rule origin `5a42e95ac6978f66d1f52d834fe3b40c53e93992`)

## Single-rule substitution

The exact Phase 3 `classify_and_render` function was loaded from the pinned checkpoint. Its single frozen raw-solid two-tone expression was replaced once for #14700 V9 components 4, 12, and 13 with the exact V23 `topology_guard`. The thresholds, material sample, component membership (`alpha > 0`, 8-connectivity), branch order, achromatic decision, contrast computation, protected behavior, target and whole-component RGB write remain unchanged. Insufficient interior evidence returns protected/two-tone.

## Component decision trace

| V9 component | visible / solid | frozen two-tone | topology evidence | topology result | achromatic | WHITE weak fraction / 8% | correction required | decision after substitution |
|---:|---:|---|---|---|---|---|---|---|
| 4 | 814 / 430 | True | 114 px (floor 12.40) | `not-two-tone`; dark/light 0/114 | 100.0% | 80.70% / 8% | True | `RECOLOR` |
| 12 | 225 / 128 | True | 34 px (floor 10.24) | `not-two-tone`; dark/light 0/34 | 100.0% | 73.44% / 8% | True | `RECOLOR` |
| 13 | 826 / 512 | True | 159 px (floor 12.64) | `not-two-tone`; dark/light 0/159 | 100.0% | 88.67% / 8% | True | `RECOLOR` |

All three are achromatic; each has sufficient topology interior, no chromatic solid pixels, topology-aware `not-two-tone`, and requires WHITE correction to frozen `(16,16,16)`. The material low-contrast fractions are 80.70%, 73.44%, and 88.67%, above the unchanged 8% threshold.

## Remaining safety gates

The authoritative committed V15 summary (blob `6ec3d1a95fe3d9e4a8caa53316f1f3784ee9cd7b`) records complete wordmark group `[6, 7, 8, 9, 10]`, exterior MASTER context, no chromatic/true-AA/ambiguous contact, and 0 blocked grouping links. These are the current complete-wordmark/protected-link results used here. The V12 audit is retained only as historical comparison and is not treated as current evidence because the later V15 audit supersedes its proposed-link status.

V15 reports low-alpha perimeter contact, but V24 does not use low-alpha ownership as a blocker: V21 established that this was a later experimental guard, not frozen V9 contract. The entire `alpha > 0` V9 components remain the edit units. Pixel `(109,73)` is `(0,63,63,4)`, visible in component 4 and outside the solid sample; no special case is used, and whole-component V9 RGB assignment includes it if the component passes.

| Final gate | Result | Evidence |
|---|---|---|
| Complete wordmark | PASS | V15 group complete; all three M0-bearing V9 components included |
| Exterior / MASTER context | PASS | V15 exterior topology and MASTER context true |
| Chroma / true-AA / ambiguous protection | PASS | V15 protected contact false; V22 target components have no path to chromatic material |
| Blocked grouping links | PASS | V15 reports 0 |
| Topology two-tone | PASS | all three `not-two-tone`; sufficient interior evidence |
| Frozen achromatic/material classification | PASS | 100% of each `alpha >=32` sample meets frozen achromatic rule |
| WHITE contrast | PASS | each weak-material fraction exceeds frozen 8%; target `(16,16,16)` |
| Low-alpha ownership | NOT USED | excluded by V21 frozen V9 contract audit |
| Whole V9 replay after substitution | PASS | `AUTO-FIXED`; no residual REVIEW reason |

## Candidate and pixel invariants

Candidate generated at `14700-V24-DIAGNOSTIC-WHITE-CANDIDATE.png`, status `READY-FOR-MANUAL-VISUAL-REVIEW`. The whole-component edit mask contains 1865 visible component pixels; 1864 source RGB pixels changed to `(16,16,16)`. Composited candidate differs from CURRENT WHITE at 1707 pixels. Alpha changed = 0; changed RGB outside components 4/12/13 = 0; component 1 changes = 0. The full replay reports `AUTO-FIXED` across 12 components because it retains pre-existing frozen fixes; comparison against CURRENT WHITE confirms only 4/12/13 differ. Candidate is a diagnostic artifact only; it is not production-approved.

The comparison images show SOURCE composited over the WHITE MASTER, CURRENT WHITE, and V24 candidate at native size and nearest-neighbor wordmark zoom. They are for Stefan’s visual decision only.

## Controls

Both genuine two-tone controls remain `two-tone=true` under the V23 topology guard with adequate interior evidence, dark and light populations, and zero editable pixels. #14607/#14611 remain REVIEW and byte-identical; #14593 remains REVIEW; #14597 remains cautious REVIEW; Digi Slovakia remains PASS with 0 WHITE and BLACK changed pixels. All frozen control replays match stored outputs. #14599 was not accessed.

## Reproduction

```sh
python tools/phase4_v24_single_rule_replay.py \
  --fixtures /path/to/v22-fixtures \
  --controls /path/to/v24-fixtures/controls \
  --v22-summary reports/warder-master-production/phase4-v22-full-v9-component-reconstruction-20260927/SUMMARY.json \
  --v22-connectivity reports/warder-master-production/phase4-v22-full-v9-component-reconstruction-20260927/CONNECTIVITY-AUDIT.csv \
  --v23-summary reports/warder-master-production/phase4-v23-per-component-topology-two-tone-20260927/SUMMARY.json \
  --v23-script tools/phase4_v23_component_tone.py \
  --v15-summary reports/warder-master-production/phase4-v15-topology-aware-two-tone-20260927/SUMMARY.json \
  --phase3-generator /path/to/pinned/rebuild_master_catalog.py \
  --out /path/to/v24-results
```

## Artifacts

- `REPORT.md`
- `SAFETY-GATE-AUDIT.csv`
- `CONTROL-AUDIT.csv`
- `SUMMARY.json`
- candidate and comparison PNGs (diagnostic only)
- `tools/phase4_v24_single_rule_replay.py`
