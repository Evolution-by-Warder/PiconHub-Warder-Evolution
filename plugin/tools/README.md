# Build tools

`build_ipk.py` builds the installable IPK from `src/Plugins/Extensions/WarderPiconHub`, compiles the original translations, bundles version-matched offline release notes and excludes bytecode and receiver settings. A temporary legacy version.txt is included solely to protect an already-running old GUI during migration. `publish_plugin_release.py` verifies numbered immutable IPK bytes before updating the established stable feed. Production status and receiver validation scope are recorded in [../PRODUCTION.md](../PRODUCTION.md) and [../production.json](../production.json).


msgfmt.py is the unmodified CPython v3.13.0 Tools/i18n/msgfmt.py tool, used only at build time. Original author notices remain in that file. Source: https://github.com/python/cpython/blob/v3.13.0/Tools/i18n/msgfmt.py ; Python software is distributed under the Python Software Foundation License: https://docs.python.org/3/license.html .
