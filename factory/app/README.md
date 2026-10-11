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

## Windows one-click application

The **Factory regression (no release)** workflow builds a standalone Windows
GUI executable on `windows-latest`, launches it for a GUI startup smoke test,
and packages that tested executable into one self-extracting
`SPUSTI-WARDER-PICON-FACTORY.cmd` file. Download that single CMD artifact and
double-click it; Python and runtime libraries are bundled in the executable.
The launcher installs each application version into `%LOCALAPPDATA%` and
keeps user data in `%USERPROFILE%\\WARDER-PICONS`. Updates use versioned app
folders, verify SHA-256 before launch, and leave the user's Factory data in
place. Startup and extraction errors are recorded under
`%LOCALAPPDATA%\\WARDER-PICON-FACTORY\\launcher.log`.

The source-tree `SPUSTI-WARDER.cmd` remains a developer launcher. The one-file
Windows CMD is generated only by the Windows build job after its tests and
native GUI smoke test succeed. The job uploads it as a seven-day Actions
artifact, not as a public release.

## Source folders and safety

The engine creates its own source, original, work, report and output
directories under `WARDER_PICON_FACTORY_ROOT`. Imported originals and
Master Registry are not overwritten by this launcher. Review decisions
and local NEW-CANDIDATES are not production publication approval.

## Verification completed here

- Python 3.12 syntax compilation and unit/regression suite for source parsing,
  feed security, archive extraction limits, registry identity rules, source
  checkpoints, PNG variants and repairs, review decisions, publication safety,
  retry-safe diagnostics delivery and the generated launcher container.
- Local Linux result: 124 tests passed.
- The Windows job builds the bundled executable and launches its GUI in a
  short smoke test before producing the single-CMD artifact.

## Not verified here

- Live app-originated source archive downloads; this runtime blocks direct outbound network access.
- Chocholousek 7z extraction against a live archive; `py7zr` is included in the Windows dependency list but was not installed in this Linux environment.
- Full real Warder production tree ingestion, because the supplied archive does not include the actual picon dataset or local runtime state.
- Native Windows executable build and GUI startup remain unverified until the
  current Windows Actions job completes successfully. Windows Defender
  reputation/signing and installation on the user's own PC are also separate
  from CI verification.

## Safety boundaries

The app does not push, merge, release, delete source originals, overwrite production assets, or reassign Warder IDs. Publication utilities only create draft manifests. Any later GitHub publication remains a separate operation requiring explicit authorization.
