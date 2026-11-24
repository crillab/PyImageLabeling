"""An image whose file carries an EXIF orientation tag.

The view shows images through Qt, which does not apply the tag: the masks
are painted on the pixels as stored. OpenCV applies it by default, so such
an image was trained on (and predicted) turned against its own masks. Every
OpenCV read of the package now goes through ImageFiles.imread, which reads
the stored pixels like Qt.
"""
import pathlib
import re

import cv2
import numpy as np
import pytest
from PIL import Image
from PyQt6.QtGui import QImage

import PyImageLabeling
from PyImageLabeling.model.ImageFiles import imread
from PyImageLabeling.model.ML import Tiling


@pytest.fixture()
def rotated_jpeg(tmp_path):
    """(path, stored RGB pixels) of a JPEG tagged "rotate 180°" whose two
    halves differ (red left, blue right): turned, they swap."""
    rgb = np.zeros((96, 160, 3), dtype=np.uint8)
    rgb[:, :80] = (230, 20, 20)
    rgb[:, 80:] = (20, 20, 230)
    exif = Image.Exif()
    exif[0x0112] = 3                     # Orientation: rotate 180°
    path = tmp_path / "tagged.jpg"
    Image.fromarray(rgb).save(path, quality=95, exif=exif)
    stored = np.asarray(Image.open(path).convert("RGB"))
    return str(path), stored


def _close(a, b):
    return np.abs(a.astype(int) - b.astype(int)).mean() < 3


def test_opencv_alone_turns_the_image(rotated_jpeg):
    """What went wrong: plain cv2.imread reads it turned."""
    path, stored = rotated_jpeg
    rgb = cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2RGB)
    assert _close(rgb, stored[::-1, ::-1])
    assert not _close(rgb, stored)


def test_imread_reads_the_stored_pixels(rotated_jpeg):
    path, stored = rotated_jpeg
    rgb = cv2.cvtColor(imread(path), cv2.COLOR_BGR2RGB)
    assert _close(rgb, stored)
    grey = imread(path, cv2.IMREAD_GRAYSCALE)
    assert grey[:, :40].mean() != pytest.approx(grey[:, 120:].mean(), abs=5)
    assert _close(grey, cv2.cvtColor(stored, cv2.COLOR_RGB2GRAY))


def test_imread_matches_what_the_view_shows(qapp, rotated_jpeg):
    path, _ = rotated_jpeg
    q = QImage(path).convertToFormat(QImage.Format.Format_RGB888)
    bits = q.constBits()
    bits.setsize(q.sizeInBytes())
    shown = (np.frombuffer(bits, np.uint8)
             .reshape(q.height(), q.bytesPerLine())[:, :q.width() * 3]
             .reshape(q.height(), q.width(), 3))
    assert _close(cv2.cvtColor(imread(path), cv2.COLOR_BGR2RGB), shown)


def test_training_tiles_line_up_with_the_mask(rotated_jpeg):
    """The tile cache (training and validation) keeps the image the way
    its mask was painted."""
    path, stored = rotated_jpeg
    mask = np.zeros(stored.shape[:2], dtype=np.uint8)
    mask[:, :80] = 1                     # painted over the red half
    with Tiling.TileCache() as cache:
        source = cache.add(path, mask, [1])
        image = np.asarray(source.image)
        assert _close(image, stored)
        red = image[np.asarray(source.mask) == 1]
        assert red[:, 0].mean() > 200 and red[:, 2].mean() < 50


def test_no_direct_opencv_read_left():
    """Every OpenCV read goes through ImageFiles.imread."""
    root = pathlib.Path(PyImageLabeling.__file__).parent
    offenders = [str(p.relative_to(root)) for p in root.rglob("*.py")
                 if p.name != "ImageFiles.py"
                 and re.search(r"\bcv2\.imread\(", p.read_text(errors="ignore"))]
    assert offenders == []
