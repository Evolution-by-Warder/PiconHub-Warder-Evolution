# Phase 4 AA-boundary classification experiment

Date: 2026-09-26  
Branch: `phase4-v10-component-mask-test`  
Starting HEAD checked before experiment: `4ee40b608eaf5a43f8bd65aa8a60361197c9336b`  
Scope: #14607/#14611, #14700, #14593, cautious #14597, Digi Slovakia PASS control. Closed #14599 was not read or tested.

## Outcome

The classifier safely separated a small number of geometric-only achromatic contacts from the old one-pixel dilation ring, but it did not enable a complete wordmark repair on any original failure. Every failure candidate remains byte-identical to CURRENT WHITE and status `REVIEW`; the PASS control remains byte-identical with zero changed pixels. No production picons were written.

The most useful diagnostic is #14607/#14611: old boundary protection marked 822 pixels; only 4 had positive local AA evidence, 797 were uncertain and remain blocked, and 21 were classified as fully opaque geometric-only contacts. Those 21 pixels are shown cyan in the `RELEASED FROM OLD RING` panel. The achromatic wordmark components still touch ambiguous boundary pixels or chroma core, so the complete-wordmark guard emitted an empty edit mask. #14607 and #14611 were verified byte-identical for source, current WHITE, and candidate; the second row is only a duplicate regression check.

#14700 had 188 old boundary pixels: 2 true-AA, 186 ambiguous, and no pixels released. Ten contrast-relevant components failed the frozen two-tone gate; the full wordmark guard therefore remained REVIEW.

#14593 had 997 old boundary pixels: 14 true-AA, 952 ambiguous, and 31 geometric-only pixels released. Eleven contrast-relevant components remained unresolved across ambiguous AA, true-AA contact, two-tone, or exterior-alpha-topology guards. A partial repair was not emitted.

#14597 was included as a cautious brand/gold probe only. No candidate edit was emitted; existing gold/brand content was not promoted to editable status.

The Digi Slovakia control had zero changed pixels. Its boundary classified as 255 true-AA pixels and 1 ambiguous pixel; no candidate edit was proposed.

## Classifier and frozen rules

Pixel classes use only the fitted source RGBA pixels. Frozen V9 constants are retained: solid alpha floor 32, chromatic/achromatic channel spread delta 18, achromatic class fraction 98.5%, contrast ratio 2.50, material low-contrast fraction 8%, two-tone fraction 3%, and dark target `(16,16,16)`. The white MASTER SHA256 was verified as `c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589`.

The chromatic core is solid pixels with channel spread >18. The old boundary is the visible 8-neighbor dilation ring around that core. A ring pixel is classified as true chromatic AA only when its RGB differs from every adjacent chromatic-core pixel by no more than the frozen delta 18 **and** its alpha is lower than each adjacent core pixel. This requires both local color continuity and alpha attenuation. Low-alpha pixels remain ambiguous. Contradictory or incomplete evidence remains ambiguous. A pixel is released from the old ring only when it is fully opaque (alpha 255) and is not color-close to any neighboring chromatic-core pixel under the same frozen delta; being adjacent alone never makes an achromatic pixel protected.

A released pixel is not by itself permission to edit. The whole 4-connected achromatic component must also pass the existing contrast, two-tone, exterior-alpha topology, boundary-contact, and complete-wordmark checks. The cautious #14597 probe emits no edits. No positional or rectangle masks are used.

## Invariants

Across all six rows:

- edit-mask intersection with chroma core, true-AA, or ambiguous pixels: 0;
- alpha equality after the frozen fit: true;
- chroma core pixel equality: true;
- true-AA pixel equality: true;
- candidate-vs-current changed pixels: 0;
- Digi Slovakia PASS control: 0 changed pixels.

The complete audit, including hashes, component counts, guard results, and exact reasons, is in `AUDIT.csv`; machine-readable summary is `SUMMARY.json`.

## Artifacts

- `tools/phase4_aa_boundary_classification.py` — isolated reproducible runner; refuses output under `picons/`.
- `AUDIT.csv`, `SUMMARY.json` — measurements per fixture, including duplicate mapping.
- `COMPARISON-SHEET.jpg` — SOURCE | CURRENT WHITE | CANDIDATE for all distinct cases and PASS control; #14607/#14611 grouped once.
- `masks/*-MASK-CLASSIFICATION.jpg` — SOURCE | CHROMA CORE | OLD DILATED PROTECTED | NEW TRUE-AA PROTECTED | NEW AMBIGUOUS | RELEASED FROM OLD RING | EDITABLE ACHRO CORE | CANDIDATE.
- `comparisons/*-SOURCE-CURRENT-CANDIDATE.jpg` — focused per-case comparisons.

No source, current output, MASTER, plugin, skin, Phase 3 checkpoint, or `main` content was changed. This experiment does not approve a production algorithm or any candidate.
