
from PyQt6.QtCore import Qt, QTimer,  QThread, pyqtSignal
from PyQt6.QtGui import QColor
from PyImageLabeling.model.Core import Core
from collections import deque

from PyQt6.QtWidgets import QProgressDialog, QApplication, QMessageBox
import time


class ProcessWorker(QThread):
    """Worker class to handle long processes with timeout"""
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, func, args=None, kwargs=None, timeout=10):
        super().__init__()
        self.func = func
        self.args = args or []
        self.kwargs = kwargs or {}
        self.timeout_value = timeout
        
        # Create a separate timer for timeout
        self.timeout_timer = QTimer()
        self.timeout_timer.setSingleShot(True)
        self.timeout_timer.timeout.connect(self._on_timeout)
    
    def run(self):
        """Thread's main function (automatically called by start())"""
        try:
            # Start the timeout timer
            self.timeout_timer.start(self.timeout_value * 1000)
            
            # Run the actual function
            result = self.func(*self.args, **self.kwargs)
            
            # Stop timer and emit result
            self.timeout_timer.stop()
            self.finished.emit(result)
        except Exception as e:
            self.timeout_timer.stop()
            self.error.emit(str(e))
    
    def _on_timeout(self):
        """Handle timeout event"""
        self.terminate()  # Terminate thread
        self.error.emit(f"Operation timed out after {self.timeout_value} seconds")
        
class MagicPen(Core):
    def __init__(self):
        super().__init__() 
        self.magic_pen_tolerance = 30  # Color tolerance for magic pen
        self.max_points_limite = 50000  # Maximum points limit
        self.process_timeout = 30  # Timeout in seconds
        self.worker = None

    def magic_pen(self):
        self.checked_button = self.magic_pen.__name__
        print("magic")

    def  apply_magic_pen(self, scene_pos):
        """Fill area with points using magic pen"""
        self.raw_image = self.view.pixmap.toImage()
        self.fill_shape(scene_pos)

    def fill_shape(self, scene_pos):

        # Create progress dialog
        progress = QProgressDialog("Processing magic pen fill...", "Cancel", 0, 0, self.view)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()
        
        # Create worker thread for fill operation
        self.worker = ProcessWorker(
            self._fill_shape_worker, 
            args=[scene_pos], 
            timeout=self.process_timeout
        )
        self.worker.finished.connect(
            lambda points: self._handle_fill_complete(points, progress)
        )
        self.worker.error.connect(
            lambda error: self._handle_fill_error(error, progress)
        )
        self.worker.start()

    def _fill_shape_worker(self, scene_pos):

        image_x = int(scene_pos.x())
        image_y = int(scene_pos.y())
    
        width, height = self.raw_image.width(), self.raw_image.height()
    
        if not (0 <= image_x < width and 0 <= image_y < height):
            return []
            
        # Get target color
        target_color = QColor(self.raw_image.pixel(image_x, image_y))
        target_hue = target_color.hue()
        target_sat = target_color.saturation()
        target_val = target_color.value()
        tolerance = self.magic_pen_tolerance
    
        points_to_create = []
        visited = set()
        start_time = time.time()
    
        MAX_POINTS_LIMIT = self.max_points_limite
        directions = [
            (1, 0), (-1, 0), (0, 1), (0, -1),
            (1, 1), (-1, -1), (1, -1), (-1, 1)
        ]
    
        queue = deque([(image_x, image_y)])
    
        try:
            while queue:
                if time.time() - start_time > self.process_timeout:
                    print(f"Timeout reached ({self.process_timeout}s). Canceling fill.")
                    return []  # Return empty list → no fill

                if len(points_to_create) >= MAX_POINTS_LIMIT:
                    print(f"Too many points ({MAX_POINTS_LIMIT}). Canceling fill.")
                    return []  # Return empty list → no fill
    
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
                    hue_diff = min(abs(current_hue - target_hue), 
                                  360 - abs(current_hue - target_hue))
    
                    if (hue_diff > tolerance or
                        abs(current_sat - target_sat) > tolerance or
                        abs(current_val - target_val) > tolerance):
                        continue
    
                # Add the point
                points_to_create.append((x, y))
    
                # Add neighbors
                for dx, dy in directions:
                    new_x, new_y = x + dx, y + dy
                    if (new_x, new_y) not in visited:
                        queue.append((new_x, new_y))
    
        except Exception as e:
            print(f"Error during fill: {e}")
    
        return points_to_create
    
    def _handle_fill_complete(self, point_coords, progress):
        """Handle completion of fill operation"""
        if not progress:
            return
            
        progress.close()
        
        if not point_coords:
            return
            
        # Prepare for UI update and point creation
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        
        try:
            # Capture point parameters IMMEDIATELY at the time of fill
            current_point_color = self.labels[self.current_label]["color"]
            current_point_label = self.labels[self.current_label]["name"]
            
            # Create a batch of points
            chunk_size = 5000  # Process in larger batches for efficiency
            all_new_points = []
            
            for i in range(0, len(point_coords), chunk_size):
                chunk = point_coords[i:i + chunk_size]
                batch_points = []
                
                # Update progress dialog
                if progress and not progress.wasCanceled():
                    progress.setValue(i)
                    progress.setMaximum(len(point_coords))
                    progress.setLabelText(f"Creating points: {i}/{len(point_coords)}")
                    QApplication.processEvents()
                
                for x, y in chunk:
                    try:
                        point_item = self.view.create_point_item(
                            current_point_label,
                            x, y, 
                            current_point_color
                        )
                        self.view.zoomable_graphics_view.scene.addItem(point_item)
                        batch_points.append(point_item)
                    except Exception as e:
                        print(f"Error creating point at ({x}, {y}): {e}")
                        continue
                
                all_new_points.extend(batch_points)
                
                # Allow UI to update between chunks
                QApplication.processEvents()
            
            # Store for undo history if your system supports it
            if all_new_points and hasattr(self.view, 'points_history'):
                self.view.points_history.append(all_new_points)
                
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