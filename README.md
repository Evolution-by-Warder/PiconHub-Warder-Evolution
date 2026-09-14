# PiconHub-Warder-Evolution plugin

This directory contains the new Enigma2 plugin code for PiconHub-Warder-Evolution.

Direction:
- preserve the proven Chocholousek Picons GUI/workflow where practical;
- modernize and harden the backend incrementally;
- use this repository's `picons/` tree as the future PiconHub data source;
- keep plugin code and picon data in one project, but clearly separated.

Current layout:
- `src/Plugins/Extensions/PiconHubWarderEvolution/` — Enigma2 plugin package
- `src/Plugins/Extensions/PiconHubWarderEvolution/core/` — backend modules
- `src/Plugins/Extensions/PiconHubWarderEvolution/resources/` — plugin images/assets
- `src/Plugins/Extensions/PiconHubWarderEvolution/locale/` — translations
- `packaging/` — IPK/DEB packaging metadata and scripts

The original Chocholousek package remains the technical reference; attribution and licensing are preserved in `UPSTREAM.md`.
