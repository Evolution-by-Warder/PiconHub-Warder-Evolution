# Build tools

build_ipk.py builds the development package from the runtime tree, preserves the technical ChocholousekPicons path, compiles the original translations and does not include bytecode or receiver settings.

msgfmt.py is the unmodified CPython v3.13.0 Tools/i18n/msgfmt.py tool, used only at build time. Original author notices remain in that file. Source: https://github.com/python/cpython/blob/v3.13.0/Tools/i18n/msgfmt.py ; Python software is distributed under the Python Software Foundation License: https://docs.python.org/3/license.html .
