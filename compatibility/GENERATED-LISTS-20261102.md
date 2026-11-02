# Superseded by the complete GLES/WQHD candidate — 2 November 2026

The follow-up source changes and isolated receiver candidate are documented in GLES-WQHD-20261102.md. The previous remaining CAM/OSCam work below is now included there. Production feeds remain unchanged.

---

# Generated plugin list fixes — 2 November 2026

These are new source changes after the 1 November compatibility work. FullHDGlass 1.0.61 remains the production skin; 1.0.62-test1 is unchanged. This branch is not a published plugin release and does not change installed versions, production feeds, package identities or artwork.

Lists now end on complete rows calculated from the actual rounded pixel row height. Merely shrinking the font does not remove a partly visible extra row. Tests cover 1280×720, 1366×768, 1920×1080, 2560×1440 and 3840×2160; main/settings/popups also cover 1920×1200. These checks validate generated XML and Python controllers, not physical receiver/GLES rendering.

History implements the owner's pending request: five installed version entries with at most two description lines each. Localized text and English fallback are retained; the complete source notes file is untouched.

## Changed behavior

- Choice and directory popups formerly allocated `20 + n*60` reference pixels for `n` 60-pixel rows (500/60 for eight rows). They now allocate exactly n rounded rows. Empty lists retain a usable empty viewport.
- The embedded picker now allocates seven rounded rows instead of rounding their total independently (at 1366×768: formerly 299 pixels against 43-pixel rows; now 301).
- The update confirmation list now scales its row height as well as its font and viewport, and fits exactly three rows (FHD 150/50, HD 99/33).
- Text/progress ScrollLabel pagination retains its separate existing behavior.

## Verification

217 plugin tests pass locally. The existing OpenATV export/controller guard passes against official `8.0-next` commit `da455f57dda38b5f0de0744c913ee2270b7dc2ba` (32 exports, 25 contracts). CI additionally runs the complete suite on Python 3.9 and 3.14 alongside the existing stable 8.0 / 8.0-next / master interface matrix.

## Remaining scope

The AST binding audit still lists dynamic/generated controllers separately. Geometry and controller regression tests do not turn those unresolved fields into verified native source/GUI bindings. A uniquely versioned receiver candidate and receiver acceptance are still required before a functional release.
