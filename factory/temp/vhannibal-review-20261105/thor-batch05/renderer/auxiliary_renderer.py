#!/usr/bin/env python3
"""Auxiliary-only Warder renderer extracted from approved QC checkpoint 13dd00b5624c4b6659574cdddedd503edc18947.

This module is not imported by the channel production CLI.

The classifier is deliberately conservative.  It only recolours a complete
8-connected achromatic component.  A chromatic component is never modified;
if it contains a material light/dark region that can disappear on a master,
the source is classified REVIEW and the untouched-colour candidate is emitted.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np
from PIL import Image
from scipy import ndimage

from warder_visual_qc import (
    center_rgba_layer,
    detect_local_panels,
    fit_geometry_mask,
    logical_component_groups,
    mask_bbox as warder_visual_bbox,
)


SIZE = (220, 132)

# Frozen V9 production constants.  Borderline chroma/contrast is REVIEW.
OPAQUE_ALPHA = 32
ACHROMATIC_DELTA = 18
ACHROMATIC_REQUIRED = 0.985
ACHROMATIC_CONTRAST_RATIO = 2.50
MATERIAL_FRACTION = 0.08
TWO_TONE_FRACTION = 0.03
SAFE_MARGIN_X = 8
SAFE_MARGIN_Y = 8
RECOLOUR_BLACK = np.array([16, 16, 16], dtype=np.uint8)
RECOLOUR_WHITE = np.array([240, 240, 240], dtype=np.uint8)


@dataclass
class VariantResult:
    status: str
    reason: str
    image: Image.Image
    changed_pixels: int
    protected_pixels: int
    centering_dx: int = 0
    centering_dy: int = 0
    alpha_geometry_sha256: str = ""


def fit_logo(source: Image.Image) -> tuple[Image.Image, float, tuple[int, int, int, int]]:
    """Proportionally fit the visible logo inside the MASTER safe area and centre it."""
    bbox = source.getchannel("A").getbbox()
    if bbox is None:
        return source.copy(), 1.0, (0, 0, 0, 0)
    crop = source.crop(bbox)
    max_w = SIZE[0] - 2 * SAFE_MARGIN_X
    max_h = SIZE[1] - 2 * SAFE_MARGIN_Y
    scale = min(1.0, max_w / crop.width, max_h / crop.height)
    new_size = (max(1, round(crop.width * scale)), max(1, round(crop.height * scale)))
    if new_size != crop.size:
        crop = crop.resize(new_size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    xy = ((SIZE[0] - crop.width) // 2, (SIZE[1] - crop.height) // 2)
    canvas.alpha_composite(crop, xy)
    return canvas, scale, bbox


def rel_luma(rgb: np.ndarray) -> np.ndarray:
    x = rgb.astype(np.float32) / 255.0
    x = np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)
    return x[..., 0] * 0.2126 + x[..., 1] * 0.7152 + x[..., 2] * 0.0722


def contrast_ratio(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    la, lb = rel_luma(a), rel_luma(b)
    hi, lo = np.maximum(la, lb), np.minimum(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def master_rgb_under(master: np.ndarray, mask: np.ndarray) -> np.ndarray:
    # Masters are used exactly as stored.  For contrast QC their semi-transparent
    # pixels are evaluated against black, matching normal transparent rendering.
    rgb = master[..., :3].astype(np.float32)
    alpha = master[..., 3:4].astype(np.float32) / 255.0
    rendered = np.rint(rgb * alpha).astype(np.uint8)
    return rendered[mask]


def classify_and_render(
    source: Image.Image,
    master: Image.Image,
    style: str,
    *,
    centering_mask: np.ndarray | None = None,
) -> VariantResult:
    """Render one style using the shared Warder component-aware policy.

    Production contrast constants remain the policy authority. Local panel and
    logical grouping evidence is supplied by ``warder_visual_qc``; only
    achromatic masks are recoloured, and uncertain chromatic/two-tone cases
    remain REVIEW. Final centering translates the RGBA artwork layer only.
    """
    src = np.array(source, dtype=np.uint8)
    mst = np.array(master, dtype=np.uint8)
    alpha = src[..., 3]
    visible = alpha > 0
    solid = alpha >= OPAQUE_ALPHA
    labels, _ = ndimage.label(visible, structure=np.ones((3, 3), dtype=np.uint8))
    work = src.copy()
    changed = 0
    protected = np.zeros(visible.shape, dtype=bool)
    review_reasons: list[str] = []
    fixed_components = 0
    topology = detect_local_panels(src, achromatic_delta=ACHROMATIC_DELTA, luminance_fn=rel_luma)
    review_reasons.extend(topology.review_reasons)
    if len(topology.panels) > 1:
        review_reasons.append("multiple local panel candidates require review")
    local_masks: list[np.ndarray] = []
    for panel in topology.panels:
        hole = panel["mask"]
        work[..., :3][hole] = np.asarray(panel["panel_fill_rgb"], dtype=np.uint8)
        work[..., 3][hole] = 255
        local_masks.append(hole)
        protected |= labels == panel["enclosing_component_id"]
        for component_id in panel["positive_components_inside"]:
            protected |= labels == component_id
    for glyph in topology.knockout_glyphs:
        hole = glyph["mask"]
        work[..., :3][hole] = np.asarray(glyph["ink_rgb"], dtype=np.uint8)
        work[..., 3][hole] = 255
        local_masks.append(hole)

    local_union = np.logical_or.reduce(local_masks) if local_masks else np.zeros(visible.shape, dtype=bool)
    changed_alpha = work[..., 3] != src[..., 3]
    if np.any(changed_alpha & ~local_union):
        review_reasons.append("alpha geometry changed outside a recognized local panel/knockout mask")
    for panel in topology.panels:
        panel_bg = np.asarray(panel["panel_fill_rgb"], dtype=np.uint8).reshape((1, 1, 3))
        for component_id in panel["positive_components_inside"]:
            foreground_mask = (labels == component_id) & solid
            if not np.any(foreground_mask):
                continue
            foreground = src[..., :3][foreground_mask]
            local_bg = np.broadcast_to(panel_bg, foreground.reshape((-1, 1, 3)).shape)
            local_cr = contrast_ratio(foreground.reshape((-1, 1, 3)), local_bg).reshape(-1)
            if float(np.mean(local_cr < ACHROMATIC_CONTRAST_RATIO)) >= MATERIAL_FRACTION:
                review_reasons.append(f"local panel foreground {component_id} remains low-contrast against its panel")
    for glyph in topology.knockout_glyphs:
        frame_mask = (labels == glyph["enclosing_component_id"]) & solid
        if np.any(frame_mask):
            local_bg = np.median(src[..., :3][frame_mask], axis=0).astype(np.uint8).reshape((1, 1, 3))
            ink = np.asarray(glyph["ink_rgb"], dtype=np.uint8).reshape((1, 1, 3))
            local_cr = float(contrast_ratio(ink, local_bg)[0, 0])
            if local_cr < ACHROMATIC_CONTRAST_RATIO:
                review_reasons.append("local knockout glyph remains low-contrast against its enclosing panel")

    achromatic_delta = src[..., :3].astype(np.int16).max(axis=2) - src[..., :3].astype(np.int16).min(axis=2)
    achromatic = visible & (achromatic_delta <= ACHROMATIC_DELTA)
    grouped: list[dict] = []
    adapted_groups: list[dict] = []
    total_rgb = src[..., :3][visible]
    total_delta = (total_rgb.max(axis=1).astype(int) - total_rgb.min(axis=1).astype(int)
                   if len(total_rgb) else np.array([]))
    pure_achromatic = bool(
        len(total_delta)
        and float(np.mean(total_delta <= ACHROMATIC_DELTA)) >= ACHROMATIC_REQUIRED
        and not topology.panels
    )
    if pure_achromatic:
        whole = visible & ~protected
        samples = whole & solid
        ratios = contrast_ratio(src[..., :3][samples].reshape((-1, 1, 3)), master_rgb_under(mst, samples).reshape((-1, 1, 3))) if samples.any() else np.array([])
        weak = float(np.mean(ratios < ACHROMATIC_CONTRAST_RATIO)) if ratios.size else 0.0
        group = {"logical_component": "whole achromatic artwork", "bbox_xyxy_exclusive": warder_visual_bbox(whole),
                 "pixel_count": int(whole.sum()), "low_contrast_before_fraction": weak}
        grouped.append(group)
        if weak >= MATERIAL_FRACTION:
            target = RECOLOUR_WHITE if style == "black" else RECOLOUR_BLACK
            work[..., :3][whole] = target
            changed += int(whole.sum())
            fixed_components += 1
            adapted_groups.append({**group, "target_rgb": target.astype(int).tolist()})
        after = contrast_ratio(work[..., :3][samples].reshape((-1, 1, 3)), master_rgb_under(mst, samples).reshape((-1, 1, 3))) if samples.any() else np.array([])
        group["post_render_contrast_pass"] = (float(np.mean(after < ACHROMATIC_CONTRAST_RATIO)) < MATERIAL_FRACTION) if after.size else True
        if not group["post_render_contrast_pass"]:
            review_reasons.append("whole achromatic artwork remains low-contrast after render")
    else:
        grouped_labels, grouped_count = ndimage.label(achromatic & solid, structure=np.ones((3, 3), dtype=np.uint8))
        component_masks: list[np.ndarray] = []
        component_meta: list[int] = []
        for component_id in range(1, grouped_count + 1):
            component = grouped_labels == component_id
            if int(component.sum()) < 12 or np.any(component & protected) or any(np.any(component & mask) for mask in local_masks):
                continue
            component_masks.append(component)
            component_meta.append(component_id)
        for group_ids in logical_component_groups(component_masks):
            group_mask = np.logical_or.reduce([component_masks[i] for i in group_ids])
            samples = group_mask & solid
            if not samples.any():
                continue
            ratios = contrast_ratio(src[..., :3][samples].reshape((-1, 1, 3)), master_rgb_under(mst, samples).reshape((-1, 1, 3)))
            weak = float(np.mean(ratios < ACHROMATIC_CONTRAST_RATIO))
            group = {"component_ids": [component_meta[i] for i in group_ids],
                     "bbox_xyxy_exclusive": warder_visual_bbox(group_mask),
                     "pixel_count": int(group_mask.sum()), "low_contrast_before_fraction": weak}
            grouped.append(group)
            if weak >= MATERIAL_FRACTION:
                target = RECOLOUR_WHITE if style == "black" else RECOLOUR_BLACK
                work[..., :3][group_mask] = target
                changed += int(group_mask.sum())
                fixed_components += 1
                adapted_groups.append({**group, "target_rgb": target.astype(int).tolist()})
            after = contrast_ratio(work[..., :3][samples].reshape((-1, 1, 3)), master_rgb_under(mst, samples).reshape((-1, 1, 3)))
            group["post_render_contrast_pass"] = float(np.mean(after < ACHROMATIC_CONTRAST_RATIO)) < MATERIAL_FRACTION
            if not group["post_render_contrast_pass"]:
                review_reasons.append(f"logical achromatic group {group['component_ids']} remains low-contrast on {style.upper()}")

    # Existing conservative chromatic/two-tone review remains active, while
    # local panel text and panel surfaces are evaluated against their local
    # field and therefore excluded from outer-master comparison.
    labels_for_review, review_count = ndimage.label(visible, structure=np.ones((3, 3), dtype=np.uint8))
    for component_id in range(1, review_count + 1):
        component = (labels_for_review == component_id) & ~local_union
        if np.any(component & protected):
            continue
        component_solid = component & solid
        if not component_solid.any():
            continue
        rgb = src[..., :3][component_solid]
        delta = rgb.max(axis=1).astype(np.int16) - rgb.min(axis=1).astype(np.int16)
        is_achromatic = float(np.mean(delta <= ACHROMATIC_DELTA)) >= ACHROMATIC_REQUIRED
        luma = rel_luma(rgb.reshape((-1, 1, 3))).reshape(-1) * 255.0
        two_tone = (float(np.mean(luma <= 64.0)) >= TWO_TONE_FRACTION
                    and float(np.mean(luma >= 192.0)) >= TWO_TONE_FRACTION)
        if is_achromatic and not two_tone:
            continue
        protected |= component
        cr = contrast_ratio(rgb.reshape((-1, 1, 3)), master_rgb_under(mst, component_solid).reshape((-1, 1, 3))).reshape(-1)
        weak = float(np.mean(cr < ACHROMATIC_CONTRAST_RATIO))
        if weak >= MATERIAL_FRACTION:
            kind = "two-tone achromatic" if two_tone else "chromatic"
            review_reasons.append(f"{kind} component {component_id} has {weak:.1%} materially low-contrast pixels on {style.upper()}")

    chromatic = visible & solid & (achromatic_delta > ACHROMATIC_DELTA)
    if local_masks:
        chromatic &= ~local_union
    if np.any(work[..., :3][chromatic] != src[..., :3][chromatic]):
        raise RuntimeError("chromatic brand component changed")

    logo = Image.fromarray(work, "RGBA")
    centered = center_rgba_layer(logo, geometry_mask=centering_mask)
    if centered.reason:
        review_reasons.append(centered.reason)
    logo = centered.image
    result = Image.alpha_composite(master, logo)
    if review_reasons:
        status = "REVIEW"
        reason = "; ".join(review_reasons)
    elif changed:
        status = "AUTO-FIXED"
        reason = f"recoloured {fixed_components} safely isolated achromatic component(s)"
    else:
        status = "PASS"
        reason = "source components preserved; no approved contrast correction required"
    alpha_geometry_sha256 = hashlib.sha256(np.asarray(logo, dtype=np.uint8)[..., 3].tobytes()).hexdigest()
    return VariantResult(status, reason, result, changed, int(protected.sum()), centered.dx, centered.dy, alpha_geometry_sha256)
