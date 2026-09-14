# Changelog

## 0.1.0-dev

- rebuilt the plugin around a modular PiconHub engine;
- switched the data source to `Evolution-by-Warder/PiconHub-Warder-Evolution/picons/`;
- removed the old `picon.cz`/7z archive dependency from the new engine;
- restored normal TLS certificate verification;
- added streamed downloads with temporary files, integrity checks and atomic replacement;
- added Git blob SHA comparison so unchanged picons are not downloaded again;
- added safe target-path validation and optional package-scoped orphan cleanup;
- added TV / TV+radio bouquet filtering;
- moved network and update jobs outside the Enigma2 GUI thread;
- disabled the legacy self-updater so the new plugin cannot overwrite itself with the old upstream package;
- preserved explicit credit to Chocholousek (picons) and s3n0 (original Enigma2 plugin).
