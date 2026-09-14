# -*- coding: utf-8 -*-
"""Plugin self-update policy.

Self-updating is intentionally disabled in the first PiconHub-Warder-Evolution
line. Packages must come from an explicit release channel rather than the old
s3n0/Chocholousek updater paths. This prevents the evolved plugin from
accidentally replacing itself with the upstream legacy package.
"""

from ..constants import REPOSITORY_WEB


def update_channel():
    return REPOSITORY_WEB + '/releases'


def automatic_update_supported():
    return False
