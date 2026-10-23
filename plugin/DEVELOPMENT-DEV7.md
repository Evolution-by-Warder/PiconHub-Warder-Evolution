# PiconHub Warder Evolution 0.1.0-dev7

Replace the former settings heading/profile area with "Posledné pridané picony"
and six genuine recent logos, horizontally arranged. Retain dev6's single visible
configuration, improved selection contrast and colors, and the live smaller seconds.

The strip uses added transparent PNG paths from the main source repository's Git
history. It does not mistake modified files, white/black variants or identical
Git blobs for new additions. Bundled thumbnails are byte-for-byte source PNGs;
images/recent/sources.json records their exact source paths, commits and Git hashes.
The reproducible seed tool is plugin/tools/build_recent_seed.py.

Startup shows the bundled six immediately, then checks the GitHub API in a separate
worker. The bounded scan examines at most eight recent picon commits and the first
100 files of each. Previously known actual additions fill the strip if fewer than
six are found. This is a recent-additions gallery, not a full historical index.

Downloaded PNGs are checked against their reported Git blob SHA and bounded in size
and dimensions. Requests use verified HTTPS and immutable commit-based asset URLs.
The cache holds gallery thumbnails under /var/cache/piconhub-warder-evolution/recent,
independently of the configured picon installation folder. Refresh is throttled to
30 minutes to respect anonymous API limits; offline/API-limit failures retain the
last valid cache or bundled genuine additions. No picon install is triggered by
the gallery. Worker results reach widgets only on the existing GUI timer, and
closed screens discard late results.

65 tests pass: recent-source selection, duplicate exclusion, network/cache/offline
behavior, corrupt/oversized data, GUI-thread display and closed-screen lifecycle,
six bundled images in the built IPK, existing update and rollback tests, and HD/FHD
layout bounds. A live network check returned six verified thumbnails into a
temporary cache. Local layout review uses the actual native XML; the final
appearance still requires receiver confirmation.

```sh
opkg install /tmp/enigma2-plugin-extensions-piconhub-warder-evolution_0.1.0-dev7_all.ipk
```

Restart the GUI through the receiver menu after successful installation.
