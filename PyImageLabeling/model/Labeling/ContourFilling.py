from PyQt6.QtWidgets import QMessageBox, QProgressDialog
from PyQt6.QtCore import Qt, QPointF, QPoint
from PyQt6.QtGui import QPixmap, QImage, QColor
from PyImageLabeling.model.Core import Core
import numpy as np
import cv2
import traceback

class ContourFilling(Core):
    def __init__(self):
        super().__init__()
        self.contour_layer_applied = False
        self.contours = []
        self.point_color = QColor(Qt.GlobalColor.red)  # Default point color
        self.point_label = "Contour"  # Default point label

    def contour_filling(self):
        self.checked_button = self.contour_filling.__name__

    def start_contour_filling(self):
        self.view.zoomable_graphics_view.change_cursor("filling")
        self.apply_contour()

    def apply_contour(self):
        """Detects contours from the base image and applies the contour layer with improved parameters."""
        if not hasattr(self, 'base_pixmap') or self.base_pixmap is None:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Error")
            msg_box.setText("No image loaded.")
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #000000;
                    color: white;
                    font-size: 14px;
                    border: 1px solid #444444;
                }
                QLabel {
                    color: white;
                    background-color: #000000;
                }
                QPushButton {
                    background-color: #000000;
                    color: white;
                    border: 1px solid #555555;
                    border-radius: 5px;
                    padding: 5px 10px;
                }
                QPushButton:hover {
                    background-color: #222222;
                }
            """)
            msg_box.exec()
            return

        # Get the pixmap data
        image = self.view.pixmap.toImage()
        width, height = image.width(), image.height()

        # Convert QImage to NumPy array
        buffer = image.constBits()
        buffer.setsize(height * width * 4)  # 4 channels (RGBA)
        img_array = np.frombuffer(buffer, dtype=np.uint8).reshape((height, width, 4))

        # Convert to grayscale (use OpenCV)
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGBA2GRAY)

        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Apply Canny edge detection with adjusted parameters
        edges = cv2.Canny(blurred, 50, 150)  # Lower thresholds for more sensitive detection

        # Apply slight dilation to connect nearby edges
        kernel = np.ones((2, 2), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=1)

        # Find contours with hierarchy to better handle nested shapes
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_TC89_L1)

        # Filter out very small contours that might be noise
        min_contour_area = 10  # Adjust based on your needs
        contours = [cnt for cnt in contours if cv2.contourArea(cnt) > min_contour_area]

        # Save contours in image_label for later use
        self.contours = contours

        # Create a transparent layer to visualize the contours (Blue lines)
        contour_layer = np.zeros((height, width, 4), dtype=np.uint8)
        cv2.drawContours(contour_layer, contours, -1, (0, 0, 255, 255), 1)

        # Convert NumPy array to QImage
        contour_qimage = QImage(contour_layer.data, width, height, width * 4, QImage.Format.Format_RGBA8888)

        # Set the overlay in the image viewer
        overlay_pixmap = QPixmap.fromImage(contour_qimage)
        self.add_overlay(overlay_pixmap)

        # Mark that the contour layer is applied
        self.contour_layer_applied = True

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Contour")
        msg_box.setText("Contour layer applied successfully.")
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #000000;
                color: white;
                font-size: 14px;
                border: 1px solid #444444;
            }
            QLabel {
                color: white;
                background-color: #000000;
            }
            QPushButton {
                background-color: #000000;
                color: white;
                border: 1px solid #555555;
                border-radius: 5px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #222222;
            }
        """)
        msg_box.exec()

    def fill_contour(self):
        """Fill the contour clicked by the user."""
        if not hasattr(self, "contour_layer_applied") or not self.contour_layer_applied:
            QMessageBox.warning(self, "Error", "Contour layer is not applied.")
            return

        if not hasattr(self, 'base_pixmap') or self.base_pixmap is None:
            QMessageBox.warning(self, "Error", "No image loaded.")
            return

        if not hasattr(self, "last_mouse_pos") or not self.last_mouse_pos:
            QMessageBox.warning(self, "Error", "No position to fill. Click on an area first.")
            return

        # Create progress dialog
        progress = QProgressDialog("Processing...", "Cancel", 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()

        try:
            filled_points = self._fill_contour_worker(self.last_mouse_pos)
            self._handle_fill_contour_complete(filled_points, progress)
        except Exception as e:
            self._handle_fill_contour_error(str(e), progress)

    def _fill_contour_worker(self, pos):
        """Worker function to perform the contour fill with improved gap tolerance."""
        try:
            if isinstance(pos, QPointF):
                scene_pos = QPoint(int(pos.x()), int(pos.y()))
            else:
                scene_pos = pos

            scene_pos = self.mapToScene(scene_pos)

            item_pos = QPointF(0, 0)
            if hasattr(self, 'pixmap_item') and self.pixmap_item:
                item_pos = self.pixmap_item.pos()

            image_x = int(scene_pos.x() - item_pos.x())
            image_y = int(scene_pos.y() - item_pos.y())

            if not hasattr(self, 'base_pixmap') or self.base_pixmap is None:
                raise ValueError("No base pixmap available")

            width = self.base_pixmap.width()
            height = self.base_pixmap.height()

            if not (0 <= image_x < width and 0 <= image_y < height):
                raise ValueError("Click position outside image bounds")

            # Ensure contours are available
            contours = self.contours
            if not contours:
                raise ValueError("No contours found")

            # Find the specific contour that contains the click position
            target_contour = None
            for contour in contours:
                if cv2.pointPolygonTest(contour, (image_x, image_y), False) >= 0:
                    target_contour = contour
                    break

            if target_contour is None:
                # If no direct contour contains the point, try nearby points within a tolerance
                tolerance = 5  # Adjust this value based on desired gap tolerance
                for dx in range(-tolerance, tolerance + 1):
                    for dy in range(-tolerance, tolerance + 1):
                        check_x = image_x + dx
                        check_y = image_y + dy

                        # Skip if out of bounds
                        if not (0 <= check_x < width and 0 <= check_y < height):
                            continue

                        for contour in contours:
                            if cv2.pointPolygonTest(contour, (check_x, check_y), False) >= 0:
                                target_contour = contour
                                break

                        if target_contour is not None:
                            break

                    if target_contour is not None:
                        break

            if target_contour is None:
                raise ValueError("Click position is outside any detected contour (even with tolerance)")

            # Create a mask from the specific contour
            mask = np.zeros((height, width), dtype=np.uint8)
            cv2.drawContours(mask, [target_contour], 0, 255, -1)  # Fill the contour with white

            # Apply morphological closing to fill small gaps in the contour
            kernel_size = 3  # Adjust based on the typical gap size
            kernel = np.ones((kernel_size, kernel_size), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

            # Extract points inside the filled contour
            filled_points = []
            for y in range(height):
                for x in range(width):
                    if mask[y, x] == 255:
                        filled_points.append(QPointF(float(x), float(y)))

            return filled_points

        except Exception as e:
            print(f"Fill contour error: {type(e).__name__} - {str(e)}")
            raise

    def _handle_fill_contour_complete(self, new_points, progress):
        """Handles the completion of the fill operation."""
        try:
            progress.close()

            if not new_points:
                QMessageBox.information(self, "Fill Complete", "No points were filled.")
                return

            # Ensure the ZoomableGraphicsView has the necessary attributes
            if not hasattr(self, 'scene'):
                QMessageBox.warning(self, "Error", "Graphics view is not properly initialized.")
                return

            # Process points in chunks to avoid UI freezing
            chunk_size = 10000
            chunks = [new_points[i:i + chunk_size] for i in range(0, len(new_points), chunk_size)]

            # Ensure points and points_history attributes exist
            if not hasattr(self, 'points'):
                self.points = []
            if not hasattr(self, 'points_history'):
                self.points_history = []

            # Create point items and add to the image label
            new_point_items = []
            for chunk in chunks:
                chunk_items = []
                for point in chunk:
                    point_item = self.view.create_point_item(self.point_label, point.x(), point.y(), self.point_color)
                    chunk_items.append(point_item)

                new_point_items.extend(chunk_items)

            # Add the new points to the existing points list
            self.points.extend(new_point_items)

            # Add to points history for potential undo functionality
            self.points_history.append(new_point_items)

            # Update the points overlay to reflect new points
            if hasattr(self, 'update_points_overlay'):
                self.update_points_overlay()

            QMessageBox.information(self, "Fill Complete", f"Filled {len(new_points)} points.")

        except Exception as e:
            QMessageBox.warning(self, "Rendering Error", f"Failed to render fill: {str(e)}")
            print(f"Fill rendering error: {traceback.format_exc()}")

    def _handle_fill_contour_error(self, error, progress):
        """Handles any errors that occur during the fill operation."""
        progress.close()
        QMessageBox.warning(self, "Error", f"Fill operation failed: {error}")
