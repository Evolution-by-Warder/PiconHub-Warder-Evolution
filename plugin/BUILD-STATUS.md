# PiconHub Warder Evolution — rebuild started

Date: 2026-10-23. Working branch: `plugin/futuristic-rebuild`.

The owner authorized starting the new futuristic plugin after the verified primary backup was completed in private Trezor: `backup-20261023-verified` (38 assets). The attempted additional Library copy timed out and is not claimed as a saved independent copy. The primary archive includes the preceding project histories and documentation.

## First working batch

- New Python 3 core, separate from the preserved original updater and historical plugin branches.
- Read the actual skin-hosted channel catalog, schema 1 and raw GitHub parts.
- Exact satellite/provider selector, resolution and background selection. No silent fallback to a different package.
- Validate package and part SHA256, sizes, complete ordered parts, expected download URLs and unambiguous selections.
- Bounded-memory content verifier for damaged, truncated or oversized downloads.
- Read-only command-line catalog inspection. No receiver paths are written and no archive is installed.

The inspected real catalog contains 468 packages and 53 distinct selector IDs. Selector IDs include provider bundles and split satellite choices; they are not a count of satellite positions and do not define the future menu. Historical packages remain readable without automatically offering them in the UI. Three historical 45°W entries omit PNG count; this is retained as unknown rather than invented or treated as an empty package.

Local validation: nine unit tests; all 468 selections checked against the real catalog; live manifest read; a real 45°W package downloaded with part and whole-archive SHA256 checked. CI results are separate evidence.

## Current direction — owner clarification, 2026-10-23

Retain the functional Chocholousek base and modernize its interface as PiconHub Warder Evolution. This explicitly supersedes the preceding from-scratch runtime direction. The separately implemented catalog core remains available as a future Warder-source adapter.

The original upstream 5.0.240904 source was statically reviewed. The historical migration branch is a workspace skeleton, not a complete preserved runtime. See design/CHOCHOL-WARDER-INTERFACE.md for exact source identity, the proposed four-screen interface and required integration changes. New Enigma2 screens, upstream import and receiver validation remain pending.

This is a core development checkpoint, not an installable Enigma2 plugin or a receiver-tested release. No IPK has been published. Original recovered asset bytes and production picons remain unchanged.
