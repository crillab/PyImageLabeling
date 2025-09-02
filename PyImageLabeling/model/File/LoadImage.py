

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtGui import QPixmap, QBitmap, QImage

from model.Core import Core
from model.Utils import Utils

import os
import numpy
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
        super().load_image(path_image)
        
        
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
            
        

    
    
