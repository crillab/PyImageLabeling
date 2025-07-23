from PyQt6.QtWidgets import QMessageBox, QProgressDialog
from PyQt6.QtCore import Qt, QPointF, QPoint
from PyQt6.QtGui import QPixmap, QImage, QColor,  QPainter, QPen
from PyImageLabeling.model.Core import Core
import numpy as np
import cv2
import traceback

class ContourFilling(Core):
    def __init__(self):
        super().__init__()
        self.contour_layer_applied = False
        self.contours = []
        # Separate overlay items for contours and filled shapes
        self.overlay_pixmap_item_contour = None  
        self.overlay_pixmap_contour = None  
        self.overlay_pixmap_item_filled = None  
        self.overlay_pixmap_filled = None  
        
        # Contour tolerance parameters
        self._tolerance_params = {
            1: {'canny_low': 100, 'canny_high': 200, 'blur_kernel': 3, 'dilate_iter': 0, 'min_area': 50},
            2: {'canny_low': 80, 'canny_high': 180, 'blur_kernel': 3, 'dilate_iter': 1, 'min_area': 30},
            3: {'canny_low': 70, 'canny_high': 160, 'blur_kernel': 3, 'dilate_iter': 1, 'min_area': 20},
            4: {'canny_low': 60, 'canny_high': 140, 'blur_kernel': 5, 'dilate_iter': 1, 'min_area': 15},
            5: {'canny_low': 50, 'canny_high': 150, 'blur_kernel': 5, 'dilate_iter': 1, 'min_area': 10}, 
            6: {'canny_low': 40, 'canny_high': 120, 'blur_kernel': 5, 'dilate_iter': 2, 'min_area': 8},
            7: {'canny_low': 30, 'canny_high': 100, 'blur_kernel': 7, 'dilate_iter': 2, 'min_area': 5},
            8: {'canny_low': 25, 'canny_high': 80, 'blur_kernel': 7, 'dilate_iter': 2, 'min_area': 3},
            9: {'canny_low': 20, 'canny_high': 60, 'blur_kernel': 9, 'dilate_iter': 3, 'min_area': 2},
            10: {'canny_low': 15, 'canny_high': 40, 'blur_kernel': 9, 'dilate_iter': 3, 'min_area': 1}
        }

    def contour_filling(self):
        self.checked_button = self.contour_filling.__name__

    def start_contour_filling(self):
        self.view.zoomable_graphics_view.change_cursor("filling")
        self.base_pixmap = self.view.pixmap.toImage()
        self.view.point_color = self.labels[self.current_label]["color"]
        self.view.point_label = self.labels[self.current_label]["name"]
        self.apply_contour()

    def add_contour_overlay(self, new_overlay_pixmap_contour):
        """
        Add or update the contour overlay layer on top of the base image.
        """
        if new_overlay_pixmap_contour is None:
            return False

        # Scale the overlay to match the base image size if needed
        if self.view.pixmap and new_overlay_pixmap_contour.size() != self.view.pixmap.size():
            new_overlay_pixmap_contour = new_overlay_pixmap_contour.scaled(
                self.view.pixmap.size(),
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

        # Set the contour overlay
        self.overlay_pixmap_contour = new_overlay_pixmap_contour

        # Create or update the contour overlay pixmap item
        if self.overlay_pixmap_item_contour is None:
            self.overlay_pixmap_item_contour = self.view.zoomable_graphics_view.scene.addPixmap(self.overlay_pixmap_contour)
            if hasattr(self.view, 'pixmap_item'):
                self.overlay_pixmap_item_contour.setPos(self.view.pixmap_item.pos())
            self.overlay_pixmap_item_contour.setZValue(1)  # Set Z-value to be above the base image
        else:
            self.overlay_pixmap_item_contour.setPixmap(self.overlay_pixmap_contour)

        # Update the scene
        self.view.zoomable_graphics_view.scene.update()
        return True

    def add_filled_overlay(self, new_overlay_pixmap_filled):
        """
        Add or update the filled shapes overlay layer on top of the contour overlay.
        """
        if new_overlay_pixmap_filled is None:
            return False

        # Scale the overlay to match the base image size if needed
        if self.view.pixmap and new_overlay_pixmap_filled.size() != self.view.pixmap.size():
            new_overlay_pixmap_filled = new_overlay_pixmap_filled.scaled(
                self.view.pixmap.size(),
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

        # Merge the new filled overlay with the existing filled overlay if one exists
        if self.overlay_pixmap_filled is None:
            self.overlay_pixmap_filled = new_overlay_pixmap_filled
        else:
            # Create a painter to merge the new overlay with the existing one
            from PyQt6.QtGui import QPainter
            painter = QPainter(self.overlay_pixmap_filled)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            painter.drawPixmap(0, 0, new_overlay_pixmap_filled)
            painter.end()

        # Create or update the filled overlay pixmap item
        if self.overlay_pixmap_item_filled is None:
            self.overlay_pixmap_item_filled = self.view.zoomable_graphics_view.scene.addPixmap(self.overlay_pixmap_filled)
            if hasattr(self.view, 'pixmap_item'):
                self.overlay_pixmap_item_filled.setPos(self.view.pixmap_item.pos())
            self.overlay_pixmap_item_filled.setZValue(2)  # Set Z-value to be above the contour overlay
        else:
            self.overlay_pixmap_item_filled.setPixmap(self.overlay_pixmap_filled)

        # Update the scene
        self.view.zoomable_graphics_view.scene.update()
        return True

    def remove_overlay(self):
        """
        Remove the contour overlay layer from the image.
        """
        if self.overlay_pixmap_item_contour is not None:
            self.view.zoomable_graphics_view.scene.removeItem(self.overlay_pixmap_item_contour)
            self.overlay_pixmap_item_contour = None
            self.overlay_pixmap_contour = None
            self.contour_layer_applied = False
            self.view.zoomable_graphics_view.scene.update()

    def apply_contour(self):
        """Detects contours from the base image using tolerance-based parameters."""
        if not hasattr(self, 'base_pixmap') or self.base_pixmap is None:
            msg_box = QMessageBox()
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

        # Get tolerance parameters based on current tolerance level
        params = self._tolerance_params[self.view.contour_tolerance]

        # Get the pixmap data
        width, height = self.base_pixmap.width(), self.base_pixmap.height()

        # Convert QImage to NumPy array
        buffer = self.base_pixmap.constBits()
        buffer.setsize(height * width * 4)  # 4 channels (RGBA)
        img_array = np.frombuffer(buffer, dtype=np.uint8).reshape((height, width, 4))

        # Convert to grayscale (use OpenCV)
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGBA2GRAY)

        # Apply Gaussian blur to reduce noise (kernel size based on tolerance)
        blur_kernel = params['blur_kernel']
        blurred = cv2.GaussianBlur(gray, (blur_kernel, blur_kernel), 0)

        # Apply Canny edge detection with tolerance-based parameters
        edges = cv2.Canny(blurred, params['canny_low'], params['canny_high'])

        # Apply dilation to connect nearby edges (iterations based on tolerance)
        if params['dilate_iter'] > 0:
            kernel = np.ones((2, 2), np.uint8)
            edges = cv2.dilate(edges, kernel, iterations=params['dilate_iter'])

        # Find contours with hierarchy to better handle nested shapes
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_TC89_L1)

        # Filter out small contours based on tolerance level
        min_contour_area = params['min_area']
        contours = [cnt for cnt in contours if cv2.contourArea(cnt) > min_contour_area]

        # Save contours for later use
        self.contours = contours

        # Create a transparent layer to visualize the contours (Blue lines)
        contour_layer = np.zeros((height, width, 4), dtype=np.uint8)
        cv2.drawContours(contour_layer, contours, -1, (0, 0, 255, 255), 1)

        # Convert NumPy array to QImage
        contour_qimage = QImage(contour_layer.data, width, height, width * 4, QImage.Format.Format_RGBA8888)

        # Set the overlay in the image viewer using the dedicated contour overlay method
        overlay_pixmap_contour = QPixmap.fromImage(contour_qimage)
        self.add_contour_overlay(overlay_pixmap_contour)

        # Mark that the contour layer is applied
        self.contour_layer_applied = True

        print(f"Applied contours with tolerance level {self.view.contour_tolerance}: {len(contours)} contours found")

    def fill_contour(self, scene_pos):
        """Fill the contour clicked by the user."""
        progress = QProgressDialog("Processing magic pen fill...", "Cancel", 0, 0, self.view)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()

        try:
            filled_points = self._fill_contour_worker(scene_pos)
            self._handle_fill_contour_complete(filled_points, progress)
        except Exception as e:
            self._handle_fill_contour_error(str(e), progress)

    def _fill_contour_worker(self, scene_pos):
        """Worker function to perform the contour fill with improved gap tolerance."""
        try:
            image_x = int(scene_pos.x())
            image_y = int(scene_pos.y())

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
                # Use contour tolerance to determine search radius
                search_tolerance = max(1, self.view.contour_tolerance // 2)
                for dx in range(-search_tolerance, search_tolerance + 1):
                    for dy in range(-search_tolerance, search_tolerance + 1):
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

            # Apply morphological closing to fill small gaps based on tolerance
            # Higher tolerance = larger kernel for filling bigger gaps
            kernel_size = min(2 + (self.view.contour_tolerance // 3), 7)  # Scale from 2 to 7
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
        """Handles the completion of the fill operation using pixmap overlay."""
        if progress:
            progress.close()

        try:
            if not new_points:
                QMessageBox.information(self.view, "Fill Complete", "No points were filled.")
                return

            # Store the points as QPointF objects (not QGraphicsItems)
            if not hasattr(self, 'filled_points'):
                self.filled_points = []
            if not hasattr(self, 'points_history'):
                self.points_history = []

            # Add the new points to our collection
            self.filled_points.extend(new_points)
            self.points_history.append(new_points)

            # Create and apply the points overlay using the dedicated filled overlay method
            self.create_points_overlay()

            QMessageBox.information(self.view, "Fill Complete", f"Filled {len(new_points)} points.")

        except Exception as e:
            QMessageBox.warning(self.view, "Rendering Error", f"Failed to render fill: {str(e)}")
            print(f"Fill rendering error: {traceback.format_exc()}")

    def create_points_overlay(self):
        """Create a pixmap overlay showing all filled points."""
        if not hasattr(self, 'base_pixmap') or self.base_pixmap is None:
            return
        
        if not hasattr(self, 'filled_points') or not self.filled_points:
            return

        # Create a transparent pixmap for the points overlay
        width, height = self.base_pixmap.width(), self.base_pixmap.height()
        points_overlay = QPixmap(width, height)
        points_overlay.fill(Qt.GlobalColor.transparent)

        # Create a QPainter to draw on the points overlay
        painter = QPainter(points_overlay)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Set the brush for filled circles instead of just points
        painter.setBrush(self.view.point_color)
        painter.setPen(QPen(self.view.point_color, 1))

        # Draw each point as a small filled circle
        point_size = 2  # Adjust size as needed
        for point in self.filled_points:
            x, y = int(point.x()), int(point.y())
            painter.drawEllipse(x - point_size//2, y - point_size//2, point_size, point_size)

        painter.end()

        # Add the points overlay using the dedicated filled overlay system
        self.add_filled_overlay(points_overlay)

    def update_points_overlay(self):
        """Update method - delegates to create_points_overlay."""
        self.create_points_overlay()

    def _handle_fill_contour_error(self, error, progress):
        """Handles any errors that occur during the fill operation."""
        if progress:
            progress.close()
        QMessageBox.warning(self.view, "Error", f"Fill operation failed: {error}")
