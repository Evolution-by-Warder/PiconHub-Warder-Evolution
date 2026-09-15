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
Historical version family: `5.0.240904.x`.
Planned Warder Evolution version family: new independent numbering beginning with the migration generation; exact first version must be explicitly approved before release.

Current work:
1. Preserve LOCKED graphics, GUI layout and established structure.
2. Complete/verify Warder Evolution catalog normalization and BLACK/WHITE production under the frozen MASTER quality rules.
3. Keep transparent originals and MASTER templates unchanged.
4. Continue plugin modernization around the locked UI/structure: compatibility, reliability, backend behavior, updater/package handling and other approved functionality.
5. Keep mass catalog work isolated on a controlled working branch and review before merge to `main`.
6. Only after catalog normalization/approval, proceed to the separately planned Orbit Watch / satellite-change monitor.

Current production branch for the BLACK/WHITE rebuild: `warder-master-production`. Do not use that branch for unrelated plugin/UI development while the rebuild is active.

### Persistent legacy migration compatibility — REQUIRED

The migration from the original s3n0/Chocholousek installation is a long-term compatibility feature of PiconHub Warder Evolution, not a one-release installer workaround.

Every future Warder Evolution release must retain a compatible migration path so that a user installing the current release months or years later can still migrate directly from an installed legacy `ChocholousekPicons` plugin without first installing an old Warder Evolution release.

Required behavior:
- detect a legacy `ChocholousekPicons` installation and its legacy configuration namespace; do not restrict detection only to `5.0.240904.6`;
- read and preserve supported legacy user settings before any destructive operation;
- translate/copy those settings into the current PiconHub Warder Evolution configuration format;
- verify that migration completed successfully before removing any legacy package, directory, registration or configuration that is no longer required;
- if migration or verification fails, keep the legacy plugin/configuration intact and report the failure; never sacrifice the working legacy installation to complete an upgrade;
- migrate package/plugin identity as well as files: after a successful migration, the new PiconHub Warder Evolution package/Plugins/Addons identity must be authoritative and stale legacy package registration must not remain as a duplicate installed plugin;
- preserve original s3n0/Chocholousek authorship and project credits after migration;
- make migration idempotent: a system already migrated to Warder Evolution must not be destructively migrated again or have valid current settings overwritten merely because a later release runs the compatibility check;
- keep the legacy migration code/path in future releases until an explicit project decision retires legacy compatibility; routine cleanup or refactoring must not silently remove it;
- tests for future releases must include at least a legacy-install migration case, an already-migrated case, and a migration-failure/no-delete case.

The migration implementation must be version-aware. Resetting Warder Evolution to a new version family must not rely on a naive numeric comparison that would classify the new generation as older than historical `5.0.240904.x` builds.

Current dedicated plugin migration branch: `plugin-warder-evolution-migration`. It is separate from `warder-master-production` and must not interfere with the catalog rebuild.

## Shared operating rule

At the start of every future PiconHub task, explicitly resolve the target line:
- Project A = PiconHub / futuristic Warder UI / `0.6.x–0.7.x`;
- Project B = PiconHub Warder Evolution / s3n0 modernization / historical `5.0.240904.x`, followed by its explicitly approved new independent version family.

Do not mix artifacts, rules, versions or visual decisions between them. If a requested change could cross the boundary, obtain Štefan's explicit approval first.
