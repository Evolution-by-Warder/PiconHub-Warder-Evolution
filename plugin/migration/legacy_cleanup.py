# -*- coding: utf-8 -*-
"""Verified legacy cleanup helper for PiconHub Warder Evolution.

Cleanup is deliberately separate from settings migration.  Callers must pass a
successful migration result.  No recursive deletion is performed here; package
manager ownership must be used for package removal in the final integration.
"""
from __future__ import print_function

LEGACY_PACKAGE = "enigma2-plugin-extensions-chocholousek-picons"


def cleanup_plan(migration_result):
    """Return an auditable cleanup plan only after a verified migration."""
    verified = bool(migration_result and migration_result.get("verified"))
    status = migration_result.get("status") if migration_result else None
    if not verified or status not in ("MIGRATED", "NO_LEGACY_SETTINGS"):
        return {
            "allowed": False,
            "reason": "migration-not-verified",
            "package": LEGACY_PACKAGE,
        }
    return {
        "allowed": True,
        "reason": "migration-verified",
        "package": LEGACY_PACKAGE,
    }


def opkg_remove_command(migration_result):
    """Build, but do not execute, the legacy package removal command."""
    plan = cleanup_plan(migration_result)
    if not plan["allowed"]:
        return None
    return ["opkg", "remove", LEGACY_PACKAGE]
