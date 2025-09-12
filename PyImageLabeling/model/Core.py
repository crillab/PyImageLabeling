
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

    def __init__(self, label, scene, width, height):
        self.label = label
        
        self.scene = scene # The associated QGraphicScene of the QGraphicsView
        self.width = width # The width of the Labeling Overlay QPixmap 
        self.height = height # The height of the Labeling Overlay QPixmap
        self.zvalue = 3 # The default ZValue 
        self.opacity = Utils.load_parameters()["labeling_opacity"]/100 # To normalize

        #self.label_id = label_id
        #self.name = name
        #self.labeling_mode = labeling_mode
        #self.color = QColor(color) # The color of labels in the Labeling Overlay
        # Note: The color is in RGB, the alpha is set at only the end for the view part :)
       
        # Initialize the QPixmap
        self.labeling_overlay_pixmap = QPixmap(QSize(self.width, self.height))
        self.labeling_overlay_pixmap.fill(Qt.GlobalColor.transparent)
        self.labeling_overlay_item = None

        # Initialize the deque for the `undo` feature
        self.undo_deque = deque()
        self.undo_deque.append(self.labeling_overlay_pixmap.copy()) 
        
        # Initialize the associated QPainter
        self.labeling_overlay_painter = QPainter(self.labeling_overlay_pixmap)      
        self.reset_pen()

        # Initialize the previous pixmap for the `undo` feature
        self.previous_labeling_overlay_pixmap = None

        # Initialize others pixmaps and painters to change the color or opacity operations
        self.labeling_overlay_opacity_pixmap = QPixmap(self.width, self.height)
        self.labeling_overlay_opacity_painter = QPainter()
        
        self.labeling_overlay_color_pixmap = QPixmap(self.width, self.height)
        self.labeling_overlay_color_painter = QPainter()

        self.is_displayed_in_scene = False
        
    def update_scene(self):
        if self.is_displayed_in_scene is False:
            self.labeling_overlay_item = self.scene.addPixmap(self.generate_opacity_pixmap())
            self.labeling_overlay_item.setZValue(self.zvalue)
            self.is_displayed_in_scene = True
        
        self.labeling_overlay_item.setVisible(self.label.get_visible())

    #def change_visible(self):
    #    if self.labeling_overlay_item.isVisible() is True:
    #        self.labeling_overlay_item.setVisible(False)
    #    else:
    #        self.labeling_overlay_item.setVisible(True)

    def reset(self):
        #self.labeling_overlay_painter.end()

        self.labeling_overlay_pixmap.fill(Qt.GlobalColor.transparent)
        if self.is_displayed_in_scene is True:
            self.labeling_overlay_item.setPixmap(self.labeling_overlay_pixmap)
        
        first_labeling_overlay_pixmap = self.undo_deque[0].copy()
        self.undo_deque.clear()
        self.undo_deque.append(first_labeling_overlay_pixmap)

        self.previous_labeling_overlay_pixmap = None
        
    def remove(self):
        if self.is_displayed_in_scene is True:
            self.scene.removeItem(self.labeling_overlay_item)
            self.labeling_overlay_item = None
        
        self.labeling_overlay_painter.end()
        
    def set_opacity(self, opacity):
        self.opacity = opacity

        # Change and update the QPixmap 
        if self.is_displayed_in_scene is True:
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
        # Now we can fill the pixmap
        self.labeling_overlay_opacity_pixmap.fill(Qt.GlobalColor.transparent)
        
        # Restart the painter
        self.labeling_overlay_opacity_painter.begin(self.labeling_overlay_opacity_pixmap)
        self.labeling_overlay_opacity_painter.setOpacity(self.get_opacity())
        self.labeling_overlay_opacity_painter.drawPixmap(0, 0, self.labeling_overlay_pixmap)
        self.labeling_overlay_opacity_painter.end()

        return self.labeling_overlay_opacity_pixmap

    def update_color(self):
        # Apply Color
        self.labeling_overlay_color_pixmap.fill(self.label.get_color())
        self.labeling_overlay_painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        self.labeling_overlay_painter.drawPixmap(0, 0, self.labeling_overlay_color_pixmap)
        self.labeling_overlay_painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        
        # Update
        if self.is_displayed_in_scene is True:
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

    #def get_color(self):
    #     return self.color
    
    #def set_color(self, color):
    #     self.color = color

    #def get_name(self):
    #    return self.name
    
    # def set_name(self, name):
    #     self.name = name

    # def get_labeling_mode(self):
    #     return self.labeling_mode
    
    # def set_labeling_mode(self, labeling_mode):
    #     self.labeling_mode = labeling_mode

    # def get_label_id(self):
    #     return self.label_id
    
    def get_painter(self):
        return self.labeling_overlay_painter

    def set_zvalue(self, zvalue):
        self.zvalue = zvalue
        print("esss:", zvalue)
        self.labeling_overlay_item.setZValue(self.zvalue)

    def reset_pen(self):
        self.labeling_overlay_painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        self.labeling_overlay_painter.setPen(QPen(self.label.color, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        self.labeling_overlay_painter.setBrush(self.label.color)
    
    def set_is_displayed_in_scene(self, is_displayed_in_scene):
        self.is_displayed_in_scene = is_displayed_in_scene

    def set_visible(self, is_visible):
        if self.labeling_overlay_item is not None:
            self.labeling_overlay_item.setVisible(is_visible)

class ImageItem():

    def __init__(self, view, controller, path_image, icon_button):
        self.view = view
        self.controller = controller
        self.path_image = path_image
        self.icon_button = icon_button
        
        self.zoomable_graphics_view = view.zoomable_graphics_view

        self.image_pixmap = QPixmap(path_image) # The current pixmap of the image
        self.image_item = None # The current pixmap item of the image in the scene
        self.image_numpy_pixels_rgb = None # The current RGB numpy matrix of the image  

        self.backgroung_item = None # The QBackgroundItem behind the images

        self.labeling_overlays = dict() # dict of LabelingOverlay instance 

        self.current_labeling_overlay = None # The current selected LabelingOverlay

        self.image_qrect = self.image_pixmap.rect() # Integer size in Qrect
        self.image_qrectf = self.image_qrect.toRectF() # Float size in QRectF
        
        # the background item
        self.alpha_color = Utils.load_parameters()["load_image"]["alpha_color"] 
        
        #save a numpy matrix of colors
        self.image_numpy_pixels_rgb = numpy.array(Image.open(path_image).convert("RGB"))

        self.is_displayed_in_scene = False

        self.is_edited = False

    def get_edited(self):
        return self.is_edited

    def set_edited(self, is_edited):
        self.is_edited = is_edited

    def get_image_pixmap(self):
        return self.image_pixmap
    
    def get_qrectf(self):
        return self.image_qrectf
    
    def get_labeling_overlays(self):
        return list(self.labeling_overlays.values())
    
    def update_scene(self):
        if self.is_displayed_in_scene is False:
            # Add the backgroung_item in the scene
            self.backgroung_item = QBackgroundItem(self.image_qrectf, self.controller, self.alpha_color)
            self.view.zoomable_graphics_view.scene.addItem(self.backgroung_item)
            self.backgroung_item.setZValue(0) # Base layer
            
            # Add the image in the scene
            self.image_item = self.zoomable_graphics_view.scene.addPixmap(self.image_pixmap)
            self.image_item.setZValue(1) # Image layer 
            
            # Set the Event listener in the background item to the image item 
            self.image_item.installSceneEventFilter(self.backgroung_item)

            # Set the good visual parameters for the scene
            self.zoomable_graphics_view.setSceneRect(self.image_qrectf)
            self.zoomable_graphics_view.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.zoomable_graphics_view.centerOn(self.image_qrect.width()/2,self.image_qrect.height()/2)

            self.initialyse_zoom_factor()
            self.is_displayed_in_scene = True
            # for label_id in self.labeling_overlays:
            #     self.labeling_overlays[label_id].update_scene()
                
            #     # Apply the label's visibility state using existing change_visible logic
            #     if label_id in self.controller.model.get_label_items():
            #         label_item = self.controller.model.get_label_items()[label_id]
            #         overlay = self.labeling_overlays[label_id]
                    
            #         # Only change if current visibility doesn't match desired state
            #         if overlay.labeling_overlay_item.isVisible() != label_item.get_visible():
            #             overlay.change_visible()
        
        # Update the labeling overlays
        for label_id in self.labeling_overlays:
            self.labeling_overlays[label_id].update_scene()
        
        print("update scene")

    def clear_scene(self):
        self.is_displayed_in_scene = False
        for label_id in self.labeling_overlays:
            self.labeling_overlays[label_id].set_is_displayed_in_scene(False)
       
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

    def update_labeling_overlays(self, label_items, selected_label_id):
        # Ensure all existing labels have an overlay
        for label_id in label_items:
            if label_id not in self.labeling_overlays:
                self.labeling_overlays[label_id] = LabelingOverlay(
                    label_items[label_id],
                    self.view.zoomable_graphics_view.scene,
                    self.image_qrect.width(),
                    self.image_qrect.height()
                )

        self.current_labeling_overlay = self.labeling_overlays[selected_label_id]
        self.current_label_id = selected_label_id
    
    def foreground_current_labeling_overlay(self):        
        for label_id in self.labeling_overlays:
            if label_id == self.current_label_id:
                self.labeling_overlays[label_id].set_zvalue(3)
            else:
                self.labeling_overlays[label_id].set_zvalue(2)
        # Force the visibility 
        # self.current_labeling_overlay.labeling_overlay_item.setVisible(True)
        # print("update_labeling_overlays end")
        
       

    # def new_labeling_overlay(self, label_id, name, labeling_mode, color):
    #     # Add a new labeling overlay 
    #     self.current_labeling_overlay = 
        
    #     # Add the data of this new label in the label dictionnary
    #     self.labeling_overlays[label_id] = self.current_labeling_overlay

    #     # Set the current label
    #     self.current_label_id = label_id
        
    #     # Put at the first plan the current label
    #     self.foreground_current_labeling_overlay()

    # # Change the current labeling overlay
    # def select_labeling_overlay(self, label_id):
    #     self.current_label_id = label_id

    #     self.current_labeling_overlay = self.labeling_overlays[label_id]
    #     self.current_labeling_overlay.labeling_overlay_item.setVisible(True)
    #     self.foreground_current_labeling_overlay()

    def n_labeling_overlays(self):
        return len(self.labeling_overlays)
    
    def get_labeling_overlay(self):
        return self.current_labeling_overlay

    # Update the current labeling overlay 
    def update_labeling_overlay(self):
        self.current_labeling_overlay.update()
        if self.get_edited() is False:
            self.set_edited(True)
            self.icon_button.setPixmap(self.view.icon_asterisk_red)
    # # Put at the foreground the current labeling overlay 
    # def foreground_current_labeling_overlay(self):        
    #     for label_id in self.labeling_overlays:
    #         if label_id == self.current_label_id:
    #             self.labeling_overlays[label_id].set_zvalue(3)
    #         else:
    #             self.labeling_overlays[label_id].set_zvalue(2)
    #     self.view.zoomable_graphics_view.scene.update()

    # Return QPixmap of all labeling overlay except the current one in a ordered list. 
    def get_labeling_overlay_pixmaps(self):
        if self.n_labeling_overlays() == 1:
            return []
        result = [labeling_overlay for labeling_overlay in self.labeling_overlays.values() if labeling_overlay != self.current_labeling_overlay]
        result.sort(key=lambda x: x.label.get_label_id())
        return [element.labeling_overlay_pixmap for element in result]
        
    def set_opacity(self, opacity):
        for labeling_overlay in self.labeling_overlays.values():
            labeling_overlay.set_opacity(opacity)
    
    def update_color(self, label_id):
        self.labeling_overlays[label_id].update_color()

    def get_image_numpy_pixels_rgb(self):
        return self.image_numpy_pixels_rgb
    
    def get_width(self):
        return self.image_qrect.width()

    def get_height(self):
        return self.image_qrect.height()
    
class LabelItem():

    static_label_id = 0

    def __init__(self, name, labeling_mode, color):
        self.label_id = LabelItem.static_label_id
        self.name = name
        self.labeling_mode = labeling_mode
        self.color = QColor(color) # The color of labels in the Labeling Overlay
        self.is_visible = True 
        LabelItem.static_label_id +=1 

    def get_label_id(self):
        return self.label_id
    
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

    def set_visible(self, is_visible):
        self.is_visible = is_visible
    
    def get_visible(self):
        return self.is_visible
    
class Core():

    def __init__(self):
        
        #self.labels = dict() # All labels in the form of {'label1': {'name': 'label1', 'color': <PyQt6.QtGui.QColor>, 'labeling_mode': 'Pixel-by-pixel'}, ...}
        
        self.checked_button = None # The current button checked => usefull to know the labelinf tool to use
        
        self.file_paths = [] # List of file paths of images (in the good order)

        self.image_items = dict() # Dictionnary: (key: file_path) -> (value: ImageItem or None)
        self.label_items = dict() # Dictionnary: (key: label_id) -> (value: LabelItem)
        
        self.current_label_item = None # The current label selected
        self.current_image_item = None # The current ImageItem that is display 

        self.icon_button_files = dict()

    def get_label_items(self):
        return self.label_items
    
    def get_image_items(self):
        return self.image_items
    
    def get_current_label_item(self):
        return self.current_label_item
    
    def set_current_label_item(self, current_label_item):
        self.current_label_item = current_label_item
    
    def get_current_image_item(self):
        return self.current_image_item
    
    def get_current_labeling_overlay(self, label_id):
        return self.current_image_item.labeling_overlays[label_id]
    
    def get_static_label_id(self):
        return LabelItem.static_label_id
    
    def set_view(self, view):
        self.view = view
        self.zoomable_graphics_view = view.zoomable_graphics_view # short-cut

    def set_controller(self, controller):
        self.controller = controller

    def set_opacity(self, opacity):
        for file in self.file_paths:
            if self.image_items[file] is not None:
                self.image_items[file].set_opacity(opacity)

    def update_color(self, label_id):
        for file in self.file_paths:
            if self.image_items[file] is not None:
                self.image_items[file].update_color(label_id)

    def name_already_exists(self, name):
        for label_id, label_item in self.label_items.items():
            if label_item.get_name() == name:
                return True
        return False
    
    def new_label(self, name, labeling_mode, color):
        label = LabelItem(name, labeling_mode, color)
        self.label_items[label.get_label_id()] = label
        return label

    def update_labeling_overlays(self, selected_label_id):
        print("update_labeling_overlays")
        for file in self.file_paths:
            if self.image_items[file] is not None:
                print("for file:", file)
                self.image_items[file].update_labeling_overlays(self.label_items, selected_label_id)
        self.current_label_item = self.label_items[selected_label_id]

        self.current_image_item.update_scene()
        self.current_image_item.foreground_current_labeling_overlay()

    def select_image(self, path_image):
        print("select_image")
        if self.checked_button == "contour_filling":
            self.remove_contour()

        self.zoomable_graphics_view.scene.clear()
        self.zoomable_graphics_view.resetTransform()
        for file in self.file_paths:
            if self.image_items[file] is not None:
                self.image_items[file].clear_scene()

        if self.image_items[path_image] is None:
            print("select_image new")
            # We have to load image and theses labels
            self.image_items[path_image] = ImageItem(self.view, self.controller, path_image, self.icon_button_files[path_image])
            self.current_image_item = self.image_items[path_image]
            self.image_items[path_image].update_scene()
            if len(self.label_items) != 0:
                self.image_items[path_image].update_labeling_overlays(self.label_items, self.current_label_item.get_label_id())
        else:
            print("select_image already exists")
            # Image and these labels are already loaded, display it 
            self.image_items[path_image].update_scene()
            self.current_image_item = self.image_items[path_image]

        if self.checked_button == "contour_filling":
            self.apply_contour()

        
            
    