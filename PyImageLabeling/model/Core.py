
from PyQt6.QtGui import QPainter, QBitmap, QImage, QPixmap, QColor, QPainter, QBrush, QPen
from PyQt6.QtCore import Qt, QSize

from view.QBackgroundItem import QBackgroundItem

from PIL import Image
import numpy
from collections import deque

from model.Utils import Utils

class Core():

    def __init__(self):
        self.labels = dict() # All labels in the form of {'label1': {'name': 'label1', 'color': <PyQt6.QtGui.QColor>, 'labeling_mode': 'Pixel-by-pixel'}, ...}
        
        self.current_label = None # The current label selected
        self.checked_button = None # The current button checked
        

        self.backgroung_item = None # The QBackgroundItem behind the images

        self.image_pixmap = None # The current pixmap of the image
        self.image_item = None # The current pixmap item of the image in the scene
        self.image_numpy_pixels_rgb = None # The current RGB numpy matrix of the image  

        self.labeling_overlay_pixmap = None # The current pixmap of labeling_overlay
        self.labeling_overlay_item = None # The current pixmap item of labeling_overlay
        self.labeling_overlay_painter = None # The painter of labeling_overlay
        self.previous_labeling_overlay_pixmap = None

        self.image_qrectf = None # Float size in QRectF
        self.image_qrect = None # Integer size in Qrect

        self.undo_deque = deque()

    def set_view(self, view):
        self.view = view
        self.zoomable_graphics_view = view.zoomable_graphics_view # short-cut

    def set_controller(self, controller):
        self.controller = controller

    def load_image(self, path_image):
        self.image_pixmap = QPixmap(path_image)
        
        # Clear some values
        self.zoomable_graphics_view.scene.clear()
        self.zoomable_graphics_view.resetTransform()
        
        # Add the image
        self.image_item = self.zoomable_graphics_view.scene.addPixmap(self.image_pixmap)
        self.image_qrectf = self.image_item.boundingRect() 
        self.image_qrect = self.image_pixmap.rect()


        self.image_item.setZValue(1) # Image layer 
        self.zoomable_graphics_view.setSceneRect(self.image_qrectf)
        self.zoomable_graphics_view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zoomable_graphics_view.centerOn(self.image_qrect.width()/2,self.image_qrect.height()/2)
        
        # Add the background item
        alpha_color = Utils.load_parameters()["load_image"]["alpha_color"] 
        self.backgroung_item = QBackgroundItem(self.image_qrectf, self.controller, alpha_color)
        self.backgroung_item.setZValue(0) # Base layer
        self.view.zoomable_graphics_view.scene.addItem(self.backgroung_item)
        self.image_item.installSceneEventFilter(self.backgroung_item)
        
        # Compute the good value of the zoom 
        self.initialyse_zoom_factor()

        #save a numpy matrix of colors
        self.image_numpy_pixels_rgb = numpy.array(Image.open(path_image).convert("RGB"))

       
        print("load_image:", self.image_pixmap)
        
    def initialyse_zoom_factor(self):
        self.view.min_zoom = self.view.zoomable_graphics_view.data_parameters["zoom"]["min_zoom"]
        self.view.max_zoom = self.view.zoomable_graphics_view.data_parameters["zoom"]["max_zoom"]

        viewport_width = self.view.zoomable_graphics_view.viewport().width()
        viewport_height = self.view.zoomable_graphics_view.viewport().height()
        diagonal_viewport = numpy.sqrt(viewport_width**2 + viewport_height**2)
        diagonal_pixmap = numpy.sqrt(self.image_qrect.width()**2 + self.image_qrect.height()**2)

        self.view.zoom_factor = diagonal_pixmap / diagonal_viewport
        if self.view.zoom_factor < self.view.min_zoom: self.view.min_zoom = self.view.zoom_factor
        self.view.max_zoom = diagonal_pixmap/self.view.max_zoom        
        self.view.initial_zoom_factor = self.view.zoom_factor

    def update_labeling_overlay(self):
        
        self.labeling_overlay_item.setPixmap(self.labeling_overlay_pixmap)
        if self.previous_labeling_overlay_pixmap is not None:
            self.undo_deque.append(self.previous_labeling_overlay_pixmap)

        self.previous_labeling_overlay_pixmap = self.labeling_overlay_pixmap.copy()


    def new_label(self, data_new_label):
        self.labels[data_new_label["name"]] = data_new_label
        self.set_current_label(data_new_label["name"])
        self.initialyse_labeling_overlay()
        
    def initialyse_labeling_overlay(self):
        self.labeling_overlay_pixmap = QPixmap(QSize(self.image_qrect.width(), self.image_qrect.height()))
        self.labeling_overlay_pixmap.fill(Qt.GlobalColor.transparent)
        self.undo_deque.append(self.labeling_overlay_pixmap.copy()) 

        if self.labeling_overlay_item is None:
            self.labeling_overlay_item = self.view.zoomable_graphics_view.scene.addPixmap(self.labeling_overlay_pixmap)
            self.labeling_overlay_item.setZValue(3)  
        else:
            self.labeling_overlay_item.setPixmap(self.labeling_overlay_pixmap)

        self.labeling_overlay_painter = QPainter(self.labeling_overlay_pixmap)        
        self.labeling_overlay_painter.setPen(QPen(self.labels[self.current_label]["color"], 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        self.labeling_overlay_painter.setBrush(self.labels[self.current_label]["color"])
        self.previous_labeling_overlay_pixmap = None
        
    def set_current_label(self, name):
        self.current_label = name
        print("current_label:", self.current_label)
        
    

    