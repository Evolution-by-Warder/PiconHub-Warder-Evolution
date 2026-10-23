# Warder interface languages

Version 0.1.2 supports Slovak (sk), Czech (cs), English (en), German (de), Polish (pl), Hungarian (hu), Russian (ru), French (fr), Italian (it) and Spanish (es).

The current Enigma2 language is read whenever text is requested; reopening the plugin after a system language change rebuilds all visible menus and labels in that language. Region suffixes such as en_GB or es_ES are normalized. Unsupported languages use English. No additional Python package is needed.

`src/Plugins/Extensions/ChocholousekPicons/data/translations.json` contains 104 interface messages per language. The catalogs cover the main screen, dialogs, progress messages, native engine errors, plugin installation and plugin browser description. Service names and satellite identifiers are preserved. Technical details originating in the operating system or third-party validators are displayed as supplied.

`warder_model.clock_text` supplies localized day and month names without relying on the host locale. `warder_i18n.localize_skin` translates native XML titles and static labels. Selection identifiers and filesystem paths are never translated.

Release manifests may contain an optional `notes_i18n` map. New updaters select the current language, then English, then the legacy notes field. Existing older installed builds remain compatible and use the legacy notes field for the first upgrade. The publisher reads version-matched `update/RELEASE-NOTES.i18n.json` before publishing.

To add a language, add a complete catalog with the same keys and unchanged printf placeholders, add its calendar names, and extend the language tests. The tests check catalog completeness, interpolation order, system-language changes, unsupported-language fallback, rendered screen labels, selection identity, and update-note validation.
