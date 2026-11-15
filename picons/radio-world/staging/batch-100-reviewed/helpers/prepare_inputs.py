"""Apply artwork from the official players of Radio Art and Sveriges Radio."""
import runpy
import sys
from pathlib import Path
from urllib.parse import urlsplit

batch = Path(__file__).resolve().parents[1]
previous = batch.parent / "batch-98-reviewed" / "helpers" / "prepare_inputs.py"
runner = runpy.run_path(str(previous))["main"]
context = runner.__globals__
evidence = context["read"](batch / "official-source-evidence.json")
candidates = {row["station"]["reference"]: row for row in evidence["candidates"]}


def check_identity(row):
    station = row["station"]
    candidate = candidates[station["reference"]]
    assert all(row[field] == candidate[field] for field in ("station", "country", "publisher", "original"))
    publisher = candidate["publisher"]
    assert row["image"] == publisher["logo"] == row["original"]["url"]
    assert context["key"](station["url"]) in {context["key"](url) for url in publisher["streams"]}
    site = urlsplit(publisher["source"]["url"]).hostname
    artwork = urlsplit(publisher["logo"]).hostname
    assert (row["country"], site, artwork) in {
        ("GR", "www.radioart.com", "cdn.radioart.com"),
        ("SE", "api.sr.se", "static-cdn.sr.se"),
    }


context["check_identity"] = check_identity
runner(int(sys.argv[1]))
