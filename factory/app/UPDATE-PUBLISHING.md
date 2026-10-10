# WARDER Factory automatic updates

The launcher checks `https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/main/factory/update/manifest.json` at each startup. The manifest is **not yet published**. Until it is published, the installed Factory starts offline-safe.

Publish a Factory-only ZIP as a GitHub Release named `factory-vX.Y.Z`, with asset `warder-picon-factory-X.Y.Z.zip`. The ZIP root must directly contain `engine.py`, `factory_launcher.py`, `requirements-runtime.txt`, `.factory-version.json`, and the remaining application code. Calculate the ZIP SHA-256 and exact byte size, then commit the manifest to `factory/update/manifest.json` only after explicit user approval. Schema: `{"schema":1,"version":"factory-vX.Y.Z","url":"https://github.com/Evolution-by-Warder/PiconHub-Warder-Evolution/releases/download/factory-vX.Y.Z/warder-picon-factory-X.Y.Z.zip","size":123456,"sha256":"<64 hex>"}`.

No GitHub write is performed by the launcher. Updates swap application code only, preserving `01-SOURCES`, `02-ORIGINALS`, `04-WORK`, `05-QA`, `06-OUTPUT`, `08-REPORTS`, the SQLite database and mutable state under `11-APP/.factory-data`, which are migrated from the previous application folder before any update is activated.
