"""SAM automatic mask generation: segment everything, no text needed.

Used as fallback when Grounding-DINO doesn't know the object (e.g.
"flood water", "cells", "mountains"). SAM generates all possible masks,
then CLIP scores them against the description.
"""

import numpy as np

SAM2_AUTO_MODEL_ID = "facebook/sam2.1-hiera-tiny"

_auto_model = None
_auto_processor = None
_auto_device = None


def ensure_auto(device="cuda"):
    global _auto_model, _auto_processor, _auto_device
    if _auto_model is not None:
        return _auto_model, _auto_processor, _auto_device
    import torch
    from transformers import Sam2Model, Sam2Processor
    dev = device
    if dev == "auto" or dev is None:
        dev = "cuda" if torch.cuda.is_available() else "cpu"
    if dev == "cuda" and not torch.cuda.is_available():
        dev = "cpu"
    _auto_processor = Sam2Processor.from_pretrained(SAM2_AUTO_MODEL_ID)
    _auto_model = Sam2Model.from_pretrained(SAM2_AUTO_MODEL_ID).to(dev).eval()
    _auto_device = dev
    print(f"[auto-mask] SAM2 on {dev}")
    return _auto_model, _auto_processor, _auto_device


def generate_masks(rgb, device="cuda", max_masks=32):
    """Generate all possible masks from an image (no text prompt).

    Returns bool [M, H, W] array of masks, or None on failure.
    """
    import torch
    from PIL import Image
    h, w = rgb.shape[:2]
    model, processor, dev = ensure_auto(device)
    inputs = processor(images=Image.fromarray(rgb), return_tensors="pt")
    inputs = {k: (v.to(dev) if hasattr(v, "to") else v)
              for k, v in inputs.items()}
    with torch.no_grad():
        outputs = model(**inputs)
    # SAM2 automatic mode: generate masks from grid points
    # Use the processor's built-in mask generation
    try:
        # Try the automatic mask generation API
        masks = processor.image_processor.post_process_masks(
            outputs.pred_masks,
            inputs["original_sizes"],
            inputs["reshaped_input_sizes"],
        )[0]
        # masks: [num_masks, H, W] -> bool
        bool_masks = (masks.sigmoid().cpu().numpy() >= 0.5)
        # filter: remove tiny and huge masks
        total = h * w
        good = []
        for m in bool_masks:
            area = m.sum()
            if 0.0005 * total < area < 0.9 * total:
                good.append(m)
        if len(good) == 0:
            return None
        return np.stack(good[:max_masks])
    except Exception as e:
        print(f"[auto-mask] generation failed: {e}")
        return None
