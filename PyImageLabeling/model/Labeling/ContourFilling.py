from PyQt6.QtWidgets import QMessageBox, QProgressDialog, QGraphicsItem
from PyQt6.QtCore import Qt, QPointF, QPoint, QLine, QRectF, QRect
from PyQt6.QtGui import QPixmap, QImage, QColor,  QPainter, QPen
from PyImageLabeling.model.Core import Core
import numpy as np
import cv2
import traceback

from PyImageLabeling.model.Utils import Utils

import time

TOLERENCE_PARAMETERS = {
    1:  {'canny_low': 100, 'canny_high': 200, 'blur_kernel': 3, 'dilate_iter': 0, 'min_area': 60},
    2:  {'canny_low': 90,  'canny_high': 190, 'blur_kernel': 3, 'dilate_iter': 0, 'min_area': 50},
    3:  {'canny_low': 80,  'canny_high': 180, 'blur_kernel': 3, 'dilate_iter': 1, 'min_area': 40},
    4:  {'canny_low': 70,  'canny_high': 160, 'blur_kernel': 3, 'dilate_iter': 1, 'min_area': 30},
    5:  {'canny_low': 65,  'canny_high': 150, 'blur_kernel': 5, 'dilate_iter': 1, 'min_area': 25},
    6:  {'canny_low': 60,  'canny_high': 140, 'blur_kernel': 5, 'dilate_iter': 1, 'min_area': 20},
    7:  {'canny_low': 55,  'canny_high': 130, 'blur_kernel': 5, 'dilate_iter': 1, 'min_area': 18},
    8:  {'canny_low': 50,  'canny_high': 120, 'blur_kernel': 5, 'dilate_iter': 2, 'min_area': 16},
    9:  {'canny_low': 45,  'canny_high': 110, 'blur_kernel': 5, 'dilate_iter': 2, 'min_area': 14},
    10: {'canny_low': 40,  'canny_high': 100, 'blur_kernel': 5, 'dilate_iter': 2, 'min_area': 12},
    11: {'canny_low': 35,  'canny_high': 90,  'blur_kernel': 7, 'dilate_iter': 2, 'min_area': 10},
    12: {'canny_low': 30,  'canny_high': 85,  'blur_kernel': 7, 'dilate_iter': 2, 'min_area': 8},
    13: {'canny_low': 28,  'canny_high': 80,  'blur_kernel': 7, 'dilate_iter': 2, 'min_area': 6},
    14: {'canny_low': 25,  'canny_high': 75,  'blur_kernel': 7, 'dilate_iter': 2, 'min_area': 5},
    15: {'canny_low': 22,  'canny_high': 70,  'blur_kernel': 9, 'dilate_iter': 2, 'min_area': 4},
    16: {'canny_low': 20,  'canny_high': 65,  'blur_kernel': 9, 'dilate_iter': 2, 'min_area': 3},
    17: {'canny_low': 18,  'canny_high': 60,  'blur_kernel': 9, 'dilate_iter': 3, 'min_area': 3},
    18: {'canny_low': 16,  'canny_high': 55,  'blur_kernel': 9, 'dilate_iter': 3, 'min_area': 2},
    19: {'canny_low': 15,  'canny_high': 50,  'blur_kernel': 9, 'dilate_iter': 3, 'min_area': 2},
    20: {'canny_low': 12,  'canny_high': 40,  'blur_kernel': 9, 'dilate_iter': 3, 'min_area': 1}
}

class ContourItem():

    def __init__(self, points, color):
        super().__init__()
        self.points = points
        self.color = color
        
        self.qrectf = QRectF(points[0][0][0], points[0][0][1], 1, 1)
        for point in points:   
            self.qrectf = self.qrectf.united(QRectF(point[0][0], point[0][1], 1, 1))
        
        self.qrect = self.qrectf.toRect()
        contour_numpy_pixels = np.zeros((self.qrect.height(), self.qrect.width(), 4), dtype=np.uint8)
        
        for point in self.points:
            point[0][0], point[0][1] = point[0][0]-self.qrect.x(), point[0][1]-self.qrect.y()
        
        cv2.drawContours(contour_numpy_pixels, [self.points], -1, self.color.getRgb(), -1)
        cv2.drawContours(contour_numpy_pixels, [self.points], 0, self.color.getRgb(), 1)
        
        self.image_pixmap = QPixmap.fromImage(QImage(contour_numpy_pixels.data, self.qrect.width(), self.qrect.height(), self.qrect.width() * 4, QImage.Format.Format_RGBA8888))
    
    def paint_labeling_overlay(self, labeling_overlay_painter):
        labeling_overlay_painter.drawPixmap(self.qrect.x(), self.qrect.y(), self.image_pixmap) 

        

class ContourFilling(Core):
    def __init__(self):
        super().__init__()
        self.contours = [] # It is in list of contours. A contour is a list of points (x, y).
        self.contour_items = [] # QGraphicItem for each contour clicked
        
        self.coutour_filling_pixmap = None
        self.coutour_filling_item = None

    def contour_filling(self):
        self.checked_button = self.contour_filling.__name__

    def start_contour_filling(self):
        self.view.zoomable_graphics_view.change_cursor("filling")
        self.apply_contour()
    
    def end_contour_filling(self):
        # Remove the dislay of all these item
        for item in self.contour_items:
            self.zoomable_graphics_view.scene.removeItem(item)
        self.contour_items.clear()
        
    def remove_contour(self):
        if self.coutour_filling_item is not None:
            self.view.zoomable_graphics_view.scene.removeItem(self.coutour_filling_item)
            self.coutour_filling_item = None
    
    def get_contours(self):
        # Convert to grayscale (use OpenCV)
        image_numpy_pixels_gray = cv2.cvtColor(self.get_current_image_item().get_image_numpy_pixels_rgb(), cv2.COLOR_RGB2GRAY)
        # Apply Gaussian blur to reduce noise (kernel size based on tolerance)
        image_numpy_pixels_blurred = cv2.GaussianBlur(image_numpy_pixels_gray, (self.tolerance_parameters["blur_kernel"], self.tolerance_parameters["blur_kernel"]), 0)
        # Apply Canny edge detection with tolerance-based parameters
        image_numpy_pixels_canny = cv2.Canny(image_numpy_pixels_blurred, self.tolerance_parameters["canny_low"], self.tolerance_parameters["canny_high"]) 
        # Apply dilation to connect nearby edges (iterations based on tolerance)
        if self.tolerance_parameters['dilate_iter'] > 0:
            image_numpy_pixels_canny = cv2.dilate(image_numpy_pixels_canny, np.ones((2, 2), np.uint8), iterations=self.tolerance_parameters['dilate_iter'])
        # Find contours with hierarchy to better handle nested shapes
        contours, _ = cv2.findContours(image_numpy_pixels_canny, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_TC89_L1)
        # Filter out small contours based on tolerance level
        contours = [cnt for cnt in contours if cv2.contourArea(cnt) > self.tolerance_parameters["min_area"]]
        return contours

    def apply_contour(self):
        self.width = self.get_current_image_item().get_width()
        self.height = self.get_current_image_item().get_height()
        
        self.tolerance = Utils.load_parameters()["contour_filling"]["tolerance"]
        self.tolerance_parameters = TOLERENCE_PARAMETERS[self.tolerance]
        self.contours = self.get_contours() # It is in list of contours. A contour is a list of points (x, y). 
        if len(self.contours) == 0:
            raise ValueError("No contours found !")

        self.color = self.get_current_label_item().get_color()
        # It is more faster to do that because cv2 loop into the points of contours in c++, not python
        contour_numpy_pixels = np.zeros((self.height, self.width, 4), dtype=np.uint8)
        cv2.drawContours(contour_numpy_pixels, self.contours, -1, self.color.darker(200).getRgb(), 1)
        self.coutour_filling_pixmap = QPixmap.fromImage(QImage(contour_numpy_pixels.data, self.width, self.height, self.width * 4, QImage.Format.Format_RGBA8888))
        self.coutour_filling_item = self.view.zoomable_graphics_view.scene.addPixmap(self.coutour_filling_pixmap)
        self.coutour_filling_item.setZValue(1)
        print("end apply_contour")

    def find_closest_contour(self, position_x, position_y):
        for contour in self.contours:
            if cv2.pointPolygonTest(contour, (position_x, position_y), False) >= 0:
                return contour
        return None
            
    def fill_contour(self, position):
        # Find the good contour
        self.color = self.get_current_label_item().get_color()
        position_x, position_y = int(position.x()), int(position.y()) 
        closest_contour = self.find_closest_contour(position_x, position_y)
        if closest_contour is None: return # We are not cliked inside of a contour

        # Create a little QPixmap of this contour with cv2 
        coutour_item = ContourItem(closest_contour.copy(), self.color)
        
        # Draw the contour QPixmap on the good labeling overlay 
        coutour_item.paint_labeling_overlay(self.get_current_image_item().get_labeling_overlay().get_painter())
        
        # Update the labeling overlay
        self.get_current_image_item().update_labeling_overlay()
        
