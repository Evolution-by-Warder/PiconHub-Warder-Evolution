# WARDER Factory updates

Application code lives under `D:\WARDER-PICON-FACTORY\11-APP\WARDER-PICON-FACTORY`.
Every installer/update must pass the read-only preflight for all 13 categories
before writing. Runtime data stay in their authoritative folders (`00-STATE`
through `12-ARCHIVE`); no data migration is performed. Failed or superseded app
versions are retained under `11-APP` for explicit operator recovery.

The Windows one-file CMD verifies the executable SHA-256 and swaps only the
application directory. It does not delete an older app folder or modify the
workspace data categories. Installer diagnostics go to `09-LOGS` after the
preflight passes. A public GitHub Release or production update manifest is a
separate operation and is not performed by this workflow.
