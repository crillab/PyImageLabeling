

from PyImageLabeling.model.Core import Core
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtGui import QPixmap

import os
import numpy

import matplotlib
from PIL import Image

from PyImageLabeling.view.QBackgroundItem import QBackgroundItem
from skimage.color import rgb2hsv
        
class LoadImage(Core):
    def __init__(self):
        super().__init__() 
        self.loaded_image_paths = []

    def set_view(self, view):
        super().set_view(view)
    
    def load_image(self, path_image):
        #remove all overlays#
        #self.clear_all()

        pixmap = QPixmap(path_image)

        #save a numpy matrix of colors
        self.numpy_pixels_rgb = numpy.array(Image.open(path_image).convert("RGB"))
        #print("self.numpy_pixels_rgb:", self.numpy_pixels_rgb[0,0])
        #self.numpy_pixels_hsv = matplotlib.colors.rgb_to_hsv(numpy.divide(self.numpy_pixels_rgb, 255))
        #self.numpy_pixels_hsv = numpy.multiply(rgb2hsv(numpy.array(Image.open(path_image).convert("RGB"))), 255)
        
        #print("self.numpy_pixels_hsv:", self.numpy_pixels_hsv[0,0])

        print("load_image:", pixmap)
        #load the image
        self.zoomable_graphics_view.scene.clear()
        self.clear_all()

        
        
        #Add the image
        self.image_pixmap_item = self.zoomable_graphics_view.scene.addPixmap(pixmap)
        self.qrect_size = self.image_pixmap_item.boundingRect() 
        self.image_pixmap_item.setZValue(1)  # Base layer
        self.zoomable_graphics_view.setSceneRect(self.qrect_size)
        #self.zoomable_graphics_view.fitInView(self.image_pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
        self.zoomable_graphics_view.setAlignment(Qt.AlignmentFlag.AlignCenter)

        

        #Add the background item
        self.view.event_eater_item = QBackgroundItem(self.qrect_size, self.controller)
        self.view.event_eater_item.setZValue(0)
        self.view.zoomable_graphics_view.scene.addItem(self.view.event_eater_item)
        self.image_pixmap_item.installSceneEventFilter(self.view.event_eater_item)
        
        
        print("self.view.event_eater_item:", self.view.event_eater_item)
       
        print("sceneRect() 1:", self.zoomable_graphics_view.sceneRect() )
        print("sceneRect() 2:", self.zoomable_graphics_view.scene.itemsBoundingRect())
        
        self.image_pixmap = pixmap
        
    def init_load_image(self):
        print("init_load_image")
        file_dialog = QFileDialog()
        file_paths, _ = file_dialog.getOpenFileNames(
            self.view, "Open Image", "", "Images (*.png *.xpm *.jpg *.jpeg *.bmp *.gif)"
        )
        if file_paths == "": return
        
        valid_images = []
        for file_path in file_paths:
            image = QPixmap(file_path)
            if not image.isNull() and file_path not in self.loaded_image_paths:
                valid_images.append(file_path)
                filename = os.path.basename(file_path)
                self.view.file_bar_list.addItem(self.view.add_file_to_list(filename, self.loaded_image_paths))
                self.loaded_image_paths.append(file_path)
            else:
                print(f"Warning: Could not load image {file_path}")
        
        if not valid_images:
            print("Load Images", "Could not load any of the selected images.")
            return
        
        # Load the first valid image
        #self.load_image(valid_images[0])

        for button_name in self.view.buttons_file_bar:
            if 'previous' in button_name or 'next' in button_name:
                self.view.buttons_file_bar[button_name].setEnabled(True)

        # Select the first item in the list
        if self.view.file_bar_list.count() > 0:
            self.view.file_bar_list.setCurrentRow(0) 
            #self.view.select_image()

            # Check all possible button names for previous/next
            
        #self.zoomable_graphics_view.setSceneRect(self.pixmap_item.boundingRect())
        # Resize tthe 
        
        #self.zoomable_graphics_view.fitInView(self.pixmap_item.boundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
        
        
        # Reset view
        #self.setSceneRect(self.pixmap_item.boundingRect())
        #
        #self.zoom_factor = 1.0
        
        # Reset transformations
        #self.resetTransform()

        #self.image_label.setBasePixmap(pixmap)
        #self.image_label.reset_view()
        #self.activate_move_mode(True)

    
    
