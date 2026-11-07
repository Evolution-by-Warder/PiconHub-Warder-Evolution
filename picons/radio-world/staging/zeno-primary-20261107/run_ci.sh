#!/usr/bin/env bash
set -euo pipefail
stage=picons/radio-world/staging/zeno-primary-20261107
python3 "$stage/prepare_seed.py" "$stage" "$RUNNER_TEMP/zeno-seed"
python3 "$stage/restore_checkpoint.py" "$RUNNER_TEMP/zeno-output"
chmod +x "$stage/checkpoint_hook.sh"
python3 "$stage/freezer.py" --root "$RUNNER_TEMP/zeno-output" --input "$stage/input.json" --cache "$RUNNER_TEMP/zeno-seed/cache" --checkpoint-every 100 --checkpoint-hook "$GITHUB_WORKSPACE/$stage/checkpoint_hook.sh"
