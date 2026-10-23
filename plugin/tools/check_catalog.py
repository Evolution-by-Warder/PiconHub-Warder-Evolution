#!/usr/bin/env python3
"""Inspect local or live Warder catalog; no downloads are installed or extracted."""
import argparse
import json
import pathlib
import sys
from dataclasses import asdict
from urllib.request import urlopen

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from PiconHubWarderEvolution.catalog import Catalog, CatalogError, CATALOG_URL


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=pathlib.Path, help="Use a saved manifest instead of the live catalog")
    parser.add_argument("--selector", help="Exact catalog selector, e.g. 235E or ANTIKSAT")
    parser.add_argument("--resolution", default="220x132")
    parser.add_argument("--style", default="transparent")
    args = parser.parse_args()
    limit = 8 * 1024 * 1024
    try:
        if args.file:
            with args.file.open("rb") as source:
                payload = source.read(limit + 1)
        else:
            with urlopen(CATALOG_URL, timeout=30) as response:
                payload = response.read(limit + 1)
        if len(payload) > limit:
            raise CatalogError("Catalog exceeds size limit")
        catalog = Catalog.from_json(payload)
        result = {"packages": len(catalog.packages), "selector_count": len(catalog.selectors),
                  "selectors": catalog.selectors, "receiver_tested": False}
        if args.selector:
            result["selection"] = asdict(catalog.select(args.selector, args.resolution, args.style))
        print(json.dumps(result, indent=2))
    except (CatalogError, OSError) as exc:
        parser.exit(1, str(exc) + "\n")


if __name__ == "__main__":
    main()
