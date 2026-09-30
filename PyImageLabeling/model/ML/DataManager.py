import os
from PyImageLabeling.model.Core import Core, KEYWORD_SAVE_LABEL
import numpy as np

class DataManager(Core):
    """
    Data Manager Tool - inherits from Core
    Handles export to YOLO/COCO formats using existing annotations
    """
    
    def __init__(self):
        super().__init__()
        # path -> True/False, for images that are NOT currently loaded.
        # Seeded from disk, and updated when a loaded ImageItem is released,
        # so that releasing memory does not turn annotated images into
        # "unlabeled" ones.
        self._ml_annotated = {}
        self._ml_disk_annotated = {}
        # path -> (stamp, has_painted_pixels); see _has_painted_pixels
        self._ml_painted_cache = {}

    def ml_note_annotated_state(self, file_path, annotated):
        """Remember whether an image is annotated (used once it is unloaded)."""
        self._ml_annotated[file_path] = bool(annotated)

    def _annotated_basenames_on_disk(self):
        """Basenames of images that have a saved label file in their folder.

        Scanned once per folder: relying only on the in-memory registry
        missed images annotated in a previous session, and stat-ing every
        candidate on every call is too slow for large projects.
        """
        cache = getattr(self, "_ml_disk_annotated", None)
        if cache is None:
            cache = {}
            self._ml_disk_annotated = cache
        bases = {}
        for file_path in self.file_paths:
            folder = os.path.dirname(file_path)
            if folder in bases:
                continue
            found = set()
            try:
                for name in os.listdir(folder):
                    if KEYWORD_SAVE_LABEL in name:
                        found.add(name.split(KEYWORD_SAVE_LABEL)[0])
            except OSError:
                pass
            bases[folder] = found
            cache[folder] = found
        return cache, bases

    def _annotated_from_disk(self, file_path):
        """True if annotations for this image exist on disk or in the loaded jsons."""
        cache, bases = self._annotated_basenames_on_disk()
        folder = os.path.dirname(file_path)
        base = os.path.basename(file_path)
        root = base.rsplit(".", 1)[0] if "." in base else base
        if root in bases.get(folder, ()):
            return True
        try:
            for key in getattr(self, "labeling_overview_file_paths", {}):
                if key.startswith(base + KEYWORD_SAVE_LABEL) or \
                        key.startswith(root + KEYWORD_SAVE_LABEL):
                    return True
        except Exception:
            pass
        for store in ("left_rectangles", "left_ellipses", "left_polygons"):
            entries = getattr(self, store, None)
            if entries and (entries.get(base) or entries.get(root)):
                return True
        return False

    def ml_invalidate_painted_cache(self, path_image=None):
        """Drop the cached paint scan (one image, or all)."""
        if path_image is None:
            self._ml_painted_cache.clear()
        else:
            self._ml_painted_cache.pop(path_image, None)

    def ml_invalidate_caches(self, path_image=None):
        """Drop every derived ML cache (stats counts, paint scan, disk scan)."""
        try:
            self.ml_invalidate_painted_cache(path_image)
        except Exception:
            pass
        try:
            self.controller.ml_invalidate_stats_cache(path_image)
        except Exception:
            pass

    def ml_invalidate_disk_cache(self):
        """Forget the on-disk scan (call after saving/importing new masks)."""
        self._ml_disk_annotated = {}

    def _image_is_annotated(self, image_item):
        """Live annotation check for a LOADED image."""
        return not (
            image_item is None
            or not (
                bool(image_item.image_rectangles)
                or bool(image_item.image_ellipses)
                or bool(image_item.image_polygons)
                or self._has_painted_pixels(image_item)
            )
        )

    def ml_get_unlabeled_images(self):
        """
        Get list of images without any annotations
        Returns list of file paths
        """
        unlabeled = []

        for file_path in self.file_paths:
            image_item = self.image_items.get(file_path)

            if image_item is not None:
                # loaded: ask the image itself, and remember the answer
                annotated = self._image_is_annotated(image_item)
                self._ml_annotated[file_path] = annotated
                if not annotated:
                    unlabeled.append(file_path)
                continue

            # not loaded: an unloaded image is NOT necessarily unlabeled
            known = self._ml_annotated.get(file_path)
            if known is None:
                known = self._annotated_from_disk(file_path)
                self._ml_annotated[file_path] = known
            if not known:
                unlabeled.append(file_path)

        return unlabeled

    def _painted_stamp(self, image_item):
        """Cheap fingerprint of an image's overlay state.

        Changes whenever an overlay is added, repainted or reset, so the
        cached answer is dropped exactly when it goes stale.
        """
        return tuple(
            (label_id, id(overlay.labeling_overlay_pixmap),
             overlay.get_is_edited(), overlay.get_is_undo_none())
            for label_id, overlay in image_item.labeling_overlays.items())

    def _has_painted_pixels(self, image_item, min_pixels=50):
        """True if any labeling overlay holds painted pixels.

        The scan reads the whole overlay alpha channel, so the result is
        cached per image and only recomputed when that image's overlays
        change. ml_get_unlabeled_images() asks this for every loaded image
        on each call (e.g. on every "Suggest next"), which made it the
        most repeated full-image scan in the app.
        """
        stamp = self._painted_stamp(image_item)
        cached = self._ml_painted_cache.get(image_item.path_image)
        if cached is not None and cached[0] == stamp:
            return cached[1]

        painted = self._scan_painted_pixels(image_item, min_pixels)
        self._ml_painted_cache[image_item.path_image] = (stamp, painted)
        return painted

    @staticmethod
    def _scan_painted_pixels(image_item, min_pixels=50):
        try:
            from PyQt6.QtGui import QImage
            import numpy as np
            for overlay in image_item.labeling_overlays.values():
                pix = overlay.labeling_overlay_pixmap
                if pix is None or pix.isNull():
                    continue
                img = pix.toImage().convertToFormat(
                    QImage.Format.Format_ARGB32)
                ptr = img.bits()
                ptr.setsize(img.sizeInBytes())
                arr = np.frombuffer(ptr, dtype=np.uint8).reshape(
                    (img.height(), img.width(), 4))
                if int((arr[:, :, 3] > 0).sum()) >= min_pixels:
                    return True
        except Exception:
            pass
        return False