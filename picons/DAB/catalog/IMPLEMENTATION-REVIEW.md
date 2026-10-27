# Implementation checkpoint — 27 October 2026

## Completed locally

- Exact receiver mapping imported: 82 identities / 52 labels.
- Authentic sources selected: 80 identities / 51 labels, three styles.
- Corrected misleading upstream identities: ENERGY uses the official German NRJ logo; NOSTALGIE uses nostalgie-radio.de; national RADIO BOB! avoids the old Hessen tagline; OLDIE ANTENNE uses the national 80er/90er identity.
- Original transparent source assets and frozen MASTER frames preserved.
- Explicit component contrast fixes: Oldie (top wordmark on white), ERF Plus (Plus on white), ENERGY (slogan on white), AIDAradio (wordmark on black), Absolut CLASSICS (Absolut wordmark on black). Reviewed white monochrome NOSTALGIE/RADIO BOB! sources receive a consistent dark monochrome variant on white.
- ZIP integrity and installation connected to the existing background download, progress, cancellation and rollback flow.
- Existing startup update checker retained; startup/offline tests exercise it. No new blocking GUI network request added.
- New candidate release notes provided in all ten existing plugin languages.

## Publication authorized — 27 October 2026

The owner explicitly requested activation and production publication after accepting the corrected official-logo composition. `publication-approval.json` pins this authorization to the exact artwork manifest. ASA DE stays excluded. FullHDGlass radio picons in both infobars are confirmed by the owner. Physical receiver testing of PiconHub 0.1.26 is not claimed; automated and public-download checks are recorded separately.

The old sparse-checkout CI failure was fixed in 8342272ae218221fec07941e1b34c4d143f5f180; both workflows passed there. New runtime/artwork tests supersede the earlier placeholder-only checks.

## Owner correction — official logo identity

On 27 October the owner rejected substituting a different Absolut GERMANY wordmark on BLACK. GERMANY, BELLA, HOT and TOP 2000 now all use the exact same official circular source as their transparent/white versions, preserving the logo’s own white backing. No alternate wordmark is substituted to suit the master background. All station identities, source assets and contrast choices must remain official or explicitly owner-approved. The artwork generator also now emits source provenance for both upstream and official-site records; output metadata is checked in CI.

## Owner acceptance recorded — 27 October 2026

The corrected Absolut GERMANY sample and the same-official-source composition rule were accepted ("teraz je uz perfektne"). Acceptance is recorded in `catalog/owner-decisions.json`, the DAB README, artwork QUALITY.md and PR #11. BELLA, HOT and TOP 2000 follow this composition rule. The record does not assert visual review of the full 51-label catalog or a receiver test of 0.1.26.

FullHDGlass: the owner confirmed radio picons display in both infobars; the skin rendering issue is closed.

## Release scope

Activate the verified catalog and publish PiconHub 0.1.26 through the existing update feed. Preserve the three background styles, exact service-reference names, configured destination and existing picons outside package coverage. Production package hash and CI run are recorded in `plugin/production.json` after byte verification.
