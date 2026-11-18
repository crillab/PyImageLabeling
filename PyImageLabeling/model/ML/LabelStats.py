"""What the annotations hold, label by label, for the ML settings.

On large images the painted pixels are often a few percent of each image:
the rest is background. These figures show it before a training: how many
images hold each label, its share of their pixels, and what a training on
the chosen labels would see (share of the pixels, tiles holding them).

Each mask is read once: its painted pixel count, its size, and a map of
the BLOCK x BLOCK px blocks holding a painted pixel. The tiles of any size
that is a multiple of BLOCK are counted from that map, without reading the
mask again.

Nothing here depends on Qt or torch.
"""

import os
from dataclasses import dataclass

import numpy as np

BLOCK = 32

# keys of the rows that are not labels, in summarize()'s "share"
BACKGROUND = "background"
IGNORED = "ignored"


@dataclass
class MaskStats:
    pixels: int            # painted pixels
    shape: tuple           # (height, width) of the mask
    blocks: np.ndarray     # (ceil(h / BLOCK), ceil(w / BLOCK)) bool


def painted_stats(painted):
    """MaskStats of a boolean (height, width) array."""
    painted = np.asarray(painted, dtype=bool)
    h, w = painted.shape
    hb, wb = -(-h // BLOCK), -(-w // BLOCK)
    if h % BLOCK or w % BLOCK:
        padded = np.zeros((hb * BLOCK, wb * BLOCK), dtype=bool)
        padded[:h, :w] = painted
    else:
        padded = painted
    blocks = padded.reshape(hb, BLOCK, wb, BLOCK).any(axis=(1, 3))
    return MaskStats(int(np.count_nonzero(painted)), (h, w), blocks)


def file_stats(mask_path, cache, reader=None):
    """MaskStats of a mask file, or None when it cannot be read. `cache`
    (a dict) keeps them by path, file size and date."""
    try:
        st = os.stat(mask_path)
    except OSError:
        return None
    key = (os.path.abspath(mask_path), st.st_mtime_ns, st.st_size)
    hit = cache.get(key)
    if hit is not None:
        return hit
    if reader is None:
        from PyImageLabeling.model.Masks import read_painted_mask
        reader = read_painted_mask
    painted = reader(mask_path)
    if painted is None:
        return None
    stats = painted_stats(painted)
    cache[key] = stats
    return stats


def tiles_holding(blocks, k):
    """(tiles, tiles holding a True block) of a grid of k x k blocks."""
    hb, wb = blocks.shape
    ht, wt = -(-hb // k), -(-wb // k)
    if hb % k or wb % k:
        padded = np.zeros((ht * k, wt * k), dtype=bool)
        padded[:hb, :wb] = blocks
    else:
        padded = blocks
    pooled = padded.reshape(ht, k, wt, k).any(axis=(1, 3))
    return ht * wt, int(np.count_nonzero(pooled))


def summarize(images, chosen=None, ignore_others=False, tile_px=None):
    """Figures of the images considered for a training.

    images: {image path: {label id: MaskStats}} (the labels painted there;
        an image with none can be left out).
    chosen: labels learnt, or None for all of them.
    ignore_others: the pixels of the other labels are left out of the loss
        (else they are background).
    tile_px: side of the tiles, in pixels of the image (tile size / scale),
        or None for whole images.

    Returns {
      "labels": {label id: {"images": n, "density": share of the pixels of
                 the images it is painted on}},
      "training_images": images holding a chosen label,
      "share": {label id | BACKGROUND | IGNORED: share of the pixels of
                the training images},
      "tiles": {label id: share of the tiles holding it} or None,
      "empty_tiles": share of the tiles holding no chosen label, or None,
    }
    The shares ignore overlaps between labels (a pixel painted with two
    labels counts twice); the background is what is left.
    """
    labels = {}
    for per_label in images.values():
        for label_id, st in per_label.items():
            if st is None or not st.pixels:
                continue
            entry = labels.setdefault(label_id, [0, 0, 0])
            entry[0] += 1
            entry[1] += st.pixels
            entry[2] += st.shape[0] * st.shape[1]
    out = {"labels": {lid: {"images": n,
                            "density": pixels / area if area else 0.0}
                      for lid, (n, pixels, area) in labels.items()}}

    def learnt(label_id):
        return chosen is None or label_id in chosen

    k = max(1, int(tile_px) // BLOCK) if tile_px else None
    total = learnt_px = ignored_px = 0
    share = {}
    tiles, tiles_with = 0, {}
    empty = 0
    n_training = 0
    for per_label in images.values():
        painted = {lid: st for lid, st in per_label.items()
                   if st is not None and st.pixels}
        mine = {lid: st for lid, st in painted.items() if learnt(lid)}
        if not mine:
            continue
        n_training += 1
        h, w = next(iter(painted.values())).shape
        total += h * w
        for lid, st in mine.items():
            share[lid] = share.get(lid, 0) + st.pixels
            learnt_px += st.pixels
        if ignore_others:
            ignored_px += sum(st.pixels for lid, st in painted.items()
                              if lid not in mine)
        if k is not None:
            union = None
            n = 0
            for lid, st in mine.items():
                n, held = tiles_holding(st.blocks, k)
                tiles_with[lid] = tiles_with.get(lid, 0) + held
                union = st.blocks if union is None else (
                    union | st.blocks if union.shape == st.blocks.shape
                    else union)
            tiles += n
            empty += n - tiles_holding(union, k)[1]

    out["training_images"] = n_training
    if total:
        out["share"] = {lid: px / total for lid, px in share.items()}
        out["share"][BACKGROUND] = max(0, total - learnt_px - ignored_px) \
            / total
        if ignore_others:
            out["share"][IGNORED] = ignored_px / total
    else:
        out["share"] = {}
    if k is not None and tiles:
        out["tiles"] = {lid: n / tiles for lid, n in tiles_with.items()}
        out["empty_tiles"] = empty / tiles
    else:
        out["tiles"] = None
        out["empty_tiles"] = None
    return out
