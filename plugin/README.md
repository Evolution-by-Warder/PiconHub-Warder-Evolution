# PiconHub Warder Evolution

Current direction: retain the functional Chocholousek Picons base and give it a modern Warder interface. The owner clarified this direction on 2026-10-23, superseding the earlier plan for a new runtime from scratch.

[Code review and interface proposal](design/CHOCHOL-WARDER-INTERFACE.md) records the actual upstream source, preserved behavior, screen mapping and required integration work. The proposal is not an implemented Enigma2 screen or a receiver-tested release.

The historical migration branch contains a workspace skeleton, not a complete runtime. The reviewed original source is s3n0/e2plugins, ChocholousekPicons, version 5.0.240904. Preserve attribution and compatibility with the existing configuration and runtime directory.

recovery/original-updater/ contains the genuine historical Warder 0.6.12.23 updater and two headers. Preserve their bytes.

src/PiconHubWarderEvolution contains the separately implemented Warder catalog reader and integrity checks, available for future source-adapter integration. It does not replace the Chocholousek runtime or make the plugin installable yet.

```sh
PYTHONPATH=plugin/src python3 -m unittest discover -s plugin/tests -v
python3 plugin/tools/check_catalog.py --selector 235E --resolution 220x132 --style transparent
```

Run these commands from the repository root. The inspector reads the live catalog unless --file is supplied; it installs nothing. Main, production data, preserved branches and the verified Trezor backup remain unchanged.
