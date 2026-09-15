# -*- coding: utf-8 -*-
"""Persistent legacy migration support for PiconHub Warder Evolution.

This module intentionally contains no Enigma2 UI code.  It provides the
transactional filesystem/config migration primitives used by installers and
future plugin releases.  Legacy compatibility is a long-term project feature.

Safety contract:
  * discover/read before writing;
  * never delete the legacy installation from this module;
  * write migrated settings atomically;
  * verify the written values before reporting success;
  * repeated runs are safe (idempotent).
"""
from __future__ import print_function

import os
import tempfile

LEGACY_PLUGIN_DIR = "/usr/lib/enigma2/python/Plugins/Extensions/ChocholousekPicons"
CURRENT_PLUGIN_DIR = "/usr/lib/enigma2/python/Plugins/Extensions/PiconHubWarderEvolution"
ENIGMA2_SETTINGS = "/etc/enigma2/settings"

LEGACY_PREFIXES = (
    "config.plugins.chocholousekpicons_id=",
    "config.plugins.chocholousekpicons.",
)
CURRENT_ID_PREFIX = "config.plugins.piconhubwarderevolution_id="
CURRENT_PREFIX = "config.plugins.piconhubwarderevolution."
MIGRATION_MARKER = "config.plugins.piconhubwarderevolution.legacy_migration=1"


def legacy_plugin_present(path=LEGACY_PLUGIN_DIR):
    return os.path.isdir(path)


def _is_legacy_setting(line):
    return line.startswith(LEGACY_PREFIXES)


def read_legacy_settings(settings_path=ENIGMA2_SETTINGS):
    """Return legacy settings verbatim, without modifying the settings file."""
    if not os.path.isfile(settings_path):
        return []
    with open(settings_path, "r") as handle:
        return [line.rstrip("\r\n") for line in handle if _is_legacy_setting(line.rstrip("\r\n"))]


def translate_setting(line):
    """Translate only the namespace; preserve profile keys and values exactly."""
    if line.startswith("config.plugins.chocholousekpicons_id="):
        return CURRENT_ID_PREFIX + line.split("=", 1)[1]
    if line.startswith("config.plugins.chocholousekpicons."):
        return CURRENT_PREFIX + line[len("config.plugins.chocholousekpicons."):]
    return None


def translated_legacy_settings(settings_path=ENIGMA2_SETTINGS):
    translated = []
    for line in read_legacy_settings(settings_path):
        new_line = translate_setting(line)
        if new_line is not None:
            translated.append(new_line)
    return translated


def migration_required(settings_path=ENIGMA2_SETTINGS, legacy_dir=LEGACY_PLUGIN_DIR):
    """True only when legacy evidence exists and migration is not already marked."""
    existing = _read_all_lines(settings_path)
    if MIGRATION_MARKER in existing:
        return False
    return legacy_plugin_present(legacy_dir) or bool(read_legacy_settings(settings_path))


def _read_all_lines(settings_path):
    if not os.path.isfile(settings_path):
        return []
    with open(settings_path, "r") as handle:
        return [line.rstrip("\r\n") for line in handle]


def _current_key(line):
    return line.split("=", 1)[0] if "=" in line else line


def migrate_settings(settings_path=ENIGMA2_SETTINGS):
    """Atomically add/update current settings and verify them.

    Legacy settings remain untouched.  Their cleanup belongs to a later,
    separately gated packaging step after this function returns success.
    """
    legacy = read_legacy_settings(settings_path)
    if not legacy:
        return {"status": "NO_LEGACY_SETTINGS", "migrated": 0, "verified": True}

    translated = [translate_setting(line) for line in legacy]
    translated = [line for line in translated if line is not None]
    original = _read_all_lines(settings_path)

    replacements = dict((_current_key(line), line) for line in translated)
    output = []
    seen = set()
    for line in original:
        key = _current_key(line)
        if key in replacements:
            output.append(replacements[key])
            seen.add(key)
        elif line != MIGRATION_MARKER:
            output.append(line)
    for line in translated:
        key = _current_key(line)
        if key not in seen:
            output.append(line)
            seen.add(key)
    output.append(MIGRATION_MARKER)

    directory = os.path.dirname(settings_path) or "."
    fd, tmp_path = tempfile.mkstemp(prefix=".piconhub-migrate-", dir=directory)
    try:
        with os.fdopen(fd, "w") as handle:
            for line in output:
                handle.write(line + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.rename(tmp_path, settings_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        raise

    written = set(_read_all_lines(settings_path))
    verified = MIGRATION_MARKER in written and all(line in written for line in translated)
    if not verified:
        return {"status": "VERIFY_FAILED", "migrated": len(translated), "verified": False}
    return {"status": "MIGRATED", "migrated": len(translated), "verified": True}


def legacy_cleanup_allowed(migration_result):
    """Hard gate for packaging cleanup.  This module itself never deletes legacy."""
    return bool(migration_result and migration_result.get("verified") and
                migration_result.get("status") in ("MIGRATED", "NO_LEGACY_SETTINGS"))
