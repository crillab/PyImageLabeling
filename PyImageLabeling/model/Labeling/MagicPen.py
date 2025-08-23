from PyQt6.QtCore import Qt, QRectF
from PyImageLabeling.model.Core import Core
from PyQt6.QtGui import QColor, QPixmap, QBrush, QPainter, QBitmap, QColorConstants, QImage
from PyQt6.QtWidgets import QProgressDialog, QApplication, QMessageBox
from collections import deque

import numpy

from PyImageLabeling.model.Utils import Utils
#DIRECTIONS = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1))

DIRECTIONS = ((1, 0), (-1, 0), (0, 1), (0, -1))

class MagicPen(Core):
    def __init__(self):
        super().__init__()

    def magic_pen(self):
        self.checked_button = self.magic_pen.__name__
        print("magic")

    def start_magic_pen(self, scene_pos):
        """Fill area with points using magic pen"""
        self.view.zoomable_graphics_view.change_cursor("magic")
        self.raw_image = self.image_pixmap.toImage()
        self.fill_shape(scene_pos)

    def fill_shape(self, scene_pos):
        # Create progress dialog
        self.view.progressBar.reset()

        #progress = QProgressDialog("Processing magic pen fill...", "Cancel", 0, 0, self.view)
        #progress.setWindowModality(Qt.WindowModality.WindowModal)
        #progress.show()

        try:
            new_overlay = self._fill_shape_worker(scene_pos)
            self.update_overlay(new_overlay) 
            #self._handle_fill_complete(new_overlay_pixmap, self.view.progressBar)
        except Exception as e:
            self._handle_fill_error(str(e), self.view.progressBar)

    def _fill_shape_worker(self, scene_pos):
        #Create some variables
        initial_position_x, initial_position_y = int(scene_pos.x()), int(scene_pos.y()) 
        width, height = self.raw_image.width(), self.raw_image.height()
        if not (0 <= initial_position_x < width and 0 <= initial_position_y < height): return None

        #Get parameters
        tolerance = Utils.load_parameters()["magic_pen"]["tolerance"] 
        max_pixels = Utils.load_parameters()["magic_pen"]["max_pixels"] 
        method = Utils.load_parameters()["magic_pen"]["method"] 

        #Initialize some data
        new_overlay_image = QImage(width, height, QImage.Format.Format_Mono)
        new_overlay_image.fill(Qt.GlobalColor.color0)
        visited = numpy.full((width, height), False)

        #Call the good method
        if method == "HSV SPE":
            return self._fill_shape_hsv_spe(new_overlay_image, visited, initial_position_x, initial_position_y, width, height, tolerance, max_pixels)
        elif method == "RGB AVG":
            return self._fill_shape_rgb_avg(new_overlay_image, visited, initial_position_x, initial_position_y, width, height, tolerance, max_pixels)
        elif method == "RGB MIN":
            pass
        else:
            raise NotImplementedError("Mathod not implmented: "+str(method))
        print("MagicPen: image created")
        
    def _fill_shape_rgb_avg(self, new_overlay_image, visited, initial_position_x, initial_position_y, width, height, tolerance, max_pixels):
        #target_color = QColor(self.raw_image.pixel(initial_position_x, initial_position_y))
        target_rgb = self.numpy_pixels_rgb[initial_position_y, initial_position_x].astype(int)   
        queue = deque()
        
        if (0 <= initial_position_x < width and 0 <= initial_position_y < height): 
            queue.append((initial_position_x, initial_position_y))
        
        n_pixels = 0
        while queue and n_pixels <= max_pixels:
            x, y = queue.popleft()
            if visited[x][y] == True: continue
            visited[x][y] = True
            current_rgb = self.numpy_pixels_rgb[y, x].astype(int)
            dist = numpy.mean(100-numpy.divide(numpy.multiply(numpy.abs(target_rgb-current_rgb), 100), 255))
            
            if dist < tolerance: continue
            
            #Color the new_overlay
            new_overlay_image.setPixel(x, y, 1)
            n_pixels += 1

            # Add neighbors
            for dx, dy in DIRECTIONS:
                new_x, new_y = x + dx, y + dy
                if (0 <= new_x < width and 0 <= new_y < height):
                    queue.append((new_x, new_y))

        print("MagicPen: end n_pixels:", n_pixels)
        return new_overlay_image

    def _fill_shape_hsv_spe(self, new_overlay_image, visited, initial_position_x, initial_position_y, width, height, tolerance, max_pixels):
        # Problem with this method: getHsv() do not the difference between gray colors (black and white for example)
        target_color = QColor(self.raw_image.pixel(initial_position_x, initial_position_y))
        target_hue, target_sat, target_val, alpha = target_color.getHsv()  
        print("here1:", target_hue, target_sat, target_val, alpha)
        target_hue, target_sat, target_val = target_color.hue(), target_color.saturation(), target_color.value()
        print("here2:", target_hue, target_sat, target_val)

        print("here3:",  self.numpy_pixels_hsv[initial_position_x, initial_position_y])

        
        queue = deque()
        
        if (0 <= initial_position_x < width and 0 <= initial_position_y < height): 
            queue.append((initial_position_x, initial_position_y))
        

        n_pixels = 0
        while queue and n_pixels <= max_pixels:
            x, y = queue.popleft()
            if visited[x][y] == True: continue
            visited[x][y] = True
            
            current_hue, current_sat, current_val, _ = QColor(self.raw_image.pixel(x, y)).getHsv()    
            
            if target_hue == -1 or current_hue == -1:
                if abs(current_val - target_val) > tolerance:
                    continue
            else:

                hue_diff = min(abs(current_hue - target_hue), 360 - abs(current_hue - target_hue))
                
                if (hue_diff > tolerance or
                    abs(current_sat - target_sat) > tolerance or
                    abs(current_val - target_val) > tolerance):
                    continue
            
            #Color the new_overlay
            new_overlay_image.setPixel(x, y, 1)
            n_pixels += 1

            # Add neighbors
            for dx, dy in DIRECTIONS:
                new_x, new_y = x + dx, y + dy
                if (0 <= new_x < width and 0 <= new_y < height):
                    queue.append((new_x, new_y))
        print("MagicPen: end n_pixels:", n_pixels)
        return new_overlay_image
    
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
    
    

