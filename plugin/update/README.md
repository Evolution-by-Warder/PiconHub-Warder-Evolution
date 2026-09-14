# PiconHub-Warder-Evolution update channel

This directory is the canonical self-update source for the Enigma2 plugin.

- `manifest.json` tells installed plugins which version is current.
- `packages/` contains the installable `.ipk`/`.deb` package referenced by the manifest.
- the updater accepts packages only from this repository's HTTPS raw path.
- SHA-256 and optional file size are verified before installation.
- package-manager exit status is checked; a failed install is never reported as success.

## Publishing a plugin update

1. Build and runtime-test the package on Enigma2.
2. Upload it under `plugin/update/packages/`.
3. Calculate the package SHA-256 and byte size.
4. Update `manifest.json` with the new version, exact package URL, SHA-256 and size.
5. Set `enabled` to `true` only when that package is ready for users.

The old Chocholousek/s3n0 plugin update endpoint is not used by PiconHub-Warder-Evolution.
