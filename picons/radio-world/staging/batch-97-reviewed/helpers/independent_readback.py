"""Verify new country packages from immutable public GitHub URLs."""
import concurrent.futures
import gzip
import hashlib
import io
import json
import sys
import urllib.request
from pathlib import Path
from zipfile import ZipFile

from PIL import Image

BASE = "https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/"
LIMIT = 32 * 1024 * 1024


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main(batch, checkpoint, cache):
    stage = Path(f"picons/radio-world/staging/batch-{batch}-reviewed")
    cache.mkdir(parents=True, exist_ok=True)

    def fetch(url, size=None, digest=None):
        assert url.startswith(BASE)
        path = cache / sha(url.encode())
        if path.exists():
            raw = path.read_bytes()
        else:
            with urllib.request.urlopen(url, timeout=60) as response:
                raw = response.read(size + 1 if size is not None else 10 * 1024 * 1024)
            path.write_bytes(raw)
        if size is not None:
            assert len(raw) == size
        if digest is not None:
            assert sha(raw) == digest
        return raw

    def get(entry):
        return fetch(entry["url"], entry["bytes"], entry["sha256"])

    index = json.loads(fetch(BASE + checkpoint + f"/{stage}/countries.proposed.json"))
    prior = json.loads((stage / "baseline.previous.json").read_bytes())
    rows = json.loads(gzip.decompress((stage / "selection.json.gz").read_bytes()))["entries"]
    spec = json.loads((stage / "source-inputs/recovery-spec.json").read_bytes())
    old = {country["id"]: country for country in prior["countries"]}
    new = {country["id"]: country for country in index["countries"]}
    assert old.keys() == new.keys() and len(new) == 219
    total = sum(country["picons"] for country in new.values())
    assert sum(country["picons"] for country in old.values()) == spec["baseline_references"]
    assert total == spec["baseline_references"] + len(rows)
    selected = {row["country"] for row in rows}
    for code in old.keys() - selected:
        assert old[code] == new[code], code
    by_ref = {r["station"]["reference"]: r for r in spec["stations"]}
    tasks = []
    for code in sorted(selected):
        manifest = json.loads(get(new[code]["release"]))
        previous = json.loads(get(old[code]["release"])) if old[code]["release"] else None
        assert manifest["country"] == code
        added = {row["ref"].replace(":", "_") + ".png": row for row in rows if row["country"] == code}
        assert new[code]["picons"] == old[code]["picons"] + len(added)
        for size in ("50x30", "220x132", "400x240"):
            for style in ("transparent", "white", "black"):
                entry = manifest["packages"][size][style]
                prior_files = previous["packages"][size][style]["files"] if previous else {}
                assert not prior_files.keys() & added.keys()
                variant = f"{size}/{style}"
                expected = {**prior_files, **{n: r["variants"][variant][0] for n, r in added.items()}}
                assert entry["files"] == expected
                inventory = {}
                for number, part in enumerate(entry.get("parts") or [entry], 1):
                    suffix = f"-part{number:02d}" if entry.get("parts") else ""
                    collection = new[code]["collection"]
                    path = f"picons/{collection}/packages/{collection.lower()}-{style}-{size}{suffix}.zip"
                    assert part["url"] == BASE + manifest["payload_commit"] + "/" + path
                    assert 0 < part["bytes"] <= LIMIT and not inventory.keys() & part["files"].keys()
                    inventory.update(part["files"])
                    tasks.append((code, size, style, part, added, prior_files))
                assert inventory == expected

    def audit(task):
        code, size, style, part, added, prior_files = task
        raw = get(part)
        dims = tuple(map(int, size.split("x")))
        variant = f"{size}/{style}"
        count = 0
        with ZipFile(io.BytesIO(raw)) as archive:
            assert archive.testzip() is None
            assert len(archive.infolist()) == len(part["files"])
            assert set(archive.namelist()) == set(part["files"])
            for name, expected in part["files"].items():
                image = archive.read(name)
                assert sha(image) == expected
                with Image.open(io.BytesIO(image)) as png:
                    assert png.format == "PNG" and png.mode == "RGBA" and png.size == dims
                    if name in added:
                        row = added[name]
                        assert list(png.getchannel("A").getextrema()) == by_ref[row["ref"]]["alpha_extrema"][variant]
                with Image.open(io.BytesIO(image)) as png:
                    png.verify()
                if name in added:
                    digest, length, blob = added[name]["variants"][variant]
                    assert (digest, length) == (expected, len(image))
                    assert hashlib.sha1(f"blob {length}\0".encode() + image).hexdigest() == blob
                    count += 1
                else:
                    assert prior_files[name] == expected
        return dict(country=code, url=part["url"], bytes=len(raw), sha256=sha(raw),
                    members=len(part["files"]), new=count, preserved=len(part["files"]) - count,
                    CRC="pass", PNG_dimensions_RGBA="pass", alpha_matches_saved_approved_source="pass",
                    new_exact_approved_bytes="pass")

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(audit, tasks))
    assert sum(item["new"] for item in results) == 9 * len(rows)
    report = dict(status="pass", audited_commit=checkpoint, independent_runner=True,
                  independent_actual_ZIP_readback=True, baseline_references=spec["baseline_references"],
                  covered_references=total, remaining_references=35560-total,
                  references_added=len(rows), PNG_added=9*len(rows), archives=results,
                  part_limit_bytes=LIMIT, unchanged_country_descriptors=len(new)-len(selected))
    (stage / "results").mkdir(exist_ok=True)
    (stage / "results/independent-postwrite-audit.json").write_text(json.dumps(report, indent=2) + "\n")
    (stage / "SHA256SUMS.txt").write_text("".join(f"{item['sha256']}  {item['url']}\n" for item in results))
    print("PASS:", len(results), "actual GitHub ZIPs,", 9*len(rows), "new PNG entries", flush=True)


if __name__ == "__main__":
    main(int(sys.argv[1]), sys.argv[2], Path(sys.argv[3]))
