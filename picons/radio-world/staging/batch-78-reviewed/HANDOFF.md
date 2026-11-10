# Radio batch 78 — completed; continue with batch 79

Date: 2026-11-10. Audit checkpoint: 596526ab7e0c865c4cc0095cda8235405c2d8433.
Working branch: work/radio-world-batch38-contrast-pass1-history-20261107.
PR #68 remains open, Draft and unmerged.

## Verified totals

- 3,428 / 35,560 country references; 32,132 remaining.
- 31,428 PNG instances including aliases.
- 131 / 219 countries covered.
- Batches 01–78 are completed. Do not reprocess or re-audit them.

| Batch | Added references | Added PNG | New ZIP versions | Country | Audit checkpoint | CI run |
|---|---:|---:|---:|---|---|---|
| 77 | 1 | 9 | 9 | GR | 892f95133fe17c24f2baaba1cf69659f70682be3 | 42816797328 |
| 78 | 1 | 9 | 9 | GR | 596526ab7e0c865c4cc0095cda8235405c2d8433 | 42817446888 |

## Completed identities and assets

77: Amore 87.5, Chania. The official radioamore.gr player names the approved HTTPS endpoint. Provider playlist evidence and an exact 32,768-byte compressed-audio overlap bind the candidate stream. The existing approved logo explicitly shows Amore 87.5 and Chania.

78: Radio Lefkimmi 105.5. The named HTTPS proxy's public status-json API explicitly reports the approved source http://i3.streams.ovh:12006/live. The direct source API corroborates the mapping, and 65,536 compressed-audio bytes match exactly. The approved logo explicitly shows Radio Lefkimmi 105.5.

All nine existing approved variants were copied byte-for-byte for each reference. Zero renders or artwork alterations.

Each completed batch has exactly one successful final independent audit on a separate runner, downloading its actual new ZIPs and checking SHA256, CRC, every old/new member hash, dimensions, RGBA and exact approved PNG/git-blob bytes. Exact bytes preserve alpha. Source readback also records alpha extrema. Stable downloader replay covered only GR. No physical receiver test was performed.

78 audited build: 3dd8396d6c2b53e04236ae279927480af3c2b9f0.
78 payload: ee4f6ac306fd14c8f612386d0f0931480b01df45.
78 immutable manifest commit: 34856ef73fe3eb6db605cc2052f073a26ff3a3f6.
Payload branch: work/radio-world-batch43-reviewed-payload-20261107.
Candidate index: countries.proposed.json.
Audit: results/independent-postwrite-audit.json.
ZIP checksums: SHA256SUMS.txt.

## Preserved boundaries and holds

All earlier candidate PNGs remain intact, as do all 31,329 activated-production PNGs, including the original 10,332 protected subset. All 923 configuration blocks and historical holds remain in force.

Production main 59ec70708d4d05a28f17c741742c78451d4fc45b and its index/packages were not modified. Production index SHA256: a70036892456d105ae2844a715f462eac1b87aef16769c57c7a9699b1cfac2b1. Stable Radio, IPK and update feeds were not changed. Main Radio remains 527493e36246bd98c9640365ca6794f814fc4149. Results are staging-only and may be activated separately later; no activation or merge is authorized here.

Initial batch77 prebuild failed on an existing Palmos historical hold BEFORE any PNG/ZIP write. The amended selection excluded both Palmos comparisons and completed successfully. Preserve ../batch-77-reviewed/source-inputs/deferred-palmos.json: matching provider/audio identifies the current 93.4 stream but does not resolve the historical 102.7 catalogue versus 93.4 artwork conflict. No hold was overridden.

Lemon Radio and Lemon 88.8 are separate identities. Identical account-like text radio888 on different providers is not a binding. Preserve the deferred decision.

## Continue batch 79

Batch79 is NOT completed and has no new PNG/ZIP payload yet. No further safely confirmed alias remains in the groups inspected during this work; the whole 32,132-reference backlog is NOT exhausted.

Read results/next-source-observations.json and results/unreviewed-discovery-pool.json:
- 184 remaining broad-name comparisons are unreviewed suggestions, never approvals.
- Nine fresh streams.ovh named-proxy APIs were resolved; none mapped to an existing approved country reference. Their exact source mappings are saved.
- Codec/mount normalization across Infomaniak, Triton and Radio France yielded no additional eligible comparison.
- Expanded account/mount matching across Radio.co, Revma, Radiojar, Zeno and Radioking yielded none.
- Unordered name tokens preserving numbers yielded none.
- Distinct Italian provider ports 8144/8009 versus 8621 do not justify PRL/Stereo5 → Antenna Verde artwork.
- FM Life 105.3 versus Radio Madness is unconfirmed; sharing port8044 on different hosts is insufficient.
- Previously deferred Vibra, Nostalgie, 80s80s, Divina and Valentina resurfaced only as name suggestions; their failed endpoint checks were NOT repeated.

Continue with another independent country/provider or approved-artwork group. Consult historical ledgers BEFORE network work and selection, not only configuration holds. Every target must exist in cfg.world's frozen country catalogue; current receiver data is corroboration only. Retain significant ports, service IDs, frequency/region/brand distinctions and query routing. Never persist query-token values. See batch76 for older frontier and Millenium/Arab Mix/Merakia exclusions.
