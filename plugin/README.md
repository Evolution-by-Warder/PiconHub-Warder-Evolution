# PiconHub Warder Evolution

The new futuristic rebuild has started on `plugin/futuristic-rebuild` after the verified Trezor backup. See [BUILD-STATUS.md](BUILD-STATUS.md), ../docs/CURRENT-STATUS.md and ../docs/PICONHUB-WORK-PLAN.md.

recovery/original-updater/ contains the exact historical 0.6.12.23 updater and two top-header graphics. These are genuine recovery inputs, not a complete runnable plugin. Preserve their bytes. New screen/function design and implementation are still pending.

The first core batch lives in `src/PiconHubWarderEvolution`. It reads the real catalog, selects exact packages and verifies download integrity. It has no Enigma2 entry point or installable IPK yet.

```sh
PYTHONPATH=plugin/src python3 -m unittest discover -s plugin/tests -v
python3 plugin/tools/check_catalog.py --selector 235E --resolution 220x132 --style transparent
```

Run these commands from the repository root. The inspector reads the live catalog unless `--file path/to/manifest.json` is supplied; it does not install anything.
