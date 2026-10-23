# Warder interface languages

Version 0.1.2 supports Slovak (sk), Czech (cs), English (en), German (de), Polish (pl), Hungarian (hu), Russian (ru), French (fr), Italian (it) and Spanish (es).

The current Enigma2 language is read whenever text is requested; reopening the plugin after a system language change rebuilds all visible menus and labels in that language. Region suffixes such as en_GB or es_ES are normalized. Unsupported languages use English. No additional Python package is needed.

`src/Plugins/Extensions/WarderPiconHub/data/translations.json` contains 117 interface messages per language. The catalogs cover the main screen, dialogs, progress messages, native engine errors, plugin installation and plugin browser description. Service names and satellite identifiers are preserved. Technical details originating in the operating system or third-party validators are displayed as supplied.

`warder_model.clock_text` supplies localized day and month names without relying on the host locale. `warder_i18n.localize_skin` translates native XML titles and static labels. Selection identifiers and filesystem paths are never translated.

Release manifests may contain an optional `notes_i18n` map. New updaters select the current language, then English, then the legacy notes field. Existing older installed builds remain compatible and use the legacy notes field for the first upgrade. The publisher reads version-matched `update/RELEASE-NOTES.i18n.json` before publishing.

To add a language, add a complete catalog with the same keys and unchanged printf placeholders, add its calendar names, and extend the language tests. The tests check catalog completeness, interpolation order, system-language changes, unsupported-language fallback, rendered screen labels, selection identity, and update-note validation.

All custom popups use the same opaque dark-blue surface, cyan title separator and action-only footer labels. Red returns, green confirms or uses a folder, blue opens the log. No color name or button-name prefix is printed on these captions. During picon downloads, red requests safe cancellation and returns only after the worker completes.

Popup footer actions occupy equally sized slots with horizontal and vertical centering and no line wrapping. The white selection caption explicitly names the OK button in all 10 languages.

Since 0.1.7 the live runtime and package payload use WarderPiconHub. Configuration keys in /etc/enigma2/settings are preserved. Pre-install records a transition before opkg removes old files. Post-install archives leftover legacy files outside plugin discovery and temporarily exposes only version.txt for the old running screen timer. The new package import removes that marked compatibility directory after GUI restart. Legacy gettext catalog filenames remain compatible with upstream translations.
