"""Fail-closed brand-integrity gate around the unchanged Warder renderer."""
import numpy as np
from PIL import Image
from scipy import ndimage

class BrandIntegrityError(RuntimeError):
    pass

def classify_and_render_guarded(renderer, source, master, style, *, centering_mask=None):
    """Reject changes anywhere in a mixed-colour connected brand component.

    Neutral pixels and enclosed holes belong to the same protected component.
    A disconnected text component may still use the renderer's frozen policy.
    This gate never repairs or replaces an unsafe output.
    """
    src=np.asarray(source.convert('RGBA'),dtype=np.uint8)
    alpha=src[...,3]
    labels,count=ndimage.label(alpha>0,structure=np.ones((3,3),dtype=np.uint8))
    delta=src[...,:3].max(axis=2).astype(np.int16)-src[...,:3].min(axis=2).astype(np.int16)
    protected=np.zeros(alpha.shape,dtype=bool)
    for i in range(1,count+1):
        component=labels==i
        if np.any(component & (alpha>=renderer.OPAQUE_ALPHA) & (delta>renderer.ACHROMATIC_DELTA)):
            protected |= ndimage.binary_fill_holes(component)
    aligned=renderer.center_rgba_layer(source.convert('RGBA'),geometry_mask=centering_mask)
    if aligned.clipped or not aligned.safe_area or not aligned.centered:
        raise BrandIntegrityError('Original artwork geometry requires review: '+aligned.reason)
    mask_image=Image.fromarray(protected.astype(np.uint8)*255)
    shifted=Image.new('L',source.size);shifted.paste(mask_image,(aligned.dx,aligned.dy))
    mask=np.asarray(shifted)>0
    result=renderer.classify_and_render(source,master,style,centering_mask=centering_mask)
    expected=np.asarray(Image.alpha_composite(master,aligned.image))
    actual=np.asarray(result.image)
    changed=np.any(actual!=expected,axis=2)&mask
    if np.any(changed):
        raise BrandIntegrityError(f'Protected complete brand component changed: {int(changed.sum())} pixels; raw engine status={result.status}')
    return result
