import os
import re
import hashlib

from PyImageLabeling.logging_setup import get_logger

log = get_logger("masks")

log = get_logger("core")

KEYWORD_SAVE_LABEL = ".label."
PATH_HASH_LEN = 8
DEFAULT_KEEP_LOADED_IMAGES = 8


def path_hash(file_path):
    """Stable short digest of an image's absolute path.

    Masks used to be keyed by the image *basename* alone, so two images
    named IMG_001.png in two different folders (or IMG_001.png/IMG_001.jpg
    in one folder) silently overwrote each other's annotations at save
    time. The digest disambiguates them without keeping any registry.
    normcase() makes it stable across case-insensitive filesystems.
    """
    norm = os.path.normcase(os.path.abspath(file_path))
    return hashlib.md5(norm.encode("utf-8")).hexdigest()[:PATH_HASH_LEN]


def mask_image_base(file_path):
    """Stem under which this image's masks are written."""
    name = os.path.basename(file_path)
    if "." in name:
        name = name.rsplit(".", 1)[0]
    return f"{name}.{path_hash(file_path)}"


def mask_file_name(directory, file_path, label_id):
    """Mask file of (image, label) inside a project directory."""
    return os.path.join(
        directory,
        f"{mask_image_base(file_path)}{KEYWORD_SAVE_LABEL}{label_id}.png")


def image_base_from_mask_name(mask_name):
    """Stem of the owning image, from a mask file name (legacy or v2).

    Loads-side indexations compare this against image basenames, so the
    optional path digest appended by mask_image_base must be stripped:
    "IMG_001.a1b2c3d4.label.0.png" and "IMG_001.label.0.png" both give
    "IMG_001". A plain stem that happens to end with .abcdef12 loses its
    last section only for the cosmetic "has annotations" tag.
    """
    left = mask_name.split(KEYWORD_SAVE_LABEL)[0]
    return re.sub(r"\.[0-9a-f]{8}$", "", left)

