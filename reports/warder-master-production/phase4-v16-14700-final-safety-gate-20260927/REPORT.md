# Phase 4 — #14700 final safety gate

**Result: TWO-TONE FALSE POSITIVE RESOLVED / CANDIDATE STILL BLOCKED BY low-alpha perimeter ownership.** No candidate was generated.

## Gate evaluation

- **wordmark_group_complete: PASS** — The single proposed group contains all contrast-relevant components; members=[6, 7, 8, 9, 10], reconstructed group pixels=1224.
- **topology_aware_two_tone: PASS** — Topology interior=307 px, dark=0, light=307; result=not-two-tone. Frozen result remains two-tone=True and is replaced only for this decision.
- **sufficient_interior_evidence: PASS** — 307 interior px versus frozen V9 material evidence floor 12.64 px.
- **exterior_master_context: PASS** — Existing exterior-alpha topology result=True; no topology rule changed.
- **chromatic_core_contact: PASS** — Perimeter contact=False; candidate/group intersection=0 px.
- **confirmed_chromatic_AA_contact: PASS** — Perimeter contact=False; candidate/group intersection=0 px.
- **ambiguous_boundary_contact: PASS** — Perimeter contact=False; candidate/group intersection=0 px.
- **protected_link_blockers: PASS** — Frozen grouping reports 0 blocked links in this group.
- **low_alpha_perimeter_ownership: REVIEW** — 300 visible alpha<32 pixels directly touch the full proposed wordmark perimeter. Frozen AA ownership rules do not prove these pixels belong to the wordmark; ownership/perimeter guard remains active.
- **contrast_adaptation_required: PASS** — Frozen V9 contrast ratio 2.5; low-contrast fraction=0.837383, material fraction floor=0.080; target RGB verified from frozen generator constant [16, 16, 16].
- **edit_mask_complete: REVIEW** — The core plus 154 previously proven tonal attachments forms the candidate group, but adjacent alpha<32 edge ownership is unresolved, so natural AA-complete ownership cannot be certified without changing a frozen guard.
- **edit_mask_intersects_protected: PASS** — Intersections with chroma/true-AA/ambiguous masks are {'chromatic_core': 0, 'confirmed_true_AA': 0, 'ambiguous_boundary': 0}; all must be zero.

## Decision

The topology-aware guard returns `not-two-tone` with 307 interior pixels (dark 0, light 307); evidence sufficiency passes. The complete group contains 1224 pixels (1070 solid core + 154 already proven tonal attachments), and all chromatic/true-AA/ambiguous intersections and grouping blockers are zero.

The independent frozen low-alpha ownership/perimeter check finds **300 visible alpha<32 pixels directly adjacent to the proposed full wordmark**. Their ownership is not proven by the frozen AA classifier. Since the experiment permits changing only the two-tone decision, this ownership guard remains a REVIEW blocker. The edit mask cannot be certified complete while those edge pixels remain unresolved. No recolor candidate or candidate PNG was created.

Target RGB is imported from the frozen V9 generator constant: `(16,16,16)`. It was not used because the candidate gate did not pass.

## Regression controls

Both genuine two-tone positive controls remain `two-tone=true` and receive no candidate. #14593 remains REVIEW (incomplete, protected contact, 14 blocked links). #14607/#14611 remain frozen negative controls with no reconstruction. #14597 remains cautious REVIEW with no target. Digi Slovakia remains PASS with zero changes.

## Preservation

`editable_pixels=0`; candidate changed pixels=0 (no candidate exists); production PNG writes=0; source and MASTER were read-only. Protected mask and geometry were not modified.

## Visual diagnostic

See `diagnostics/14700-final-gate-blocker.jpg` for SOURCE, CURRENT WHITE, complete wordmark mask, protected mask, and the low-alpha blocker mask.
