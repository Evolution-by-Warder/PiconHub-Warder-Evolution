# PiconHub Warder Evolution

Modern continuation and evolution of the Chocholousek Picons ecosystem for Enigma2, maintained by **Warder**.

## IMPORTANT: two separate PiconHub projects

There are **two independent PiconHub development lines**. They must never be mixed together in code, graphics, package versions, checkpoints or development decisions.

### 1. PiconHub — original Warder project

This is Warder's independently developed PiconHub plugin with the **new futuristic PiconHub graphics/UI** and its own functionality. Its development history includes the `0.6.x` / `0.7.x` line (for example `0.7.0-dev3`).

This project is **not** the s3n0/Chocholousek modernization line.

### 2. PiconHub Warder Evolution — THIS repository

This repository is the modernization/evolution line based on the original **Chocholousek Picons Enigma2 plugin by s3n0**, with the `5.0.240904.x` package line.

For this line, the approved original graphics, GUI layout and established structure are **LOCKED**. Development may modernize code, compatibility, functionality, reliability, backend behavior and packaging, but must **not** independently redesign, replace, reposition or reorganize the locked graphics or structure.

**Never use screenshots, graphics, package versions or UI decisions from the separate futuristic PiconHub project as the design authority for PiconHub Warder Evolution.**

## Project status

This repository is the official home of **PiconHub Warder Evolution**.

The project combines an Enigma2 plugin with the PiconHub picon repository and continues development while preserving the approved visual identity, graphics and runtime structure.

### Current development work

- maintenance and modernization of the Enigma2 plugin
- expansion and quality control of the picon database
- provider and satellite-position organization
- BLACK / WHITE / transparent picon standardization
- compatibility and backend improvements
- controlled migration and import of additional picon sources

## Origins and credits

**PiconHub Warder Evolution** is based on the original **Chocholousek Picons** Enigma2 plugin created by **s3n0**.

The picon sets and original picon work are by **Chocholousek**.

Full credit and thanks belong to **s3n0** for the original plugin and to **Chocholousek** for the original picon work on which this continuation builds.

Warder Evolution continues, maintains and evolves their work. It does **not** claim authorship of their original work. Original authorship and credits are preserved and respected.

## Repository layout

- `picons/` — PiconHub runtime picon database
- `plugin/` — Enigma2 plugin source, packaging and update workspace
- `migration/` — controlled migration/import tooling and audit material
- `templates/` — approved project templates and master assets
- `docs/` — project plans, quality rules and recovery checkpoints

## Protected project rules

Approved graphics, GUI structure, layout, dimensions, positions and runtime directory structure are **LOCKED**. They must not be redesigned, rearranged, regenerated, renamed or "optimized" without explicit approval.

The runtime picon structure remains:

`picons/<satellite-position>/<provider>/{transparent,white,black}/<service-reference>.png`

There is no extra `satellite` directory, no `Satellite 0`, and no invented provider used merely to force an import.

The authoritative BLACK and WHITE master templates in `templates/picons/` are final as stored and must not be redrawn, regenerated, recolored, deformed or replaced by approximations.

## Development

Maintained and evolved by **Warder** as **PiconHub Warder Evolution**.

Current tested plugin baseline: `5.0.240904.6`.

Detailed recovery state and binding rules are maintained in `docs/PROJECT-CHECKPOINT.md`.
