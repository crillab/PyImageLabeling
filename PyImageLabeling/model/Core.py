
from PyQt6.QtGui import QPainter, QBitmap, QImage, QPixmap, QColor, QPainter, QBrush, QPen
from PyQt6.QtCore import Qt, QSize

from PyImageLabeling.view.QBackgroundItem import QBackgroundItem

from PIL import Image
import numpy
from collections import deque

from PyImageLabeling.model.Utils import Utils


class LabelingOverlay():
    ###
    # A LabelingOverlay is composed of a QPixmap, a QGraphicItem, a QPainter and a previous QPixmap
    ###


    def __init__(self, label_id, scene, width, height, name, labeling_mode, color):
        self.label_id = label_id
        self.scene = scene # The associated QGraphicScene of the QGraphicsView
        self.width = width # The width of the Labeling Overlay QPixmap 
        self.height = height # The height of the Labeling Overlay QPixmap
        self.zvalue = 3 # The default ZValue 
        self.opacity = Utils.load_parameters()["labeling_opacity"]/100 # To normalize

        self.name = name
        self.labeling_mode = labeling_mode
        self.color = QColor(color) # The color of labels in the Labeling Overlay
        # Note: The color is in RGB, the alpha is set at only the end for the view part :)
       
        # Initialize the QPixmap
        self.labeling_overlay_pixmap = QPixmap(QSize(self.width, self.height))
        self.labeling_overlay_pixmap.fill(Qt.GlobalColor.transparent)
        
        # Initialize the deque for the `undo` feature
        self.undo_deque = deque()
        self.undo_deque.append(self.labeling_overlay_pixmap.copy()) 
        
        # Initialize the QGraphicItem
        self.labeling_overlay_item = self.scene.addPixmap(self.labeling_overlay_pixmap)
        self.labeling_overlay_item.setZValue(self.zvalue)  

        # Initialize the associated QPainter
        self.labeling_overlay_painter = QPainter(self.labeling_overlay_pixmap)      
        self.reset_pen()

        # Initialize the previous pixmap for the `undo` feature
        self.previous_labeling_overlay_pixmap = None

        # Initialize others pixmaps and painters to change the color or opacity operations
        self.labeling_overlay_opacity_pixmap = QPixmap(self.width, self.height)
        self.labeling_overlay_opacity_painter = QPainter(self.labeling_overlay_opacity_pixmap)
        
        self.labeling_overlay_color_pixmap = QPixmap(self.width, self.height)
        self.labeling_overlay_color_painter = QPainter()
        
        
    def change_visible(self):
        if self.labeling_overlay_item.isVisible() is True:
            self.labeling_overlay_item.setVisible(False)
        else:
            self.labeling_overlay_item.setVisible(True)

    def reset(self):
        #self.labeling_overlay_painter.end()

        self.labeling_overlay_pixmap.fill(Qt.GlobalColor.transparent)
        self.labeling_overlay_item.setPixmap(self.labeling_overlay_pixmap)
        
        self.undo_deque.clear()
        self.previous_labeling_overlay_pixmap = None

    def remove(self):
        self.scene.removeItem(self.labeling_overlay_item)
        self.labeling_overlay_painter.end()
        self.labeling_overlay_opacity_painter.end()
        

        
    def set_opacity(self, opacity):
        self.opacity = opacity

        # Change and update the QPixmap 
        self.labeling_overlay_item.setPixmap(self.generate_opacity_pixmap())
        

    def get_opacity(self):
        return self.opacity
        
    def undo(self):
        if len(self.undo_deque) > 0:
            self.labeling_overlay_painter.end()
            
            self.labeling_overlay_pixmap = self.undo_deque.pop()
            self.previous_labeling_overlay_pixmap = self.labeling_overlay_pixmap.copy()

            if len(self.undo_deque) == 0:
                self.undo_deque.append(self.labeling_overlay_pixmap.copy())
            
            # Create a new pixmap for opacity

            self.labeling_overlay_item.setPixmap(self.generate_opacity_pixmap())
            self.labeling_overlay_painter.begin(self.labeling_overlay_pixmap)
            self.reset_pen()

    def generate_opacity_pixmap(self):
        self.labeling_overlay_opacity_pixmap.fill(Qt.GlobalColor.transparent)
        self.labeling_overlay_opacity_painter.setOpacity(self.get_opacity())
        self.labeling_overlay_opacity_painter.drawPixmap(0, 0, self.labeling_overlay_pixmap)
        return self.labeling_overlay_opacity_pixmap

    def update_color(self):
        # Apply Color
        self.labeling_overlay_color_pixmap.fill(self.color)
        self.labeling_overlay_painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        self.labeling_overlay_painter.drawPixmap(0, 0, self.labeling_overlay_color_pixmap)
        self.labeling_overlay_painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        
        # Update
        self.labeling_overlay_item.setPixmap(self.generate_opacity_pixmap())

        # Apply the color on the undo pixmaps
        for pixmap in self.undo_deque:
            self.labeling_overlay_color_painter.begin(pixmap)
            self.labeling_overlay_color_painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            self.labeling_overlay_color_painter.drawPixmap(0, 0, self.labeling_overlay_color_pixmap)
            self.labeling_overlay_color_painter.end()

        # do not forget the previous undo pixmap :) 
        if self.previous_labeling_overlay_pixmap is not None:
            self.labeling_overlay_color_painter.begin(self.previous_labeling_overlay_pixmap)
            self.labeling_overlay_color_painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            self.labeling_overlay_color_painter.drawPixmap(0, 0, self.labeling_overlay_color_pixmap)
            self.labeling_overlay_color_painter.end()

        
    def update(self):
        # Change and update the QPixmap 
        self.labeling_overlay_item.setPixmap(self.generate_opacity_pixmap()) 
        
        # For the `undo` feature, if we have a previous, add it in the deque 
        if self.previous_labeling_overlay_pixmap is not None:
            self.undo_deque.append(self.previous_labeling_overlay_pixmap)

        # Create a copy to keep it in the previous pixmap variable
        self.previous_labeling_overlay_pixmap = self.labeling_overlay_pixmap.copy()

    def get_color(self):
        return self.color
    
    def set_color(self, color):
        self.color = color

    def get_name(self):
        return self.name
    
    def set_name(self, name):
        self.name = name

    def get_labeling_mode(self):
        return self.labeling_mode
    
    def set_labeling_mode(self, labeling_mode):
        self.labeling_mode = labeling_mode

    def get_label_id(self):
        return self.label_id
    
    def get_painter(self):
        return self.labeling_overlay_painter

    def set_zvalue(self, zvalue):
        self.zvalue = zvalue
        self.labeling_overlay_item.setZValue(self.zvalue)

    def reset_pen(self):
        self.labeling_overlay_painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        self.labeling_overlay_painter.setPen(QPen(self.color, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        self.labeling_overlay_painter.setBrush(self.color)
        


class Core():
    static_label_id = 0

    def __init__(self):
        
        #self.labels = dict() # All labels in the form of {'label1': {'name': 'label1', 'color': <PyQt6.QtGui.QColor>, 'labeling_mode': 'Pixel-by-pixel'}, ...}
        
        self.current_label_id = None # The current label id selected
        self.checked_button = None # The current button checked => usefull to know the labelinf tool to use
        

        self.backgroung_item = None # The QBackgroundItem behind the images

        self.image_pixmap = None # The current pixmap of the image
        self.image_item = None # The current pixmap item of the image in the scene
        self.image_numpy_pixels_rgb = None # The current RGB numpy matrix of the image  

        self.labeling_overlays = dict() # dict of LabelingOverlay instance 

        self.current_labeling_overlay = None # The current selected LabelingOverlay

        self.image_qrectf = None # Float size in QRectF
        self.image_qrect = None # Integer size in Qrect

        self.undo_deque = deque()

    def get_static_label_id(self):
        return Core.static_label_id

    def new_label_id(self):
        value = Core.static_label_id
        Core.static_label_id+=1
        return value

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

    # Add a new labeling overlay 
    def new_labeling_overlay(self, label_id, name, labeling_mode, color):
        self.current_labeling_overlay = LabelingOverlay(label_id,
                                                        self.view.zoomable_graphics_view.scene, 
                                                        self.image_qrect.width(), 
                                                        self.image_qrect.height(),
                                                        name,
                                                        labeling_mode, 
                                                        color)
        
        # Add the data of this new label in the label dictionnary
        self.labeling_overlays[label_id] = self.current_labeling_overlay

        # Set the current label
        self.current_label_id = label_id
        
        # Put at the first plan the current label
        self.foreground_current_labeling_overlay()

    # Change the current labeling overlay
    def select_labeling_overlay(self, label_id):
        self.current_label_id = label_id

        self.current_labeling_overlay = self.labeling_overlays[label_id]
        self.current_labeling_overlay.labeling_overlay_item.setVisible(True)
        self.foreground_current_labeling_overlay()

    def n_labeling_overlays(self):
        return len(self.labeling_overlays)
    
    def get_labeling_overlay(self):
        return self.current_labeling_overlay
    
    def name_already_in_labels(self, name):
        for id in self.labeling_overlays:
            if self.labeling_overlays[id].get_name() == name:
                return True
        return False 


    # Update the current labeling overlay 
    def update_labeling_overlay(self):
        self.current_labeling_overlay.update()

    # Put at the foreground the current labeling overlay 
    def foreground_current_labeling_overlay(self):        
        for label_id in self.labeling_overlays:
            if label_id == self.current_label_id:
                self.labeling_overlays[label_id].set_zvalue(3)
            else:
                self.labeling_overlays[label_id].set_zvalue(2)
        self.view.zoomable_graphics_view.scene.update()

    # Return QPixmap of all labeling overlay except the current one in a ordered list. 
    def get_labeling_overlay_pixmaps(self):
        if self.n_labeling_overlays() == 1:
            return []
        result = [labeling_overlay for labeling_overlay in self.labeling_overlays.values() if labeling_overlay != self.current_labeling_overlay]
        result.sort(key=lambda x: x.label_id)
        return [element.labeling_overlay_pixmap for element in result]
        
    def set_opacity(self, opacity):
        for labeling_overlay in self.labeling_overlays.values():
            labeling_overlay.set_opacity(opacity)
            

    