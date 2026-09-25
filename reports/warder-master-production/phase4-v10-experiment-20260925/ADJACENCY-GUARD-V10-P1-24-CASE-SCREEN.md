# V10 component-mask follow-up — P1 screen 3 — 2026-09-25

## Scope

Screened 24 additional P1 mixed-logo review rows not present in the V8 or V9 screens, plus the unchanged PASS control. No repository picon output was written. The inputs came from the isolated branch archive at `c41547f15461a532e27fe8edca5482afb16cf46e`; comparison against current branch HEAD `b015bcb8a4af05619eaa3590e0c619455b4de0c4` confirms intervening commits changed only reports, checkpoint documentation, and unrelated approved picons.

## Safety result: failed

The prototype reported 20 REVIEW, 2 AUTO-FIXED, and 2 PASS among the 24 fixtures. The two PASS rows, #407 and #1009, use byte-identical transparent sources (`e271debb5a577149c00881c16ba5525ac872c51fe4ab63a47b6c04f54198d1c6`) and produce the same candidate (`840fbf2713188c87a5098fef0ceef15ad6e79f7b3a7d461ea698d68737305bbd`). Each candidate differs from its existing WHITE output in 5,487 pixels. The existing outputs for both destination paths are byte-identical (`e0940a92b71a550d43567c2911450d703c064bb868bcc6d858ceb2711b9e4679`).

Focused visual comparison of #407 shows the candidate leaves the neutral wordmark pale against the white master, while the existing output renders it dark and legible. The candidate is therefore a visible regression despite the PASS status. `#407` and `#1009` are duplicate destinations for the same source identity, not two independent source fixtures.

Alpha and protected chromatic pixels were unchanged in the pixel checks, but those assertions do not catch this neutral-text contrast regression. The PASS status is not a safe signal that an output matches or preserves the current result. This screen fails the V10 safety gate; do not apply these candidates or use the prototype for a rebuild.

## Audit and visual evidence

- `ADJACENCY-GUARD-V10-P1-24-CASE-SCREEN-AUDIT.csv` contains per-row paths, hashes, statuses, pixel differences, and preservation checks.
- `V10-P1-CASE-407-PASS-DELTA.jpg` compares the original, current WHITE output, and candidate classified PASS.
- The full 24-case contact sheet remains in the local test materials.

No candidate from this screen was applied. Approved batches and `main` remain unchanged.
