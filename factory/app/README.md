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

## One-click runtime

After a Windows build has produced `WARDER-PICON-FACTORY.exe`, run `SPUSTI-WARDER.cmd`. The app automatically creates:

- `01-INBOX` — local ZIP/PNG input
- `02-ORIGINALS` — immutable imported originals and read-only Warder snapshot
- `06-OUTPUT` — transparent, black-background, and white-background PNG variants at 220x132
- `07-EXCEPTIONS` — backups for safe deterministic repairs
- `08-REPORTS` — run, registry, QA, integrity, and review reports
- `10-TOOLS/WARDER-FACTORY` — SQLite cache, source checkpoints, and persisted review decisions

Rerunning the app resumes from the source checkpoints, cached hashes, and generated-variant size/mtime signatures. Unchanged artwork skips rendering and image decoding. The review window shows original and generated previews when available. Human decisions are persisted and evidence changes make a decision stale. Approval is only for review/publication planning; it never publishes automatically.

## Building the Windows executable

A Windows 11 x64 build host is required. From this folder, run `BUILD-WINDOWS.ps1` once in PowerShell. It installs the packages listed in `requirements.txt`, builds a single-file GUI executable, and copies it next to `SPUSTI-WARDER.cmd`. End users do not need Python after the executable is built.

This source delivery was prepared in a Linux environment without Windows, Wine, or PyInstaller. Therefore **the EXE is not included and Windows packaging/startup has not been tested here**. Do not treat the Windows build as verified until it is built and run on Windows 11.

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
