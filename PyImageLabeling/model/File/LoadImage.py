

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtGui import QPixmap

from PyImageLabeling.model.Core import Core
from PyImageLabeling.view.QBackgroundItem import QBackgroundItem
from PyImageLabeling.model.Utils import Utils

import os
import numpy
from PIL import Image
from skimage.color import rgb2hsv

        
class LoadImage(Core):
    def __init__(self):
        super().__init__() 
        self.loaded_image_paths = []

    def set_view(self, view):
        super().set_view(view)
    
    def load_image(self, path_image):
        #remove all overlays#
        self.clear_all()

        pixmap = QPixmap(path_image)

        #save a numpy matrix of colors
        self.numpy_pixels_rgb = numpy.array(Image.open(path_image).convert("RGB"))
        #print("self.numpy_pixels_rgb:", self.numpy_pixels_rgb[0,0])
        #self.numpy_pixels_hsv = matplotlib.colors.rgb_to_hsv(numpy.divide(self.numpy_pixels_rgb, 255))
        #self.numpy_pixels_hsv = numpy.multiply(rgb2hsv(numpy.array(Image.open(path_image).convert("RGB"))), 255)
        
        #print("self.numpy_pixels_hsv:", self.numpy_pixels_hsv[0,0])

        print("load_image:", pixmap)
        # Load the image
        self.zoomable_graphics_view.scene.clear()
        self.zoomable_graphics_view.resetTransform()
        
        # Add the image
        self.image_pixmap_item = self.zoomable_graphics_view.scene.addPixmap(pixmap)
        self.image_size = self.image_pixmap_item.boundingRect() 
        self.image_pixmap_item.setZValue(1) # Image layer 
        self.zoomable_graphics_view.setSceneRect(self.image_size)
        self.zoomable_graphics_view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zoomable_graphics_view.centerOn(self.image_size.width()/2,self.image_size.height()/2)
        
        # Add the background item
        self.view.event_eater_item = QBackgroundItem(self.image_size, self.controller)
        self.view.event_eater_item.setZValue(0) # Base layer
        self.view.zoomable_graphics_view.scene.addItem(self.view.event_eater_item)
        self.image_pixmap_item.installSceneEventFilter(self.view.event_eater_item)
        
        # Compute the good value of the zoom 
        self.initialyse_zoom_factor()

        print("self.view.zoom_factor:", self.view.zoom_factor)
        print("self.view.event_eater_item:", self.view.event_eater_item)
       
        print("sceneRect() 1:", self.zoomable_graphics_view.sceneRect() )
        print("sceneRect() 2:", self.zoomable_graphics_view.scene.itemsBoundingRect())
        
        self.image_pixmap = pixmap
        
    def init_load_image(self):
        default_path = Utils.load_parameters()["load_image"]["path"]
        
        print("init_load_image")
        file_dialog = QFileDialog()
        file_paths, _ = file_dialog.getOpenFileNames(
            self.view, "Open Image", default_path, "Images (*.png *.xpm *.jpg *.jpeg *.bmp *.gif)"
        )
        if file_paths == "": return
        
        valid_images = []
        for file_path in file_paths:
            image = QPixmap(file_path)
            if image.isNull():
                print(f"Warning: Could not load image {file_path}")
            elif file_path not in self.loaded_image_paths:
                valid_images.append(file_path)
                filename = os.path.basename(file_path)
                self.view.add_file_to_list(filename, self.loaded_image_paths)
                self.loaded_image_paths.append(file_path)
                default_path = os.path.dirname(file_path)
        
        data = Utils.load_parameters()
        data["load_image"]["path"] = default_path
        Utils.save_parameters(data)

        if not valid_images:
            print("Warning: Could not load any of the selected images.")
            return
        
        # Activate previous and next buttons
        for button_name in self.view.buttons_file_bar:
            if 'previous' in button_name or 'next' in button_name:
                self.view.buttons_file_bar[button_name].setEnabled(True)

        # Select the first item in the list if we have some images and no image selected
        if self.view.file_bar_list.count() > 0 and self.view.file_bar_list.currentRow() == -1:
            self.view.file_bar_list.setCurrentRow(0) 
            
        

    
    
