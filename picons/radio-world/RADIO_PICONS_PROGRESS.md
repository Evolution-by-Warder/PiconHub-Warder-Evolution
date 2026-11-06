# Warder Radio picons

## Checkpoint 2026-11-06

- PiconHub main and live country catalogue were pinned to `e90a1fe3a2734b555f48f343284f9103530180fb`. Warder Radio main was `349fd7ec25e3f7979cb28b8dab0ed5f3fbf2434b`. FullHDGlass main was `2079d56bb8f3337d2196d055ea3938952dc91077`.
- The live catalogue has 40,903 unique service references across 219 country groups and the separate HDF source group. The plugin bundles an earlier snapshot of 40,905 rows. The live catalogue was used for this batch.
- The five live Radio package manifests cover 464 exact current catalogue references across all nine variants, including 14 in the HDF source group. [coverage.json](coverage.json) records per-group catalogue counts, published matches, batch 23 matches and unresolved items found in the latest retry. These country counts omit the historical unpublished checkpoint. The five actual 50×30 transparent ZIPs were independently downloaded and matched their release manifests by archive SHA-256, CRC, inventory and every member SHA-256.
- The previous [reconciled batch 22 checkpoint](https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/blob/4dd8220efc5180db9e0fca56335b4a01b9193558/migration/radio-reconciled-checkpoint-20261105/summary.json) reports 19,756 prepared references and 177,804 PNGs. Of these, 19,706 were in its main catalogue and 21,197 catalogue references were still missing. The complete ready inventory and ZIP payloads referenced by that summary were not found in the checked Git tree or the available files. The totals here are kept separate until an exact union can be computed.
- The newer [catalogue artwork retry](https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/blob/89a1c6a59caab6110c2f160e852c441cb409eac3/migration/radio-current-metadata-refresh-20261105/results/transient-network-retry/discovery-state.json) lists 659 unresolved rows, including 16 with recovered candidate artwork. Batch 23 resolves nine of those 16. Seven have explicit identity or branding holds. The retry's remaining 643 rows still lack a usable confirmed source.
- The existing Poland, Austria and Germany sources and previously approved Antenne Kärnten, radio3 and ESKA ROCK work were preserved. Existing editorial holds for Kossuth, Radio 88 Retro / REPLAY and regional ESKA 2 remain tracked in the prior evidence.

## Batch 23

[Staging manifest and package checksums](staging/batch-23/manifest.json). The white 400×240 variant is split into two disjoint ZIP parts. The manifest contains broadcaster evidence, SHA-256 of each source, service reference, catalogue ID, per-member digests and the seven held cases.

| Country | References | PNGs |
|---|---:|---:|
| Argentina | 2 | 18 |
| Germany | 1 | 9 |
| Sweden | 1 | 9 |
| Ukraine | 1 | 9 |
| United Kingdom | 2 | 18 |
| United States | 2 | 18 |
| Total | 9 | 81 |

The approved 220×132 black and white master PNGs were used with the same centred 192×104 artwork bounds and Lanczos resizing as the previous Radio checkpoint. NTS 1 and 2 share the broadcaster logo under distinct service references. KAUH uses the current higher-resolution original of the same logo from its broadcaster. CNN Radio Salta is held because the transmitter is now branded LUP Radio and the catalogue identity needs reconciliation.

Verify the nine variants with Pillow installed, from the repository root.

```sh
python picons/radio-world/verify_batch.py picons/radio-world/staging/batch-23
```

## Integration status

All ten ZIPs passed the staging verifier and the 220×132 variants were visually checked against the selected station sources. The plugin's 29 downloader unit tests passed. A local integration run using pinned country catalogue packages and an injected staging endpoint installed, looked up and skipped on retry all nine references for each of the three 220×132 styles.

The ZIP members use the plugin's exact Enigma2 reference filenames. The current downloader still exposes only SK, CZ, AT, DE, HU and PL at 220×132. Batch 23 is staged across countries. A deployment requires splitting the staged inventory into country packages or adding a catalogue-driven shared package feed in the plugin, preserving all existing country entries and graphics. No production Radio releases or satellite manifests were written.
