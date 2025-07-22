from PyQt6.QtCore import Qt, QRectF
from PyImageLabeling.model.Core import Core
from PyQt6.QtGui import QColor, QPixmap, QBrush, QPainter
from PyQt6.QtWidgets import QProgressDialog, QApplication, QMessageBox
from collections import deque

class MagicPen(Core):
    def __init__(self):
        super().__init__()
        self.overlay_pixmap_item = None  # Single overlay pixmap item
        self.overlay_original_pixmap = None  # Original overlay pixmap
        self.overlay_pixmap = None  # Current overlay pixmap

    def magic_pen(self):
        self.checked_button = self.magic_pen.__name__
        print("magic")

    def start_magic_pen(self, scene_pos):
        """Fill area with points using magic pen"""
        self.view.zoomable_graphics_view.change_cursor("magic")
        self.raw_image = self.view.pixmap.toImage()
        self.fill_shape(scene_pos)

    def fill_shape(self, scene_pos):
        # Create progress dialog
        progress = QProgressDialog("Processing magic pen fill...", "Cancel", 0, 0, self.view)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()

        try:
            new_overlay_pixmap = self._fill_shape_worker(scene_pos)
            self._handle_fill_complete(new_overlay_pixmap, progress)
        except Exception as e:
            self._handle_fill_error(str(e), progress)

    def _fill_shape_worker(self, scene_pos):
        image_x = int(scene_pos.x())
        image_y = int(scene_pos.y())

        width, height = self.raw_image.width(), self.raw_image.height()

        if not (0 <= image_x < width and 0 <= image_y < height):
            return None

        # Get target color
        target_color = QColor(self.raw_image.pixel(image_x, image_y))
        target_hue = target_color.hue()
        target_sat = target_color.saturation()
        target_val = target_color.value()
        tolerance = self.view.magic_pen_tolerance

        # Create a transparent pixmap for the new overlay
        new_overlay_pixmap = QPixmap(width, height)
        new_overlay_pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(new_overlay_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        # Set the brush color for the filled area
        current_point_color = self.labels[self.current_label]["color"]
        painter.setBrush(QBrush(QColor(current_point_color)))
        painter.setPen(Qt.PenStyle.NoPen)

        visited = set()
        directions = [
            (1, 0), (-1, 0), (0, 1), (0, -1),
            (1, 1), (-1, -1), (1, -1), (-1, 1)
        ]

        queue = deque([(image_x, image_y)])
        points_to_fill = []

        try:
            while queue:
                if len(points_to_fill) >= self.view.max_points_limite:
                    print(f"Too many points ({self.view.max_points_limite}). Canceling fill.")
                    return None

                x, y = queue.popleft()
                if (x, y) in visited:
                    continue

                visited.add((x, y))

                if not (0 <= x < width and 0 <= y < height):
                    continue

                # Color verification with tolerance
                current_color = QColor(self.raw_image.pixel(x, y))
                current_hue = current_color.hue()
                current_sat = current_color.saturation()
                current_val = current_color.value()

                if target_hue == -1 or current_hue == -1:
                    if abs(current_val - target_val) > tolerance:
                        continue
                else:
                    hue_diff = min(abs(current_hue - target_hue), 360 - abs(current_hue - target_hue))

                    if (hue_diff > tolerance or
                        abs(current_sat - target_sat) > tolerance or
                        abs(current_val - target_val) > tolerance):
                        continue

                points_to_fill.append((x, y))

                # Add neighbors
                for dx, dy in directions:
                    new_x, new_y = x + dx, y + dy
                    if (new_x, new_y) not in visited:
                        queue.append((new_x, new_y))

        except Exception as e:
            print(f"Error during fill: {e}")
            return None

        # Draw the filled area on the new overlay pixmap
        for x, y in points_to_fill:
            painter.drawEllipse(x, y, 1, 1)  # Draw a small circle for each point

        painter.end()
        return new_overlay_pixmap

    def _handle_fill_complete(self, new_overlay_pixmap, progress):
        """Handle completion of fill operation"""
        if progress:
            progress.close()

        if new_overlay_pixmap is None:
            return

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        try:
            # Merge the new overlay with the existing overlay
            if self.overlay_pixmap is None:
                self.overlay_pixmap = new_overlay_pixmap
            else:
                # Create a painter to merge the new overlay with the existing one
                painter = QPainter(self.overlay_pixmap)
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
                painter.drawPixmap(0, 0, new_overlay_pixmap)
                painter.end()

            # Add or update the overlay in the scene
            self.add_or_update_overlay()

            # Update the view
            self.view.zoomable_graphics_view.update()
            

        except Exception as e:
            print(f"Error during fill completion: {e}")
        finally:
            QApplication.restoreOverrideCursor()

    def _handle_fill_error(self, error, progress):
        """Handle errors during fill operation"""
        if progress:
            progress.close()
        QMessageBox.warning(self.view, "Error", f"Magic pen fill operation failed: {error}")

    def add_or_update_overlay(self):
        """
        Add or update the overlay layer on top of the base image.
        """
        if self.overlay_pixmap is None:
            return False

        # Scale the overlay to match the base image size if needed
        if self.view.pixmap and self.overlay_pixmap.size() != self.view.pixmap.size():
            self.overlay_pixmap = self.overlay_pixmap.scaled(
                self.view.pixmap.size(),
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

        # Create or update the overlay pixmap item
        if self.overlay_pixmap_item is None:
            self.overlay_pixmap_item = self.view.zoomable_graphics_view.scene.addPixmap(self.overlay_pixmap)
            if hasattr(self.view, 'pixmap_item'):
                self.overlay_pixmap_item.setPos(self.view.pixmap_item.pos())
            self.overlay_pixmap_item.setZValue(1)  # Set Z-value to be above the base image
        else:
            self.overlay_pixmap_item.setPixmap(self.overlay_pixmap)

        # Update the scene
        self.view.zoomable_graphics_view.scene.update()

        return True
    
    

