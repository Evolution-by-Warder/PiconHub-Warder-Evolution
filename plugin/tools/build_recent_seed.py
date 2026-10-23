#!/usr/bin/env python3
"""Bundle six genuine latest-added black PNGs, preserving exact Git bytes."""
import hashlib
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
TARGET = ROOT / "plugin/src/Plugins/Extensions/WarderPiconHub/images/recent"


def build():
    history = subprocess.check_output(["git", "log", "-n", "20", "--diff-filter=A", "--format=@@%H", "--name-only", "--", "picons/*/*/black/*.png"], cwd=ROOT, text=True)
    items, seen, commit = [], set(), None
    TARGET.mkdir(parents=True, exist_ok=True)
    for line in history.splitlines():
        if line.startswith("@@"):
            commit = line[2:]
        elif line.startswith("picons/") and line.endswith(".png"):
            data = subprocess.check_output(["git", "show", commit + ":" + line], cwd=ROOT)
            sha = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
            if sha in seen:
                continue
            seen.add(sha)
            (TARGET / (sha + ".png")).write_bytes(data)
            items.append({"sha": sha, "commit": commit, "source_path": line})
            if len(items) == 6:
                break
    if len(items) != 6:
        raise ValueError("Not enough recent distinct additions")
    document = {"repository": "Evolution-by-Warder/PiconHub-Warder-Evolution", "selection": "Latest added black source paths; identical Git blobs deduplicated", "items": items}
    (TARGET / "sources.json").write_text(json.dumps(document, indent=2) + "\n")
    print(json.dumps(items))


if __name__ == "__main__":
    build()
