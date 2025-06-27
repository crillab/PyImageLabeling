from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QProgressDialog, QMessageBox, QApplication
from models.ProcessWorker import ProcessWorker
from models.PointItem import PointItem
import time

class MagicPenTool:
    def fill_shape(self, scene_pos):
        """Fill a shape with points using magic pen"""
        if not self.base_pixmap:
            return
            
        # Create progress dialog
        progress = QProgressDialog("Processing magic pen fill...", "Cancel", 0, 0, self)
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
        """Worker function to fill shape (runs in separate thread, with hard limits)"""
        if not self.raw_image:
            return []
            
        image_x = int(scene_pos.x())
        image_y = int(scene_pos.y())
    
        width, height = self.raw_image.width(), self.raw_image.height()
    
        if not (0 <= image_x < width and 0 <= image_y < height):
            return []
            
        # Obtenir la couleur cible
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
    
        from collections import deque
        queue = deque([(image_x, image_y)])
    
        try:
            while queue:
                if time.time() - start_time > self.process_timeout:
                    print(f"Timeout atteint ({self.process_timeout}s). Annulation du remplissage.")
                    return []  # Retourne une liste vide → pas de remplissage

                if len(points_to_create) >= MAX_POINTS_LIMIT:
                    print(f"Trop de points ({MAX_POINTS_LIMIT}). Annulation du remplissage.")
                    return []  # Retourne une liste vide → pas de remplissage
    
                x, y = queue.popleft()
                if (x, y) in visited:
                    continue
    
                visited.add((x, y))
    
                if not (0 <= x < width and 0 <= y < height):
                    continue
    
                # Vérification de la couleur avec la tolérance
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
    
                # Ajouter le point
                points_to_create.append((x, y))
    
                # Ajouter les voisins
                for dx, dy in directions:
                    new_x, new_y = x + dx, y + dy
                    if (new_x, new_y) not in visited:
                        queue.append((new_x, new_y))
    
        except Exception as e:
            print(f"Erreur pendant le remplissage : {e}")
    
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
            current_point_radius = self.point_radius
            current_point_color = self.point_color
            current_point_opacity = self.point_opacity
            current_point_label = self.point_label
            
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
                        point_item = PointItem(
                            current_point_label,
                            x, y, 
                            current_point_radius,   # Use captured radius
                            current_point_color,    # Use captured color
                            current_point_opacity   # Use captured opacity
                        )
                        self.scene.addItem(point_item)
                        self.points.append(point_item)
                        batch_points.append(point_item)
                    except Exception as e:
                        print(f"Error creating point at ({x}, {y}): {e}")
                        continue
                
                all_new_points.extend(batch_points)
                
                # Allow UI to update between chunks
                QApplication.processEvents()
            
            # Store for undo history
            if all_new_points:
                self.points_history.append(all_new_points)
                
            # Update the points overlay
            self.update_points_overlay()
        except Exception as e:
            print(f"Error during fill completion: {e}")
        finally:
            QApplication.restoreOverrideCursor()

    def _handle_fill_error(self, error, progress):
        """Handle errors during fill operation"""
        if progress:
            progress.close()
        QMessageBox.warning(self, "Error", f"Magic pen fill operation failed: {error}")


    def toggle_magic_pen(self, enabled):
        """Toggle magic pen mode on/off"""
        self.magic_pen_mode = enabled
        if enabled:
            self.paint_mode = False
            self.erase_mode = False
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)