#!/usr/bin/env python3
"""Publish an immutable plugin IPK, verify public bytes, then advance its feed."""
import argparse
import base64
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import ssl
import sys
import time
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("warder_release_core", ROOT / "src/Plugins/Extensions/WarderPiconHub/warder_update.py")
updates = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = updates
spec.loader.exec_module(updates)
REPO, BRANCH = updates.REPOSITORY, "plugin/futuristic-rebuild"
API = "https://api.github.com/repos/" + REPO
FEED_PATH = "plugin/update/stable.json"


class GitHub:
    def __init__(self, token):
        if not token:
            raise ValueError("GitHub Actions token is missing")
        self.token = token

    def request(self, method, path, payload=None, binary=None, allow_missing=False):
        url = API + path
        headers = {"Authorization": "Bearer " + self.token, "Accept": "application/vnd.github+json",
                   "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "PiconHub-release-publisher"}
        data = None if payload is None else json.dumps(payload).encode()
        if payload is not None:
            headers["Content-Type"] = "application/json"
        if binary is not None:
            # Upload destinations are constructed locally, never read from JSON.
            url = "https://uploads.github.com/repos/" + REPO + path
            data, headers["Content-Type"] = binary, "application/octet-stream"
        try:
            with urlopen(Request(url, data=data, method=method, headers=headers),
                         timeout=90, context=ssl.create_default_context()) as response:
                return json.load(response)
        except HTTPError as exc:
            if allow_missing and exc.code == 404:
                return None
            raise RuntimeError("GitHub release API failed: HTTP %d" % exc.code) from None

    def public_package(self, url, expected_bytes):
        for attempt in range(4):
            try:
                with urlopen(Request(url, headers={"User-Agent": "PiconHub-release-verifier", "Cache-Control": "no-cache"}),
                             timeout=45, context=ssl.create_default_context()) as response:
                    return response.read(expected_bytes + 1)
            except (HTTPError, OSError):
                if attempt == 3:
                    raise
                time.sleep(3)


def manifest(path, version, notes):
    if updates.version_key(version)[4] != 4:
        raise ValueError("Only numbered releases can be published to this compatible feed")
    expected_name = updates.PACKAGE_ID + "_" + version + "_all.ipk"
    if path.name != expected_name:
        raise ValueError("Unexpected IPK filename")
    data = path.read_bytes()
    release = {"version": version, "tag": "v" + version,
               "url": "https://github.com/" + REPO + "/releases/download/v" + version + "/" + expected_name,
               "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "notes": notes.strip()}
    notes_path = ROOT / "update/RELEASE-NOTES.i18n.json"
    if notes_path.is_file():
        translated = json.loads(notes_path.read_text(encoding="utf-8"))
        if translated.get("version") == version:
            release["notes_i18n"] = translated["notes"]
    document = {"schema": 1, "product": "PiconHub Warder Evolution", "channel": "stable", "release": release}
    offered = updates.parse_release(json.dumps(document), "0.0.0")
    updates.validate_ipk(path, offered)
    return document


def publish(path, version, revision, notes, client):
    if not re.fullmatch(r"[a-f0-9]{40}", revision):
        raise ValueError("Invalid source revision")
    document = manifest(path, version, notes)
    item = document["release"]
    current = client.request("GET", "/contents/" + FEED_PATH + "?ref=" + quote(BRANCH, safe=""))
    previous = json.loads(base64.b64decode(current["content"]))
    old = previous.get("release")
    if old and updates.version_key(old["version"]) > updates.version_key(version):
        raise ValueError("Refusing to downgrade the published feed")
    if old and old["version"] == version:
        if old["sha256"] != item["sha256"] or old["bytes"] != item["bytes"]:
            raise ValueError("Published version already has different immutable bytes")
        public = client.public_package(item["url"], item["bytes"])
        if len(public) != item["bytes"] or hashlib.sha256(public).hexdigest() != item["sha256"]:
            raise ValueError("Existing published package verification failed")
        return document
    ref_path = "/git/refs/heads/" + BRANCH
    head = client.request("GET", ref_path)["object"]["sha"]
    if head != revision:
        raise ValueError("Source branch advanced; skip publishing a superseded build")
    release = client.request("GET", "/releases/tags/" + item["tag"], allow_missing=True)
    if release is None:
        release = client.request("POST", "/releases", {"tag_name": item["tag"], "target_commitish": revision,
            "name": "PiconHub Warder Evolution " + version, "body": notes.strip(),
            "draft": True, "prerelease": True, "make_latest": "false"})
    release_id = release["id"]
    if type(release_id) is not int or release_id <= 0 or release["target_commitish"] != revision:
        raise ValueError("Existing release has a different source revision")
    assets = {asset["name"]: asset for asset in release.get("assets", [])}
    package_data = path.read_bytes()
    files = ((path.name, package_data),
             (path.name + ".sha256", (item["sha256"] + "  " + path.name + "\n").encode()))
    for name, data in files:
        asset = assets.get(name)
        if asset is None:
            if not release["draft"]:
                raise ValueError("Cannot add missing bytes to an already public release")
            asset = client.request("POST", "/releases/%d/assets?name=%s" % (release_id, quote(name)), binary=data)
        if asset.get("size") != len(data) or asset.get("digest") != "sha256:" + hashlib.sha256(data).hexdigest():
            raise ValueError("Release asset does not match verified build bytes")
    if release["draft"]:
        client.request("PATCH", "/releases/%d" % release_id, {"draft": False, "prerelease": True, "make_latest": "false"})
    public = client.public_package(item["url"], item["bytes"])
    if len(public) != item["bytes"] or hashlib.sha256(public).hexdigest() != item["sha256"]:
        raise ValueError("Public release package verification failed; feed was not changed")
    # Only after public bytes pass verification, publish the feed with a strict
    # fast-forward commit. A concurrent source change makes ref advancement fail.
    source = client.request("GET", "/git/commits/" + revision)
    feed_text = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    project = json.loads((ROOT / "project.json").read_text())
    project.update(ipk_published=True, latest_published_version=version)
    tree = client.request("POST", "/git/trees", {"base_tree": source["tree"]["sha"],
        "tree": [{"path": FEED_PATH, "mode": "100644", "type": "blob", "content": feed_text},
                 {"path": "plugin/project.json", "mode": "100644", "type": "blob",
                  "content": json.dumps(project, ensure_ascii=False, indent=2) + "\n"}]})
    commit = client.request("POST", "/git/commits", {"message": "Publish verified plugin update " + version,
        "tree": tree["sha"], "parents": [revision]})
    client.request("PATCH", ref_path, {"sha": commit["sha"], "force": False})
    return document


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=pathlib.Path, default=ROOT / "build")
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    version = (ROOT / "src/Plugins/Extensions/WarderPiconHub/version.txt").read_text().strip()
    if updates.version_key(version)[4] != 4:
        print("Development package: release feed is unchanged.")
    else:
        path = args.output / (updates.PACKAGE_ID + "_" + version + "_all.ipk")
        notes = (ROOT / "update/RELEASE-NOTES.md").read_text()
        result = publish(path, version, args.revision, notes, GitHub(os.environ.get("GITHUB_TOKEN")))
        print("Verified plugin update published:", result["release"]["version"])
