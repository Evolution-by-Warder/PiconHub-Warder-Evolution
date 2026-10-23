# PiconHub Warder Evolution 0.1.0-dev5

Show live seconds beside the header clock, with a separate smaller label:
HH:MM uses 62 px and :SS uses 32 px at Full HD, scaled for HD.
Header spacing accommodates seconds between the date and version dividers.
Both labels use the same local system-time sample and the existing one-second
GUI timer; there is no network dependency or extra polling thread.

Retain the dev3 dependency correction and dev4 OpenATV Screen.scale fix.
All 57 tests pass, including seconds advancing on consecutive GUI ticks,
midnight/localized clock output and HD/FHD layout fields and font sizes.
Physical validation of the seconds display remains pending.

```sh
opkg install /tmp/enigma2-plugin-extensions-piconhub-warder-evolution_0.1.0-dev5_all.ipk
```

Restart the GUI through the receiver menu after a successful installation.
