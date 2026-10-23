# PiconHub Warder Evolution 0.1.0-dev4

Fix the startup crash reported on OpenATV 8.0.1 / GigaBlue UHD Quad 4K Pro
in 20261023-132625-enigma2-crash.log. Screen.applySkin assigns its own scale
tuple before onLayoutFinish. The plugin had also used self.scale as a scalar
for menu geometry; ready -> refresh then called round() on a tuple.

Use self.warder_scale for plugin menu geometry in both WarderMainScreen and
ChoiceDialog. Leave Screen.scale owned by Enigma2. This also fixes the same
collision when toggling satellites or navigating the directory dialog after
their skins have been applied.

Regression tests reproduce the OpenATV assignment before layout callbacks and
exercise main screen opening, profile/style changes, satellite toggling and
directory navigation. All 57 local tests pass. These controller tests use
Enigma2 component doubles; successful physical receiver operation is still
pending. Retain the dev3 gettext dependency correction.

Copy the IPK into /tmp and install only this exact filename:

```sh
opkg install /tmp/enigma2-plugin-extensions-piconhub-warder-evolution_0.1.0-dev4_all.ipk
```

After installation succeeds, restart the GUI through the receiver menu before
opening the plugin again.
