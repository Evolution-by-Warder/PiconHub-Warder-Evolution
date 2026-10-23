# PiconHub Warder Evolution 0.1.0-dev8

Every new opening starts with five neutral "Vyber si…" rows. No saved satellites,
size, background, mode or destination is silently treated as the current choice.
The underlying configuration is retained; only explicitly confirmed choices are
saved. All five fields must be chosen in the current screen session before a
download can start. Cancelled pickers leave the neutral state or prior explicit
selection unchanged. Opening the screen performs no picon installation or deletion.

The initial preview displays the genuine PiconHub brand from the existing graphic,
without altering its pixels. A native parent viewport clips the left brand area;
the child image keeps its aspect ratio. Selecting a background replaces the logo
with its actual picon sample. Selecting a resolution changes the centered sample
to 50x30, 220x132 or 400x240 (scaled for the receiver desktop). The caption states
when a resolution has not yet been selected.

The recent-picon strip now uses only approved black source PNGs. Its six bundled
files and Git provenance have been regenerated from black source additions. Runtime
discovery also selects black additions. A separate recent-black cache and style
marker prevent the previous transparent thumbnails from being reused.

Footer actions are direct: red Zatvoriť, green Stiahnuť, yellow Aktualizácia pluginu,
blue O projekte. Per-launch plugin checking remains enabled. No extra options
dialog stands between the colored key and its named action.

Shift the date/time/version group left. Seconds are larger (38px rather than 32px
at FHD) and white. Version text takes the cyan color and has a 210px field so the
current version fits on a single line. Preserve the one-second GUI clock timer.

70 tests cover neutral startup and reopening, cancellation, complete-choice gating,
preview/logo switching and dimensions, direct color-key actions, black gallery
selection/cache separation, header spacing/colors, HD/FHD widget bounds, package
contents and the existing download/update/rollback behavior. These use component
doubles; physical receiver layout and native clipping remain to be confirmed.

```sh
opkg install /tmp/enigma2-plugin-extensions-piconhub-warder-evolution_0.1.0-dev8_all.ipk
```

Restart the GUI through the receiver menu after successful installation.
