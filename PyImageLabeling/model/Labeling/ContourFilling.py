from PyQt6.QtWidgets import QMessageBox, QProgressDialog, QGraphicsItem
from PyQt6.QtCore import Qt, QPointF, QPoint, QLine, QRectF, QRect
from PyQt6.QtGui import QPixmap, QImage, QColor,  QPainter, QPen
from model.Core import Core
import numpy as np
import cv2
import traceback

from model.Utils import Utils
from controller.settings.ContourFillinApplyCancel import ContourFillinApplyCancel

import time

TOLERENCE_PARAMETERS = {
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
class ContourItem(QGraphicsItem):

    def __init__(self, points, color, labeling_overlay_painter):
        super().__init__()
        self.points = points
        self.color = color
        self.labeling_overlay_painter = labeling_overlay_painter
        
        print("points", self.points[0])
        self.qrectf = QRectF(points[0][0][0], points[0][0][1], 1, 1)
        for point in points:   
            self.qrectf = self.qrectf.united(QRectF(point[0][0], point[0][1], 1, 1))
        
        self.qrect = self.qrectf.toRect()
        print("self.qrectf:", self.qrectf)
        contour_numpy_pixels = np.zeros((self.qrect.height(), self.qrect.width(), 4), dtype=np.uint8)
        
        print("self.qrect:", self.qrect)
        for point in self.points:
            point[0][0], point[0][1] = point[0][0]-self.qrect.x(), point[0][1]-self.qrect.y()
        
        print("points", self.points[0])
        cv2.drawContours(contour_numpy_pixels, [self.points], -1, self.color.getRgb(), -1)
        cv2.drawContours(contour_numpy_pixels, [self.points], 0, self.color.getRgb(), 1)
        
        self.image_pixmap = QPixmap.fromImage(QImage(contour_numpy_pixels.data, self.qrect.width(), self.qrect.height(), self.qrect.width() * 4, QImage.Format.Format_RGBA8888))
        
        
        #QRectF(int(self.x)-(self.size/2)-5, int(self.y)-(self.size/2)-5, self.size+10, self.size+10)
        
        #self.image_pixmap = QPixmap(self.size, self.size) 
        #self.image_pixmap.fill(Qt.GlobalColor.transparent)
        
        #painter = QPainter(self.image_pixmap)
        #self.pen = QPen(color, self.size)
        #self.pen.setCapStyle(Qt.PenCapStyle.RoundCap) 
        #painter.setPen(self.pen)
        #painter.drawPoint(int(self.size/2), int(self.size/2))
        #painter.end()
        
    def boundingRect(self):
        return self.qrectf
    
    def paint(self, painter, option, widget):
        pass
    
    def paint_labeling_overlay(self):
        self.labeling_overlay_painter.drawPixmap(self.qrect.x(), self.qrect.y(), self.image_pixmap) 

        

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
        self.view.point_color = self.labels[self.current_label]["color"]
        self.view.point_label = self.labels[self.current_label]["name"]
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
        image_numpy_pixels_gray = cv2.cvtColor(self.image_numpy_pixels_rgb, cv2.COLOR_RGB2GRAY)
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
        self.tolerance = Utils.load_parameters()["contour_filling"]["tolerance"]
        self.tolerance_parameters = TOLERENCE_PARAMETERS[self.tolerance]
        self.contours = self.get_contours() # It is in list of contours. A contour is a list of points (x, y). 
        if len(self.contours) == 0:
            raise ValueError("No contours found !")

        # It is more faster to do that because cv2 loop into the points of contours in c++, not python
        contour_numpy_pixels = np.zeros((self.image_qrect.height(), self.image_qrect.width(), 4), dtype=np.uint8)
        cv2.drawContours(contour_numpy_pixels, self.contours, -1, self.labels[self.current_label]["color"].darker(200).getRgb(), 1)
        self.coutour_filling_pixmap = QPixmap.fromImage(QImage(contour_numpy_pixels.data, self.image_qrect.width(), self.image_qrect.height(), self.image_qrect.width() * 4, QImage.Format.Format_RGBA8888))
        self.coutour_filling_item = self.view.zoomable_graphics_view.scene.addPixmap(self.coutour_filling_pixmap)
        self.coutour_filling_item.setZValue(2)


        
        #self.contourfillingsetting = ContourFillinApplyCancel(self.view.zoomable_graphics_view)
        #self.contourfillingsetting.show()
        print("end apply_contour")

    def find_closest_contour(self, position_x, position_y):
        for contour in self.contours:
            if cv2.pointPolygonTest(contour, (position_x, position_y), False) >= 0:
                return contour
        return None
            
    def fill_contour(self, position):
        self.color = self.labels[self.current_label]["color"]
        position_x, position_y = int(position.x()), int(position.y()) 
        closest_contour = self.find_closest_contour(position_x, position_y)
        if closest_contour is None: return # We are not cliked inside of a contour

        coutour_item = ContourItem(closest_contour, self.color, self.labeling_overlay_painter)
        self.zoomable_graphics_view.scene.addItem(coutour_item) # update is already call in this method
        coutour_item.setZValue(3) # To place in the top of the item
        self.contour_items.append(coutour_item)
        
        coutour_item.paint_labeling_overlay()
        self.update_labeling_overlay()
        
