# V26 — Topology-aware two-tone generalization / regression qualification

## Decision

**RULE-GENERALIZATION-NEEDS-MORE-EVIDENCE**. This is an audit-only sample, not a production rollout recommendation. No picon candidate or output was written.

## Scope and fixed corpus

The 22 controls were fixed from existing project evidence before V26 computation: five prior deterministic Class P wordmarks (V17 selection ranks 23, 35, 39, 72, 139); the two V23 genuine two-tone positives; the manually approved #14700 query; the required #14593/#14597/#14607/#14611 cases; four existing mixed/chromatic/protected stress cases (#11359, #14406, #10954, #5136); four already manually approved monochromatic controls (#3021, #3032, #3072, #3096), used only for source classifier regression with approvals unchanged; and two historical zero-change PASS controls (Digi Slovakia and ProTV). No manual approval was revisited. #14599 was not selected or accessed. Source paths and hashes plus selection basis are in CONTROL-SELECTION.csv.

## Exact comparison

Each source was fit with the pinned Phase 3 generator and labeled `alpha > 0`, 8-connected. Solid material is component pixels with `alpha >=32`, falling back to the component only if empty. Frozen V9 two-tone uses raw-source linear Rec.709 luminance, dark `<=64`, light `>=192`, with both populations at least 3% of the frozen solid sample. The V23 topology rule uses the same luminance thresholds and fraction over `M AND binary_erosion(M, 3x3 all-ones, border_value=0)`. Evidence is sufficient only when the interior has at least 8% of the largest 8-connected solid-material component; otherwise it is explicitly `INSUFFICIENT_INTERIOR_EVIDENCE`. Achromatic classification is frozen at delta `<=18` and fraction `>=0.985`. No threshold changed.

## Aggregate results

- Fixed corpus: 22 sources; `{"APPROVED": 4, "N": 8, "P": 5, "PASS": 2, "QUERY": 1, "T": 2}` by control class.
- Components audited: 320 total, 245 frozen-achromatic.
- Comparison classes by corpus class: `{"APPROVED": {"achromatic_components": 56, "all_components": 70, "comparison_classes": {"BOTH_FALSE": 3, "FROZEN_TRUE__TOPOLOGY_FALSE": 6, "NOT_APPLICABLE_CHROMATIC_COMPONENT": 14, "TOPOLOGY_INSUFFICIENT_EVIDENCE": 47}}, "N": {"achromatic_components": 135, "all_components": 188, "comparison_classes": {"BOTH_FALSE": 17, "NOT_APPLICABLE_CHROMATIC_COMPONENT": 53, "TOPOLOGY_INSUFFICIENT_EVIDENCE": 118}}, "P": {"achromatic_components": 26, "all_components": 27, "comparison_classes": {"BOTH_FALSE": 13, "NOT_APPLICABLE_CHROMATIC_COMPONENT": 1, "TOPOLOGY_INSUFFICIENT_EVIDENCE": 13}}, "PASS": {"achromatic_components": 3, "all_components": 9, "comparison_classes": {"NOT_APPLICABLE_CHROMATIC_COMPONENT": 6, "TOPOLOGY_INSUFFICIENT_EVIDENCE": 3}}, "QUERY": {"achromatic_components": 16, "all_components": 17, "comparison_classes": {"FROZEN_TRUE__TOPOLOGY_FALSE": 3, "NOT_APPLICABLE_CHROMATIC_COMPONENT": 1, "TOPOLOGY_INSUFFICIENT_EVIDENCE": 13}}, "T": {"achromatic_components": 9, "all_components": 9, "comparison_classes": {"BOTH_TRUE": 2, "TOPOLOGY_INSUFFICIENT_EVIDENCE": 7}}}`.
- There were zero frozen-false → topology-true changes. The nine frozen-true → topology-false cases were #14700 components 4/12/13 plus four #3032 components and two #3072 components.
- 201 of 245 achromatic components had insufficient interior evidence under the frozen V23 evidence floor; the V26 rule therefore cannot safely make a positive tone decision for most segmented achromatic components in this sample.
- Achromatic component comparisons: `{"both_false": 33, "both_true": 2, "frozen_false_to_topology_true": 0, "frozen_true_to_topology_false": 9, "insufficient": 201}`. Per-component evidence is in COMPONENT-AUDIT.csv.

## Required control outcomes

- Genuine two-tone positives #T-NEOSAT and #T-DEMIR: frozen and topology-aware remain `two-tone=true` with sufficient interior; script hard-fails otherwise.
- #14700 components 4, 12, 13: frozen true → topology-aware not-two-tone, matching V23. Component 14 also has frozen `two-tone=true` but topology interior is insufficient; its WHITE low-contrast fraction is 6.67%, below the frozen 8% material fraction, so the frozen branch is a protected no-op and not a contrast target. The approved #14700 output remains specific to components 4/12/13; this does not establish broader rule safety.
- #14607/#14611: source hashes remain byte-identical duplicates; prior REVIEW/protected status is retained.
- #14593 remains incomplete-group REVIEW (14 blocked links and protected contacts); #14597 remains cautious gold/brand REVIEW. #14607/#14611 retain protected chroma/true-AA/ambiguous and incomplete-group blockers. #10954 is blocked at protected chromatic boundaries; #5136 retains its protected-boundary rejection. #11359/#14406 retain the prior finding that topology candidates did not establish a visually new repair. These independent dispositions are never overridden by tone statistics.
- Digi Slovakia: pinned V9 WHITE replay is `PASS`, changed pixels `0`. ProTV is included as a second earlier 0-change PASS fixture.
- The four old approval-ledger entries are classifier-only regression inputs; their prior approvals and outputs were neither changed nor visually reopened.

## Interpretation

V26 tests the component-level decision change on a small, curated but multi-class corpus. It does not replay complete Phase 4 ownership/grouping safety for every catalog case, and several controls intentionally carry external frozen blockers. This sample cannot establish false-positive/false-negative rates for a catalog-wide rule. Although both genuine positives were retained, 201 of 245 achromatic components had insufficient interior evidence and six already-approved monochrome control components changed from frozen true to topology false; this warrants broader independent, end-to-end qualification before integration. The target #14700 result was not used to select fixtures or tune thresholds. Genuine two-tone retention and zero-change PASS checks passed, but wider independent sampling and end-to-end safety qualification are still needed before considering generator integration.

## Invariants

Audit-only; generator not modified; thresholds unchanged; candidate/production picon writes = 0; templates/Masters/sources unchanged; #14599 untouched.

## Reproduction

`python tools/phase4_v26_topology_two_tone_generalization.py --repo-root . --phase3-generator tools/rebuild_master_catalog.py --white-master templates/picons/white-sablona.png --selection reports/warder-master-production/phase4-v26-topology-two-tone-generalization-20260927/CONTROL-SELECTION.csv --out reports/warder-master-production/phase4-v26-topology-two-tone-generalization-20260927`
