

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFileDialog, QProgressDialog
from PyQt6.QtGui import QPixmap, QBitmap, QImage

from PyImageLabeling.model.Core import Core
from PyImageLabeling.model.Utils import Utils

import os
import numpy
from skimage.color import rgb2hsv

        
class LoadImage(Core):
    def __init__(self):
        super().__init__() 

    def set_view(self, view):
        super().set_view(view)
    
    def select_image(self, path_image):
        #remove all overlays#
        #self.clear_all()
        super().select_image(path_image)
        
        
    def init_load_image(self):
        default_path = Utils.load_parameters()["load_image"]["path"]
        
        print("init_load_image")
        file_dialog = QFileDialog()
        current_file_paths, _ = file_dialog.getOpenFileNames(
            self.view, "Open Image", default_path, "Images (*.png *.xpm *.jpg *.jpeg *.bmp *.gif)"
        )
        if len(current_file_paths) == 0: return

        
        self.view.file_bar_add(current_file_paths)
        print("end")      
        
        data = Utils.load_parameters()
        data["load_image"]["path"] = os.path.dirname(current_file_paths[0])
        Utils.save_parameters(data)

        #if not valid_images:
        #    print("Warning: Could not load any of the selected images.")
        #    return
        
        # Activate previous and next buttons
        for button_name in self.view.buttons_file_bar:
            if 'previous' in button_name or 'next' in button_name:
                self.view.buttons_file_bar[button_name].setEnabled(True)

        # Select the first item in the list if we have some images and no image selected
        if self.view.file_bar_list.count() > 0 and self.view.file_bar_list.currentRow() == -1:
            self.view.file_bar_list.setCurrentRow(0) 
            
        

    
    
