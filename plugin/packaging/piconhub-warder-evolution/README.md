# Warder Evolution package migration contract

Target package identity: `enigma2-plugin-extensions-piconhub-warder-evolution`.
Target runtime directory: `/usr/lib/enigma2/python/Plugins/Extensions/PiconHubWarderEvolution/`.
Legacy package identity: `enigma2-plugin-extensions-chocholousek-picons`.
Legacy runtime directory: `/usr/lib/enigma2/python/Plugins/Extensions/ChocholousekPicons/`.

`Replaces`/`Conflicts` declares package identity migration, but maintainer scripts MUST NOT blindly delete the legacy directory. The persistent runtime migrator copies and verifies settings first. Legacy cleanup is permitted only after the migration verification gate succeeds.

The final release builder must substitute `@VERSION@` with the explicitly approved Warder Evolution release version. The version reset is not yet locked by this packaging skeleton.

Do not remove original s3n0/Chocholousek credits.
