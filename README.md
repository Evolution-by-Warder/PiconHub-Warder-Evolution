# PiconHub Warder Evolution

Modern continuation and evolution of the Chocholousek Picons ecosystem for Enigma2, maintained by **Warder**.

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
