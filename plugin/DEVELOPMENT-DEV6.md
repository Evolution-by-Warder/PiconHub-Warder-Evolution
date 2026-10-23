# PiconHub Warder Evolution 0.1.0-dev6

Simplify the screen to one visible configuration: Satellites, Resolution,
Background, Mode and Folder. Remove profile tabs, the enabled row and remote
number/left/right profile switching. Preserve and edit the previously selected
configuration in place using its existing stored identity; do not erase dormant
legacy configurations or silently reset the selected folder and satellites.

Updating now runs exactly the displayed settings, regardless of legacy enabled
flags. Hidden old configurations cannot launch additional downloads or writes.
The reset option refers to settings and resets only that displayed configuration.

Refresh the native interface with cyan panel accents, numbered rows, larger row
spacing, subtle dividers, explicit white selected text, a brighter blue selection,
a framed preview well and four accented footer buttons. Selection colors are
explicit to avoid inheriting the low-contrast selected text from the receiver skin.
Keep the original background artwork, live seconds and startup plugin updater.

58 tests pass, including retained active settings, no profile navigation, exactly
one update task despite hidden enabled legacy configurations, screen lifecycle,
HD/FHD layout bounds and existing download/rollback/package tests. Visual review
on the physical receiver remains pending.

```sh
opkg install /tmp/enigma2-plugin-extensions-piconhub-warder-evolution_0.1.0-dev6_all.ipk
```

Restart the GUI through the receiver menu after successful installation.
