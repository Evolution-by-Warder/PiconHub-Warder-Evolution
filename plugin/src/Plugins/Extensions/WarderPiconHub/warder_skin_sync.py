# -*- coding: utf-8 -*-
"""FullHDGlass17 Warder Evolution - receiver driven picon synchronisation.

Pure planning helpers live here so the Enigma2 GUI can stay small.  No network
or GUI side effects are performed by this module.
"""
from __future__ import absolute_import

import os
import re
import hashlib
import stat
import zipfile
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

ENIGMA2_DIR = "/etc/enigma2"
# Published channel catalogues are data, independent of the installed IPK.
# Stable receivers follow only approved main; archives retain content-addressed
# filenames and SHA-256 verification. The pinned TEST descriptor is opt-in.
RUNTIME_PUBLICATION_ENABLED = True
PUBLICATION_SOURCES = {
    "production": {
        "manifest_url": "https://raw.githubusercontent.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/main/assets/warder/downloads/picons/channels/manifest.json",
        "package_root": "https://raw.githubusercontent.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/main/assets/warder/downloads/picons/channels/",
    },
    "test-candidate": {
        "manifest_url": "https://raw.githubusercontent.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/da8458a8ec0197974fcc319e93e4e57ce0e1e53e/assets/warder/downloads/picons/channels/test-candidate/manifest.json",
        "package_root": "https://raw.githubusercontent.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/warder-modernization-work/assets/warder/downloads/picons/channels/test-candidate/",
    },
}
ACTIVE_PUBLICATION_SOURCE = "production"
RUNTIME_MANIFEST_URL = PUBLICATION_SOURCES[ACTIVE_PUBLICATION_SOURCE]["manifest_url"]

# TEST202 auxiliary archives come from an immutable PiconHub review commit.
# The FullHDGlass catalog can describe these assets, but it cannot broaden the
# set of URLs accepted by this descriptor.
AUXILIARY_CANDIDATE_COMMIT = "db5eec9f1cdb7a4d587cb1bcdeebc6b3f0d51819"
# The immutable candidate manifest records archive locator URLs at the commit
# where those archives were first published. Runtime downloads remain pinned
# independently to AUXILIARY_CANDIDATE_COMMIT below.
AUXILIARY_CANDIDATE_MANIFEST_ARCHIVE_REF = "7387e9e7310e9cd6eca2fc5abf56451c2e1b73a9"
AUXILIARY_CANDIDATE_MANIFEST_URL = (
    "https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/"
    + AUXILIARY_CANDIDATE_COMMIT
    + "/reports/warder-master-production/auxiliary-hybrid-runtime-candidate-2026-10-07/candidate-downloads.json"
)
AUXILIARY_CANDIDATE_ARCHIVE_ROOT = (
    "https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/"
    + AUXILIARY_CANDIDATE_COMMIT
    + "/reports/warder-master-production/auxiliary-hybrid-runtime-candidate-2026-10-07/archives/"
)
AUXILIARY_CANDIDATE_MANIFEST_ARCHIVE_ROOT = AUXILIARY_CANDIDATE_ARCHIVE_ROOT.replace(
    AUXILIARY_CANDIDATE_COMMIT, AUXILIARY_CANDIDATE_MANIFEST_ARCHIVE_REF)
AUXILIARY_PUBLICATION_SOURCES = {
    "fullhd-test": {
        "expected_origin": "raw.githubusercontent.com",
        "repository": "Evolution-by-Warder/FullHDGlass-Warder-Evolution",
        "ref": "warder-modernization-work",
        "pinned_commit": None,
        "manifest_url": "https://raw.githubusercontent.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/warder-modernization-work/assets/warder/downloads.json",
        "source_root": "https://raw.githubusercontent.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/warder-modernization-work/assets/warder/downloads/",
        "package_root": "https://raw.githubusercontent.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/warder-modernization-work/assets/warder/downloads/",
        "redirect_root": "https://raw.githubusercontent.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/warder-modernization-work/assets/warder/downloads/",
    },
    "fullhd-provider-bundle": {
        "expected_origin": "raw.githubusercontent.com",
        "repository": "Evolution-by-Warder/FullHDGlass-Warder-Evolution",
        "ref": "cf9e93e60d6f345ad33a0275a980487bff45bc98",
        "pinned_commit": "cf9e93e60d6f345ad33a0275a980487bff45bc98",
        "manifest_url": "https://raw.githubusercontent.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/cf9e93e60d6f345ad33a0275a980487bff45bc98/assets/warder/downloads.json",
        "source_root": "https://raw.githubusercontent.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/cf9e93e60d6f345ad33a0275a980487bff45bc98/assets/warder/downloads/",
        "package_root": "https://raw.githubusercontent.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/cf9e93e60d6f345ad33a0275a980487bff45bc98/assets/warder/downloads/",
        "redirect_root": "https://raw.githubusercontent.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/cf9e93e60d6f345ad33a0275a980487bff45bc98/assets/warder/downloads/",
    },
    "fullhd-production": {
        "expected_origin": "raw.githubusercontent.com",
        "repository": "Evolution-by-Warder/FullHDGlass-Warder-Evolution",
        "ref": "main",
        "pinned_commit": None,
        "manifest_url": "https://raw.githubusercontent.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/main/assets/warder/downloads.json",
        "source_root": "https://raw.githubusercontent.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/main/assets/warder/downloads/",
        "package_root": "https://raw.githubusercontent.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/main/assets/warder/downloads/",
        "redirect_root": "https://raw.githubusercontent.com/Evolution-by-Warder/FullHDGlass-Warder-Evolution/main/assets/warder/downloads/",
    },
    "piconhub-aux-candidate": {
        "expected_origin": "raw.githubusercontent.com",
        "repository": "Evolution-by-Warder/PiconHub-Warder-Evolution",
        "ref": AUXILIARY_CANDIDATE_COMMIT,
        "pinned_commit": AUXILIARY_CANDIDATE_COMMIT,
        "manifest_url": AUXILIARY_CANDIDATE_MANIFEST_URL,
        "manifest_archive_root": AUXILIARY_CANDIDATE_MANIFEST_ARCHIVE_ROOT,
        "source_root": AUXILIARY_CANDIDATE_ARCHIVE_ROOT.rsplit("archives/", 1)[0],
        "package_root": AUXILIARY_CANDIDATE_ARCHIVE_ROOT,
        "redirect_root": AUXILIARY_CANDIDATE_ARCHIVE_ROOT,
    },
}

# Exact archive pins from PiconHub's candidate-downloads.json at the commit
# above. Keep this allowlist separate from the FullHD production URL root.
AUXILIARY_CANDIDATE_ASSETS = {
    "piconProv-legacy-t": ("provider-transparent-legacy-fallback.zip", 11462366, "ee325732bb83ac36b25d16e5f3b65eb4312eb251528689cc6ae3d938ea5be7f0", "piconProv", 1145),
    "piconProv-warder-safe-b": ("provider-black-warder-safe-220x132.zip", 5736394, "7b7499ca87529fd89859b3f10b8bd76ed8234a268f93c29e94fe3e23f075bb3d", "piconProv_220x132", 172),
    "piconProv-warder-safe-t": ("provider-transparent-warder-safe-220x132.zip", 1081152, "ffb5e4a8afd2ce8f5873f67883ecbb93ba892b9983eefc3e3e9b4c76ff1189fe", "piconProv_220x132", 172),
    "piconProv-warder-safe-w": ("provider-white-warder-safe-220x132.zip", 5752522, "5e95db06d006ef212d8d3e756ffa067fe18b0bbc5f2c8825cebaa8ba6222e4ae", "piconProv_220x132", 172),
    "piconSat-legacy-t": ("satellite-transparent-legacy-fallback.zip", 773004, "c134ac5b7d9fdb2ba80b87e8a4b5671537ae634ef9b495b17e783b314394942a", "piconSat", 69),
    "piconSat-warder-safe-b": ("satellite-black-warder-safe-220x132.zip", 36521, "0808057c83a060fff98aa0bf0f1d2c2cda5b49ea9574b44af3e1a47d9477ed0e", "piconSat_220x132", 1),
    "piconSat-warder-safe-t": ("satellite-transparent-warder-safe-220x132.zip", 8400, "9d52030633e5b88af40ea1b806862cdd6ad866fb3453ea1993aac4e6fdf33abf", "piconSat_220x132", 1),
    "piconSat-warder-safe-w": ("satellite-white-warder-safe-220x132.zip", 36634, "9d55e86a420bfce1e7ad25eee8e5fba823b796119efd1665ee45109af684166e", "piconSat_220x132", 1),
}
AUXILIARY_PUBLICATION_SOURCES["piconhub-aux-candidate"]["allowed_paths"] = tuple(
    AUXILIARY_CANDIDATE_ARCHIVE_ROOT + item[0]
    for item in AUXILIARY_CANDIDATE_ASSETS.values())
AUXILIARY_LEGACY_FALLBACK_PINS = {
    "piconProv-b": (12059628, "0a492f508eb05783d2135118f21abc370e33efe7d02db48d1577c2c2634c91e3", "piconProv", 1299),
    "piconProv-transparent-fullhd": (11471774, "f9df118455826f6f240ea7b1c9b1959af7bc43ce1a6e2459ae7480f12ad4a929", "piconProv", 1148),
    "piconProv-w": (14038220, "68d747b5ea47611c35ba1ab93e3b63b0266298a810d09c9e0bd5c204dfa7452e", "piconProv", 1258),
    "piconSat-b": (2244970, "6458bdf32db1dddd21ecf8894864e130d5c5535fcfe7fe2681509ad7b0958d8a", "piconSat", 269),
    "piconSat-w": (2421870, "539cda4f3f599f5e3f2b6e6690a4625fc5c678bdfb46cb9b1b68622d28b08b2b", "piconSat", 269),
}
AUXILIARY_VARIANT_IDS = {
    "piconProv": {"transparent": ("piconProv-transparent-fullhd", "piconProv-warder-safe-t"),
                  "black": ("piconProv-b", "piconProv-warder-safe-b"),
                  "white": ("piconProv-w", "piconProv-warder-safe-w")},
    "piconSat": {"transparent": ("piconSat-legacy-t", "piconSat-warder-safe-t"),
                 "black": ("piconSat-b", "piconSat-warder-safe-b"),
                 "white": ("piconSat-w", "piconSat-warder-safe-w")},
}
_BOUQUET_RE = re.compile(r'FROM BOUQUET "([^"]+)"', re.I)
_HEX = re.compile(r"^[0-9A-Fa-f]+$")


def normalize_service_reference(reference):
    """Return the canonical Enigma2 picon filename stem for a service ref."""
    if reference is None:
        return ""
    ref = str(reference).strip()
    if ref.startswith("#SERVICE"):
        ref = ref.split(None, 1)[1].strip() if " " in ref else ""
    ref = ref.split("::", 1)[0].strip()
    if ":" in ref:
        fields = ref.split(":")
    else:
        fields = ref.split("_")
    if len(fields) < 10:
        return ""
    fields = fields[:10]
    if not all(_HEX.match(x or "0") for x in fields):
        return ""
    return "_".join((x or "0").upper() for x in fields)


def namespace_to_orbital_position(namespace):
    """Map DVB-S namespace to PiconHub folder form such as 23.5e or 0.8w."""
    try:
        value = int(str(namespace), 16) if not isinstance(namespace, int) else namespace
    except (TypeError, ValueError):
        return None
    orbital = (value >> 16) & 0xFFFF
    if orbital == 0 or orbital == 0xFFFF:
        return None
    if orbital > 1800:
        orbital = 3600 - orbital
        suffix = "w"
    else:
        suffix = "e"
    return "%d.%d%s" % (orbital // 10, orbital % 10, suffix)


def position_token(position):
    """Normalize a canonical orbital token only; display labels are not parsed."""
    text = str(position or "").strip().lower()
    if text in ("dtt", "eee"):
        return "dtt"
    if re.match(r"^[0-9]+(?:\.[0-9]+)?[ew]$", text):
        return text
    return text


def service_orbital_position(reference):
    stem = normalize_service_reference(reference)
    if not stem:
        return None
    fields = stem.split("_")
    return namespace_to_orbital_position(fields[6])


def _read_lines(path):
    try:
        with open(path, "r") as handle:
            return handle.readlines()
    except (IOError, OSError):
        return []


def bouquet_files(enigma2_dir=ENIGMA2_DIR, root_name="bouquets.tv"):
    """Return bouquet files referenced by bouquets.tv, preserving user order."""
    result = []
    seen = set()
    for line in _read_lines(os.path.join(enigma2_dir, root_name)):
        match = _BOUQUET_RE.search(line)
        if not match:
            continue
        name = os.path.basename(match.group(1))
        if name in seen:
            continue
        seen.add(name)
        result.append(os.path.join(enigma2_dir, name))
    return result


def bouquet_services(enigma2_dir=ENIGMA2_DIR, include_radio=False):
    """Read exact playable service references from receiver bouquet files."""
    roots = ["bouquets.tv"]
    if include_radio:
        roots.append("bouquets.radio")
    refs = []
    seen = set()
    for root in roots:
        for path in bouquet_files(enigma2_dir, root):
            for line in _read_lines(path):
                if not line.startswith("#SERVICE"):
                    continue
                raw = line[len("#SERVICE"):].strip()
                if "FROM BOUQUET" in raw.upper():
                    continue
                stem = normalize_service_reference(raw)
                if not stem or stem in seen:
                    continue
                seen.add(stem)
                refs.append(stem)
    return refs


def build_sync_request(enigma2_dir=ENIGMA2_DIR, selected_positions=None,
                       style="transparent", resolution="220x132",
                       include_radio=False):
    """Build a deterministic receiver-driven request; no provider guessing."""
    selected = set(x.lower() for x in (selected_positions or []) if x)
    if not selected:
        raise ValueError("no-satellite-position-selected")
    services = []
    for stem in bouquet_services(enigma2_dir, include_radio):
        position = service_orbital_position(stem.replace("_", ":"))
        if selected and (not position or position.lower() not in selected):
            continue
        services.append({"service_reference": stem, "position": position})
    return {
        "mode": UPDATE_MODE_SYNC_TV_RADIO if include_radio else UPDATE_MODE_SYNC_TV,
        "style": style,
        "resolution": resolution,
        "services": services,
    }


UPDATE_MODE_SYNC_TV = "sync-tv-lists"
UPDATE_MODE_SYNC_TV_RADIO = "sync-tv-radio-lists"
UPDATE_MODE_REPLACE_ALL = "replace-all-selected"
UPDATE_MODE_INCREMENTAL = "incremental-selected"
# Kept for source compatibility with TEST195 callers; its package-copy mode is
# now explicitly named incremental rather than the ambiguous legacy "FULL".
UPDATE_MODE_FULL = UPDATE_MODE_INCREMENTAL
DEFAULT_UPDATE_MODE = None
DEFAULT_STYLE = None
DEFAULT_RESOLUTION = None
DEFAULT_DESTINATION = "/usr/share/enigma2/picon"
CHANNEL_RESOLUTION_CHOICES = (
    ("50x30", "50 x 30 - Mini picons"),
    ("220x132", "220 x 132 - Picons"),
    ("400x240", "400 x 240 - Large picons"),
)
CANALPLUS_SELECTOR_IDS = ("CANALPLUS_SK", "CANALPLUS_CZ")


def channel_resolution_choices(package_selectors=None):
    """Return the original channel picon sizes for every provider selection."""
    return CHANNEL_RESOLUTION_CHOICES


AUXILIARY_ASSET_KEYS = (
    "piconProv-220", "piconProv-b", "piconProv-w",
    "piconProv-canalplus-t", "piconProv-canalplus-b", "piconProv-canalplus-w",
    "piconSat-220", "piconSat-b", "piconSat-w",
    "piconCam-b", "piconCam-w",
    "piconWeather-b", "piconWeather-w",
)
CANAL_PROVIDER_BUNDLE_ASSETS = {
    "transparent": ("piconProv-canalplus-t", "provider-canalplus-transparent.zip",
                    ("CANALPLUS_SK.png", "CANALPLUS_CZ.png")),
    "black": ("piconProv-canalplus-b", "provider-canalplus-black.zip",
              ("CANALPLUS_SK.png", "CANALPLUS_CZ.png")),
    "white": ("piconProv-canalplus-w", "provider-canalplus-white.zip",
              ("CANALPLUS_SK.png", "CANALPLUS_CZ.png")),
}
PICON_DESTINATIONS = (
    ("/usr/share/enigma2/picon", "Receiver memory"),
    ("/media/hdd/picon", "Hard disk"),
    ("/media/usb/picon", "USB storage"),
    ("/media/sdcard/picon", "SD card"),
    ("/media/mmc/picon", "MMC storage"),
    ("/picon", "Root picon directory"),
)

UPDATE_MODES = (
    (UPDATE_MODE_SYNC_TV, "Synchronize with TV lists"),
    (UPDATE_MODE_SYNC_TV_RADIO, "Synchronize with TV and radio lists"),
    (UPDATE_MODE_REPLACE_ALL, "Copy all; replace current selected-position picons"),
    (UPDATE_MODE_INCREMENTAL, "Copy all; incremental update"),
)
STYLES = (
    ("transparent", "Transparent"),
    ("black", "Black"),
    ("white", "White"),
)
RESOLUTIONS = (
    ("220x132", "220 x 132"),
    ("400x240", "400 x 240"),
)


# Genuine delivery options recovered from the pinned FullHDGlass/Trezor catalog.
# 220x132 transparent/black/white is the native Warder channel package triad.
CHANNEL_RESOLUTION_STYLES = {
    "50x30": ("transparent", "black", "white"),
    "150x90": ("black", "white"),
    "220x132": ("transparent", "black", "white"),
    "400x240": ("transparent", "black", "white"),
}
LEGACY_CHANNEL_ARCHIVE_COLUMNS = {
    ("400x240", "transparent"): 3,
    ("50x30", "black"): 4,
    ("150x90", "black"): 5,
    ("50x30", "white"): 6,
    ("150x90", "white"): 7,
    ("220x132", "transparent"): 9,
}
LEGACY_CHANNEL_DESTINATIONS = {
    "50x30": "picon_50x30",
    "150x90": "picon",
    "220x132": "picon_220x132",
    "400x240": "picon_400x240",
}


def channel_style_supported(resolution, style):
    return style in CHANNEL_RESOLUTION_STYLES.get(str(resolution), ())


def channel_delivery_backend(resolution, style):
    if not channel_style_supported(resolution, style):
        return None
    return "warder" if resolution in ("50x30", "220x132", "400x240") else "pinned-legacy"


def legacy_channel_archive_column(resolution, style):
    return LEGACY_CHANNEL_ARCHIVE_COLUMNS.get((str(resolution), str(style)))


def legacy_channel_destination(resolution):
    return LEGACY_CHANNEL_DESTINATIONS.get(str(resolution))


def plan_legacy_channel_archives(selected_selector_ids, satlist, resolution, style):
    """Resolve explicit selector IDs to the matching pinned SATLIST archive column."""
    selectors = list(selected_selector_ids or [])
    if not valid_position_selection(selectors):
        raise ValueError("no-satellite-position-selected")
    column = legacy_channel_archive_column(resolution, style)
    if column is None:
        raise ValueError("no-pinned-channel-archive-for-resolution-and-colour")
    by_selector = {}
    for row in satlist or []:
        if not row:
            continue
        selector = selector_id_for_display_label(row[0])
        if not selector:
            continue
        if selector in by_selector:
            raise ValueError("ambiguous-satellite-package-selector")
        by_selector[selector] = row
    result = []
    seen_ids = set()
    for selector in selectors:
        row = by_selector.get(selector)
        if row is None or len(row) <= column:
            raise ValueError("satellite-position-not-in-pinned-archive-catalog")
        archive_id = str(row[column] or "").strip()
        if not re.match(r"^[0-9]{1,5}$", archive_id):
            raise ValueError("pinned-channel-archive-not-available-for-selected-position")
        if archive_id in seen_ids:
            raise ValueError("duplicate-pinned-channel-archive")
        seen_ids.add(archive_id)
        result.append((selector, archive_id))
    return result


def default_preferences(destination=DEFAULT_DESTINATION):
    return {
        "positions": [],
        "package_selectors": [],
        "position_bindings": [],
        "resolution": None,
        "style": None,
        "destination": destination or DEFAULT_DESTINATION,
        "update_mode": None,
        "prepared": False,
    }


def reset_working_preferences(preferences=None):
    """Return the deliberate empty state used after a fully successful action."""
    return default_preferences(DEFAULT_DESTINATION)


def preferences_after_task(preferences, outcome):
    """Reset only after success; Cancel and Error retain a retryable snapshot."""
    state = str(outcome or "").lower()
    if state == "success":
        return reset_working_preferences(preferences)
    if state in ("cancel", "error"):
        return dict(preferences or {})
    raise ValueError("unknown Warder task outcome")


def set_task_position_bindings(preferences, bindings):
    result = dict(default_preferences())
    result.update(preferences or {})
    original = list(bindings or [])
    normalized = normalize_position_bindings(original)
    if len(normalized) != len(original):
        normalized = []
    result["position_bindings"] = normalized
    result["positions"] = task_positions_from_bindings(normalized)
    result["package_selectors"] = task_package_selectors_from_bindings(normalized)
    result["prepared"] = bool(normalized)
    return result


def channel_preferences_ready(preferences):
    prefs = dict(preferences or {})
    return bool(valid_task_selection(prefs)
                and prefs.get("resolution") in tuple(size for size, label in CHANNEL_RESOLUTION_CHOICES)
                and prefs.get("style") in dict(STYLES)
                and channel_style_supported(prefs.get("resolution"), prefs.get("style"))
                and prefs.get("update_mode") in dict(UPDATE_MODES)
                and validate_destination(prefs.get("destination")))


def auxiliary_variants(asset_keys):
    """List only real catalog-backed variants, in a stable color order."""
    definitions = {
        "piconProv": (("piconProv-220", "Transparent"), ("piconProv-b", "Black"), ("piconProv-w", "White")),
        "piconSat": (("piconSat-220", "Transparent"), ("piconSat-b", "Black"), ("piconSat-w", "White")),
        "piconCam": (("piconCam-220", "Transparent"), ("piconCam-b", "Black"), ("piconCam-w", "White")),
        "piconWeather": (("piconWeather-220", "Transparent"), ("piconWeather-b", "Black"), ("piconWeather-w", "White")),
    }
    available = set(asset_keys or [])
    return {kind: tuple((key, label) for key, label in options if key in available)
            for kind, options in definitions.items()}


def auxiliary_hybrid_variants(kind):
    """Keep the original three color choices for provider and satellite packs."""
    if kind not in AUXILIARY_VARIANT_IDS:
        return ()
    return (("transparent", "Transparent"), ("black", "Black"), ("white", "White"))


def trusted_auxiliary_url(url, source_id):
    """Validate an auxiliary URL against one isolated publication descriptor."""
    source = AUXILIARY_PUBLICATION_SOURCES.get(source_id)
    if not source:
        return False
    try:
        parsed = urlparse(str(url))
        root = source["package_root"]
        parsed_root = urlparse(root)
    except Exception:
        return False
    if (parsed.scheme != "https" or parsed.netloc != source["expected_origin"]
            or parsed.hostname != source["expected_origin"] or parsed.username or parsed.password
            or parsed.query or parsed.fragment or "%" in parsed.path or "\\" in parsed.path):
        return False
    root_path = parsed_root.path
    if not parsed.path.startswith(root_path) or not root_path.endswith("/"):
        return False
    tail = parsed.path[len(root_path):]
    if not tail or any(part in ("", ".", "..") for part in tail.split("/")):
        return False
    if source_id == "piconhub-aux-candidate":
        return str(url) in source["allowed_paths"]
    return bool(re.match(r"^[A-Za-z0-9._/-]+$", tail))


def validate_auxiliary_candidate_manifest(document, manifest_url=None):
    """Require the immutable PiconHub manifest and all eight exact archive pins."""
    errors = []
    descriptor = AUXILIARY_PUBLICATION_SOURCES["piconhub-aux-candidate"]
    if manifest_url != descriptor["manifest_url"]:
        errors.append("auxiliary candidate manifest URL mismatch")
    if not isinstance(document, dict):
        return errors + ["auxiliary candidate manifest is not an object"]
    if (descriptor.get("ref") != AUXILIARY_CANDIDATE_COMMIT
            or AUXILIARY_CANDIDATE_COMMIT not in str(manifest_url or "")):
        errors.append("auxiliary candidate commit mismatch")
    assets = document.get("assets")
    if not isinstance(assets, dict):
        return errors + ["auxiliary candidate assets missing"]
    if set(assets) != set(AUXILIARY_CANDIDATE_ASSETS):
        errors.append("auxiliary candidate asset set mismatch")
    for asset_id, expected in AUXILIARY_CANDIDATE_ASSETS.items():
        item = assets.get(asset_id)
        if not isinstance(item, dict):
            errors.append("auxiliary candidate asset missing: " + asset_id)
            continue
        filename, size, sha, root, count = expected
        # candidate-downloads.json has historical archive locator URLs. They
        # are metadata only; runtime fetches are separately pinned to db5eec9.
        manifest_asset_url = descriptor["manifest_archive_root"] + filename
        classification = "LEGACY_FALLBACK_ONLY" if asset_id.endswith("legacy-t") else "WARDER_SAFE_APPROVED"
        if (item.get("filename") != filename or item.get("archive") not in (None, filename)
                or item.get("size") != size or item.get("size_bytes") not in (None, size)
                or item.get("sha256") != sha or item.get("root") != root
                or item.get("classification") != classification
                or item.get("destination") not in (None, root)
                or item.get("url") != manifest_asset_url):
            errors.append("auxiliary candidate pin mismatch: " + asset_id)
    return errors


def validate_auxiliary_hybrid_catalog(document, candidate_manifest=None):
    """Validate catalog mapping, exact pins, and fallback/safe separation."""
    errors = []
    if not isinstance(document, dict) or not isinstance(document.get("assets"), dict):
        return ["invalid FullHD auxiliary catalog"]
    hybrid = document.get("auxiliary_hybrid")
    if not isinstance(hybrid, dict) or hybrid.get("schema") != 1:
        return ["auxiliary hybrid mapping missing"]
    if hybrid.get("candidate_commit") != AUXILIARY_CANDIDATE_COMMIT:
        errors.append("auxiliary hybrid commit mismatch")
    if hybrid.get("candidate_manifest_url") != AUXILIARY_CANDIDATE_MANIFEST_URL:
        errors.append("auxiliary hybrid manifest URL mismatch")
    if hybrid.get("candidate_source_id") != "piconhub-aux-candidate":
        errors.append("auxiliary hybrid source mismatch")
    assets = document["assets"]
    for asset_id, expected in AUXILIARY_CANDIDATE_ASSETS.items():
        item = assets.get(asset_id)
        filename, size, sha, root, count = expected
        expected_url = AUXILIARY_PUBLICATION_SOURCES["piconhub-aux-candidate"]["package_root"] + filename
        classification = "LEGACY_FALLBACK_ONLY" if asset_id.endswith("legacy-t") else "WARDER_SAFE_APPROVED"
        if (not isinstance(item, dict) or item.get("filename") != filename
                or item.get("size") != size or item.get("sha256") != sha
                or item.get("root") != root or item.get("png_count") != count
                or item.get("classification") != classification
                or item.get("url") != expected_url
                or item.get("publication_source_id") != "piconhub-aux-candidate"):
            errors.append("FullHD auxiliary candidate mapping mismatch: " + asset_id)
    for kind, domainspec in (("provider", "piconProv"), ("satellite", "piconSat")):
        domain = hybrid.get("domains", {}).get(kind, {})
        if (domain.get("base_fallback_directory") != domainspec
                or domain.get("priority_directory") != domainspec + "_220x132"
                or domain.get("lookup_priority") != [domainspec + "_220x132", domainspec]):
            errors.append("auxiliary destination/lookup mismatch: " + kind)
        variants = domain.get("variants", {})
        for variant, (fallback_id, safe_id) in AUXILIARY_VARIANT_IDS[domainspec].items():
            spec = variants.get(variant, {})
            if (spec.get("fallback_asset_id") != fallback_id or spec.get("safe_asset_id") != safe_id
                    or spec.get("install_order") != ["legacy_fallback", "warder_safe_priority"]):
                errors.append("auxiliary job mapping mismatch: %s/%s" % (kind, variant))
            fallback = assets.get(fallback_id, {})
            if fallback_id not in AUXILIARY_CANDIDATE_ASSETS:
                pin = AUXILIARY_LEGACY_FALLBACK_PINS.get(fallback_id)
                source_id = fallback.get("publication_source_id", "fullhd-production")
                if (pin is None or source_id not in ("fullhd-production", "fullhd-test")
                        or not trusted_auxiliary_url(fallback.get("url", ""), source_id)
                        or fallback.get("root") != pin[2] or fallback.get("size") != pin[0]
                        or fallback.get("sha256") != pin[1]
                        or spec.get("fallback_png_count") != pin[3]
                        or spec.get("fallback_size_bytes") != pin[0]
                        or spec.get("fallback_sha256") != pin[1]):
                    errors.append("unsafe auxiliary legacy fallback: " + fallback_id)
            else:
                pin = AUXILIARY_CANDIDATE_ASSETS[fallback_id]
                if (spec.get("fallback_png_count") != pin[4]
                        or spec.get("fallback_size_bytes") != pin[1]
                        or spec.get("fallback_sha256") != pin[2]):
                    errors.append("auxiliary candidate fallback metadata mismatch: " + fallback_id)
            safe = assets.get(safe_id, {})
            safe_pin = AUXILIARY_CANDIDATE_ASSETS.get(safe_id)
            if (safe_pin is None or safe.get("publication_source_id") != "piconhub-aux-candidate"
                    or safe.get("root") != domainspec + "_220x132"
                    or safe.get("size") != safe_pin[1] or safe.get("sha256") != safe_pin[2]
                    or spec.get("safe_png_count") != safe_pin[4]):
                errors.append("unsafe auxiliary safe overlay: " + safe_id)
    if candidate_manifest is not None:
        errors.extend(validate_auxiliary_candidate_manifest(candidate_manifest, hybrid.get("candidate_manifest_url")))
        candidate_assets = candidate_manifest.get("assets", {}) if isinstance(candidate_manifest, dict) else {}
        for asset_id in AUXILIARY_CANDIDATE_ASSETS:
            if assets.get(asset_id) != candidate_assets.get(asset_id):
                # FullHD catalog adds source metadata; compare the pinned payload fields only.
                local = assets.get(asset_id, {})
                remote = candidate_assets.get(asset_id, {})
                if any(local.get(key) != remote.get(key) for key in ("filename", "size", "sha256", "root")):
                    errors.append("catalog/candidate manifest disagreement: " + asset_id)
    return errors


def build_auxiliary_jobs(document, candidate_manifest, domain_kind, variant):
    """Return exactly fallback then safe-overlay jobs for one GUI variant."""
    errors = validate_auxiliary_hybrid_catalog(document, candidate_manifest)
    if errors:
        return {"state": "invalid-catalog", "jobs": [], "errors": errors}
    if domain_kind not in ("provider", "satellite") or variant not in ("transparent", "black", "white"):
        return {"state": "invalid-selection", "jobs": [], "errors": ["invalid auxiliary selection"]}
    hybrid_domain = document["auxiliary_hybrid"]["domains"][domain_kind]
    spec = hybrid_domain["variants"][variant]
    jobs = []
    for layer, asset_id in (("legacy_fallback", spec["fallback_asset_id"]),
                            ("warder_safe_priority", spec["safe_asset_id"])):
        asset = dict(document["assets"][asset_id])
        if asset_id in AUXILIARY_CANDIDATE_ASSETS:
            expected = AUXILIARY_CANDIDATE_ASSETS[asset_id]
            asset["png_count"] = expected[4]
            asset["publication_source_id"] = "piconhub-aux-candidate"
        else:
            asset["publication_source_id"] = document["assets"][asset_id].get("publication_source_id", "fullhd-production")
            asset["png_count"] = spec["fallback_png_count"]
        if asset.get("root") != spec["fallback_destination" if layer == "legacy_fallback" else "safe_destination"]:
            return {"state": "invalid-catalog", "jobs": [], "errors": ["auxiliary job root mismatch"]}
        asset.update({"asset_id": asset_id, "layer": layer, "domain": domain_kind,
                      "variant": variant, "destination": spec["fallback_destination" if layer == "legacy_fallback" else "safe_destination"]})
        jobs.append(asset)
    return {"state": "ready", "jobs": jobs, "errors": []}


def validate_auxiliary_archive(archive_path, asset):
    """Verify archive bytes, ZIP CRC, exact root, PNG-only members, and count."""
    try:
        if not os.path.isfile(archive_path) or os.path.islink(archive_path):
            return ["auxiliary archive is not a regular file"]
        expected_size = int(asset.get("size", -1))
        if expected_size < 1 or os.path.getsize(archive_path) != expected_size:
            return ["auxiliary archive size mismatch"]
        digest = hashlib.sha256()
        with open(archive_path, "rb") as stream:
            magic = stream.read(8)
            if magic.startswith(b"<!DOCTYPE") or magic.startswith(b"<html") or not magic.startswith(b"PK"):
                return ["auxiliary archive is not a ZIP"]
            stream.seek(0)
            for chunk in iter(lambda: stream.read(1024 * 128), b""):
                digest.update(chunk)
        if digest.hexdigest().lower() != str(asset.get("sha256", "")).lower():
            return ["auxiliary archive SHA-256 mismatch"]
        root = str(asset.get("root", ""))
        if not root or "/" in root or "\\" in root or root in (".", ".."):
            return ["invalid auxiliary archive root"]
        count = 0
        names = set()
        with zipfile.ZipFile(archive_path, "r") as package:
            if package.testzip() is not None:
                return ["auxiliary archive CRC failure"]
            for info in package.infolist():
                name = info.filename.replace("\\", "/")
                if not name or name.startswith("/") or any(x in ("", ".", "..") for x in name.rstrip("/").split("/")):
                    return ["unsafe auxiliary ZIP path"]
                if name.rstrip("/") == root and info.is_dir():
                    continue
                parts = name.split("/")
                if len(parts) != 2 or parts[0] != root or not parts[1].lower().endswith(".png") or info.is_dir():
                    return ["auxiliary ZIP root/member mismatch"]
                mode = (info.external_attr >> 16) & 0xFFFF
                file_type = stat.S_IFMT(mode)
                if stat.S_ISLNK(mode) or (file_type and file_type != stat.S_IFREG):
                    return ["non-regular auxiliary ZIP member"]
                key = parts[1].lower()
                if key in names:
                    return ["duplicate auxiliary ZIP filename"]
                with package.open(info, "r") as png:
                    if png.read(8) != b"\x89PNG\r\n\x1a\n":
                        return ["auxiliary ZIP contains a non-PNG payload"]
                names.add(key)
                count += 1
        if count != int(asset.get("png_count", -1)):
            return ["auxiliary archive PNG count mismatch"]
    except (IOError, OSError, ValueError, zipfile.BadZipFile, RuntimeError) as err:
        return ["invalid auxiliary archive: " + str(err)]
    return []


def set_preference(preferences, key, value):
    """Return a copied preference state and mark it as a prepared action."""
    if key not in ("positions", "resolution", "style", "destination", "update_mode"):
        raise KeyError(key)
    result = dict(preferences)
    result[key] = value
    result["prepared"] = True
    return result


def has_executable_action(preferences, ordinary_selected=False):
    """Mirror FullHDGlass blue-button semantics for the assimilated planner."""
    return bool(ordinary_selected or preferences.get("prepared", False))


PUBLICATION_LOCKED = "publication-locked"
READY = "ready"


# SATLIST identity must stay separate from orbital filtering. Provider selectors can
# share one orbital position, while nearby legacy selectors may have distinct IDs.
_SELECTOR_LABEL_BINDINGS = {
    "(0.8W) Freesat": (
        "FREESAT",
        "0.8w"
    ),
    "(0.8W) Digi / Telly": (
        "DIGI_TELLY",
        "0.8w"
    ),
    "(16.0E) Antiksat": (
        "ANTIKSAT",
        "16.0e"
    ),
    "(23.5E) Canal+ SK": (
        "CANALPLUS_SK",
        "23.5e"
    ),
    "(23.5E) Canal+ CZ": (
        "CANALPLUS_CZ",
        "23.5e"
    ),
    "DVB-T sk/cz": (
        "DVB-T-SK-CZ",
        "dtt"
    ),
    "(45.0W) Intelsat 14 (IS-14)": (
        "450W",
        "45.0w"
    ),
    "(30.0W) Hispasat 1D,1E": (
        "300W",
        "30.0w"
    ),
    "(27.5W) Intelsat 907": (
        "275W",
        "27.5w"
    ),
    "(24.5W) AlcomSat 1": (
        "248W",
        "24.5w"
    ),
    "(22.0W) SES 4": (
        "220W",
        "22.0w"
    ),
    "(15.0W) Telstar 12": (
        "150W",
        "15.0w"
    ),
    "(14.0W) Express AM8": (
        "140W",
        "14.0w"
    ),
    "(8.0W) Eutelsat 8 West B,D": (
        "80W",
        "8.0w"
    ),
    "(7.0W) Nilesat 102,201/Eutelsat 7 West A": (
        "70W",
        "7.0w"
    ),
    "(5.0W) Eutelsat 5 West A,B": (
        "50W",
        "5.0w"
    ),
    "(4.0W) Amos 2/Amos 3": (
        "40W",
        "4.0w"
    ),
    "(1.0W) Thor 5,6,7/Intelsat 10-02": (
        "10W",
        "1.0w"
    ),
    "(0.8W) Thor 5,6,7/Intelsat 10-02": (
        "08W",
        "0.8w"
    ),
    "(1.9E) BulgariaSat-1": (
        "19E",
        "1.9e"
    ),
    "(3.0E) Eutelsat 3B": (
        "30E",
        "3.0e"
    ),
    "(4.8E) SES 5/Astra 4A": (
        "48E_A",
        "4.8e"
    ),
    "(4.9E) SES 5/Astra 4A": (
        "48E_B",
        "4.9e"
    ),
    "(7.0E) Eutelsat 7A/7B": (
        "70E",
        "7.0e"
    ),
    "(9.0E) Eutelsat 9A": (
        "90E",
        "9.0e"
    ),
    "(10.0E) Eutelsat 10A": (
        "100E",
        "10.0e"
    ),
    "(13.0E) Hot Bird 13B/13C/13D": (
        "130E",
        "13.0e"
    ),
    "(16.0E) Eutelsat 16A": (
        "160E",
        "16.0e"
    ),
    "(19.2E) Astra 1KR,1L,1M,1N": (
        "192E",
        "19.2e"
    ),
    "(21.5E) Eutelsat 21B": (
        "216E",
        "21.5e"
    ),
    "(23.5E) Astra 3B": (
        "235E",
        "23.5e"
    ),
    "(26.0E) Badr 4,5,6": (
        "260E",
        "26.0e"
    ),
    "(28.2E) Astra 2A,2E,2F,2G": (
        "282E",
        "28.2e"
    ),
    "(30.5E) Arabsat 5A,6A": (
        "305E",
        "30.5e"
    ),
    "(31.5E) Astra 1G,5B": (
        "315E",
        "31.5e"
    ),
    "(33.0E) Eutelsat 33C": (
        "330E",
        "33.0e"
    ),
    "(36.0E) Eutelsat 36A,36B": (
        "360E",
        "36.0e"
    ),
    "(39.0E) Hellas Sat 2": (
        "390E",
        "39.0e"
    ),
    "(42.0E) Turksat 2A,3A,4A": (
        "420E",
        "42.0e"
    ),
    "(45.0E) Intelsat 12 (IS-12)": (
        "450E",
        "45.0e"
    ),
    "(46.0E) Azerspace-1": (
        "460E",
        "46.0e"
    ),
    "(51.5E) Belintersat 1": (
        "515E",
        "51.5e"
    ),
    "(52.0E) TurkmenAlem/MonacoSat": (
        "520E",
        "52.0e"
    ),
    "(52.5E) Yahsat 1A": (
        "525E",
        "52.5e"
    ),
    "(53.0E) Express AM6": (
        "530E",
        "53.0e"
    ),
    "(54.9E) Yamal 402": (
        "549E",
        "54.9e"
    ),
    "(56.0E) Express AT1": (
        "560E",
        "56.0e"
    ),
    "(62.0E) Intelsat 902": (
        "620E",
        "62.0e"
    ),
    "(66.0E) Intelsat 17": (
        "660E",
        "66.0e"
    ),
    "(68.5E) Intelsat 20 (IS-20)": (
        "685E",
        "68.5e"
    ),
    "(70.5E) Eutelsat 70B": (
        "705E",
        "70.5e"
    ),
    "(75.0E) ABS 2/ABS 2A": (
        "750E",
        "75.0e"
    ),
    "(80.0E) Satelit 80.0E": ("800E", "80.0e"),
    "(0.8W) Digi": ("DIGI_TELLY", "0.8w"),
    "(0.8W) Telly": ("DIGI_TELLY", "0.8w"),
    "(0.8W) Digi/Telly": (
        "DIGI_TELLY",
        "0.8w"
    )
}
_SELECTOR_ID_TO_POSITION = {
    "FREESAT": "0.8w",
    "DIGI_TELLY": "0.8w",
    "ANTIKSAT": "16.0e",
    "CANALPLUS_SK": "23.5e",
    "CANALPLUS_CZ": "23.5e",
    "DVB-T-SK-CZ": "dtt",
    "450W": "45.0w",
    "300W": "30.0w",
    "275W": "27.5w",
    "248W": "24.5w",
    "220W": "22.0w",
    "150W": "15.0w",
    "140W": "14.0w",
    "80W": "8.0w",
    "70W": "7.0w",
    "50W": "5.0w",
    "40W": "4.0w",
    "10W": "1.0w",
    "08W": "0.8w",
    "19E": "1.9e",
    "30E": "3.0e",
    "48E_A": "4.8e",
    "48E_B": "4.9e",
    "70E": "7.0e",
    "90E": "9.0e",
    "100E": "10.0e",
    "130E": "13.0e",
    "160E": "16.0e",
    "192E": "19.2e",
    "216E": "21.5e",
    "235E": "23.5e",
    "260E": "26.0e",
    "282E": "28.2e",
    "305E": "30.5e",
    "315E": "31.5e",
    "330E": "33.0e",
    "360E": "36.0e",
    "390E": "39.0e",
    "420E": "42.0e",
    "450E": "45.0e",
    "460E": "46.0e",
    "515E": "51.5e",
    "520E": "52.0e",
    "525E": "52.5e",
    "530E": "53.0e",
    "549E": "54.9e",
    "560E": "56.0e",
    "620E": "62.0e",
    "660E": "66.0e",
    "685E": "68.5e",
    "705E": "70.5e",
    "750E": "75.0e",
    "800E": "80.0e",
}

def position_binding(selector_id):
    """Return the immutable orbital binding for an explicit package selector ID."""
    selector = str(selector_id or "").strip()
    position = _SELECTOR_ID_TO_POSITION.get(selector)
    if not position:
        return None
    return {"selector_id": selector, "orbital_position": position}

def selector_id_for_display_label(label):
    """Attach a stable selector ID while constructing a GUI item; never use its label later."""
    pair = _SELECTOR_LABEL_BINDINGS.get(str(label or "").strip())
    return pair[0] if pair else None

def canonical_position_for_selector(selector_id):
    """Resolve a technical package selector through the explicit domain binding."""
    return _SELECTOR_ID_TO_POSITION.get(str(selector_id or ""))


def task_binding_for_display_label(label):
    """Capture canonical position and technical selector when creating a GUI item."""
    pair = _SELECTOR_LABEL_BINDINGS.get(str(label or "").strip())
    if not pair:
        return None
    selector, position = pair
    return {"canonical_position": position_token(position).upper(), "package_selector": selector}


def task_binding_for_package_selector(package_selector):
    """Create an explicit task binding from a known package selector."""
    selector = str(package_selector or "").strip()
    position = canonical_position_for_selector(selector)
    if not position:
        return None
    return {"canonical_position": position_token(position).upper(), "package_selector": selector}


def normalize_position_bindings(bindings):
    """Validate task bindings without deriving identity from display text."""
    result = []
    seen = set()
    for item in bindings or []:
        if not isinstance(item, dict):
            return []
        selector = str(item.get("package_selector") or "").strip()
        canonical = position_token(item.get("canonical_position")).upper()
        expected = canonical_position_for_selector(selector)
        if not selector or not expected or canonical != position_token(expected).upper() or selector in seen:
            return []
        seen.add(selector)
        result.append({"canonical_position": canonical, "package_selector": selector})
    return result


def task_positions_from_bindings(bindings):
    result = []
    seen = set()
    for item in normalize_position_bindings(bindings):
        position = item["canonical_position"]
        if position not in seen:
            seen.add(position)
            result.append(position)
    return result


def task_package_selectors_from_bindings(bindings):
    return [item["package_selector"] for item in normalize_position_bindings(bindings)]


def position_bindings_for_preferences(preferences):
    """Validate canonical task positions and separate package selectors as one state."""
    prefs = dict(preferences or {})
    bindings = normalize_position_bindings(prefs.get("position_bindings"))
    if not bindings:
        return []
    if list(prefs.get("positions", []) or []) != task_positions_from_bindings(bindings):
        return []
    if list(prefs.get("package_selectors", []) or []) != task_package_selectors_from_bindings(bindings):
        return []
    return bindings


def valid_task_selection(preferences):
    return bool(position_bindings_for_preferences(preferences))


def task_positions_for_display(preferences):
    """Expose only the already-selected canonical task positions to the GUI."""
    if not valid_task_selection(preferences):
        return []
    return list((preferences or {}).get("positions", []))


def package_display_name(package_selector):
    """Return display-only text for a package after its canonical binding is known."""
    selector = str(package_selector or "").strip()
    for label, pair in _SELECTOR_LABEL_BINDINGS.items():
        if pair[0] == selector:
            return label.split(") ", 1)[1] if label.startswith("(") and ") " in label else label
    return ""



def selected_selector_ids(selector_ids):
    result = []
    seen = set()
    for selector in selector_ids or []:
        binding = position_binding(selector)
        sid = binding.get("selector_id") if binding else None
        if sid and sid not in seen:
            seen.add(sid)
            result.append(sid)
    return result


def valid_position_selection(selector_ids):
    """Accept only explicit package selector IDs attached to GUI items."""
    values = [str(x).strip() for x in (selector_ids or []) if str(x).strip()]
    if not values or len(set(values)) != len(values):
        return False
    return all(position_binding(selector) for selector in values)


def family_for_style(style):
    return {
        "transparent": "channel-transparent",
        "black": "channel-black",
        "white": "channel-white",
    }.get(style)


def select_manifest_packages(document, preferences):
    """Select exact packages from explicit task positions and package selectors."""
    errors = validate_publication_manifest(document)
    if errors:
        return {"state": "invalid-manifest", "packages": [], "errors": errors}
    prefs = dict(default_preferences())
    prefs.update(preferences or {})
    if not valid_task_selection(prefs):
        return {"state": "invalid-selection", "packages": [], "errors": ["no-satellite-position-selected"]}
    family = family_for_style(prefs.get("style"))
    if not family:
        return {"state": "unsupported-style", "packages": [], "errors": ["unsupported style"]}
    wanted = selected_selector_ids(prefs.get("package_selectors"))
    resolution = prefs.get("resolution", DEFAULT_RESOLUTION)
    packages = [p for p in document.get("packages", [])
                if p.get("family") == family and p.get("resolution") == resolution]
    wanted_set = set(wanted)
    packages = [p for p in packages if p.get("selector_id") in wanted_set]
    available = set(p.get("selector_id") for p in packages)
    missing = [sid for sid in wanted if sid not in available]
    return {
        "state": "ready" if not missing else "partial",
        "packages": packages,
        "missing_selectors": missing,
        "selector_ids": wanted,
        "positions": list(prefs.get("positions", [])),
        "family": family,
        "resolution": resolution,
    }


def selector_id_for_position(position):
    value = position_token(position)
    for selector, canonical in _SELECTOR_ID_TO_POSITION.items():
        if canonical == value and selector not in ("FREESAT", "DIGI_TELLY", "ANTIKSAT", "CANALPLUS_SK", "CANALPLUS_CZ"):
            return selector
    return None


def plan_runtime_packages(document, queue, manifest_url=None):
    """Resolve packages only when canonical positions and selectors agree."""
    selectors = list(queue.get("package_selectors", []))
    task_bindings = normalize_position_bindings(queue.get("position_bindings", []))
    prefs = {
        "positions": list(queue.get("positions", [])),
        "package_selectors": selectors,
        "position_bindings": task_bindings,
        "style": queue.get("style", DEFAULT_STYLE),
        "resolution": queue.get("resolution", DEFAULT_RESOLUTION),
    }
    if not task_bindings or not valid_position_selection(selectors):
        return {"state": "invalid-selection", "packages": [], "errors": ["no-satellite-position-selected"],
                "missing_selectors": [], "selector_ids": [], "family": family_for_style(prefs["style"]),
                "resolution": prefs["resolution"]}
    binding_selectors = task_package_selectors_from_bindings(task_bindings)
    derived_positions = set(position_token(x) for x in task_positions_from_bindings(task_bindings))
    explicit_positions = set(position_token(x) for x in queue.get("positions", []))
    if binding_selectors != selectors or explicit_positions != derived_positions:
        return {"state": "invalid-selection", "packages": [], "errors": ["selector-position-binding-mismatch"],
                "missing_selectors": [], "selector_ids": selectors, "family": family_for_style(prefs["style"]),
                "resolution": prefs["resolution"]}
    explicit = selectors
    if explicit:
        wanted = explicit
    elif queue.get("mode") in (UPDATE_MODE_SYNC_TV, UPDATE_MODE_SYNC_TV_RADIO):
        wanted = []
        seen = set()
        for service in queue.get("services", []):
            sid = selector_id_for_position(service.get("position"))
            if sid and sid not in seen:
                seen.add(sid)
                wanted.append(sid)
    else:
        wanted = []
    family = family_for_style(prefs["style"])
    if not family:
        return {"state": "invalid-preferences", "packages": [], "errors": ["unsupported style"],
                "missing_selectors": [], "selector_ids": wanted, "family": None,
                "resolution": prefs["resolution"]}
    if not re.match(r"^[1-9][0-9]*x[1-9][0-9]*$", str(prefs["resolution"])):
        return {"state": "invalid-preferences", "packages": [], "errors": ["invalid resolution"],
                "missing_selectors": [], "selector_ids": wanted, "family": family,
                "resolution": prefs["resolution"]}
    manifest_url = manifest_url or queue.get("manifest_url") or runtime_publication().get("manifest_url")
    errors = validate_publication_manifest(document, manifest_url)
    if errors:
        return {"state": "invalid-manifest", "packages": [], "errors": errors}
    selected_positions = derived_positions
    candidates = [p for p in document.get("packages", [])
                  if p.get("family") == family and p.get("resolution") == prefs["resolution"]
                  and (p.get("orbital_position") or canonical_position_for_selector(p.get("selector_id"))) in selected_positions]
    if wanted:
        wanted_set = set(wanted)
        packages = [p for p in candidates if p.get("selector_id") in wanted_set]
        available = set(p.get("selector_id") for p in packages)
        missing = [sid for sid in wanted if sid not in available]
    elif queue.get("mode") in (UPDATE_MODE_SYNC_TV, UPDATE_MODE_SYNC_TV_RADIO):
        # Empty selective input means there is nothing to synchronize. Never
        # reinterpret it as FULL/all-packages.
        packages = []
        missing = []
    else:
        packages = candidates
        missing = []
    packages = sorted(packages, key=lambda p: (p.get("selector_id", ""), p.get("filename", "")))
    return {
        "state": "ready" if not missing else "partial",
        "packages": packages,
        "missing_selectors": missing,
        "selector_ids": wanted,
        "family": family,
        "resolution": prefs["resolution"],
    }


def build_download_jobs(document, package_plan, manifest_url=None):
    """Turn a package plan into integrity-complete download jobs."""
    manifest_url = manifest_url or runtime_publication().get("manifest_url")
    source = publication_source(manifest_url)
    errors = validate_publication_manifest(document, manifest_url)
    if errors or source is None:
        return {"state": "invalid-manifest", "jobs": [], "errors": errors or ["untrusted manifest url"]}
    if package_plan.get("state") not in ("ready", "partial"):
        return {"state": "invalid-plan", "jobs": [], "errors": ["package plan is not executable"]}
    part_meta = {p["filename"]: p for p in document.get("parts", []) if isinstance(p, dict)}
    delivery = document.get("delivery", "direct")
    jobs = []
    for package in package_plan.get("packages", []):
        selector = package["selector_id"]
        orbital_position = package.get("orbital_position") or canonical_position_for_selector(selector)
        job = {
            "selector_id": selector,
            "orbital_position": orbital_position,
            "family": package["family"],
            "resolution": package["resolution"],
            "filename": package["filename"],
            "bytes": package["bytes"],
            "sha256": package["sha256"],
            "publication_source_id": source["id"],
            "publication_root": source["package_root"],
            "parts": [],
        }
        if delivery == "raw-github-parts" and package.get("parts"):
            for url in package.get("parts", []):
                name = str(url).rsplit("/", 1)[-1]
                meta = part_meta.get(name)
                if meta is None:
                    return {"state": "invalid-manifest", "jobs": [], "errors": ["part metadata not found"]}
                job["parts"].append({
                    "url": url, "filename": name,
                    "bytes": meta["bytes"], "sha256": meta["sha256"],
                })
        else:
            job["parts"].append({
                "url": package["url"], "filename": package["filename"],
                "bytes": package["bytes"], "sha256": package["sha256"],
            })
        jobs.append(job)
    return {
        "state": "ready" if package_plan.get("state") == "ready" else "partial",
        "jobs": jobs,
        "missing_selectors": list(package_plan.get("missing_selectors", [])),
    }


def validate_destination(path):
    """Reject relative/root destinations; UI may only stage into a real subdirectory."""
    raw = os.path.normpath(str(path or ""))
    if not os.path.isabs(raw):
        return None
    value = os.path.realpath(raw)
    # Do not silently follow a user supplied symlink while installing files.
    if value != os.path.abspath(raw):
        return None
    probe = os.path.sep
    for component in [part for part in raw.split(os.path.sep) if part]:
        probe = os.path.join(probe, component)
        if os.path.islink(probe):
            return None
    if value == os.path.sep:
        return None
    if value == DEFAULT_DESTINATION:
        return value
    protected = ("/bin", "/boot", "/dev", "/etc", "/lib", "/proc", "/root", "/run", "/sbin", "/sys", "/usr", "/var")
    if value in protected or any(value.startswith(p + os.path.sep) for p in protected):
        return None
    return value


def destination_storage_available(path):
	"""Do not create a removable-storage preset on the receiver's root disk."""
	value = validate_destination(path)
	if not value:
		return False
	for mountpoint in ("/media/hdd", "/media/usb", "/media/sdcard", "/media/mmc"):
		if value == mountpoint or value.startswith(mountpoint + os.path.sep):
			return os.path.ismount(mountpoint)
	return True


def wanted_picon_names(queue):
    """Selective mode installs only receiver bouquet identities; FULL installs all."""
    if queue.get("mode") not in (UPDATE_MODE_SYNC_TV, UPDATE_MODE_SYNC_TV_RADIO):
        return None
    names = set()
    for service in queue.get("services", []):
        stem = normalize_service_reference(service.get("service_reference", ""))
        if stem:
            names.add(stem + ".png")
    return names


def classify_requested_picons(wanted, upstream_names, installed_names):
    """Scope sync results to selected package assets before reporting missing files."""
    upstream = set(upstream_names or [])
    installed = set(installed_names or [])
    if wanted is None:
        relevant = set(upstream)
        outside = set()
    else:
        requested = set(wanted or [])
        relevant = requested.intersection(upstream)
        outside = requested.difference(upstream)
    return {
        "relevant": relevant,
        "outside_selected_packages": outside,
        "missing": relevant.difference(installed),
    }


def plan_stale_position_picons(existing_names, selected_positions, package_names):
    """Select only stale PNG service identities for explicitly selected orbits."""
    selected = set(position_token(x) for x in (selected_positions or []) if x)
    if not selected:
        return []
    packages = set(package_names or [])
    stale = []
    for name in sorted(set(existing_names or [])):
        if not str(name).lower().endswith(".png") or name in packages:
            continue
        stem = normalize_service_reference(os.path.basename(str(name))[:-4].replace("_", ":"))
        position = service_orbital_position(stem.replace("_", ":")) if stem else None
        if position and position.lower() in selected:
            stale.append(str(name))
    return stale


def success_summary(updated, selected_services=None, translate=None):
    """Format localized result lines without ambiguous 'file(s)' wording."""
    translate = translate or (lambda message: message)
    count = int(updated)
    result = translate("%d picon successfully updated" if count == 1 else "%d picons successfully updated") % count
    if selected_services is not None:
        services = int(selected_services)
        result += "\n" + (translate("%d service selected" if services == 1 else "%d services selected") % services)
    return result


def package_result_summary(package_results, translate=None):
    """Format measured counts by selected package and canonical orbital position."""
    translate = translate or (lambda message: message)
    rows = sorted(package_results or [], key=lambda x: (str(x.get("orbital_position") or ""), str(x.get("selector_id") or "")))
    lines = []
    total_updated = 0
    total_failures = 0
    for row in rows:
        position = str(row.get("orbital_position") or "—").upper()
        selector = str(row.get("package_selector") or row.get("selector_id") or "")
        package_name = package_display_name(selector)
        updated = max(0, int(row.get("updated", 0)))
        failures = max(0, int(row.get("failures", 0)))
        total_updated += updated
        total_failures += failures
        row_status = ("ERROR" if failures and not updated else
                      "PARTIAL SUCCESS" if failures else "SUCCESSFUL")
        lines.append(translate(row_status) + ": " +
                     (translate("%s / %s: %d picons updated; %d failures") %
                      (position, package_name or translate("Package"), updated, failures)))
        detail = " ".join(str(row.get("error") or "").split())[:240]
        if failures and detail:
            lines.append(translate("ERROR") + ": " + detail)
    total_status = ("ERROR" if total_failures and not total_updated else
                    "PARTIAL SUCCESS" if total_failures else "SUCCESSFUL")
    lines.append(translate(total_status) + ": " +
                 (translate("Total: %d picons updated") % total_updated))
    failures_status = "ERROR" if total_failures else "SUCCESSFUL"
    lines.append(translate(failures_status) + ": " +
                 (translate("Failures: %d") % total_failures))
    if total_failures and total_updated:
        status = translate("PARTIAL SUCCESS")
    elif total_failures:
        status = translate("ERROR")
    else:
        status = translate("SUCCESSFUL")
    return {"status": status, "updated": total_updated, "failures": total_failures, "text": "\n".join(lines)}


def auxiliary_result_summary(domain, variant, fallback_updated, fallback_total,
                             safe_updated, safe_total, translate=None):
    """Summarize the measured fallback and safe-overlay copies as one GUI task."""
    translate = translate or (lambda message: message)
    fallback_updated = max(0, int(fallback_updated))
    fallback_total = max(0, int(fallback_total))
    safe_updated = max(0, int(safe_updated))
    safe_total = max(0, int(safe_total))
    updated = fallback_updated + safe_updated
    failures = max(0, fallback_total - fallback_updated) + max(0, safe_total - safe_updated)
    status = "ERROR" if failures and not updated else ("PARTIAL SUCCESS" if failures else "SUCCESSFUL")
    text = translate("Fallback %d/%d; safe overlay %d/%d; errors %d") % (
        fallback_updated, fallback_total, safe_updated, safe_total, failures)
    return {"status": translate(status), "updated": updated, "failures": failures,
            "text": translate(status) + ": " + text}


def safe_archive_member(name):
    value = str(name or "").replace("\\", "/")
    if not value or value.startswith("/") or value.startswith("../") or "/../" in ("/" + value):
        return False
    base = value.rsplit("/", 1)[-1]
    return bool(base) and base not in (".", "..")


def publication_source(source_id_or_manifest_url=None):
    """Return one exact publication descriptor by ID or exact manifest URL."""
    value = source_id_or_manifest_url or ACTIVE_PUBLICATION_SOURCE
    if isinstance(value, dict):
        value = value.get("publication_source_id") or value.get("manifest_url")
    if value in PUBLICATION_SOURCES:
        return dict(PUBLICATION_SOURCES[value], id=value)
    for source_id, source in PUBLICATION_SOURCES.items():
        if value == source["manifest_url"]:
            return dict(source, id=source_id)
    return None


def runtime_publication():
    source = publication_source(ACTIVE_PUBLICATION_SOURCE)
    return {
        "persistent": bool(RUNTIME_PUBLICATION_ENABLED and source),
        "manifest_url": source["manifest_url"] if RUNTIME_PUBLICATION_ENABLED and source else None,
        "publication_source_id": source["id"] if RUNTIME_PUBLICATION_ENABLED and source else None,
        "package_root": source["package_root"] if RUNTIME_PUBLICATION_ENABLED and source else None,
        "redirect_root": source["package_root"] if RUNTIME_PUBLICATION_ENABLED and source else None,
    }

def build_runtime_queue(preferences, enigma2_dir=ENIGMA2_DIR, publication=None):
    """Create a queue with canonical task positions and separate package selectors."""
    prefs = dict(default_preferences())
    prefs.update(preferences or {})
    mode = prefs.get("update_mode")
    bindings = position_bindings_for_preferences(prefs)
    if not bindings:
        raise ValueError("no-satellite-position-selected")
    selected = list(prefs.get("positions", []) or [])
    selectors = list(prefs.get("package_selectors", []) or [])
    if mode not in dict(UPDATE_MODES):
        raise ValueError("unsupported update mode")
    resolution = prefs.get("resolution")
    style = prefs.get("style")
    if channel_delivery_backend(resolution, style) != "warder":
        raise ValueError("non-native resolution requires pinned selected-position archives")
    if not channel_style_supported(resolution, style):
        raise ValueError("unsupported Warder channel picon colour")
    destination = validate_destination(prefs.get("destination"))
    if not destination:
        raise ValueError("invalid Warder picon destination")
    if mode in (UPDATE_MODE_SYNC_TV, UPDATE_MODE_SYNC_TV_RADIO):
        request = build_sync_request(
            enigma2_dir, selected, style, resolution,
            include_radio=(mode == UPDATE_MODE_SYNC_TV_RADIO))
        services = request["services"]
    else:
        services = []
    published = bool((publication or {}).get("persistent") and (publication or {}).get("manifest_url"))
    source = publication_source((publication or {}).get("manifest_url"))
    if source is None or not published:
        source = None
    return {
        "state": READY if published and source else PUBLICATION_LOCKED,
        "mode": mode,
        "positions": selected,
        "package_selectors": selectors,
        "position_bindings": bindings,
        "style": style,
        "resolution": resolution,
        "destination": destination,
        "services": services,
        "service_count": len(services),
        "manifest_url": source["manifest_url"] if source else None,
        "publication_source_id": source["id"] if source else None,
    }


def build_service_index(entries):
    """Index package entries by canonical service reference and expose collisions."""
    index = {}
    collisions = {}
    for entry in entries or []:
        stem = normalize_service_reference(entry.get("service_reference", ""))
        if not stem:
            continue
        candidate = dict(entry)
        candidate["service_reference"] = stem
        previous = index.get(stem)
        if previous is None:
            index[stem] = candidate
            continue
        if previous == candidate:
            continue
        bucket = collisions.setdefault(stem, [previous])
        if candidate not in bucket:
            bucket.append(candidate)
    for stem in collisions:
        index.pop(stem, None)
    return index, collisions


def resolve_service_entry(index, collisions, service_reference):
    """Never guess across a collision: ambiguous identities are explicitly blocked."""
    stem = normalize_service_reference(service_reference)
    if not stem:
        return {"state": "invalid-service-reference", "service_reference": ""}
    if stem in (collisions or {}):
        return {"state": "collision-blocked", "service_reference": stem,
                "candidates": list(collisions[stem])}
    entry = (index or {}).get(stem)
    if entry is None:
        return {"state": "missing", "service_reference": stem}
    return {"state": "matched", "service_reference": stem, "entry": entry}


_ALLOWED_MANIFEST_HOST = "raw.githubusercontent.com"
_FAMILIES = ("channel-transparent", "channel-black", "channel-white")
_SHA256_RE = re.compile("^[0-9a-f]{64}$")
_FILENAME_RE = re.compile("^[A-Za-z0-9._-]+[.](?:zip|7z)$")


def trusted_publication_url(url, source_id_or_manifest_url=None):
    """Validate URLs against the exact package and redirect root of one source."""
    source = publication_source(source_id_or_manifest_url)
    if source is None:
        return False
    try:
        parsed = urlparse(str(url))
    except Exception:
        return False
    root = source["package_root"]
    root_path = urlparse(root).path
    path = parsed.path
    if (parsed.scheme != "https" or parsed.netloc != _ALLOWED_MANIFEST_HOST
            or parsed.hostname != _ALLOWED_MANIFEST_HOST
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or "%" in path or "\\" in path or not path.startswith(root_path)):
        return False
    tail = path[len(root_path):]
    if not tail or any(segment in (".", "..") for segment in tail.split("/")):
        return False
    return bool(re.match(r"^[A-Za-z0-9._/-]+$", tail))


def _trusted_https_url(url, manifest_url=None):
    """Compatibility wrapper bound to the active or explicitly named source."""
    return trusted_publication_url(url, manifest_url)


def validate_publication_manifest(document, manifest_url=None):
    """Validate the receiver-facing Warder manifest before any download is queued."""
    errors = []
    source = publication_source(manifest_url)
    if source is None:
        errors.append("untrusted manifest url")
    if not isinstance(document, dict):
        return errors + ["manifest is not an object"]
    if document.get("schema") != 1:
        errors.append("unsupported manifest schema")
    generated = document.get("generated_from")
    if not isinstance(generated, dict) or generated.get("repository") != "Evolution-by-Warder/PiconHub-Warder-Evolution":
        errors.append("unexpected manifest source")
    elif len(str(generated.get("ref", ""))) < 7:
        errors.append("invalid source ref")
    delivery = document.get("delivery", "direct")
    if delivery not in ("direct", "raw-github-parts"):
        errors.append("unsupported delivery")
    packages = document.get("packages")
    if not isinstance(packages, list) or not packages:
        errors.append("packages missing")
        return errors
    seen = set()
    part_meta = {}
    if delivery == "raw-github-parts":
        parts = document.get("parts")
        if not isinstance(parts, list) or not parts:
            errors.append("part metadata missing")
        else:
            for part in parts:
                name = part.get("filename", "") if isinstance(part, dict) else ""
                size = part.get("bytes", 0) if isinstance(part, dict) else 0
                sha = part.get("sha256", "") if isinstance(part, dict) else ""
                if not name or name in part_meta or not isinstance(size, int) or size < 1 or size > 20 * 1024 * 1024 or not _SHA256_RE.match(str(sha)):
                    errors.append("invalid part metadata")
                    continue
                part_meta[name] = (size, sha)
    referenced_parts = set()
    for package in packages:
        if not isinstance(package, dict):
            errors.append("invalid package")
            continue
        selector = package.get("selector_id")
        declared_position = package.get("orbital_position")
        bound_position = canonical_position_for_selector(selector)
        if declared_position is not None and declared_position != bound_position:
            errors.append("incorrect canonical orbital position binding")
        key = (selector, package.get("family"), package.get("resolution"))
        if key in seen:
            errors.append("duplicate selector/family/resolution")
        seen.add(key)
        if package.get("family") not in _FAMILIES:
            errors.append("invalid family")
        resolution = str(package.get("resolution", ""))
        if not re.match(r"^[1-9][0-9]*x[1-9][0-9]*$", resolution):
            errors.append("invalid package resolution")
        name = str(package.get("filename", ""))
        if not _FILENAME_RE.match(name):
            errors.append("invalid package filename")
        size = package.get("bytes", 0)
        if not isinstance(size, int) or size < 1:
            errors.append("invalid package size")
        if not _SHA256_RE.match(str(package.get("sha256", ""))):
            errors.append("invalid package sha256")
        if delivery == "direct" or (delivery == "raw-github-parts" and not package.get("parts")):
            if source is None or not trusted_publication_url(package.get("url", ""), source["id"]):
                errors.append("untrusted package url")
        else:
            urls = package.get("parts")
            if not isinstance(urls, list) or not urls:
                errors.append("package parts missing")
                continue
            package_part_names = set()
            package_part_bytes = 0
            for url in urls:
                if source is None or not trusted_publication_url(url, source["id"]):
                    errors.append("untrusted part url")
                    continue
                part_name = str(url).rsplit("/", 1)[-1]
                expected_part_name = name + ".part%02d" % len(package_part_names)
                if part_name != expected_part_name:
                    errors.append("non-canonical package part")
                    continue
                if part_name in package_part_names:
                    errors.append("duplicate package part")
                    continue
                package_part_names.add(part_name)
                if part_name not in part_meta:
                    errors.append("part metadata not found")
                else:
                    package_part_bytes += part_meta[part_name][0]
                referenced_parts.add(part_name)
            if isinstance(size, int) and size > 0 and package_part_bytes != size:
                errors.append("package part size mismatch")
    if delivery == "raw-github-parts" and part_meta and referenced_parts != set(part_meta):
        errors.append("part metadata/reference mismatch")
    return errors


def publication_from_manifest(manifest_url, document):
    """Return runtime publication evidence only after strict manifest validation."""
    source = publication_source(manifest_url)
    errors = validate_publication_manifest(document, manifest_url)
    return {
        "persistent": not errors,
        "manifest_url": source["manifest_url"] if source and not errors else None,
        "publication_source_id": source["id"] if source and not errors else None,
        "package_root": source["package_root"] if source and not errors else None,
        "redirect_root": source["package_root"] if source and not errors else None,
        "delivery": document.get("delivery", "direct") if isinstance(document, dict) else None,
        "errors": errors,
    }

