# PiconHub-Warder-Evolution update channel

This directory is the canonical self-update channel used by the Enigma2 plugin.

The plugin reads `src/version.txt`. If that version is newer than the installed version, it reconstructs the matching IPK/DEB from base64 text parts listed in `released_build/<package>.parts`, verifies the package against `released_build/<package>.sha256`, and only then installs it.

The GUI and its layout are not part of this update-channel change.
