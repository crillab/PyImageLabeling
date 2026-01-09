from PyQt6.QtCore import Qt, QRectF
from PyImageLabeling.model.Core import Core
from PyQt6.QtGui import QColor, QPixmap, QImage, QPen, QBrush
from PyQt6.QtWidgets import QMessageBox
from PyImageLabeling.model.Utils import Utils
from collections import deque
import numpy
from PyImageLabeling.model.Labeling.RectangleItem import RectangleItem
from PyImageLabeling.model.Labeling.EllipseItem import EllipseItem
from PyImageLabeling.model.Labeling.PolygonItem import PolygonItem

DIRECTIONS = ((1, 0), (-1, 0), (0, 1), (0, -1))


class ChangeLabel(Core):
    def __init__(self):
        super().__init__()
        self.target_label_id = None
        self.max_pixels = None

    def change_label(self):
        self.checked_button = self.change_label.__name__
        self.view.zoomable_graphics_view.change_cursor("magic")

        # Load settings on activation
        self._load_settings()

        if self.target_label_id is None:
            QMessageBox.warning(
                None,
                "Change Label",
                "No target label selected.\nPlease configure Change Label settings."
            )
            return

        print("ChangeLabel activated → target:", self.target_label_id)

    def _load_settings(self):
        data = Utils.load_parameters()
        params = data.get("change_label", {})
        self.target_label_id = params.get("target_label_id", None)
        self.max_pixels = params.get("max_pixels", 200000)

    def start_change_label(self, scene_pos):
        """Handle both geometric shapes and pixel-based labeling."""
        if self.target_label_id is None:
            return

        image_item = self.get_current_image_item()
        if image_item is None:
            return

        # Target label may have been deleted
        if self.target_label_id not in image_item.labeling_overlays:
            QMessageBox.warning(
                None,
                "Change Label",
                "Target label no longer exists.\nPlease update Change Label settings."
            )
            return

        # Check for selected geometric shapes first
        shape_classes = (RectangleItem, EllipseItem, PolygonItem)
        selected_shapes = [
            item for item in self.view.zoomable_graphics_view.scene.selectedItems()
            if isinstance(item, shape_classes)
        ]

        if selected_shapes:
            # Process all selected geometric shapes
            for shape in selected_shapes:
                print("Relabeling geometric shape:", shape)
                self._relabel_shape(shape, image_item)
        else:
            # Fall back to pixel-based flood-fill
            self.view.progressBar.reset()
            self._change_label_worker(scene_pos)
            image_item.update_labeling_overlay()

    def _relabel_shape(self, shape, image_item):
        """Move a selected shape to the target label, update color and model_ref."""
        old_label_id = getattr(shape, "label_id", None)
        if old_label_id == self.target_label_id:
            print("Shape already in target label, skipping")
            return  # Already in target label

        # Remove from old overlay if exists
        if old_label_id is not None:
            old_overlay = image_item.labeling_overlays.get(old_label_id)
            if old_overlay and hasattr(old_overlay, "shapes") and shape in old_overlay.shapes:
                old_overlay.shapes.remove(shape)
                print(f"Removed shape from old label: {old_label_id}")

        # Add to target overlay
        target_overlay = image_item.labeling_overlays[self.target_label_id]
        if not hasattr(target_overlay, "shapes"):
            target_overlay.shapes = []
        target_overlay.shapes.append(shape)
        print(f"Added shape to target label: {self.target_label_id}")

        # Get current pen width safely
        pen_width = Utils.load_parameters()["geometric_shape"]["thickness"]

        # Update shape color
        new_color = target_overlay.label.get_color()
        shape.setPen(QPen(new_color, pen_width))

        # Only set brush for shapes that support it
        try:
            shape.setBrush(QBrush(new_color, Qt.BrushStyle.NoBrush))
        except Exception:
            pass

        # Update label_id and model reference
        shape.label_id = self.target_label_id
        if hasattr(shape, "model_ref") and shape.model_ref is not None:
            shape.model_ref["label"] = self.target_label_id
            print(f"Updated model_ref label to: {self.target_label_id}")

        # Deselect the shape after relabeling
        shape.setSelected(False)
        shape.update()

    def _change_label_worker(self, scene_pos):
        """Pixel-based flood-fill labeling for drawn regions."""
        x0, y0 = int(scene_pos.x()), int(scene_pos.y())
        image_item = self.get_current_image_item()

        width, height = image_item.get_width(), image_item.get_height()
        if not (0 <= x0 < width and 0 <= y0 < height):
            return

        # Find source label overlay
        source_overlay = self._find_source_overlay(x0, y0)
        if source_overlay is None:
            print("No source overlay found at clicked position")
            return

        source_label_id = source_overlay.label.get_label_id()
        if source_label_id == self.target_label_id:
            print("Source and target labels are the same, skipping")
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

        # Flood-fill ONLY inside source label
        while queue and n_pixels <= self.max_pixels:
            x, y = queue.popleft()

            if visited[x][y]:
                continue
            visited[x][y] = True

            if src_img.pixelColor(x, y).alpha() == 0:
                continue

            # Remove from source
            src_img.setPixelColor(x, y, QColor(0, 0, 0, 0))

            # Add to target
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

        print(f"ChangeLabel: moved {n_pixels} pixels from label {source_label_id} to {self.target_label_id}")

    def _find_source_overlay(self, x, y):
        """Find which label overlay contains a pixel at the given position."""
        image_item = self.get_current_image_item()

        overlays = list(image_item.labeling_overlays.values())
        overlays.sort(key=lambda o: o.zvalue, reverse=True)

        for overlay in overlays:
            img = overlay.labeling_overlay_pixmap.toImage()
            if img.pixelColor(x, y).alpha() > 0:
                return overlay

        return None