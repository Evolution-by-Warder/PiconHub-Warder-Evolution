"""V2: preserve a coloured logo as one whole, including disconnected lettering."""
import numpy as np
from PIL import Image

POLICY_VERSION = 'WHOLE_COLOURED_LOGO_V2'

class BrandIntegrityError(RuntimeError):
    pass

def is_coloured_logo(source):
    """Any non-neutral visible pixel locks the complete artwork.

    Ambiguous coloured AA/noise is conservatively locked too. This does not
    change the frozen renderer's contrast thresholds or create a recolour mask.
    """
    src=np.asarray(source.convert('RGBA'),dtype=np.uint8)
    rgb=src[...,:3]
    return bool(np.any((src[...,3]>0)&((rgb[...,0]!=rgb[...,1])|(rgb[...,1]!=rgb[...,2]))))

def classify_and_render_guarded(renderer, source, master, style, *, centering_mask=None, original_source=None):
    """Reject any colour, lettering, alpha, panel or edge change in a coloured logo.

    Spatial separation is NOT permission: disconnected neutral text belonging
    to a coloured logo is locked as well. Any exception requires an independently
    approved exact output SHA256; this function has no automatic exceptions.
    """
    aligned=renderer.center_rgba_layer(source.convert('RGBA'),geometry_mask=centering_mask)
    if aligned.clipped or not aligned.safe_area or not aligned.centered:
        raise BrandIntegrityError('Original artwork geometry requires review: '+aligned.reason)
    result=renderer.classify_and_render(source,master,style,centering_mask=centering_mask)
    if is_coloured_logo(source) or (original_source is not None and is_coloured_logo(original_source)):
        expected=np.asarray(Image.alpha_composite(master,aligned.image))
        actual=np.asarray(result.image)
        changed=np.any(actual!=expected,axis=2)
        if np.any(changed):
            raise BrandIntegrityError(f'WHOLE_COLOURED_LOGO_CHANGED: {int(changed.sum())} pixels; neutral text, disconnected letters, panels, alpha and AA are protected; raw engine status={result.status}')
    return result
