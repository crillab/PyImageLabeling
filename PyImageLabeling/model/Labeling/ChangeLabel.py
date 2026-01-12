from PyQt6.QtCore import Qt, QRectF
from PyImageLabeling.model.Core import Core
from PyQt6.QtGui import QColor, QPixmap, QImage, QPen, QBrush, QPainter
from PyQt6.QtWidgets import QMessageBox
from PyImageLabeling.model.Utils import Utils
from collections import deque
import numpy as np
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
            for shape in selected_shapes:
                print("Relabeling geometric shape:", shape)
                self._relabel_shape(shape, image_item)
        else:
            self.view.progressBar.reset()
            self._change_label_worker(scene_pos)
            image_item.update_labeling_overlay()

    def _relabel_shape(self, shape, image_item):
        """Move a selected shape to the target label, update color and model_ref."""
        old_label_id = getattr(shape, "label_id", None)
        if old_label_id == self.target_label_id:
            print("Shape already in target label, skipping")
            return

        if old_label_id is not None:
            old_overlay = image_item.labeling_overlays.get(old_label_id)
            if old_overlay and hasattr(old_overlay, "shapes") and shape in old_overlay.shapes:
                old_overlay.shapes.remove(shape)
                print(f"Removed shape from old label: {old_label_id}")

        target_overlay = image_item.labeling_overlays[self.target_label_id]
        if not hasattr(target_overlay, "shapes"):
            target_overlay.shapes = []
        target_overlay.shapes.append(shape)
        print(f"Added shape to target label: {self.target_label_id}")

        pen_width = Utils.load_parameters()["geometric_shape"]["thickness"]
        new_color = target_overlay.label.get_color()
        shape.setPen(QPen(new_color, pen_width))

        try:
            shape.setBrush(QBrush(new_color, Qt.BrushStyle.NoBrush))
        except Exception:
            pass

        shape.label_id = self.target_label_id
        if hasattr(shape, "model_ref") and shape.model_ref is not None:
            shape.model_ref["label"] = self.target_label_id
            print(f"Updated model_ref label to: {self.target_label_id}")

        shape.setSelected(False)
        shape.update()

    def _change_label_worker(self, scene_pos):
        """Optimized flood-fill using numpy arrays for direct pixel access."""
        x0, y0 = int(scene_pos.x()), int(scene_pos.y())
        image_item = self.get_current_image_item()
        width, height = image_item.get_width(), image_item.get_height()
        
        if not (0 <= x0 < width and 0 <= y0 < height):
            return

        source_overlay = self._find_source_overlay(x0, y0)
        if source_overlay is None:
            print("No source overlay found at clicked position")
            return

        source_label_id = source_overlay.label.get_label_id()
        if source_label_id == self.target_label_id:
            print("Source and target labels are the same, skipping")
            return

        target_overlay = image_item.labeling_overlays[self.target_label_id]

        # End any active painters
        if source_overlay.labeling_overlay_painter.isActive():
            source_overlay.labeling_overlay_painter.end()
        if target_overlay.labeling_overlay_painter.isActive():
            target_overlay.labeling_overlay_painter.end()

        # Convert to numpy arrays for fast pixel access
        src_img = source_overlay.labeling_overlay_pixmap.toImage().convertToFormat(QImage.Format.Format_ARGB32)
        tgt_img = target_overlay.labeling_overlay_pixmap.toImage().convertToFormat(QImage.Format.Format_ARGB32)

        # Get raw pixel data as numpy arrays
        src_ptr = src_img.bits()
        tgt_ptr = tgt_img.bits()
        src_ptr.setsize(src_img.sizeInBytes())
        tgt_ptr.setsize(tgt_img.sizeInBytes())
        
        src_array = np.frombuffer(src_ptr, dtype=np.uint8).reshape((height, width, 4)).copy()
        tgt_array = np.frombuffer(tgt_ptr, dtype=np.uint8).reshape((height, width, 4)).copy()

        # Get target color
        target_color = target_overlay.label.get_color()
        target_rgba = np.array([target_color.blue(), target_color.green(), 
                                target_color.red(), 255], dtype=np.uint8)

        # Optimized flood-fill using numpy
        visited = np.zeros((height, width), dtype=bool)
        queue = deque([(y0, x0)])  # Note: numpy uses (row, col) = (y, x)
        n_pixels = 0

        while queue and n_pixels <= self.max_pixels:
            y, x = queue.popleft()
            
            if visited[y, x]:
                continue
            
            # Check if pixel has alpha > 0 in source
            if src_array[y, x, 3] == 0:
                continue
            
            visited[y, x] = True
            
            # Clear source pixel
            src_array[y, x] = [0, 0, 0, 0]
            
            # Set target pixel
            tgt_array[y, x] = target_rgba
            
            n_pixels += 1
            
            # Add neighbors
            for dy, dx in DIRECTIONS:
                ny, nx = y + dy, x + dx
                if 0 <= ny < height and 0 <= nx < width and not visited[ny, nx]:
                    queue.append((ny, nx))

        # Convert numpy arrays back to QImage
        src_img_new = QImage(src_array.data, width, height, src_array.strides[0], 
                             QImage.Format.Format_ARGB32)
        tgt_img_new = QImage(tgt_array.data, width, height, tgt_array.strides[0], 
                             QImage.Format.Format_ARGB32)

        # Update pixmaps
        source_overlay.labeling_overlay_pixmap = QPixmap.fromImage(src_img_new.copy())
        target_overlay.labeling_overlay_pixmap = QPixmap.fromImage(tgt_img_new.copy())

        # Restart painters
        source_overlay.labeling_overlay_painter.begin(source_overlay.labeling_overlay_pixmap)
        target_overlay.labeling_overlay_painter.begin(target_overlay.labeling_overlay_pixmap)
        source_overlay.reset_pen()
        target_overlay.reset_pen()

        # Update the overlays
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