# Audited picons/picons assimilation — 30 October 2026

Owner instruction: “laska zober co nam chyba aleb osa nam hodi a asimiluj to do nasho standardu.”

The publication plan covers 70 missing service identities and 117 exact service-reference filenames, corroborated against the 30 October Vhannibal Motor setting. The reference list includes the release's type-1 lookup and the actual current-setting service type where different. These are not 117 new stations.

50 logos reuse the exact existing Warder PNGs, including all three approved backgrounds, from SHA256-verified current public archives. 13 additional upstream logos are normalized to our three styles. In total this provenance contains 63 logical graphics and 189 base PNGs at 220×132. Publication also produces the existing 50×30 and 400×240 variants with premultiplied-alpha proportional resizing.

Upstream: picons/picons release `2026-10-25--00-12-17`. The original light and dark tarball SHA256 values, preserved source PNGs, SVG originals for Metro TV/Sport 24 Extra, canonical source hashes, settings and catalogue hashes are in `publication-plan.json`. Upstream artwork authorship is retained; no artwork is claimed as newly designed by Warder.

## Quality and contrast

All new base outputs were visually reviewed together at native proportions on Transparent, WHITE and BLACK. WHITE and BLACK use the exact frozen MASTER files. Original branded badges are retained for MAX One, Kartoon Channel, Al Qamar and Pame Stoixima Racing. BBC HD uses the permitted complete monochrome inversion, preserving alpha and layout.

Every contrast correction uses a separately frozen and reviewed per-logo PNG component mask. Metro TV uses only the six verified SVG wordmark paths and preserves the entire bird emblem. Sport 24 Extra preserves the yellow paths, including their antialias pixels. Sahel TV preserves its orange symbol; Prime preserves its turquoise elements; Quran radio preserves its coloured petals. The masks are explicit inputs, not darkness thresholds. `generate.py` checks all untouched foreground RGBA pixels, alpha, MASTER hashes and every output PNG hash. It performs no automatic mask discovery.

`source/` preserves received originals and inputs; `artwork/{transparent,white,black}/` contains the exact prepared outputs. `quality-review.png` records the reviewed 13-logo sheet. Run `python generate.py` with Pillow 12.3.0 to reproduce all 189 pinned outputs without network access.

## Exclusions and publication scope

Nine audited rows remain excluded, with exact reasons in the plan: five suspicious station/logo associations, two MTNINFO transport-information services, one technical UHD demo, and the ambiguous CCTV4 America regional/badge case. The latter must not receive a guessed regional logo or a different badge merely for background contrast.

Only missing references are appended. Existing PNGs are checked byte for byte and are never replaced. Satellite package membership follows the current verified service identity. No unverified provider membership, terrestrial or IPTV mappings are inferred. Shared downloaded data serve both PiconHub and FullHDGlass; receiver Python, IPK versions and updater logic do not change. Trezor is outside the scope and was not accessed.
