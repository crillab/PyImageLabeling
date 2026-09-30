"""Folder-level mask import: binary / indexed multi-class / RGB masks.

Used when opening a folder whose non-native PNGs look like external
masks (basename = image basename + separator + suffix, e.g.
``img_mask.png`` for ``img.png``).

Unlike the per-label import (LabelSetting, one label at a time), the
folder flow can create MULTIPLE labels at once:
- binary      -> one label for all matched masks,
- indexed     -> one label per foreground value (e.g. 1,2,3 -> class_1..3),
- rgb         -> one label per distinct non-black colour found.

Converted masks are written in the native ``<base>.label.<id>.png``
format plus a ``labels.json``, so the standard loading machinery
takes over afterwards.
"""

import os

import numpy as np
from PIL import Image
from PyQt6.QtGui import QColor

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif")
SEPARATORS = ("_", "-", " ", ".")

PALETTE = [
    QColor(255, 0, 0), QColor(0, 200, 0), QColor(0, 120, 255),
    QColor(255, 200, 0), QColor(0, 220, 220), QColor(255, 0, 255),
    QColor(255, 128, 0), QColor(128, 0, 255), QColor(0, 255, 128),
    QColor(255, 128, 128),
]


def match_image_basename(mask_name, image_bases_longest_first):
    """Return the image basename this mask file belongs to, or None.

    Rule: image basename is a prefix of the mask name (without ext),
    followed by a separator (or exact match).
    """
    for base in image_bases_longest_first:
        if mask_name == base:
            return base
        if mask_name.startswith(base):
            rest = mask_name[len(base):]
            if rest and rest[0] in SEPARATORS:
                return base
    return None


def find_mask_candidates(image_paths, other_files):
    """Split other image files into (mask_candidates, plain_images).

    mask_candidates: [(mask_path, image_path)] matched by basename rule.
    plain_images: files matching no image (loaded as images, as before).

    A file never matches itself: its own basename is excluded, so only a
    STRICT prefix (+ separator) of another image counts.
    """
    base_to_path = {}
    for p in image_paths:
        base = os.path.splitext(os.path.basename(p))[0]
        base_to_path.setdefault(base, p)
    candidates, plains = [], []
    for f in other_files:
        name = os.path.splitext(os.path.basename(f))[0]
        others = sorted((b for b in base_to_path if b != name),
                        key=len, reverse=True)
        hit = match_image_basename(name, others)
        if hit is not None:
            candidates.append((f, base_to_path[hit]))
        else:
            plains.append(f)
    return candidates, plains


# ----------------------------------------------------------------------
# Converters (shared with LabelSetting per-label import)
# ----------------------------------------------------------------------

def normalize_binary_mask(file_path):
    """Any non-zero pixel -> 255. Handles 0/1 masks AND 0/255 masks."""
    arr = np.array(Image.open(file_path).convert("L"))
    return Image.fromarray((arr > 0).astype(np.uint8) * 255, mode="L")


def indexed_to_binary(file_path, index_values):
    """Pixels whose value is in index_values -> white, rest black."""
    arr = np.array(Image.open(file_path).convert("L"))
    mask = np.isin(arr, list(index_values)).astype(np.uint8) * 255
    return Image.fromarray(mask, mode="L")


def rgb_to_binary(file_path, color):
    """Pixels exactly matching (r, g, b) -> white, rest black."""
    arr = np.array(Image.open(file_path).convert("RGB"))
    if isinstance(color, QColor):
        target = np.array([color.red(), color.green(), color.blue()],
                          dtype=np.uint8)
    else:
        target = np.array(list(color)[:3], dtype=np.uint8)
    mask = np.all(arr == target, axis=2).astype(np.uint8) * 255
    return Image.fromarray(mask, mode="L")


def indexed_values_present(file_path):
    """Sorted distinct values of a grayscale mask (bg included)."""
    arr = np.array(Image.open(file_path).convert("L"))
    return sorted(int(v) for v in np.unique(arr).tolist())


def rgb_colors_present(file_path, max_colors=32):
    """Distinct non-black RGB colours of a mask, most frequent first."""
    arr = np.array(Image.open(file_path).convert("RGB")).reshape(-1, 3)
    nonblack = arr[np.any(arr != 0, axis=1)]
    if len(nonblack) == 0:
        return []
    colors, counts = np.unique(nonblack, axis=0, return_counts=True)
    order = np.argsort(-counts)[:max_colors]
    return [tuple(int(c) for c in colors[i]) for i in order]


def palette_color(i):
    return PALETTE[i % len(PALETTE)]
