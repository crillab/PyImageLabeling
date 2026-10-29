from PyQt6.QtGui import QPainter, QImage, QPixmap, QColor
from PyQt6.QtCore import Qt, QSize
import numpy as np
from collections import deque

from PyImageLabeling.model.Utils import Utils


class CompactUndoEntry:
    """
    Stores a pixmap for the undo stack, in whichever of three forms is
    cheapest for the moment:

    - pending: a plain copy of the pixmap. Taken in one memcpy on every
      commit, because it is the only form cheap enough to run inside a
      brush stroke.
    - sparse: only the non-transparent pixels, as (y, x, ARGB), 8 B per
      painted pixel. Wins on lightly annotated images.
    - dense: the ARGB32 image, 4 B per pixel. Cheaper AND smaller than the
      sparse form once the image is more than half painted.

    A pending entry is compacted later (see LabelingOverlay.compact_undo),
    when the user is idle, so the expensive full-image scan never sits in
    the middle of a stroke. Without that, the scan made every stroke slower
    as the annotation grew: ~4 ms on a fresh image, ~20 ms once full.
    """

    # sparse costs 8 B/painted px, dense costs 4 B/px: break even at 50 %
    _SPARSE_MAX_DENSITY = 0.5

    def __init__(self, pixmap, compact=True):
        """Store pixmap. With compact=False, keep a cheap copy to compact later."""
        self.sparse = False
        self.y_coords = None
        self.x_coords = None
        self.colors = None
        self._image = None
        self._pending_pixmap = None
        self.width = pixmap.width()
        self.height = pixmap.height()

        if not compact:
            self._pending_pixmap = pixmap.copy()
            return

        self._compact_from(pixmap)

    def _compact_from(self, pixmap):
        image = pixmap.toImage()

        if image.isNull():
            # fallback: create an empty 1x1 transparent image
            image = QImage(1, 1, QImage.Format.Format_ARGB32)
            image.fill(Qt.GlobalColor.transparent)

        image = image.convertToFormat(QImage.Format.Format_ARGB32)

        width = image.width()
        height = image.height()
        self.width = width
        self.height = height

        # Extract pixel data
        ptr = image.bits()
        ptr.setsize(image.sizeInBytes())

        # Convert to numpy for efficient processing
        arr = np.frombuffer(ptr.asarray(), dtype=np.uint8).reshape((height, width, 4))

        # Find non-transparent pixels (alpha > 0)
        alpha_channel = arr[:, :, 3]
        n_painted = int(np.count_nonzero(alpha_channel))

        if n_painted == 0:
            # Empty image
            self._image = image.copy()
            return

        if n_painted <= self._SPARSE_MAX_DENSITY * width * height:
            self.sparse = True
            ys, xs = np.nonzero(alpha_channel > 0)
            # Store only non-transparent pixel positions and colors
            self.y_coords = ys.astype(np.uint16)  # Use uint16 to save memory
            self.x_coords = xs.astype(np.uint16)
            self.colors = arr[ys, xs].astype(np.uint8)  # ARGB values
        else:
            # Dense: cheaper to keep the image than the coordinate list
            self._image = image.copy()

    def is_pending(self):
        return self._pending_pixmap is not None

    def compact(self):
        """Turn a pending entry into its compact form. Safe to call twice."""
        if self._pending_pixmap is not None:
            pixmap = self._pending_pixmap
            self._pending_pixmap = None
            self._compact_from(pixmap)

    def has_painted_pixels(self):
        """True if this entry holds at least one non-transparent pixel."""
        if self._pending_pixmap is not None:
            image = self._pending_pixmap.toImage()
            alpha = image.convertToFormat(
                image.Format.Format_ARGB32)
            ptr = alpha.bits()
            ptr.setsize(alpha.sizeInBytes())
            arr = np.frombuffer(ptr, np.uint8).reshape(
                (alpha.height(), alpha.width(), 4))
            return bool(np.count_nonzero(arr[:, :, 3]))
        if not self.sparse:
            if self._image is None:
                return False
            ptr = self._image.bits()
            ptr.setsize(self._image.sizeInBytes())
            arr = np.frombuffer(ptr, np.uint8).reshape(
                (self.height, self.width, 4))
            return bool(np.count_nonzero(arr[:, :, 3]))
        return self.y_coords is not None and len(self.y_coords) > 0

    def to_pixmap(self):
        """Reconstruct pixmap from its stored representation"""
        if self._pending_pixmap is not None:
            return self._pending_pixmap.copy()

        if not self.sparse:
            if self._image is None:
                pixmap = QPixmap(self.width, self.height)
                pixmap.fill(Qt.GlobalColor.transparent)
                return pixmap
            return QPixmap.fromImage(self._image)

        # Create empty pixmap
        pixmap = QPixmap(self.width, self.height)
        pixmap.fill(Qt.GlobalColor.transparent)

        if self.y_coords is None:
            return pixmap
        
        # Create image to set pixels
        image = pixmap.toImage()
        image = image.convertToFormat(QImage.Format.Format_ARGB32)
        
        # Get pointer to image data
        ptr = image.bits()
        ptr.setsize(image.sizeInBytes())
        arr = np.frombuffer(ptr, dtype=np.uint8).reshape((self.height, self.width, 4))
        
        # Restore non-transparent pixels
        arr[self.y_coords, self.x_coords] = self.colors
        
        return QPixmap.fromImage(image)

