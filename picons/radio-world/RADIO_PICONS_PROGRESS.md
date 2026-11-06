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

## Batch 23 country packages, 2026-11-06

The [offline builder](prepare_country_packs.py) builds 54 candidate ZIPs for AR, DE, GB, SE, UA and US from the checked-in staging ZIPs. It verifies the exact country, service reference, station name and stream URL against the pinned Radio catalogue. Germany starts from the verified DE r3 release and preserves all 90 existing PNG members per variant. Two independent builds produced identical output. The [candidate checksums](staging/batch-23/country-pack-checksums.json) record every archive and input pin.

To reproduce, save the pinned [world search snapshot](https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/blob/e90a1fe3a2734b555f48f343284f9103530180fb/picons/IPTV-SK-CZ/catalog/global/search/2ae88890a953c2f68d3f20352ad56a7390645bd3ce189573dd94e50c8a65abfe.json.gz) as `world.json.gz` and the pinned [DE r3 manifest](https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/blob/e90a1fe3a2734b555f48f343284f9103530180fb/picons/IPTV-DE/catalog/release.json) as `de-release.json`. Save the nine ZIPs at the manifest's URLs under `de-packages/` with their original basenames. From the repository root, with Pillow installed:

```sh
python picons/radio-world/prepare_country_packs.py \
  picons/radio-world/staging/batch-23 world.json.gz de-release.json de-packages candidate
```

The output contains the package layout expected by the downloader and a local inventory with every PNG hash. The build does not write live release manifests. The checked-in ZIP checksums describe the validation build. Compression library versions may affect ZIP hashes while the member SHA-256 values remain unchanged.

The existing downloader passed its 29 unit tests. A local integration run used the pinned country catalogue snapshots and candidate packages through a test endpoint for all three 220×132 styles. It installed 64 existing German catalogue matches, added nine new matches across six countries, preserved a user override and all previous index entries, then repeated without downloading the ZIPs. The live menu and packages were outside this staging test. The remaining integration step is to expose the additional country collections in the Radio UI alongside a separately approved package publication.


## Universal country availability and batch 26, 2026-11-06

The work branch `work/radio-world-batch26-20261106` combines batches 24 and 25 in
country payload commit `64aff3cd` and pinned release commit
`c33c3cb33c4fc32682ca5dc1c4ad1933bdb96803`. Both deterministic builds passed. All 99
previous PNG members per complete nine-variant inventory were preserved, with 20
incoming references producing 119 files per variant across the six collections.

`build_country_index.py` creates the complete 219-country structure from the live
catalogue. Availability is computed from exact references common to all three
220×132 background inventories. Unpublished countries are explicit; the HDF
source view is separate. The plugin consumes this index without requiring a new
IPK when another country's packages become available. 50×30 and 400×240 packages
remain preserved in GitHub, while the receiver downloads only selected 220×132
backgrounds. The working index must not be described as a live published feed.

Batch 26 revisited 219 raster-source candidates from the unresolved retry and
stages nine newly evidenced references (Chile, Greece, Lithuania, Romania,
Sri Lanka, the United Kingdom and three in the United States). The source plan
records nine originals, exact streams, receiver references, catalogue identities,
current broadcaster page hashes and 210 held candidates. No overlap was found
with batches 23–25 or the recovered 11,846-reference historical seed. The complete
checkpoint-22 union remains unavailable; no global historical total is invented.

The original Gavdos/Skai affiliate banner stays whole. UrbanUP uses the current
2026 player mark. KVKVI uses the current broadcaster player cover, while its
unrelated old favicon is rejected. KCRW Eclectic24 is evidenced by the official
`e24_aac/playlist.m3u8` declaration for the same catalogue stream endpoint.
Redirected or mismatched CNN Salta, OpenSky, NRW1, MandalayFM, La Q, Fiebre Latina,
PabloMix and Tailgate candidates remain held. The approved Warder masters and
192×104 artwork bounds are unchanged. All nine local variants passed SHA-256,
CRC, RGBA, dimensions and exact-inventory checks, and 220×132 styles were viewed.

The branch-only build records the frozen originals, nine batch ZIPs, country
inventories and immutable downloader release/index pins. Production publication,
plugin merge and the IPK release require the owner's explicit approval.
