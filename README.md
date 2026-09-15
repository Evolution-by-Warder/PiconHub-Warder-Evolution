# PiconHub Warder Evolution

Modern continuation and evolution of the Chocholousek Picons ecosystem for Enigma2, maintained by **Warder**.

> **STOP before development:** There are two independent PiconHub projects. Read `docs/PICONHUB-PROJECT-LINES.md` and `docs/PICONHUB-WORK-PLAN.md`. Do not mix their graphics, versions, packages, checkpoints or UI decisions.

## IMPORTANT: two separate PiconHub projects

### 1. PiconHub — original Warder project

Warder's independently developed PiconHub plugin with the **new futuristic PiconHub graphics/UI** and its own functionality. Development/package family: `0.6.x / 0.7.x`.

This is NOT the s3n0/Chocholousek modernization line.

### 2. PiconHub Warder Evolution — THIS repository

Modernization/evolution based on the original **Chocholousek Picons Enigma2 plugin by s3n0**. Development/package family: `5.0.240904.x`.

For this line, approved original graphics, GUI layout and established structure are **LOCKED**. Development may modernize code, compatibility, functionality, reliability, backend behavior and packaging, but must not independently redesign, replace, reposition or reorganize the locked graphics or structure.

Never use screenshots, graphics, provider-panel counts, package versions or UI decisions from the separate futuristic PiconHub project as authority for PiconHub Warder Evolution.

Binding separation: `docs/PICONHUB-PROJECT-LINES.md`  
Parallel work plan: `docs/PICONHUB-WORK-PLAN.md`  
Recovery checkpoint: `docs/PROJECT-CHECKPOINT.md`

## Project status

This repository is the official home of **PiconHub Warder Evolution**.

Current work includes maintenance and modernization of the Enigma2 plugin, expansion/QC of the picon database, provider/satellite organization, BLACK/WHITE/transparent standardization, compatibility/backend improvements and controlled migrations.

## Origins and credits

**PiconHub Warder Evolution** is based on the original **Chocholousek Picons** Enigma2 plugin created by **s3n0**. The picon sets and original picon work are by **Chocholousek**.

Full credit and thanks belong to **s3n0** for the original plugin and to **Chocholousek** for the original picon work. Warder Evolution continues, maintains and evolves their work and does not claim authorship of their original work.

## Repository layout

- `picons/` — PiconHub runtime picon database
- `plugin/` — Enigma2 plugin source, packaging and update workspace
- `migration/` — controlled migration/import tooling and audit material
- `templates/` — approved project templates and master assets
- `docs/` — project plans, quality rules and recovery checkpoints

## Protected project rules

Approved graphics, GUI structure, layout, dimensions, positions and runtime directory structure are **LOCKED** and may not be redesigned, rearranged, regenerated, renamed or "optimized" without explicit approval.

Runtime picon structure:

`picons/<satellite-position>/<provider>/{transparent,white,black}/<service-reference>.png`

No extra `satellite`, no `Satellite 0`, and no invented provider merely to force an import.

The authoritative BLACK and WHITE MASTER templates in `templates/picons/` are final as stored and must not be redrawn, regenerated, recolored, deformed or replaced by approximations.

## Development

Maintained and evolved by **Warder** as **PiconHub Warder Evolution**.

Current tested plugin baseline: `5.0.240904.6`.
