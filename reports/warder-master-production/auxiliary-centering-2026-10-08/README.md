# Auxiliary candidate centering checkpoint

Candidate-only checkpoint on the auxiliary review branch. It stores translated versions of the existing 173 identity / 346 variant PNG set. The content renderer was not run. Only integer translation of each already-rendered foreground RGBA layer was applied. Transparent source masters remain pinned and unchanged.

Each translated layer must reverse-translate and composite against the pinned Warder template to reproduce the original candidate PNG byte-for-byte at the pixel level. Items that cannot satisfy exact round-trip, center tolerance, safe area, or clipping checks remain unchanged and are marked `CENTERING_REVIEW`.

See `centering-audit.jsonl`, `summary.json`, `sha256-manifest.jsonl`, `provenance.json`, and `verification-sheets/`.
