import os
import re
import hashlib

from PyImageLabeling.logging_setup import get_logger

log = get_logger("masks")

log = get_logger("core")

KEYWORD_SAVE_LABEL = ".label."
PATH_HASH_LEN = 8
DEFAULT_KEEP_LOADED_IMAGES = 8


IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".tif")

_DIGEST = r"\.[0-9a-f]{%d}" % PATH_HASH_LEN


def path_hash(file_path):
    """Short digest of an image's absolute path.

    Development versions after 1.0.14 named masks "<stem>.<digest>.label.
    <id>.png" to keep IMG_001.png of two folders apart. The digest changes
    as soon as the project folder is moved or renamed (or unzipped on
    another machine), and the masks were then no longer found. Masks are
    not named with it any more (one project = one folder: two images of a
    project cannot share a file name); it is only used to read the masks
    those versions wrote.
    """
    norm = os.path.normcase(os.path.abspath(file_path))
    return hashlib.md5(norm.encode("utf-8")).hexdigest()[:PATH_HASH_LEN]


def _name_and_stem(file_path):
    name = os.path.basename(file_path)
    stem = name.rsplit(".", 1)[0] if "." in name else name
    return name, stem


def stem_is_shared(file_path):
    """True when another image of the same folder has the same stem
    (dup.png next to dup.jpg)."""
    name, stem = _name_and_stem(file_path)
    try:
        names = os.listdir(os.path.dirname(file_path) or ".")
    except OSError:
        return False
    return any(
        other != name and KEYWORD_SAVE_LABEL not in other
        and other.lower().endswith(IMAGE_EXTENSIONS)
        and other.rsplit(".", 1)[0] == stem
        for other in names)


def mask_image_base(file_path):
    """Name under which this image's masks are written.

    The image stem ("IMG_001.label.0.png": the format every version reads,
    1.0.14 included), or the full file name when another image of the
    folder has the same stem ("dup.png.label.0.png" next to
    "dup.jpg.label.0.png"). Neither depends on where the folder is.
    """
    name, stem = _name_and_stem(file_path)
    return name if stem_is_shared(file_path) else stem


def mask_file_name(directory, file_path, label_id):
    """Mask file of (image, label) inside a project directory."""
    return os.path.join(
        directory,
        f"{mask_image_base(file_path)}{KEYWORD_SAVE_LABEL}{label_id}.png")


def mask_name_candidates(file_path, label_id):
    """Mask names that may hold (image, label), whatever wrote them:
    (full-name form, digest form of this very path, stem form).

    The stem form is ambiguous when the stem is shared (1.0.14 wrote one
    file for dup.png and dup.jpg): callers use it last for such images.
    """
    name, stem = _name_and_stem(file_path)
    suffix = f"{KEYWORD_SAVE_LABEL}{label_id}.png"
    return (f"{name}{suffix}", f"{stem}.{path_hash(file_path)}{suffix}",
            f"{stem}{suffix}")


def digest_mask_names(names, file_path, label_id):
    """Digest-form masks of (image, label) among `names`, whatever the
    digest: a project saved with digests then moved, renamed or unzipped
    elsewhere carries the digest of its old path."""
    _, stem = _name_and_stem(file_path)
    pattern = re.compile(re.escape(stem) + _DIGEST
                         + re.escape(f"{KEYWORD_SAVE_LABEL}{label_id}.png")
                         + "$")
    return [n for n in names if pattern.match(n)]


def image_base_from_mask_name(mask_name):
    """Stem of the owning image, from a mask file name.

    Load-side indexations compare this against image stems:
    "IMG_001.label.0.png", "IMG_001.png.label.0.png" (shared stem) and
    "IMG_001.a1b2c3d4.label.0.png" (digest form) all give "IMG_001".
    """
    left = mask_name.split(KEYWORD_SAVE_LABEL)[0]
    if left.lower().endswith(IMAGE_EXTENSIONS):
        return left.rsplit(".", 1)[0]
    return re.sub(_DIGEST + "$", "", left)
