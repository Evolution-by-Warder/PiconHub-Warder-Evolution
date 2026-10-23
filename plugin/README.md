# PiconHub Warder Evolution

Functional base: Chocholousek Picons 5.0.240904 by s3n0, imported from upstream ref 84a40ed6b01f8dc7d49b632f886525b9c51773c7 into src/Plugins/Extensions/ChocholousekPicons. Attribution, the runtime directory and existing profile settings are retained. Exact provenance is recorded in UPSTREAM.json.

The original four-screen runtime is now present in this development branch. The historical migration branch remains a skeleton; the new source was imported from upstream, not recovered from that skeleton. The modern Warder screen and picker design are still pending implementation.

Implemented: an asynchronous plugin update check on every new main-screen launch, an update offer, verified IPK staging and user-confirmed installation. See [STARTUP-UPDATES.md](STARTUP-UPDATES.md). The development release feed has no offered IPK; no plugin release is being claimed as published. Receiver testing remains pending.

The independent Warder catalog adapter remains in src/PiconHubWarderEvolution for later picon-source integration. It does not make the original engine consume Warder ZIP packages yet.

recovery/original-updater contains the genuine historical Warder updater and headers. Their bytes remain preserved.

```sh
PYTHONPATH=plugin/src python3 -m unittest discover -s plugin/tests -v
python3 plugin/tools/check_catalog.py --selector 235E --resolution 220x132 --style transparent
```

Run from the repository root. The catalog inspector installs nothing. The new plugin package itself is not yet built or published.
