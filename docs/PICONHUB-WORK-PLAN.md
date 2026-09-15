# PiconHub — work plan for two independent projects

Updated: 2026-09-15

This plan tracks two separate PiconHub development lines. See `docs/PICONHUB-PROJECT-LINES.md` before working on either line.

## A. PiconHub — original Warder project

Identity: independent PiconHub plugin with the new futuristic UI.
Version family: `0.6.x` / `0.7.x`.

Current work policy:
- preserve its own approved visual checkpoints;
- continue functionality only against this project's own code/UI baseline;
- do not import s3n0/Warder Evolution graphics, structure, package numbering or assumptions;
- treat its packages and screenshots as Project A artifacts only.

Next development work must be planned from the latest verified Project A source/package state before changing code.

## B. PiconHub Warder Evolution

Identity: modernization of the original s3n0/Chocholousek Picons Enigma2 plugin.
Repository: `Evolution-by-Warder/PiconHub-Warder-Evolution`.
Version family: `5.0.240904.x`.

Current work:
1. Preserve LOCKED graphics, GUI layout and established structure.
2. Complete/verify Warder Evolution catalog normalization and BLACK/WHITE production under the frozen MASTER quality rules.
3. Keep transparent originals and MASTER templates unchanged.
4. Continue plugin modernization around the locked UI/structure: compatibility, reliability, backend behavior, updater/package handling and other approved functionality.
5. Keep mass catalog work isolated on a controlled working branch and review before merge to `main`.
6. Only after catalog normalization/approval, proceed to the separately planned Orbit Watch / satellite-change monitor.

Current production branch for the BLACK/WHITE rebuild: `warder-master-production`. Do not use that branch for unrelated plugin/UI development while the rebuild is active.

## Shared operating rule

At the start of every future PiconHub task, explicitly resolve the target line:
- Project A = PiconHub / futuristic Warder UI / `0.6.x–0.7.x`;
- Project B = PiconHub Warder Evolution / s3n0 modernization / `5.0.240904.x`.

Do not mix artifacts, rules, versions or visual decisions between them. If a requested change could cross the boundary, obtain Štefan's explicit approval first.
