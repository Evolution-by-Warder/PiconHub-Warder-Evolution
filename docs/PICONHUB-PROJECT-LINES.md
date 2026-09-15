# PiconHub — two independent project lines

Updated: 2026-09-15
Status: BINDING PROJECT SEPARATION RULE

## Purpose

The name PiconHub is used for two separate development projects. They are related by purpose, but they are NOT one code/UI/version line. Future ChatGPT, Work, automation and human maintenance must identify the project line before making technical or visual decisions.

## Project A — PiconHub (original Warder project)

This is Warder's independently developed PiconHub plugin with the new futuristic PiconHub graphics/UI and its own functionality.

Known development/package line: `0.6.x` / `0.7.x` (including `0.7.0-dev3`).

Rules:
- this project owns the futuristic PiconHub UI and its UI decisions;
- its screenshots, graphics, coordinates, package versions and implementation decisions belong only to this project;
- it is NOT the s3n0/Chocholousek modernization line.

## Project B — PiconHub Warder Evolution

Repository: `Evolution-by-Warder/PiconHub-Warder-Evolution`

This is the modernization/evolution of the original Chocholousek Picons Enigma2 plugin by s3n0, maintained as Warder Evolution.

Known package line: `5.0.240904.x`.

Rules:
- approved original graphics, GUI layout, element positions and established structure are LOCKED;
- modernization may improve code, compatibility, functionality, reliability, backend behavior and packaging;
- modernization must adapt to the locked graphics/structure, never redesign them merely to fit new code;
- original authorship/credits for s3n0 and Chocholousek remain preserved;
- the runtime picon architecture remains `picons/<satellite-position>/<provider>/{transparent,white,black}/<service-reference>.png`.

## Hard anti-mixing rule

NEVER transfer or infer between Project A and Project B without Štefan's explicit approval:
- UI/screenshots/graphics;
- coordinates/layout decisions;
- package/version numbering;
- code baselines;
- checkpoints/roadmaps;
- provider-panel counts or artwork;
- implementation assumptions.

A screenshot or package from one line is not evidence for the other line.

Before continuing any PiconHub task, first identify whether it belongs to **PiconHub (original Warder project)** or **PiconHub Warder Evolution (s3n0 modernization)**. If the line is not clear, do not guess.
