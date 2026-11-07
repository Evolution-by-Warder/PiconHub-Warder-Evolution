#!/usr/bin/env bash
set -euo pipefail
stage=picons/radio-world/staging/zeno-primary-20261107
python3 "$stage/publish_checkpoint.py" "$1" "$2"
