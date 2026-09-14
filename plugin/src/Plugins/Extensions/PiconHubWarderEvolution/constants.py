# -*- coding: utf-8 -*-

PLUGIN_ID = 'PiconHubWarderEvolution'
PLUGIN_NAME = 'PiconHub-Warder-Evolution'
PLUGIN_VERSION = '0.1.0-dev'
AUTHOR = 'Warder'
UPSTREAM_PLUGIN_AUTHOR = 's3n0'
UPSTREAM_PICON_AUTHOR = 'Chocholousek'

REPOSITORY_OWNER = 'Evolution-by-Warder'
REPOSITORY_NAME = 'PiconHub-Warder-Evolution'
REPOSITORY_BRANCH = 'main'
REPOSITORY_FULL_NAME = REPOSITORY_OWNER + '/' + REPOSITORY_NAME
REPOSITORY_WEB = 'https://github.com/' + REPOSITORY_FULL_NAME
REPOSITORY_API = 'https://api.github.com/repos/' + REPOSITORY_FULL_NAME
REPOSITORY_RAW = 'https://raw.githubusercontent.com/%s/%s/%s' % (
    REPOSITORY_OWNER, REPOSITORY_NAME, REPOSITORY_BRANCH)
PICON_ROOT = 'picons'
PLUGIN_ROOT = 'plugin'

# Canonical Warder update channel. The plugin never contacts the legacy
# Chocholousek/s3n0 update service.
UPDATE_ROOT = REPOSITORY_RAW + '/plugin/update'
UPDATE_MANIFEST_URL = UPDATE_ROOT + '/manifest.json'
UPDATE_PACKAGE_ROOT = UPDATE_ROOT + '/packages'
UPDATE_TMP_DIR = '/tmp/piconhub-warder-evolution-update'

DEFAULT_TARGET_DIR = '/usr/share/enigma2/picon'
DEFAULT_TIMEOUT = 15
DEFAULT_RETRIES = 2
USER_AGENT = '%s/%s (Enigma2)' % (PLUGIN_NAME, PLUGIN_VERSION)

CONFIG_FILE = '/etc/enigma2/piconhub-warder-evolution.json'
LEGACY_CONFIG_FILES = (
    '/etc/enigma2/chocholousekpicons.cfg',
    '/etc/enigma2/piconhub.json',
)
