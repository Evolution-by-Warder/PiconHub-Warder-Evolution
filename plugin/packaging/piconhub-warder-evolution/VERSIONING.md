# Version-generation boundary

Historical Chocholousek/Warder builds use `5.0.240904.x`. The new Warder Evolution generation will use an independently approved version family.

Updater logic must compare versions only inside the same generation. Crossing from the legacy generation to Warder Evolution is an explicit migration transition and must never be rejected because the new semantic version has a numerically smaller first component.

The first new-generation version is intentionally not hard-coded here until Štefan explicitly approves it for release.
