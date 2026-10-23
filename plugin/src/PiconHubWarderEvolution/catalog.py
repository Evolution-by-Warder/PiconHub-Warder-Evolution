"""Read the Warder catalog and plan verified downloads without changing a receiver."""

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Optional

CATALOG_URL = (
    "https://raw.githubusercontent.com/Evolution-by-Warder/"
    "FullHDGlass-Warder-Evolution/main/assets/warder/downloads/"
    "picons/channels/manifest.json"
)
_PART_BASE = CATALOG_URL.rsplit("/", 1)[0] + "/"
_SHA256 = re.compile(r"[a-f0-9]{64}\Z")
_SELECTOR = re.compile(r"[A-Z0-9][A-Z0-9_]*\Z")
RESOLUTIONS = ("50x30", "220x132", "400x240")
STYLES = ("transparent", "white", "black")


class CatalogError(ValueError):
    """Catalog or downloaded content failed validation."""


def _positive(value, label):
    if type(value) is not int or value <= 0:
        raise CatalogError("Invalid " + label)
    return value


def _sha(value):
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise CatalogError("Invalid SHA256")
    return value


def _filename(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", value):
        raise CatalogError("Invalid filename")
    if value.startswith(".") or ".." in value:
        raise CatalogError("Unsafe filename")
    return value


@dataclass(frozen=True)
class Part:
    filename: str
    url: str
    bytes: int
    sha256: str


@dataclass(frozen=True)
class Package:
    selector_id: str
    resolution: str
    style: str
    filename: str
    bytes: int
    sha256: str
    png_count: Optional[int]
    parts: tuple


class Catalog:
    def __init__(self, document):
        if not isinstance(document, dict) or type(document.get("schema")) is not int or document["schema"] != 1:
            raise CatalogError("Unsupported catalog schema")
        if document.get("delivery") != "raw-github-parts":
            raise CatalogError("Unsupported delivery format")
        if not isinstance(document.get("parts"), list) or not isinstance(document.get("packages"), list):
            raise CatalogError("Missing parts or packages")
        index = {}
        for item in document["parts"]:
            if not isinstance(item, dict):
                raise CatalogError("Invalid part record")
            name = _filename(item.get("filename"))
            if name in index:
                raise CatalogError("Duplicate part: " + name)
            index[name] = (_positive(item.get("bytes"), "part size"), _sha(item.get("sha256")))
        packages = {}
        for item in document["packages"]:
            if not isinstance(item, dict):
                raise CatalogError("Invalid package record")
            selector = item.get("selector_id")
            if not isinstance(selector, str) or not _SELECTOR.fullmatch(selector):
                raise CatalogError("Invalid package selector")
            resolution, family = item.get("resolution"), item.get("family")
            if resolution not in RESOLUTIONS or family not in tuple("channel-" + s for s in STYLES):
                raise CatalogError("Unsupported resolution or style")
            style = family[len("channel-"):]
            name = _filename(item.get("filename"))
            if not name.endswith(".zip"):
                raise CatalogError("Expected ZIP package")
            urls = item.get("parts")
            if not isinstance(urls, list) or not urls:
                raise CatalogError("Package has no parts")
            parts = []
            for position, url in enumerate(urls):
                part_name = name + ".part%02d" % position
                # Restrict downloads to the actual catalog directory. This also
                # rejects credentials, queries, fragments and reordered parts.
                if not isinstance(url, str) or url != _PART_BASE + part_name:
                    raise CatalogError("Unexpected part URL or order")
                if part_name not in index:
                    raise CatalogError("Part has no checksum: " + part_name)
                size, sha = index[part_name]
                parts.append(Part(part_name, url, size, sha))
            size = _positive(item.get("bytes"), "package size")
            if sum(p.bytes for p in parts) != size:
                raise CatalogError("Part sizes differ from package size")
            package = Package(selector, resolution, style, name, size,
                              _sha(item.get("sha256")),
                              None if item.get("png_count") is None else
                              _positive(item["png_count"], "PNG count"), tuple(parts))
            key = (selector, resolution, style)
            if key in packages:
                raise CatalogError("Ambiguous package selection")
            packages[key] = package
        if not packages:
            raise CatalogError("Empty package catalog")
        self._packages = packages

    @classmethod
    def from_json(cls, payload):
        try:
            document = json.loads(payload)
        except (ValueError, UnicodeError, TypeError) as exc:
            raise CatalogError("Invalid catalog JSON") from exc
        return cls(document)

    @property
    def packages(self):
        return tuple(self._packages.values())

    @property
    def selectors(self):
        return tuple(sorted({p.selector_id for p in self.packages}))

    def select(self, selector_id, resolution="220x132", style="transparent"):
        try:
            return self._packages[(selector_id, resolution, style)]
        except KeyError as exc:
            # Never silently substitute another size, background or satellite.
            raise CatalogError("Requested package is unavailable") from exc


def verify_stream(stream, expected_bytes, expected_sha256):
    """Bound memory use and reject truncated, oversized or modified downloads."""
    _positive(expected_bytes, "download size")
    _sha(expected_sha256)
    digest, count = hashlib.sha256(), 0
    while True:
        chunk = stream.read(128 * 1024)
        if not chunk:
            break
        count += len(chunk)
        if count > expected_bytes:
            raise CatalogError("Download exceeds declared size")
        digest.update(chunk)
    if count != expected_bytes or digest.hexdigest() != expected_sha256:
        raise CatalogError("Download size or SHA256 mismatch")
    return True
