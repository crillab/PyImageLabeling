"""Tiles, for segmentation models on large images.

A segmentation model used to see the whole image resized to its input size
(416 px by default): a slide of 8192 px lost 95% of its resolution, and its
aspect ratio. With tiles, the network works on crops of `tile_size` px of
the image (optionally downscaled first by `scale`), at training time and at
prediction time; the predictions of the tiles are put back together.

Training samples tiles at random, half of them on an annotated pixel (so
that the classes covering a few percent of an image are seen), half
anywhere (so that the network learns the background too). Prediction
slides a window over the image; neighbouring tiles overlap by `overlap` px
and each pixel is taken from the tile where it is the farthest from the
edge, where the network sees the least around it.

Nothing here depends on Qt or torch.
"""

import os
import shutil
import tempfile

import cv2
import numpy as np

# Class value of the pixels a tile adds around an image smaller than the
# tile: the loss ignores them (classes are numbered from 0).
IGNORE_INDEX = 255

# Tile sizes are multiples of this: the backbones divide the input by 32
# and the segmentation head multiplies it back.
TILE_MULTIPLE = 32
MIN_TILE_SIZE = 64

DEFAULT_TILE_SIZE = 512
DEFAULT_OVERLAP = 128
SCALES = (1.0, 0.5, 0.25)

# Area of each image seen per epoch (on average), whatever the tile size:
# more, smaller tiles or fewer, larger ones, for about the same time.
EPOCH_COVERAGE = 1 / 3
MIN_TILES_PER_IMAGE = 4

# Share of the training tiles centred on an annotated pixel.
LABELLED_SHARE = 0.5


def normalize_tile_size(size):
    """Nearest multiple of TILE_MULTIPLE, at least MIN_TILE_SIZE."""
    try:
        size = int(size)
    except (TypeError, ValueError):
        size = DEFAULT_TILE_SIZE
    size = int(round(size / TILE_MULTIPLE)) * TILE_MULTIPLE
    return max(MIN_TILE_SIZE, size)


def normalize_overlap(overlap, tile_size):
    """Overlap between 0 and half the tile (the step stays >= tile/2)."""
    try:
        overlap = int(overlap)
    except (TypeError, ValueError):
        overlap = DEFAULT_OVERLAP
    return max(0, min(overlap, tile_size // 2))


def normalize_scale(scale):
    """One of SCALES (the closest)."""
    try:
        scale = float(scale)
    except (TypeError, ValueError):
        return 1.0
    return min(SCALES, key=lambda s: abs(s - scale))


def scaled_size(height, width, scale):
    """(height, width) of an image downscaled by `scale`."""
    if scale == 1.0:
        return height, width
    return max(1, int(round(height * scale))), max(1, int(round(width * scale)))


def rescale(array, scale, nearest=False):
    """Downscale an image (area interpolation) or a class mask (nearest)."""
    if scale == 1.0:
        return array
    h, w = scaled_size(array.shape[0], array.shape[1], scale)
    return cv2.resize(array, (w, h), interpolation=cv2.INTER_NEAREST
                      if nearest else cv2.INTER_AREA)


# ----------------------------------------------------------------------
# Sliding window
# ----------------------------------------------------------------------

def tile_starts(length, tile, overlap):
    """Offsets of the tiles along one axis: one every (tile - overlap)
    pixels, the last one flush with the end of the axis."""
    if length <= tile:
        return [0]
    starts = list(range(0, length - tile, tile - overlap))
    starts.append(length - tile)
    return starts


def keep_ranges(starts, length, tile):
    """Part of the axis each tile predicts: up to the middle of its overlap
    with the next tile, where a pixel is as far from both tile edges."""
    bounds = [0]
    for a, b in zip(starts, starts[1:]):
        bounds.append((b + a + tile) // 2)   # middle of [b, a + tile)
    bounds.append(length)
    return list(zip(bounds[:-1], bounds[1:]))


def tile_grid(height, width, tile, overlap):
    """Tiles covering an image: [(y0, x0, (ky0, ky1), (kx0, kx1))].

    (y0, x0) is the top-left corner of the tile, ky / kx the rows and
    columns of the image it predicts. Those parts cover the image exactly
    once.
    """
    ys = tile_starts(height, tile, overlap)
    xs = tile_starts(width, tile, overlap)
    yk = keep_ranges(ys, height, tile)
    xk = keep_ranges(xs, width, tile)
    return [(y0, x0, ky, kx)
            for y0, ky in zip(ys, yk) for x0, kx in zip(xs, xk)]


def crop(array, y0, x0, tile, fill=0):
    """array[y0:y0+tile, x0:x0+tile], completed with `fill` up to
    tile x tile when the image is smaller than the tile."""
    part = array[y0:y0 + tile, x0:x0 + tile]
    if part.shape[0] == tile and part.shape[1] == tile:
        return np.ascontiguousarray(part)
    out = np.full((tile, tile) + array.shape[2:], fill, dtype=array.dtype)
    out[:part.shape[0], :part.shape[1]] = part
    return out


def evenly_spaced(items, count):
    """At most `count` items, spread over the list."""
    if len(items) <= count:
        return list(items)
    picks = np.unique(np.linspace(0, len(items) - 1, count).round().astype(int))
    return [items[i] for i in picks]


# ----------------------------------------------------------------------
# Training tiles
# ----------------------------------------------------------------------

def tiles_per_image(height, width, tile, coverage=EPOCH_COVERAGE,
                    minimum=MIN_TILES_PER_IMAGE):
    """Tiles drawn from an image per epoch: `coverage` of its area."""
    return max(minimum, int(round(coverage * height * width / (tile * tile))))


def class_points(mask, classes, step=8, max_points=50000, rng=None):
    """{class: (ys, xs)}: pixels of each class where a tile can be centred.

    Read on a grid of `step` px (plus every pixel for a class too small to
    be on the grid), at most `max_points` per class.
    """
    rng = rng if rng is not None else np.random.default_rng()
    sub = mask[::step, ::step]
    counts = np.bincount(mask.ravel(), minlength=256)
    points = {}
    for c in classes:
        c = int(c)
        if c < 0 or c >= len(counts) or counts[c] == 0:
            continue
        ys, xs = np.nonzero(sub == c)
        if len(ys):
            ys, xs = ys * step, xs * step
        else:
            ys, xs = np.nonzero(mask == c)
        if len(ys) > max_points:
            pick = rng.choice(len(ys), max_points, replace=False)
            ys, xs = ys[pick], xs[pick]
        points[c] = (ys.astype(np.int32), xs.astype(np.int32))
    return points


def sample_origin(height, width, tile, rng, point=None):
    """Top-left corner of a random tile; with `point`, a tile having that
    pixel in its central half."""
    max_y, max_x = max(0, height - tile), max(0, width - tile)
    if point is None:
        return int(rng.integers(0, max_y + 1)), int(rng.integers(0, max_x + 1))
    cy, cx = point
    y0 = cy - int(rng.integers(tile // 4, 3 * tile // 4 + 1))
    x0 = cx - int(rng.integers(tile // 4, 3 * tile // 4 + 1))
    return min(max(0, y0), max_y), min(max(0, x0), max_x)


class TileSource:
    """One image of a training run: pixels and class mask (memory-mapped
    arrays at the working scale) and where its annotated pixels are."""

    def __init__(self, path, image, mask, points):
        self.path = path
        self.image = image
        self.mask = mask
        self.points = points

    @property
    def shape(self):
        return self.mask.shape

    def sample(self, tile, rng, labelled_share=LABELLED_SHARE):
        """(image tile, mask tile) drawn at random (see module doc)."""
        h, w = self.mask.shape
        point = None
        if self.points and rng.random() < labelled_share:
            classes = list(self.points)
            ys, xs = self.points[classes[int(rng.integers(len(classes)))]]
            i = int(rng.integers(len(ys)))
            point = (int(ys[i]), int(xs[i]))
        y0, x0 = sample_origin(h, w, tile, rng, point)
        return (crop(self.image, y0, x0, tile, 0),
                crop(self.mask, y0, x0, tile, IGNORE_INDEX))


class TileCache:
    """Images and class masks of a training run, decoded once and kept in
    .npy files read on demand (memory-mapped): drawing a tile takes no
    JPEG decode, and a few GB of slides do not stay in RAM.

    The files go in a temporary folder removed by close().
    """

    def __init__(self, scale=1.0, directory=None):
        self.scale = scale
        self.directory = tempfile.mkdtemp(prefix="pyimagelabeling-tiles-",
                                          dir=directory)
        self.sources = []

    def add(self, image_path, class_mask, point_classes):
        """Decode an image and store it with its class mask (same size as
        the image, class ids). Returns the TileSource, or None when the
        image cannot be read."""
        bgr = cv2.imread(image_path, cv2.IMREAD_COLOR)
        if bgr is None:
            return None
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        del bgr
        h, w = rgb.shape[:2]
        if class_mask.shape != (h, w):
            class_mask = cv2.resize(class_mask, (w, h),
                                    interpolation=cv2.INTER_NEAREST)
        rgb = rescale(rgb, self.scale)
        class_mask = np.ascontiguousarray(
            rescale(class_mask, self.scale, nearest=True), dtype=np.uint8)

        n = len(self.sources)
        image_file = os.path.join(self.directory, f"{n}.image.npy")
        mask_file = os.path.join(self.directory, f"{n}.mask.npy")
        np.save(image_file, rgb)
        np.save(mask_file, class_mask)
        points = class_points(class_mask, point_classes)
        del rgb, class_mask
        source = TileSource(image_path,
                            np.load(image_file, mmap_mode="r"),
                            np.load(mask_file, mmap_mode="r"),
                            points)
        self.sources.append(source)
        return source

    def close(self):
        for source in self.sources:
            source.image = source.mask = None   # release the mappings
        self.sources = []
        shutil.rmtree(self.directory, ignore_errors=True)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
