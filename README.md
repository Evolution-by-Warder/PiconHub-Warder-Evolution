# PiconHub-Warder-Evolution

PiconHub-Warder-Evolution is an Enigma2 picon project combining the PiconHub picon database with a modernized plugin while preserving the proven workflow of the original Chocholousek Picons plugin.

## Origins and credits

This project builds on the work of two important contributors:

- **Chocholousek** — creator of the original picon sets that form the historical foundation of this project.
- **s3n0** — creator and maintainer of the original **Chocholousek Picons** Enigma2 plugin, which provides the technical and GUI/workflow foundation for the new PiconHub-Warder-Evolution plugin.

Their original work and authorship are respected and preserved. PiconHub-Warder-Evolution is an evolution of that foundation, not an attempt to erase or replace its history.

## Direction

- preserve the proven Chocholousek Picons GUI/workflow where practical;
- modernize and harden the backend incrementally;
- use this repository's `picons/` tree as the future PiconHub data source;
- keep plugin code and picon data in one project, but clearly separated.

## Current layout

- `picons/` — PiconHub picon database
- `plugin/src/Plugins/Extensions/PiconHubWarderEvolution/` — Enigma2 plugin package
- `plugin/src/Plugins/Extensions/PiconHubWarderEvolution/core/` — backend modules
- `plugin/src/Plugins/Extensions/PiconHubWarderEvolution/resources/` — plugin images/assets
- `plugin/src/Plugins/Extensions/PiconHubWarderEvolution/locale/` — translations
- `plugin/packaging/` — IPK/DEB packaging metadata and scripts

The original Chocholousek Picons plugin remains the technical reference. Detailed upstream attribution and licensing information is preserved in `plugin/UPSTREAM.md`.
