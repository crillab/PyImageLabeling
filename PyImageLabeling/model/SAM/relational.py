"""Relational text-to-mask scoring: SAM finds all instances, CLIP picks
the one matching the full description (e.g. "dog of the background").

Strategy:
1. SAM generates multiple mask candidates for the base object
2. For each candidate, create a masked image (object visible, rest dimmed)
3. CLIP scores each masked image against the full description
4. The candidate with the highest CLIP score wins

This handles relational descriptors (background, left, bigger, etc.)
that CLIPSeg alone cannot resolve.
"""

import numpy as np

CLIP_MODEL_ID = "openai/clip-vit-base-patch32"

_clip_model = None
_clip_processor = None
_clip_device = None


def ensure_clip(device="cuda"):
    global _clip_model, _clip_processor, _clip_device
    if _clip_model is not None:
        return _clip_model, _clip_processor, _clip_device
    import torch
    from transformers import CLIPModel, CLIPProcessor
    dev = device
    if dev == "auto" or dev is None:
        dev = "cuda" if torch.cuda.is_available() else "cpu"
    if dev == "cuda" and not torch.cuda.is_available():
        dev = "cpu"
    _clip_processor = CLIPProcessor.from_pretrained(CLIP_MODEL_ID)
    _clip_model = CLIPModel.from_pretrained(CLIP_MODEL_ID).to(dev).eval()
    _clip_device = dev
    print(f"[relational] CLIP on {dev}")
    return _clip_model, _clip_processor, _clip_device


def score_candidates(rgb, masks, description, device="cuda",
                     dim_alpha=0.15):
    """Score each mask candidate against the full description.

    Uses ensemble of text templates for robust scoring.

    Args:
        rgb: HxWx3 uint8 image
        masks: bool [M, H, W] candidate masks from SAM
        description: full text description (e.g. "dog of the background")
        device: compute device
        dim_alpha: how much to dim non-object pixels (0=black, 1=original)

    Returns:
        scores: list of float, one per candidate (higher = better match)
    """
    import torch
    from PIL import Image
    if not masks:
        return []
    model, processor, dev = ensure_clip(device)
    templates = _text_templates(description)
    # batch all (mask, template) pairs in ONE forward
    # (was: one forward per mask)
    pair_imgs, pair_txts = [], []
    for mask in masks:
        masked = rgb.astype(np.float32) * (
            dim_alpha + (1 - dim_alpha) * mask[:, :, None])
        masked_img = Image.fromarray(masked.astype(np.uint8))
        for t in templates:
            pair_imgs.append(masked_img)
            pair_txts.append(t)
    inputs = processor(text=pair_txts, images=pair_imgs,
                       return_tensors="pt", padding=True)
    inputs = {k: (v.to(dev) if hasattr(v, "to") else v)
              for k, v in inputs.items()}
    from PyImageLabeling.model.SAM.precision import cuda_autocast
    with torch.no_grad(), cuda_autocast(dev):
        out = model(**inputs)
        img_emb = out.image_embeds
        txt_emb = out.text_embeds
        img_emb = img_emb / (img_emb.norm(dim=-1, keepdim=True) + 1e-6)
        txt_emb = txt_emb / (txt_emb.norm(dim=-1, keepdim=True) + 1e-6)
        pair_sim = (img_emb * txt_emb).sum(dim=-1)  # [M*T] paired sims
    sim_matrix = pair_sim.reshape(len(masks), len(templates))
    scores = sim_matrix.max(dim=1)[0].tolist()
    if not isinstance(scores, list):
        scores = [float(scores)]
    return [float(s) for s in scores]


def _text_templates(description):
    """Generate text templates for ensemble scoring."""
    desc = description.lower().strip()
    templates = [desc]
    if not desc.startswith("a "):
        templates.append("a " + desc)
    if not desc.startswith("the "):
        templates.append("the " + desc)
    relational = {"background", "foreground", "behind", "front",
                  "left", "right", "top", "bottom", "center",
                  "bigger", "smaller", "closest", "farthest",
                  "nearest", "furthest", "first", "last", "of", "the", "a"}
    words = [w for w in desc.split() if w not in relational]
    if len(words) >= 1 and " ".join(words) != desc:
        templates.append(" ".join(words))
    return list(dict.fromkeys(templates))


def pick_best_candidate(rgb, masks, description, device="cuda"):
    """Return (best_mask, best_score, all_scores) for relational matching.

    Uses CLIP scoring; falls back to position/size heuristics when CLIP
    scores are too close to distinguish (e.g. synthetic or ambiguous
    images).
    """
    if len(masks) == 0:
        return None, 0.0, []
    if len(masks) == 1:
        return masks[0], 1.0, [1.0]
    # filter out degenerate candidates (>50% of image = probably background)
    h, w = rgb.shape[:2]
    total = h * w
    good_masks = [m for m in masks if 0 < m.sum() < 0.5 * total]
    if len(good_masks) == 0:
        good_masks = masks  # fallback: use all
    scores = score_candidates(rgb, good_masks, description, device=device)
    best_idx = int(np.argmax(scores))
    # if CLIP can't distinguish (scores within 0.01), use heuristics
    if max(scores) - min(scores) < 0.01:
        heuristic_idx = _heuristic_pick(rgb, good_masks, description)
        if heuristic_idx != best_idx:
            best_idx = heuristic_idx
            scores[best_idx] = 1.0  # mark as heuristic pick
    return good_masks[best_idx], scores[best_idx], scores


def _heuristic_pick(rgb, masks, description):
    """Position/size heuristics for ambiguous CLIP scores.

    background/behind -> smaller + higher in image
    foreground/front  -> bigger + lower in image
    left/right/top/bottom -> position-based
    """
    h, w = rgb.shape[:2]
    desc = description.lower()
    best_idx, best_score = 0, -1e9
    for i, mask in enumerate(masks):
        ys, xs = np.where(mask)
        if len(ys) == 0:
            continue
        cy, cx = ys.mean(), xs.mean()
        area = mask.sum()
        # normalize: cy=0 is top, cy=1 is bottom
        ny, nx = cy / h, cx / w
        score = 0.0
        if any(w in desc for w in ("background", "behind", "back")):
            score = (1 - ny) * 2 + (1 - area / (h * w))  # high + small
        elif any(w in desc for w in ("foreground", "front")):
            score = ny * 2 + area / (h * w)  # low + big
        elif "left" in desc:
            score = 1 - nx
        elif "right" in desc:
            score = nx
        elif "top" in desc or "upper" in desc:
            score = 1 - ny
        elif "bottom" in desc or "lower" in desc:
            score = ny
        elif "bigger" in desc or "biggest" in desc or "largest" in desc:
            score = area / (h * w)
        elif "smaller" in desc or "smallest" in desc:
            score = 1 - area / (h * w)
        if score > best_score:
            best_score = score
            best_idx = i
    return best_idx
