#!/usr/bin/env python3
"""Build the pending CANAL+ provider-logo pair from the official source PNG."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image


SIZE = (220, 132)
SAFE_SIZE = (204, 116)
OFFICIAL_SOURCE_SHA256 = "9df59b91e2c73f5444b34da25f96a47190db5cca20568c3358b6ce71c078154c"
OFFICIAL_SOURCE_URL = "https://www.canalplusgroup.com/uploads/CANAL_logo_25cd1ffd9f.png"
MASTER_SHA256 = {
    "black": "61e69f7fc46e340453bf74ccd7af6ac9d8eba9f8e232884659e1ea99f6abf3fe",
    "white": "c6ae4a808a65ffc8e6458336fccbfe4216de1e832ec0a9abf800907f2f783589",
}
INK = {
    "black": np.array([240, 240, 240], dtype=np.uint8),
    "white": np.array([16, 16, 16], dtype=np.uint8),
}
TRANSPARENT_INK = np.array([16, 16, 16], dtype=np.uint8)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_wordmark_alpha(source: Image.Image) -> Image.Image:
    rgb = np.asarray(source.convert("RGB"), dtype=np.float32)
    height, width = rgb.shape[:2]
    border = np.concatenate(
        (
            rgb[:24, :, :].reshape(-1, 3),
            rgb[-24:, :, :].reshape(-1, 3),
            rgb[:, :24, :].reshape(-1, 3),
            rgb[:, -24:, :].reshape(-1, 3),
        ),
        axis=0,
    )
    background = np.median(border, axis=0)
    luma = rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722
    background_luma = float(
        background[0] * 0.2126 + background[1] * 0.7152 + background[2] * 0.0722
    )
    core = luma >= background_luma + 36.0
    ys, xs = np.nonzero(core)
    if not len(xs):
        raise SystemExit("Official source contains no detectable light CANAL+ wordmark")
    x0, x1 = max(0, int(xs.min()) - 6), min(width, int(xs.max()) + 7)
    y0, y1 = max(0, int(ys.min()) - 6), min(height, int(ys.max()) + 7)
    crop = rgb[y0:y1, x0:x1]
    channel_coverage = (crop - background.reshape(1, 1, 3)) / (
        255.0 - background.reshape(1, 1, 3)
    )
    coverage = np.clip(np.median(channel_coverage, axis=2), 0.0, 1.0)
    alpha = np.rint(coverage * 255.0).astype(np.uint8)
    alpha[alpha < 8] = 0
    if int(np.count_nonzero(alpha)) < 1000:
        raise SystemExit("Extracted CANAL+ wordmark mask is unexpectedly small")
    return Image.fromarray(alpha, "L")


def fit_mask(mask: Image.Image) -> Image.Image:
    bbox = mask.getbbox()
    if bbox is None:
        raise SystemExit("Extracted CANAL+ mask is empty")
    crop = mask.crop(bbox)
    scale = min(SAFE_SIZE[0] / crop.width, SAFE_SIZE[1] / crop.height)
    fitted_size = (
        max(1, round(crop.width * scale)),
        max(1, round(crop.height * scale)),
    )
    fitted = crop.resize(fitted_size, Image.Resampling.LANCZOS)
    canvas = Image.new("L", SIZE, 0)
    canvas.paste(fitted, ((SIZE[0] - fitted.width) // 2, (SIZE[1] - fitted.height) // 2))
    return canvas


def artwork(mask: Image.Image, ink: np.ndarray) -> Image.Image:
    alpha = np.asarray(mask, dtype=np.uint8)
    rgba = np.zeros((SIZE[1], SIZE[0], 4), dtype=np.uint8)
    rgba[..., :3] = ink
    rgba[..., 3] = alpha
    return Image.fromarray(rgba, "RGBA")


def run(repo: Path, source_path: Path) -> dict[str, object]:
    repo = repo.resolve()
    source_path = source_path.resolve()
    if sha256_file(source_path) != OFFICIAL_SOURCE_SHA256:
        raise SystemExit("Official CANAL+ source SHA256 mismatch")
    with Image.open(source_path) as raw:
        if raw.size != (1920, 1080) or raw.format != "PNG":
            raise SystemExit(f"Unexpected official source format: {raw.format} {raw.size}")
        source = raw.convert("RGB")

    out = repo / "migration/canalplus-provider-rebrand-20261022"
    source_out = out / "source/CANAL_logo_official.png"
    prepared = out / "prepared/provider-logo"
    source_out.parent.mkdir(parents=True, exist_ok=True)
    for style in ("transparent", "black", "white"):
        (prepared / style).mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_path, source_out)

    mask = fit_mask(extract_wordmark_alpha(source))
    # The source artwork is dark on transparency.  This keeps the canonical
    # asset visible in ordinary light-background previews; BLACK/WHITE variants
    # below are still rendered independently against their immutable masters.
    transparent = artwork(mask, TRANSPARENT_INK)
    transparent_path = prepared / "transparent/CANAL+.png"
    transparent.save(transparent_path, "PNG")

    outputs: dict[str, dict[str, object]] = {
        "transparent": {
            "path": transparent_path.relative_to(repo).as_posix(),
            "sha256": sha256_file(transparent_path),
            "size": list(transparent.size),
            "mode": transparent.mode,
        }
    }
    for style in ("black", "white"):
        master_path = repo / f"templates/picons/{style}-sablona.png"
        if sha256_file(master_path) != MASTER_SHA256[style]:
            raise SystemExit(f"Immutable {style.upper()} MASTER SHA256 mismatch")
        master = Image.open(master_path).convert("RGBA")
        result = Image.alpha_composite(master, artwork(mask, INK[style]))
        target = prepared / style / "CANAL+.png"
        result.save(target, "PNG")
        outputs[style] = {
            "path": target.relative_to(repo).as_posix(),
            "sha256": sha256_file(target),
            "size": list(result.size),
            "mode": result.mode,
            "master_sha256": MASTER_SHA256[style],
        }

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PREPARED_NOT_ACTIVATED",
        "provider_identity": "CANAL+",
        "official_source_url": OFFICIAL_SOURCE_URL,
        "official_source_path": source_out.relative_to(repo).as_posix(),
        "official_source_sha256": sha256_file(source_out),
        "outputs": outputs,
        "activation_rule": "Do not overwrite SKYLINK/FREESAT identities or guess service/provider mappings before verified live metadata.",
        "plugin_gui_skin_files_changed": 0,
        "master_files_changed": 0,
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.repo, args.source), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
