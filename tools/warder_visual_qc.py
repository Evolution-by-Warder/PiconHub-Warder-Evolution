#!/usr/bin/env python3
"""Conservative topology and centering helpers for Warder logo rendering.

This module adds only the reusable operations missing from the production
classifier: local panel/knockout topology, logical grouping of detached
achromatic glyphs, and lossless integer translation of a rendered RGBA layer.
It intentionally does not define contrast thresholds or recolour policy.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np
from PIL import Image
from scipy import ndimage


SIZE = (220, 132)
TARGET_CENTER = (110.0, 66.0)
SAFE_BBOX = (8, 8, 212, 124)  # right/bottom are exclusive
CENTER_TOLERANCE = 0.5

# This is the exact repeated 2x2 alpha artifact identified and excluded from
# bbox measurement by the approved 8bf726a3 checkpoint. Its pixels are kept.
KNOWN_ALPHA_NOISE_SHA256 = "21cf269c35ecfb4d870caf9eb165383d8cda3236195a2660b917324f5a6ccf59"
KNOWN_ALPHA_NOISE_BBOX = (217, 129, 219, 131)
KNOWN_ALPHA_NOISE_PIXELS = 4


@dataclass(frozen=True)
class PanelTopology:
    panels: tuple[dict, ...]
    knockout_glyphs: tuple[dict, ...]
    review_reasons: tuple[str, ...]


@dataclass(frozen=True)
class CenteringResult:
    image: Image.Image
    dx: int
    dy: int
    bbox: tuple[int, int, int, int] | None
    centered: bool
    safe_area: bool
    clipped: bool
    reason: str


def mask_bbox(mask: np.ndarray) -> tuple[int, int, int, int] | None:
    ys, xs = np.nonzero(mask)
    if not len(xs):
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def _labels(mask: np.ndarray) -> tuple[np.ndarray, int]:
    return ndimage.label(mask, structure=np.ones((3, 3), dtype=np.uint8))


def _component_signature(rgba: np.ndarray, component: np.ndarray) -> tuple[str, tuple[int, int, int, int] | None, int]:
    box = mask_bbox(component)
    payload = rgba[component].tobytes()
    return hashlib.sha256(payload).hexdigest(), box, int(component.sum())


def visible_mask_for_centering(image: Image.Image) -> tuple[np.ndarray, dict]:
    """Return visible mask excluding only the checkpoint's exact alpha-noise blob.

    No source pixels are changed. The small component is omitted from geometry
    measurement only when both its exact RGBA signature and exact bbox/count
    match the approved repeated artifact.
    """
    rgba = np.asarray(image.convert("RGBA"), dtype=np.uint8)
    mask = rgba[..., 3] > 0
    labels, count = _labels(mask)
    ignored = []
    for cid in range(1, count + 1):
        component = labels == cid
        signature, box, pixels = _component_signature(rgba, component)
        if (signature == KNOWN_ALPHA_NOISE_SHA256 and box == KNOWN_ALPHA_NOISE_BBOX
                and pixels == KNOWN_ALPHA_NOISE_PIXELS and int(rgba[..., 3][component].max()) < 128):
            mask[component] = False
            ignored.append({"bbox": list(box), "pixels": pixels, "sha256": signature})
    if len(ignored) > 1:
        return mask, {"status": "REVIEW", "reason": "repeated known alpha noise component appears more than once", "ignored": ignored}
    return mask, {"status": "PASS", "ignored": ignored}


def fit_geometry_mask(source: Image.Image, source_bbox: tuple[int, int, int, int], scale: float) -> np.ndarray:
    """Map the source visible mask through the same crop/scale/placement as fit_logo."""
    rgba = np.asarray(source.convert("RGBA"), dtype=np.uint8)
    visible, evidence = visible_mask_for_centering(source)
    if evidence["status"] != "PASS":
        raise ValueError(evidence["reason"])
    x0, y0, x1, y1 = source_bbox
    cropped = Image.fromarray(visible.astype(np.uint8) * 255, "L").crop((x0, y0, x1, y1))
    fitted_size = (max(1, round(cropped.width * scale)), max(1, round(cropped.height * scale)))
    cropped = cropped.resize(fitted_size, Image.Resampling.NEAREST)
    canvas = Image.new("L", SIZE, 0)
    canvas.paste(cropped, ((SIZE[0] - cropped.width) // 2, (SIZE[1] - cropped.height) // 2))
    return np.asarray(canvas) > 0


def logical_component_groups(masks: list[np.ndarray]) -> list[list[int]]:
    """Join detached glyph components that share a line and normal word gap."""
    boxes = [mask_bbox(mask) for mask in masks]
    parent = list(range(len(masks)))

    def root(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a: int, b: int) -> None:
        ra, rb = root(a), root(b)
        if ra != rb:
            parent[rb] = ra

    heights = [box[3] - box[1] for box in boxes if box]
    typical = float(np.median(heights)) if heights else 1.0
    for i, a in enumerate(boxes):
        if not a:
            continue
        for j in range(i + 1, len(boxes)):
            b = boxes[j]
            if not b:
                continue
            vertical_overlap = max(0, min(a[3], b[3]) - max(a[1], b[1]))
            horizontal_gap = max(0, max(a[0], b[0]) - min(a[2], b[2]))
            same_baseline = abs(a[3] - b[3]) <= max(2, 0.12 * typical)
            if ((vertical_overlap >= 0.45 * min(a[3] - a[1], b[3] - b[1]) or same_baseline)
                    and horizontal_gap <= 0.75 * typical):
                union(i, j)
    groups: dict[int, list[int]] = {}
    for i in range(len(masks)):
        groups.setdefault(root(i), []).append(i)
    return list(groups.values())


def detect_local_panels(
    source: np.ndarray, *, achromatic_delta: int, luminance_fn
) -> PanelTopology:
    """Conservatively find large framed alpha fields and nested knockout glyphs.

    Geometry and thresholds are ported from the accepted proof renderer. If a
    panel-like enclosure is ambiguous, it is returned as REVIEW evidence and
    left untouched by the caller.
    """
    alpha = source[..., 3]
    visible = alpha > 0
    fg_labels, fg_count = _labels(visible)
    void_labels, void_count = _labels(alpha < 16)
    border_ids = (set(void_labels[0, :].tolist()) | set(void_labels[-1, :].tolist())
                  | set(void_labels[:, 0].tolist()) | set(void_labels[:, -1].tolist()))
    height, width = alpha.shape
    panels: list[dict] = []
    knockouts: list[dict] = []
    reviews: list[str] = []
    used_holes: set[int] = set()

    for fg_id in range(1, fg_count + 1):
        frame = fg_labels == fg_id
        frame_box = mask_bbox(frame)
        if not frame_box:
            continue
        fx0, fy0, fx1, fy1 = frame_box
        frame_area = int(frame.sum())
        box_area = max(1, (fx1 - fx0) * (fy1 - fy0))
        if frame_area < max(700, int(0.08 * width * height)) or frame_area / box_area < 0.30:
            continue
        frame_rgb = source[..., :3][frame & (alpha >= 128)]
        if not len(frame_rgb):
            continue
        frame_delta = frame_rgb.max(axis=1).astype(int) - frame_rgb.min(axis=1).astype(int)
        if float(np.mean(frame_delta <= achromatic_delta)) < 0.97:
            continue

        enclosed: list[tuple[int, np.ndarray, tuple[int, int, int, int], int]] = []
        for hole_id in range(1, void_count + 1):
            if hole_id in border_ids:
                continue
            hole = void_labels == hole_id
            hole_box = mask_bbox(hole)
            if not hole_box:
                continue
            hx0, hy0, hx1, hy1 = hole_box
            if hx0 < fx0 or hy0 < fy0 or hx1 > fx1 or hy1 > fy1:
                continue
            dilated = ndimage.binary_dilation(hole, structure=np.ones((3, 3), dtype=bool))
            if int(np.count_nonzero(dilated & frame)) < max(20, int(0.01 * np.count_nonzero(dilated))):
                continue
            enclosed.append((hole_id, hole, hole_box, int(hole.sum())))

        if not enclosed:
            continue
        panel_count_before = len(panels)
        for hole_id, hole, hole_box, area in enclosed:
            hx0, hy0, hx1, hy1 = hole_box
            ratio = area / box_area
            panel_sized = ratio >= 0.10 and (hx1 - hx0) >= 0.18 * (fx1 - fx0) and (hy1 - hy0) >= 0.35 * (fy1 - fy0)
            if not panel_sized:
                continue
            inside_ids = set(np.unique(fg_labels[hole])) - {0, fg_id}
            inside = []
            for inside_id in inside_ids:
                component = fg_labels == inside_id
                pixels = source[..., :3][component & (alpha >= 128)]
                if len(pixels) >= 8:
                    inside.append((int(inside_id), component, pixels))
            if not inside:
                reviews.append(f"possible local panel in component {fg_id}, hole {hole_id} has no separate foreground")
                continue
            foreground = np.concatenate([entry[2] for entry in inside], axis=0)
            delta = foreground.max(axis=1).astype(int) - foreground.min(axis=1).astype(int)
            achromatic_fraction = float(np.mean(delta <= achromatic_delta))
            foreground_luma = float(np.median(luminance_fn(foreground.reshape((-1, 1, 3))).reshape(-1)))
            if achromatic_fraction < 0.97 or 0.35 < foreground_luma < 0.65:
                reviews.append(f"possible local panel in component {fg_id}, hole {hole_id} has ambiguous foreground polarity")
                continue
            fill = [16, 16, 16] if foreground_luma >= 0.65 else [240, 240, 240]
            panels.append({
                "enclosing_component_id": int(fg_id), "panel_hole_id": int(hole_id),
                "mask": hole, "bbox_xyxy_exclusive": list(hole_box),
                "positive_components_inside": [entry[0] for entry in inside],
                "panel_fill_rgb": fill, "foreground_luma_median": foreground_luma,
                "foreground_achromatic_fraction": achromatic_fraction,
            })
            used_holes.add(hole_id)

        has_panel = any(record["enclosing_component_id"] == int(fg_id) for record in panels)
        if not has_panel:
            continue
        for hole_id, hole, hole_box, area in enclosed:
            if hole_id in used_holes or area < 16 or area / box_area >= 0.10:
                continue
            hx0, hy0, hx1, hy1 = hole_box
            ymargin = max(2, int(0.025 * (fy1 - fy0)))
            xmargin = max(2, int(0.025 * (fx1 - fx0)))
            if hx0 < fx0 + xmargin or hx1 > fx1 - xmargin or hy0 < fy0 + ymargin or hy1 > fy1 - ymargin:
                continue
            local = source[..., :3][frame & (alpha >= 128)]
            if not len(local):
                continue
            local_median = np.median(local, axis=0).astype(np.uint8)
            ink = [16, 16, 16] if float(luminance_fn(local_median.reshape(1, 1, 3))[0, 0]) >= 0.5 else [240, 240, 240]
            knockouts.append({"enclosing_component_id": int(fg_id), "hole_id": int(hole_id),
                              "mask": hole, "bbox_xyxy_exclusive": list(hole_box), "ink_rgb": ink})
    return PanelTopology(tuple(panels), tuple(knockouts), tuple(reviews))


def center_rgba_layer(
    layer: Image.Image, *, geometry_mask: np.ndarray | None = None,
    safe_bbox: tuple[int, int, int, int] = SAFE_BBOX,
) -> CenteringResult:
    """Integer-translate a complete RGBA layer to canvas centre without rescaling."""
    rgba = layer.convert("RGBA")
    if rgba.size != SIZE:
        return CenteringResult(rgba, 0, 0, None, False, False, False, "layer dimensions are not 220x132")
    mask = np.asarray(geometry_mask, dtype=bool) if geometry_mask is not None else np.asarray(rgba)[..., 3] > 0
    if mask.shape != (SIZE[1], SIZE[0]):
        return CenteringResult(rgba, 0, 0, None, False, False, False, "centering mask dimensions are invalid")
    box = mask_bbox(mask)
    if box is None:
        return CenteringResult(rgba, 0, 0, None, False, False, False, "visible artwork mask is empty")
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    dx, dy = int(round(TARGET_CENTER[0] - cx)), int(round(TARGET_CENTER[1] - cy))
    moved_box = (x0 + dx, y0 + dy, x1 + dx, y1 + dy)
    mx0, my0, mx1, my1 = moved_box
    centered = (abs((mx0 + mx1) / 2.0 - TARGET_CENTER[0]) <= CENTER_TOLERANCE
                and abs((my0 + my1) / 2.0 - TARGET_CENTER[1]) <= CENTER_TOLERANCE
                and abs(mx0 - (SIZE[0] - mx1)) <= 1
                and abs(my0 - (SIZE[1] - my1)) <= 1)
    sx0, sy0, sx1, sy1 = safe_bbox
    safe = mx0 >= sx0 and my0 >= sy0 and mx1 <= sx1 and my1 <= sy1
    pixels = np.asarray(rgba)
    occupied = pixels[..., 3] > 0
    ys, xs = np.nonzero(occupied)
    clipped = bool(len(xs) and (xs.min() + dx < 0 or ys.min() + dy < 0 or xs.max() + dx >= SIZE[0] or ys.max() + dy >= SIZE[1]))
    reason = ""
    if not centered:
        reason = "integer translation cannot satisfy center tolerance"
    elif not safe:
        reason = "centered artwork would violate the 8px safe area"
    elif clipped:
        reason = "translation would clip visible RGBA pixels"
    if dx == 0 and dy == 0:
        return CenteringResult(rgba, 0, 0, box, centered, safe, clipped, reason)
    if clipped:
        return CenteringResult(rgba, dx, dy, box, centered, safe, True, reason)
    output = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    output.paste(rgba, (dx, dy))
    # Exact inverse translation is part of the pixel-integrity contract.
    reverse = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    reverse.paste(output, (-dx, -dy))
    if reverse.tobytes() != rgba.tobytes():
        return CenteringResult(rgba, dx, dy, box, centered, safe, True, "inverse translation did not restore exact layer pixels")
    return CenteringResult(output, dx, dy, box, centered, safe, False, reason)
