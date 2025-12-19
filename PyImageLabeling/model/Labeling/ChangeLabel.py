from PyQt6.QtCore import Qt, QRectF
from PyImageLabeling.model.Core import Core
from PyQt6.QtGui import QColor, QPixmap, QImage
from PyQt6.QtWidgets import QMessageBox
from PyImageLabeling.model.Utils import Utils
from collections import deque
import numpy

DIRECTIONS = ((1, 0), (-1, 0), (0, 1), (0, -1))


class ChangeLabel(Core):
    def __init__(self):
        super().__init__()
        self.target_label_id = None
        self.max_pixels = None  # NEW

    # -------------------------------------------------
    # Tool activation
    # -------------------------------------------------
    def change_label(self):
        self.checked_button = self.change_label.__name__
        self.view.zoomable_graphics_view.change_cursor("magic")

        # 🔹 Load settings on activation (NEW)
        self._load_settings()

        if self.target_label_id is None:
            QMessageBox.warning(
                None,
                "Change Label",
                "No target label selected.\nPlease configure Change Label settings."
            )
            return

        print("ChangeLabel activated → target:", self.target_label_id)

    # -------------------------------------------------
    # Settings
    # -------------------------------------------------
    def _load_settings(self):
        data = Utils.load_parameters()

        params = data.get("change_label", {})
        self.target_label_id = params.get("target_label_id", None)
        self.max_pixels = params.get("max_pixels", 200000)

    # -------------------------------------------------
    # Entry point
    # -------------------------------------------------
    def start_change_label(self, scene_pos):
        if self.target_label_id is None:
            return

        image_item = self.get_current_image_item()

        # 🔹 Target label may have been deleted (NEW)
        if self.target_label_id not in image_item.labeling_overlays:
            QMessageBox.warning(
                None,
                "Change Label",
                "Target label no longer exists.\nPlease update Change Label settings."
            )
            return

        self.view.progressBar.reset()
        self._change_label_worker(scene_pos)
        image_item.update_labeling_overlay()

    # -------------------------------------------------
    # Core logic
    # -------------------------------------------------
    def _change_label_worker(self, scene_pos):
        x0, y0 = int(scene_pos.x()), int(scene_pos.y())
        image_item = self.get_current_image_item()

        width, height = image_item.get_width(), image_item.get_height()
        if not (0 <= x0 < width and 0 <= y0 < height):
            return

        # 1️⃣ find source label overlay
        source_overlay = self._find_source_overlay(x0, y0)
        if source_overlay is None:
            return

        source_label_id = source_overlay.label.get_label_id()
        if source_label_id == self.target_label_id:
            return

        target_overlay = image_item.labeling_overlays[self.target_label_id]

        src_img = source_overlay.labeling_overlay_pixmap.toImage().convertToFormat(
            QImage.Format.Format_ARGB32
        )
        tgt_img = target_overlay.labeling_overlay_pixmap.toImage().convertToFormat(
            QImage.Format.Format_ARGB32
        )

        visited = numpy.full((width, height), False)

        # Undo snapshots
        source_overlay.previous_labeling_overlay_pixmap = (
            source_overlay.labeling_overlay_pixmap.copy()
        )
        target_overlay.previous_labeling_overlay_pixmap = (
            target_overlay.labeling_overlay_pixmap.copy()
        )

        queue = deque()
        queue.append((x0, y0))
        n_pixels = 0

        # 2️⃣ flood-fill ONLY inside source label
        while queue and n_pixels <= self.max_pixels:
            x, y = queue.popleft()

            if visited[x][y]:
                continue
            visited[x][y] = True

            if src_img.pixelColor(x, y).alpha() == 0:
                continue

            # remove from source
            src_img.setPixelColor(x, y, QColor(0, 0, 0, 0))

            # add to target
            tgt_img.setPixelColor(x, y, target_overlay.label.get_color())

            n_pixels += 1

            for dx, dy in DIRECTIONS:
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < height:
                    queue.append((nx, ny))

        source_overlay.labeling_overlay_pixmap = QPixmap.fromImage(src_img)
        target_overlay.labeling_overlay_pixmap = QPixmap.fromImage(tgt_img)

        source_overlay.update()
        target_overlay.update()

        print("ChangeLabel: moved pixels:", n_pixels)

    # -------------------------------------------------
    # Helpers
    # -------------------------------------------------
    def _find_source_overlay(self, x, y):
        image_item = self.get_current_image_item()

        overlays = list(image_item.labeling_overlays.values())
        overlays.sort(key=lambda o: o.zvalue, reverse=True)

        for overlay in overlays:
            img = overlay.labeling_overlay_pixmap.toImage()
            if img.pixelColor(x, y).alpha() > 0:
                return overlay

        return None
