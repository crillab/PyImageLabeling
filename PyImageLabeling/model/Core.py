
from PyQt6.QtGui import QPainter, QBitmap, QImage, QPixmap, QColor, QPainter, QBrush
from PyQt6.QtCore import Qt, QSize

from PyImageLabeling.view.QBackgroundItem import QBackgroundItem

from PIL import Image
import numpy

class Core():

    def __init__(self):
        self.labels = dict()
        
        self.current_label = None
        self.checked_button = None

        self.backgroung_item = None

        self.image_item = None
        self.image_pixmap = None

        self.numpy_pixels_rgb = None

        self.labeling_overlay_item = None
        self.labeling_overlay_pixmap = None

        self.image_qrectf = None
        self.image_qrect = None

        self.main_painter = None

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
        self.backgroung_item = QBackgroundItem(self.image_qrectf, self.controller)
        self.backgroung_item.setZValue(0) # Base layer
        self.view.zoomable_graphics_view.scene.addItem(self.backgroung_item)
        self.image_item.installSceneEventFilter(self.backgroung_item)
        
        # Compute the good value of the zoom 
        self.initialyse_zoom_factor()

        #save a numpy matrix of colors
        self.numpy_pixels_rgb = numpy.array(Image.open(path_image).convert("RGB"))
       
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
        
    def new_label(self, data_new_label):
        self.labels[data_new_label["name"]] = data_new_label
        self.set_current_label(data_new_label["name"])

        self.labeling_overlay_pixmap = QPixmap(QSize(self.image_qrect.width(), self.image_qrect.height()))
        self.labeling_overlay_pixmap.fill(Qt.GlobalColor.transparent)

        if self.labeling_overlay_item is None:
            self.labeling_overlay_item = self.view.zoomable_graphics_view.scene.addPixmap(self.labeling_overlay_pixmap)
            self.labeling_overlay_item.setZValue(2)  
        else:
            self.labeling_overlay_item.setPixmap(self.labeling_overlay_pixmap)
        
        self.main_painter = QPainter(self.labeling_overlay_pixmap)        
        self.main_painter.setPen(self.labels[self.current_label]["color"])

        
    def set_current_label(self, name):
        self.current_label = name
        print("current_label:", self.current_label)
        
    

    