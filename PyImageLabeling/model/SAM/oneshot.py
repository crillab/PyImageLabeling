"""One-shot propagation: 1 reference mask -> prompts for query images.

Uses DINOv2 patch features (semantic correspondence) to find where the
reference object appears in a query image, then builds SAM point/box
prompts from the similarity heatmap. No training involved.

Robustness to scale/zoom/pose changes:
- k part-prototypes (head/body/... instead of one washed-out mean),
- horizontal-flip reference pooling (left/right facing),
- multi-scale query heatmaps (max over scales).

Backbones (lazy download): dinov2-small (~90MB, default) or dinov2-base
(~350MB, stronger) via transformers.
"""

import numpy as np

DINO_MODELS = {
    "small": "facebook/dinov2-small",
    "base": "facebook/dinov2-base",
}
DEFAULT_DINO = "small"
DINO_SIZE = 448  # working resolution (stretch); grid = 32x32
DINO_PATCH = 14
N_PROTOTYPES = 4
QUERY_SCALES = (448, 672)

_dino_processor = None
_dino_model = None
_dino_device = None
_dino_key = None


def _ensure_dinov2(device="cuda", model_key=DEFAULT_DINO):
    global _dino_processor, _dino_model, _dino_device, _dino_key
    import torch
    if model_key not in DINO_MODELS:
        model_key = DEFAULT_DINO
    want = device
    if want == "auto" or want is None:
        want = "cuda" if torch.cuda.is_available() else "cpu"
    if want == "cuda" and not torch.cuda.is_available():
        want = "cpu"
    if _dino_model is not None and _dino_key == model_key:
        if _dino_device != want:
            _dino_model.to(want)  # loud: caller must see device failures
            _dino_device = want
        return _dino_processor, _dino_model, _dino_device
    # switching (or first load): drop the old backbone first
    try:
        del _dino_model
        del _dino_processor
    except Exception:
        pass
    try:
        import gc
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass
    from transformers import Dinov2Model, AutoImageProcessor
    repo = DINO_MODELS[model_key]
    _dino_processor = AutoImageProcessor.from_pretrained(repo)
    _dino_model = Dinov2Model.from_pretrained(repo).to(want).eval()
    _dino_device = want
    _dino_key = model_key
    print(f"[one-shot] DINOv2-{model_key} on {want}")
    return _dino_processor, _dino_model, _dino_device


def release_dinov2():
    """Offload DINOv2 to CPU between runs (frees VRAM, kept for reuse)."""
    global _dino_device
    try:
        if _dino_model is not None and _dino_device == "cuda":
            _dino_model.to("cpu")
            _dino_device = "cpu"
        import gc
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
    except Exception:
        pass


def _dinov2_grid_features(rgb, processor, model, device, size=DINO_SIZE):
    """Patch features [1, D, G, G] (L2-normalized) at working `size`.

    Manual preprocessing (ImageNet mean/std) instead of the
    AutoImageProcessor, whose default 224px resize would trash the grid.
    """
    import torch
    from PIL import Image
    pil_image = Image.fromarray(rgb).resize((size, size), Image.BILINEAR)
    arr = np.asarray(pil_image).astype(np.float32) / 255.0
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
    arr = (arr - mean) / std
    pv = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0).to(device)
    with torch.no_grad():
        out = model(pixel_values=pv)
    tok = out.last_hidden_state[0, 1:]  # drop CLS -> [N, D]
    n, d = tok.shape
    g = int(round(n ** 0.5))
    assert g * g == n, f"non-square patch grid: N={n}"
    grid = tok.reshape(g, g, d).permute(2, 0, 1).unsqueeze(0)  # [1,D,G,G]
    grid = grid / (grid.norm(dim=1, keepdim=True) + 1e-6)
    return grid


def _mask_to_grid(mask, g):
    from PIL import Image
    m = Image.fromarray((mask > 0).astype(np.uint8) * 255).resize(
        (g, g), Image.NEAREST)
    return np.asarray(m) > 127


def _kmeans(x, k, iters=15, seed=0):
    """Lloyd k-means with cosine similarity. x: [N, D] normalized."""
    import torch
    x = x.detach().cpu()
    n = x.shape[0]
    k = max(1, min(k, n))
    gen = torch.Generator()
    gen.manual_seed(seed)
    centers = x[torch.randperm(n, generator=gen)[:k]]
    for _ in range(iters):
        assign = (x @ centers.T).argmax(dim=1)
        new_centers = []
        for j in range(k):
            members = x[assign == j]
            if members.shape[0] == 0:
                members = x[torch.randint(
                    n, (1,), generator=gen)]
            c = members.mean(dim=0)
            new_centers.append(c / (c.norm() + 1e-6))
        centers = torch.stack(new_centers)
    return centers


def reference_prototypes(ref_rgb, ref_mask, device="cuda",
                         model_key=DEFAULT_DINO, k=N_PROTOTYPES,
                         flip=True):
    """Part prototypes + background prototype (all L2-normalized, CPU).

    Pools the mask and its horizontal flip so left/right-facing
    instances match. Returns (fg_protos[list], bg_proto|None, device).
    """
    import torch
    processor, model, dev = _ensure_dinov2(device, model_key)
    grid = _dinov2_grid_features(ref_rgb, processor, model, dev)
    g = grid.shape[-1]
    d = grid.shape[1]
    feats = grid[0].reshape(d, -1).T  # [G*G, D]
    fg_cells = _mask_to_grid(ref_mask, g).reshape(-1)
    pool = [feats[fg_cells]]
    if flip:
        grid_f = _dinov2_grid_features(np.fliplr(ref_rgb), processor,
                                       model, dev)
        feats_f = grid_f[0].reshape(d, -1).T
        fg_f = _mask_to_grid(np.fliplr(ref_mask), g).reshape(-1)
        pool.append(feats_f[fg_f])
    pool = torch.cat(pool, dim=0)
    centers = _kmeans(pool, k)
    bg_cells = ~fg_cells
    if int(bg_cells.sum()) > 0:
        bg = feats[bg_cells].mean(dim=0)
        bg = bg / (bg.norm() + 1e-6)
    else:
        bg = None
    return ([c.cpu() for c in centers],
            bg.cpu() if bg is not None else None, dev)


def _greedy_peaks(heat, k, min_dist):
    """Top-k local peaks with min pixel separation. heat: 2D numpy."""
    pts = []
    work = heat.copy()
    h, w = heat.shape
    yy, gx = np.ogrid[:h, :w]
    for _ in range(k):
        i = int(np.argmax(work))
        y, x = divmod(i, w)
        if work[y, x] <= 0:
            break
        pts.append((x, y, float(work[y, x])))
        work[(yy - y) ** 2 + (gx - x) ** 2 < min_dist ** 2] = -1
    return pts


def propose_prompts(query_rgb, fg_protos, bg_proto=None, device="cuda",
                    model_key=DEFAULT_DINO, scales=QUERY_SCALES,
                    n_pos=3, n_neg=2):
    """Build SAM prompts for a query image (scale-robust).

    fg_protos: list of part prototypes (or a single tensor for compat).
    Similarity = max over prototypes AND over scales.
    Returns dict(points, labels, box, score) in query pixel coordinates,
    or None if nothing confident was found.
    """
    import torch
    import torch.nn.functional as F
    if not isinstance(fg_protos, (list, tuple)):
        fg_protos = [fg_protos]
    processor, model, dev = _ensure_dinov2(device, model_key)
    h, w = query_rgb.shape[:2]
    heats = []
    for size in scales:
        grid = _dinov2_grid_features(query_rgb, processor, model, dev,
                                     size=size)
        flat = grid[0].reshape(grid.shape[1], -1).T  # [G*G, D]
        sims = [flat @ p.to(grid.device).reshape(-1) for p in fg_protos]
        sim = torch.stack(sims, dim=0).max(dim=0)[0]  # max over parts
        g = grid.shape[-1]
        heat_s = F.interpolate(sim.reshape(g, g)[None, None],
                               size=(h, w), mode="bilinear",
                               align_corners=False)[0, 0]
        heats.append(heat_s)
    heat = torch.stack(heats, dim=0).max(dim=0)[0].cpu().numpy()
    peak = float(heat.max())
    min_dist = max(8, min(h, w) // 40)

    pos = _greedy_peaks(np.maximum(heat, 0), n_pos, min_dist)
    if not pos:
        return None
    # negatives: lowest similarity, far from positives
    neg = []
    flat = heat.reshape(-1)
    order = np.argsort(flat)
    taken = [p[:2] for p in pos]
    for i in order:
        y, x = divmod(int(i), w)
        if all((x - tx) ** 2 + (y - ty) ** 2 >= min_dist ** 2
               for tx, ty in taken):
            neg.append((x, y))
            taken.append((x, y))
        if len(neg) >= n_neg:
            break

    # box from confident region
    thr = max(0.5 * peak, peak - 0.15)
    region = heat >= thr
    box = None
    if region.sum() >= max(4, 0.0005 * h * w):
        ys, xs = np.where(region)
        pad = 0.03
        dx, dy = (xs.max() - xs.min()) * pad, (ys.max() - ys.min()) * pad
        box = [max(0, int(xs.min() - dx)), max(0, int(ys.min() - dy)),
               min(w - 1, int(xs.max() + dx)), min(h - 1, int(ys.max() + dy))]

    points = [[x, y] for x, y, _ in pos] + [[x, y] for x, y in neg]
    labels = [1] * len(pos) + [0] * len(neg)
    return {"points": points, "labels": labels, "box": box, "score": peak}
