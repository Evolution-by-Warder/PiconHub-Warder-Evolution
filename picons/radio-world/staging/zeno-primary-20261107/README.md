# Portable Zeno primary-source continuation

Source-only continuation for the exact 1,519-reference pool, with all 17 parallel singleton refs excluded. No PNG renderer, ZIP creation, catalogue edits, graphic approval, Git operations, credentials or login are present in the freezer.

Local HTTP retrieval is stopped. The package preserves the complete successful pilot and local bulk cache: 135 original URL records, 122 distinct SHA-256 raw objects, 133 canonical URL records, 46 candidate checkpoints, 18 logo-frozen sources, and one identity-passed source still awaiting retrieval. All remaining refs are candidates. These counts are not final coverage or graphic approvals.

## Run

Requires Python 3.10+ and Pillow, Linux `fcntl` (GitHub Ubuntu runner). Extract the successful immutable cache, then run:

```bash
tar -xzf cache.tar.gz
python freezer.py --root output --input input.json --cache cache --checkpoint-every 100
```

The same output directory can be resumed with identical input. Cache directory and output directory use `objects/{sha256}.body`, successful response journals, and `source-review-rows.json`. Successful SHA objects are verified before reuse. Equivalent query encoding is canonicalized without changing raw response provenance. Existing picon ZIPs are never accessed or generated.

Optional `--checkpoint-hook /absolute/executable` invokes that exact caller-provided executable as `HOOK OUTPUT_DIR PHASE` after atomic checkpoints (every 100 completed tasks by default, at each phase boundary, and initial/final states). The caller can commit the isolated source working branch. The freezer itself does not access Git or credentials. Hooks must be idempotent because the initial checkpoint may repeat unchanged state. A failed hook stops work and saves an interruption checkpoint without invoking the failed hook again.

Retain the entire output directory, including `objects/`, `source-review-rows.json`, `http-responses.jsonl` and `http-success-cache.jsonl`. The successful cache journal includes imported successes. Temporary `.tmp` files and `freezer.lock` need not be committed. The output contains only primary source evidence; source-review contacts can be generated separately from pinned raw images after freeze ranges are ready.

## Admission and failure behavior

Public anonymous API detail must prove exact `stream.zeno.fm` mount, identical explicit `streamName`, and explicit API `country` equal to the catalogue country. The name query/title only guides discovery. It never admits a source or changes a catalogue ref. Every returned logo must be tied to the exact same station ID on the official Zeno proxy/signed-image URL, or the exact pilot-proven bucket path `https://zenoimages.s3.us-west-001.backblazeb2.com/{same-id}/images/logo`. Wrong IDs, unrelated CDN paths and generic platform asset URLs are rejected. Both original and final URLs are checked.

Four concurrent workers and a shared four-request semaphore enforce the global limit in this process; a nonblocking file lock prevents two freezers using the same output directory. Public HTTP requests have bounded timeouts. Transient HTTP 408/425/429/500/502/503/504 and network errors have at most three total attempts per URL per run, respecting Retry-After via a global cooldown. Successful URLs are not re-fetched. Permanent HTTP errors are not retried in the same run. Retrieval/transport/invalid-contract failures remain pending; they do not become country or graphic holds. A later resume may retry pending retrievals.

`logo-frozen` proves only source provenance, raw SHA and image integrity. It explicitly requires actual visual source QA and later all nine picon variants. Generic badges, photos, wrong station art and ambiguous identity are never graphically approved by this code. No output grants graphic approval. Exact mount and country can still point at an unusable logo; reviewers must hold it.

## Validation already performed

`offline-smoke-proof.json` records PASS with zero network requests: 1,519 input rows restored, all 133 canonical successful cache URLs rehashed/reused, all 18 already frozen primary identities re-ingested, and wrong station ID / generic asset / untrusted host URL tests rejected. The independent original checkpoint audit also verifies every successful raw object and each of the 18 frozen raster sources against their SHA, bytes, dimensions, exact stream and explicit country. Neither test is a visual approval.

`package-manifest.json` pins the script, exact input and cache archive by SHA-256. `build_package.py` is the local reproducible packager, not needed in CI. `offline_smoke.py` is a package-level local validation script, not a fetch or renderer.

## Isolated GitHub runner

Source branch: `work/radio-zeno1519-source-20261107`. Output branch: `work/radio-zeno1519-frozen-20261107`. Both are separate from production and open integration PR branches. The source package cache is split into 24 parts of at most 300,000 bytes and verified against `cache-parts.json` before extraction.

Exactly one CI job executes public source retrieval, with source requests paused during the checkpoint hook. The publisher uses the job-scoped token only against the fixed repository and fixed output ref; checkout does not persist credentials. Each checkpoint saves directly readable source rows/progress/success journals and incremental immutable raw-object tar shards (at most 200 objects or 16 MiB raw per shard, except a single bounded 24 MiB object). The SHA-to-shard manifest allows exact source recovery. A repeat run restores the immutable output commit, verifies all shard/object hashes, and resumes its rows and cache without refetching successful source responses. No renderer or picon package creation occurs.
