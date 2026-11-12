"""Validate publisher-bound inputs and commit hash-pinned artwork to the draft."""
import base64
import gzip
import hashlib
import io
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPException
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from PIL import Image

STAGING = Path("picons/radio-world/staging")
BRANCH = "work/radio-world-batch38-contrast-pass1-history-20261107"
BASE = "https://raw.githubusercontent.com/Evolution-by-Warder/PiconHub-Warder-Evolution/"
sys.path.insert(0, "picons/radio-world/tools")
from saved_artwork_import import get
from visual_gate import identity_blocks, merge_ledgers, read, validate_selection


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(path, obj):
    body = (json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(body, mtime=0) if path.suffix == ".gz" else body)


def key(url):
    route = urlsplit(url)
    assert route.scheme in ("http", "https") and not route.username and not route.password
    return route.hostname, route.port, route.path, route.query


def git(*args):
    subprocess.run(["git", *args], check=True)


def commit(message, *paths):
    git("add", *map(str, paths))
    git("commit", "-m", message + " [skip ci]")
    git("push", "origin", f"HEAD:refs/heads/{BRANCH}")
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def check_identity(row):
    station = row["station"]
    publisher = row["publisher"]
    assert row["image"] == row["original"]["url"] == publisher["logo"]
    if row["kind"] == "iheart-mx":
        assert row["country"] == publisher["countries"] == "MX"
        assert publisher["provider"] in {"ACIR", "Grupo Radio Centro"}
        assert publisher["isActive"] is True
        assert key(station["url"]) in {
            key(url) for url in publisher["streams"].values() if isinstance(url, str)
        }
        assert urlsplit(row["image"]).hostname == "i.iheart.com"
    elif row["kind"] == "absolut-clubnight":
        assert row["country"] == "DE" and publisher["id"] == "clubnight"
        route = key(station["url"])
        assert route[0] == "edge68.live-sm.absolutradio.de"
        assert route[1:] == key(publisher["official_mp3"])[1:]
        assert publisher["official_mp3"] == (
            "https://absolut-clubnight.live-sm.absolutradio.de/absolut-clubnight/stream/mp3"
        )
        edge = publisher["observed_edge"]
        assert edge["url"] == station["url"] == edge["final"]
        assert edge["status"] == 200 and edge["icy_name"] == "Absolut Club Night"
        assert edge["content_type"] == "audio/mpeg"
        assert urlsplit(row["image"]).hostname == "cms.antenne-deutschland.de"
    elif row["kind"] == "iono":
        assert publisher["country"] == row["country"]
        assert key(station["url"]) in {key(url) for url in publisher["streams"]}
        assert urlsplit(row["image"]).hostname == "cdn.iono.fm"
    elif row["kind"] == "rnz":
        assert row["country"] == "NZ"
        assert key(station["url"]) in {key(url) for url in publisher["streams"]}
        assert urlsplit(row["image"]).hostname in {"rnz.co.nz", "www.rnz.co.nz", "media.rnztools.nz", "rnz-ressh.cloudinary.com"}
    elif row["kind"] == "radyo-natin":
        assert row["country"] == "PH"
        assert publisher["id"].startswith("https://radyonatinfm.com/radio-channel/")
        assert row["image"].startswith("https://radyonatinfm.com/wp-content/uploads/")
        assert key(station["url"]) in {key(url) for url in publisher["streams"]}
    elif row["kind"] == "radio-algerienne":
        assert row["country"] == "DZ"
        assert publisher["id"].startswith("https://radioalgerie.dz/player/ar/live/")
        assert urlsplit(row["image"]).hostname == "radioalgerie.dz"
        assert key(station["url"]) in {key(url) for url in publisher["streams"]}
    elif row["kind"] == "radio-algerienne-regional":
        assert row["country"] == "DZ"
        assert urlsplit(publisher["id"]).hostname == "my.radioalgerie.dz"
        assert publisher["player"]["url"].startswith("https://my.radioalgerie.dz/player/")
        assert row["image"].startswith("https://my.radioalgerie.dz/sites/default/files/")
        assert "locales.png" not in row["image"]
        assert key(station["url"]) in {key(url) for url in publisher["streams"]}
    elif row["kind"] == "radio-nacional-argentina":
        assert row["country"] == "AR"
        assert urlsplit(publisher["id"]).hostname == "www.radionacional.com.ar"
        assert key(station["url"]) in {key(url) for url in publisher["streams"]}
        logo_name = urlsplit(row["image"]).path.rsplit("/", 1)[-1]
        expected = {
            "/sc_rad1": "Logo_AM870_b.png",
            "/sc_rad37": "Logo_Clasica.png",
            "/sc_rad38": "Logo_Folklorica.png",
            "/sc_rad39": "Logo_Rock.png",
            "/sc_rad35": "Logo_RAE.png",
        }
        assert expected[urlsplit(station["url"]).path] == logo_name
    elif row["kind"] in {"radio-record", "mediacorp-radio", "radio-clasic"}:
        assert row["country"] == {"radio-record": "RU", "mediacorp-radio": "SG", "radio-clasic": "RO"}[row["kind"]]
        assert key(station["url"]) in {key(url) for url in publisher["streams"]}
    elif row["kind"] == "mediaset-radio":
        assert row["country"] == "IT"
        host = urlsplit(publisher["id"]).hostname
        assert host in {"www.virginradio.it", "www.105.net", "www.radiomontecarlo.net", "www.r101.it"}
        assert urlsplit(publisher["id"]).path.startswith("/web-radio/")
        assert urlsplit(row["image"]).hostname == host
        assert urlsplit(row["image"]).path.startswith("/wp-content/uploads/")
        displayed = urlsplit(publisher["displayed_logo"])
        assert displayed.hostname == "img-api.cloud.mediaset.net"
        asset = displayed.path.split("/")[6]
        assert base64.urlsafe_b64decode(asset + "=" * (-len(asset) % 4)).decode() == row["image"]
        route = key(station["url"])
        assert route[0] == "icy.unitedradio.it"
        assert route in {key(url) for url in publisher["streams"]}
    elif row["kind"] == "ehr-latvia":
        assert row["country"] == "LV"
        assert publisher["id"] == "https://www.ehr.fm/radio/latviesu-hiti"
        assert publisher["channel_id"] == publisher["show"]["channel_id"] == 8
        assert row["image"].startswith("https://www.ehr.fm/storage/channels/")
        assert row["image"].endswith(".svg") and row["original"]["format"] == "svg"
        stream, = publisher["streams"]
        assert f'href="{stream}"' in publisher["show"]["description"]
        assert key(station["url"]) == key(stream) == ("stream.ehrhiti.lv", 8000, "/Stream_22.aac", "")
    elif row["kind"] in {"skonto-radio", "relax-fm-latvia", "radioplayer-kg", "paradise-fm-curacao"}:
        expected = {
            "skonto-radio": ("LV", "radioskonto.lv", "/uploads/"),
            "relax-fm-latvia": ("LV", "relaxfm.lv", "/upload/players/"),
            "radioplayer-kg": ("KG", "radioplayer.kg", "/img/"),
            "paradise-fm-curacao": ("CW", "player.paradisefm.cw", "/"),
        }
        country, host, logo_path = expected[row["kind"]]
        assert row["country"] == country
        assert urlsplit(publisher["source"]["url"]).hostname == host
        logo = urlsplit(row["image"])
        assert logo.hostname == host and logo.path.startswith(logo_path)
        if row["kind"] == "paradise-fm-curacao":
            assert publisher["source_fields"]["is_active"] is True
            assert urlsplit(station["url"]).hostname == "stream.paradisefm.cw"
        assert key(station["url"]) in {key(url) for url in publisher["streams"]}
    else:
        raise ValueError(f"Unknown source kind: {row['kind']}")


def verify_original(entry, body):
    if len(body) != entry["bytes"] or sha(body) != entry["sha256"]:
        raise ValueError("Original does not match the reviewed byte count and SHA-256")
    with Image.open(io.BytesIO(body)) as source:
        if list(source.size) != entry["dimensions"]:
            raise ValueError("Original dimensions differ from the visual review")
        source.verify()


def diagnostic_url(url):
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc.rsplit("@", 1)[-1], parts.path, "", ""))


def probe_cached_source(url):
    attempt = dict(method="default-probe")
    try:
        with urlopen(url, timeout=15) as response:
            attempt.update(http_status=response.status, final_url=diagnostic_url(response.geturl()))
    except HTTPError as error:
        attempt.update(http_status=error.code, final_url=diagnostic_url(error.geturl()))
        error.close()
    except (OSError, HTTPException) as error:
        attempt["error"] = type(error).__name__
    return attempt


def fetch_original(row, target):
    entry = row["original"]
    digest = entry["sha256"]
    url = entry["url"]
    path = target / (digest + ".img")
    report = dict(
        country=row["country"], reference=row["station"]["reference"],
        station=row["station"]["name"], url=diagnostic_url(url),
        expected_sha256=digest, attempts=[],
    )
    if path.is_file():
        try:
            body = path.read_bytes()
            verify_original(entry, body)
        except (OSError, ValueError, SyntaxError, Image.DecompressionBombError) as error:
            report["attempts"].append(dict(method="saved-original", error=type(error).__name__))
        else:
            if os.environ.get("GITHUB_ACTIONS") == "true":
                report["attempts"].append(probe_cached_source(url))
                print(json.dumps(report, ensure_ascii=False), flush=True)
            return digest, body, dict(report, status="verified", source="saved-original")

    headers = {
        "User-Agent": "Mozilla/5.0", "Accept": "image/*",
        "Referer": diagnostic_url(row["publisher"]["source"]["url"]),
    }
    for method, request_headers in (("default", {}), ("publisher-context", headers)):
        attempt = dict(method=method)
        report["attempts"].append(attempt)
        try:
            with urlopen(Request(url, headers=request_headers), timeout=20) as response:
                attempt.update(http_status=response.status, final_url=diagnostic_url(response.geturl()))
                body = response.read(entry["bytes"] + 1)
            verify_original(entry, body)
        except HTTPError as error:
            attempt.update(http_status=error.code, final_url=diagnostic_url(error.geturl()))
            error.close()
        except (OSError, HTTPException, ValueError, SyntaxError, Image.DecompressionBombError) as error:
            attempt["error"] = type(error).__name__
        else:
            path.write_bytes(body)
            return digest, body, dict(report, status="verified", source="publisher")
        print(json.dumps(dict(report, status="retry-or-defer"), ensure_ascii=False), flush=True)
    return digest, None, dict(report, status="deferred")


def render(body, masters, target, artwork_format=None):
    if artwork_format == "svg":
        from resvg_py import svg_to_bytes

        assert b"<text" not in body and b"href=" not in body and b"<image" not in body
        body = svg_to_bytes(svg_string=body.decode("utf-8"), skip_system_fonts=True)
    mark = Image.open(io.BytesIO(body)).convert("RGBA")
    mark.thumbnail((192, 104), Image.Resampling.LANCZOS)
    position = ((220 - mark.width) // 2, (132 - mark.height) // 2)
    variants = {}
    for style, master in masters.items():
        image = master.copy()
        if style == "transparent":
            image.paste(mark, position)
        else:
            image.alpha_composite(mark, position)
        for size in ("50x30", "220x132", "400x240"):
            dimensions = tuple(map(int, size.split("x")))
            final = image if image.size == dimensions else image.resize(dimensions, Image.Resampling.LANCZOS)
            output = io.BytesIO()
            final.save(output, format="PNG", optimize=True)
            raw = output.getvalue()
            digest = sha(raw)
            blob = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
            (target / (digest + ".png")).write_bytes(raw)
            variants[f"{size}/{style}"] = [digest, len(raw), blob]
    return variants


def main(batch):
    stage = STAGING / f"batch-{batch}-reviewed"
    previous = STAGING / f"batch-{batch - 1}-reviewed"
    spec = read(stage / "source-inputs/recovery-spec.json")
    config = read(previous / "configuration.json")
    baseline = (previous / "countries.proposed.json").read_bytes()
    assert sha(baseline) == spec["baseline_sha256"]
    assert len(config["held_references"]) == 923
    countries = {country["id"]: country["name"] for country in json.loads(baseline)["countries"]}
    world = json.loads(gzip.decompress(get(config["world"])))
    by_ref = {(row["group"], row["reference"]): row for row in world}
    paths = [
        STAGING / "source-ledger-reviewed-20261107/visual-ledger.json.gz",
        STAGING / "visual-review-34-36/decisions.json.gz",
        *(STAGING / f"batch-{n}-reviewed/visual-ledger.json.gz" for n in range(39, batch)),
    ]
    history = merge_ledgers(paths)
    known = {(e["row"]["country"], e["row"]["ref"]) for e in history["entries"]}
    blocked = identity_blocks(history)
    selected = spec["stations"]
    assert len(selected) == len({row["station"]["reference"] for row in selected}) > 0
    for row in selected:
        station = row["station"]
        ref = station["reference"]
        assert by_ref[station["group"], ref] == station and countries[row["country"]] == station["group"]
        assert sha(station["url"].encode()) == row["catalog_url_sha256"]
        assert (row["country"], ref) not in known | blocked and ref not in config["held_references"]
        check_identity(row)

    original_dir, asset_dir = stage / "originals", stage / "verified-assets"
    original_dir.mkdir(exist_ok=True)
    asset_dir.mkdir(exist_ok=True)
    entries = {row["original"]["sha256"]: row for row in selected}

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda row: fetch_original(row, original_dir), entries.values()))
    originals = {digest: body for digest, body, _ in results if body is not None}
    recovery = {digest: result for digest, _, result in results}
    deferred = [
        dict(recovery[row["original"]["sha256"]], country=row["country"],
             reference=row["station"]["reference"], station=row["station"]["name"])
        for row in selected if row["original"]["sha256"] not in originals
    ]
    recovery_proof = stage / "source-recovery.json"
    write(recovery_proof, dict(previous_failed_run=43213850034,
                               sources=list(recovery.values()), deferred=deferred))
    print(f"Verified {len(originals)} original files; {len(deferred)} references deferred", flush=True)
    assert originals, "No reviewed original was available"
    masters = {"transparent": Image.new("RGBA", (220, 132))}
    for style, digest in spec["master_sha256"].items():
        url = BASE + spec["master_commit"] + f"/plugin/artwork/templates/picons/{style}-sablona.png"
        with urlopen(url, timeout=30) as response:
            raw = response.read()
        assert sha(raw) == digest
        masters[style] = Image.open(io.BytesIO(raw)).convert("RGBA")
        assert masters[style].size == (220, 132)
    rendered = {}
    rows = []
    for offset, row in enumerate(selected):
        digest = row["original"]["sha256"]
        if digest not in originals:
            continue
        if digest not in rendered:
            rendered[digest] = render(originals[digest], masters, asset_dir, row["original"].get("format"))
        assert rendered[digest] == row["variants"], row["station"]["reference"]
        station = row["station"]
        rows.append(dict(
            index=batch * 10000 + offset, country=row["country"], ref=station["reference"],
            station=dict(name=station["name"], url=station["url"].split("?")[0], group=station["group"]),
            asset_root=str(stage), variants=row["variants"],
            provenance=dict(publisher=row["publisher"], original=row["original"],
                            catalog_url_sha256={"new": row["catalog_url_sha256"]},
                            identity_basis=row["kind"],
                            approval_authority="Owner advance approval of verified picons"),
        ))
    verification = dict(
        status="pass", references=len(rows), PNG_instances=len(rows) * 9,
        new_original_sets=len(originals), approved_alias_PNGs_copied=0,
        reused_new_original_variant_instances=9 * (len(rows) - len(originals)),
        existing_PNGs_rerendered=0, configuration_blocks=923,
        historical_holds_preserved=True, master_sha256=spec["master_sha256"],
    )
    proof = stage / "verification-proof.json"
    write(proof, verification)
    git("config", "user.name", "github-actions[bot]")
    git("config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
    asset_commit = commit(f"Save batch {batch} reviewed originals and PNGs", original_dir, asset_dir, proof, recovery_proof)
    for row in rows:
        row.update(source_commit=asset_commit, final_visual_approval=dict(
            decision="approve", reason="Publisher originals on approved masters, visually inspected",
            reviewed_variants=row["variants"],
        ))
    selection = stage / "selection.json.gz"
    ledger = stage / "visual-ledger.json.gz"
    write(selection, dict(entries=rows))
    write(ledger, dict(entries=[dict(row=row, decision="approve", reason=row["final_visual_approval"]["reason"],
                                     reviewed_variants=row["variants"]) for row in rows],
                       source_holds=[], pending_sources=[]))
    assert validate_selection(rows, merge_ledgers(paths + [ledger])) == len(rows)
    previous_index = stage / "baseline.previous.json"
    previous_index.write_bytes(baseline)
    config.update(batch=f"{batch}-reviewed", references=len(rows), parent_candidate=spec["parent"],
                  expected_coverage=spec["baseline_references"] + len(rows),
                  selection_sha256=sha(selection.read_bytes()),
                  baseline_index=dict(url=BASE + spec["parent"] + "/" + str(previous / "countries.proposed.json"),
                                      bytes=len(baseline), sha256=sha(baseline)))
    configuration = stage / "configuration.json"
    write(configuration, config)
    commit(f"Save batch {batch} selection and identity bindings", selection, ledger, previous_index, configuration)


if __name__ == "__main__":
    main(int(sys.argv[1]))
