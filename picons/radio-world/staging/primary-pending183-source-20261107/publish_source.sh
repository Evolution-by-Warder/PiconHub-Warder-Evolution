#!/usr/bin/env bash
set -eu
stage=picons/radio-world/staging/primary-pending183-source-20261107
branch=work/radio-primary-pending183-source-20261107
chunk=002
if test -f "$stage/chunks/chunk-$chunk/source-proof.json"; then
  python3 -c 'import json,sys; p=json.load(open(sys.argv[1])); assert p["status"]=="pass"; print("Existing exact completed source chunk preserved; regeneration skipped")' "$stage/chunks/chunk-$chunk/source-proof.json"
  exit 0
fi
python3 "$stage/reproduce_source.py" --root . --chunk "$chunk"
git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
git add "$stage"
git commit -m "Save reviewed primary source chunk $chunk exact new PNGs [skip ci]"
git push origin HEAD:"refs/heads/$branch"
python3 "$stage/pin_source.py" "$chunk"
git add "$stage"
git commit -m "Pin completed primary source chunk $chunk to immutable PNG commit [skip ci]"
git push origin HEAD:"refs/heads/$branch"
