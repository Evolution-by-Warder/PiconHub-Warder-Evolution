# WARDER PICON FACTORY

Unified Windows desktop application built from the supplied WARDER PICON FACTORY source archive. The modular engine, Tkinter application, review queue, and source processors now run as one project. The v0.9/intermediate duplicate is retained only in the original source archive, not shipped as a second app.

## Windows target

- Windows 11 x64
- Default working directory: `D:\WARDER-PICONS`
- CPU and image processing: bounded parallel download and multi-process PNG work; worker count is capped at 24 to leave room for Windows.
- The app creates its folder structure on first run. Existing source files and generated results are not deleted.

## Included source feeds

- **Vhannibal** — reads the current Motor picon entry from the official homepage and downloads only when the page entry changes.
- **OpenATV 8** — reads the OE-Alliance picons-feed package index, verifies GitHub's blob hash, package SHA-256 and selects current 220x132 transparent SRP packages.
- **Chocholousek** — checks the official updater index no more than once a week and imports only new archive entries.
- **Warder Master** — read-only snapshot from `PiconHub-Warder-Evolution/warder-master-production`. Master assets are indexed and excluded from candidate rendering. No identities are assigned or changed.

These feeds are equal-priority candidates. The app retains provenance in separate source folders and checkpoints. Failed feeds do not discard successful source state. Source terms and restrictions apply; imported graphics stay local and the app does not republish source archives.

## Windows one-click source delivery

Download the **warder-picon-factory-test-build.zip** artifact from the
**Factory regression (no release)** workflow, extract it into a persistent
directory, and double-click **SPUSTI-WARDER.cmd**. The launcher creates a
local `.venv`, installs the runtime dependencies and starts `engine.py`.
If Python is missing it attempts to install Python 3.12 using `winget`.
Internet access is required for first-time dependency installation. Existing
data in `WARDER_PICON_FACTORY_ROOT` is not deleted. The default data root
for this launcher is `%USERPROFILE%\\WARDER-PICONS`.

The Windows workflow runs the CMD setup in non-GUI mode and checks its
imports; this is a **source-based Windows package**, not a compiled EXE.
A real GUI launch, Windows installation on the user's PC, and a full dataset
run still require separate verification. No public GitHub Release is made
by the regression workflow.

## Source folders and safety

The engine creates its own source, original, work, report and output
directories under `WARDER_PICON_FACTORY_ROOT`. Imported originals and
Master Registry are not overwritten by this launcher. Review decisions
and local NEW-CANDIDATES are not production publication approval.

## Verification completed here

- Python syntax compilation.
- Unit and regression suite for source parsing, feed security, archive extraction limits, registry identity rules, source checkpoints, PNG variants and repairs, review decisions, and publication safety.
- Local result: 88 tests passed.

## Not verified here

- Live app-originated source archive downloads; this runtime blocks direct outbound network access.
- Chocholousek 7z extraction against a live archive; `py7zr` is included in the Windows dependency list but was not installed in this Linux environment.
- Full real Warder production tree ingestion, because the supplied archive does not include the actual picon dataset or local runtime state.
- Native Windows executable build, startup, Windows Defender/signing, and GUI display.

## Safety boundaries

The app does not push, merge, release, delete source originals, overwrite production assets, or reassign Warder IDs. Publication utilities only create draft manifests. Any later GitHub publication remains a separate operation requiring explicit authorization.
