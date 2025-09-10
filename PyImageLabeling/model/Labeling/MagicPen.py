from PyQt6.QtCore import Qt, QRectF
from PyImageLabeling.model.Core import Core
from PyQt6.QtGui import QColor, QPixmap, QBrush, QPainter, QBitmap, QColorConstants, QImage
from PyQt6.QtWidgets import QProgressDialog, QApplication, QMessageBox
from collections import deque

import numpy
import matplotlib

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
        self.fill_shape(scene_pos)

    def fill_shape(self, scene_pos):
        # Create progress dialog
        self.view.progressBar.reset()

        self._fill_shape_worker(scene_pos)
        self.get_current_image_item().update_labeling_overlay()
    
    def _fill_shape_worker(self, scene_pos):
        #Create some variables
        initial_position_x, initial_position_y = int(scene_pos.x()), int(scene_pos.y()) 
        width, height = self.get_current_image_item().get_width(), self.get_current_image_item().get_height()
        if not (0 <= initial_position_x < width and 0 <= initial_position_y < height): return None

        self.numpy_pixels_rgb = self.get_current_image_item().get_image_numpy_pixels_rgb()

        #Get parameters
        tolerance = Utils.load_parameters()["magic_pen"]["tolerance"] 
        max_pixels = Utils.load_parameters()["magic_pen"]["max_pixels"] 
        method = Utils.load_parameters()["magic_pen"]["method"] 

        #Initialize some data
        visited = numpy.full((width, height), False)

        #Call the good method
        if method == "HSV":
            return self._fill_shape_hsv(visited, initial_position_x, initial_position_y, width, height, tolerance, max_pixels)
        elif method == "RGB":
            return self._fill_shape_rgb(visited, initial_position_x, initial_position_y, width, height, tolerance, max_pixels)
        else:
            raise NotImplementedError("Mathod not implmented: "+str(method))
        print("MagicPen: image created")
        
    def _fill_shape_rgb(self, visited, initial_position_x, initial_position_y, width, height, tolerance, max_pixels):
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
            #self.labeling_overlay.setPixel(x, y, 1)
            self.get_current_image_item().get_labeling_overlay().get_painter().drawPoint(x, y)
            n_pixels += 1

            # Add neighbors
            for dx, dy in DIRECTIONS:
                new_x, new_y = x + dx, y + dy
                if (0 <= new_x < width and 0 <= new_y < height):
                    queue.append((new_x, new_y))
        
        print("MagicPen: end n_pixels:", n_pixels)
        
    
    def _fill_shape_hsv(self, visited, initial_position_x, initial_position_y, width, height, tolerance, max_pixels):
        #Convertion HSV is to slow: an optimization to do is to use openCv2 to store an HSV matrix in LoadImage. 

        #target_color = QColor(self.raw_image.pixel(initial_position_x, initial_position_y))
        target_hsv = matplotlib.colors.rgb_to_hsv(numpy.divide(self.numpy_pixels_rgb[initial_position_y, initial_position_x].astype(float), 255))   
        queue = deque()
        
        if (0 <= initial_position_x < width and 0 <= initial_position_y < height): 
            queue.append((initial_position_x, initial_position_y))
        
        n_pixels = 0
        while queue and n_pixels <= max_pixels:
            x, y = queue.popleft()
            if visited[x][y] == True: continue
            visited[x][y] = True
            current_hsv = matplotlib.colors.rgb_to_hsv(numpy.divide(self.numpy_pixels_rgb[y, x].astype(float), 255))
            #print("target_hsv:", target_hsv)
            #print("current_hsv:", current_hsv)
            
            dist = numpy.mean(100-numpy.multiply(numpy.abs(target_hsv-current_hsv), 100))
            #print("dist:", dist)
            if dist < tolerance: continue
            
            #Color the new_overlay
            self.get_current_image_item().get_labeling_overlay().get_painter().drawPoint(x, y)
            n_pixels += 1
            
            # Add neighbors
            for dx, dy in DIRECTIONS:
                new_x, new_y = x + dx, y + dy
                if (0 <= new_x < width and 0 <= new_y < height):
                    queue.append((new_x, new_y))

        print("MagicPen: end n_pixels:", n_pixels)
   
    
    
    
    

