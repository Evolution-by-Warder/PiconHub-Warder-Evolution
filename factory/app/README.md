# WARDER PICON FACTORY

Unified Windows desktop application built from the supplied WARDER PICON FACTORY source archive. The modular engine, Tkinter application, review queue, and source processors now run as one project. The v0.9/intermediate duplicate is retained only in the original source archive, not shipped as a second app.

## Windows target

- Windows 11 x64
- The one-click Windows launcher stores user data under `%USERPROFILE%\WARDER-PICONS`.
- CPU and image processing: bounded parallel download and multi-process PNG work; worker count is capped at 24 to leave room for Windows.
- The app creates its folder structure on first run. Existing source files and generated results are not deleted.

## Included source feeds

- **Vhannibal** — reads the current Motor picon entry from the official homepage and downloads only when the page entry changes.
- **OpenATV 8** — reads the OE-Alliance picons-feed package index, verifies GitHub's blob hash, package SHA-256 and selects current 220x132 transparent SRP packages.
- **Chocholousek** — reads the current official 220×132 download page, offers only its published satellite-position archives, honors the provider's weekly update limit, and downloads only positions explicitly selected in Settings. Empty selection performs no download.
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

## Integrated GUI

The desktop window has Dashboard, Sources, Master Registry, Candidates, QA,
Exceptions, Settings, and Diagnostics sections. Panels read actual run reports,
checkpoints, review decisions, and local output. Exceptions are reviewed in
pages of ten with previews of available variants. Large source-tree counting
runs off the Tk event thread. A safe-stop action waits for the current bounded
download or atomic operation, stops scheduling work, and skips local
finalization of a cancelled run. Closing during a run offers the same safe
stop-and-close behavior.

## Verification

- Python compile check and local Linux regression/integration suite: 142 tests passed, including the real 7z extractor using an isolated fixture archive.
- Live Vhannibal Motor archive: SHA-256 verified; 13,961 PNGs imported into a temporary workspace; a real sample rendered to all three variants and passed QA.
- Live OpenATV 8 SRP archive: feed SHA-256 verified; 30,047 PNGs imported into a temporary workspace; a real sample rendered to all three variants and passed QA.
- Live Chocholousek public page: 49 current archive links discovered. No provider archive was downloaded because the user's active satellite positions are unknown; Settings requires an explicit selection. The 7z extractor, archive validation, and PNG import were exercised end-to-end with a generated archive fixture.
- A persisted 5,877-item review queue loaded with all records intact. The user's historical queue and full production dataset were not available in this workspace.
- Native Windows build and GUI smoke test require the Windows Actions run for the commit containing these changes; installation on the user's own PC is not observable here.

## Safety boundaries

The app does not push, merge, release, delete source originals, overwrite production assets, or reassign Warder IDs. Publication utilities only create draft manifests. Any later GitHub publication remains a separate operation requiring explicit authorization.
