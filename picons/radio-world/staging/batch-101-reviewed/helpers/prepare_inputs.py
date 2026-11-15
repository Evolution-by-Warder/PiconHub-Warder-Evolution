"""Apply broadcaster-bound artwork and reuse the approved Malmöhus logo."""
import runpy
import sys
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import urlopen

batch = Path(__file__).resolve().parents[1]
previous = batch.parent / "batch-98-reviewed" / "helpers" / "prepare_inputs.py"
runner = runpy.run_path(str(previous))["main"]
context = runner.__globals__
evidence = context["read"](batch / "official-source-evidence.json")
candidates = {row["station"]["reference"]: row for row in evidence["candidates"]}
donors = {
    row["original"]["sha256"]: row["donor"]
    for row in candidates.values() if "donor" in row
}
render_original = context["render"]
write_json = context["write"]


def check_identity(row):
    station = row["station"]
    candidate = candidates[station["reference"]]
    assert all(row[field] == candidate[field] for field in ("station", "country", "publisher", "original"))
    publisher = candidate["publisher"]
    assert row["image"] == publisher["logo"] == row["original"]["url"]
    assert station["url"] == publisher["streams"][0]
    prior, now = (publisher[key] for key in ("legacy_observation", "current_observation"))
    assert prior["status"] == now["status"] == 200 and prior["media_type"] == now["media_type"] == "audio/mpeg"
    previous_route, current_route = (urlsplit(r["final_url"]) for r in (prior, now))
    assert previous_route.path == current_route.path
    if row["country"] == "CH":
        assert prior["icy_name"] == now["icy_name"] and now["icy_name"].startswith("1.FM ")
        assert prior["icy_url"] == now["icy_url"] == "http://1.fm"
        assert urlsplit(publisher["source"]["url"]).hostname == "www.1.fm"
        assert urlsplit(publisher["logo"]).hostname == "minio.1cloud.fm"
    else:
        assert row["country"] == "SE" and publisher["id"] == 207
        assert urlsplit(publisher["source"]["url"]).hostname == "api.sr.se"
        assert urlsplit(publisher["logo"]).hostname == "static-cdn.sr.se"
        assert {previous_route.hostname, current_route.hostname} <= {"edge1.sr.se", "edge2.sr.se"}


def render_or_reuse(body, masters, target, artwork_format=None):
    donor = donors.get(context["sha"](body))
    if donor is None:
        return render_original(body, masters, target, artwork_format)
    for digest, length, git_blob in donor["variants"].values():
        name = digest + ".png"
        url = context["BASE"] + f"{donor['commit']}/{donor['asset_root']}/{name}"
        with urlopen(url, timeout=30) as response:
            data = response.read(length + 1)
        assert len(data) == length and context["sha"](data) == digest and len(git_blob) == 40
        (target / name).write_bytes(data)
    return donor["variants"]


def write_with_reuse_proof(path, document):
    if path.name == "verification-proof.json":
        source_recovery = context["read"](path.parent / "source-recovery.json")
        copied = len(donors.keys() - {row["expected_sha256"] for row in source_recovery["deferred"]}) * 9
        document["approved_alias_PNGs_copied"] = copied
        document["new_original_sets"] -= copied // 9
    write_json(path, document)


context.update(check_identity=check_identity, render=render_or_reuse, write=write_with_reuse_proof)
runner(int(sys.argv[1]))
