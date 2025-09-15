

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFileDialog, QProgressDialog
from PyQt6.QtGui import QPixmap, QBitmap, QImage

from model.Core import Core, KEYWORD_SAVE_LABEL
from model.Utils import Utils


import os
import numpy
from skimage.color import rgb2hsv

        
class Files(Core):
    def __init__(self):
        super().__init__() 

    def set_view(self, view):
        super().set_view(view)
    
    def select_image(self, path_image):
        #remove all overlays#
        #self.clear_all()
        super().select_image(path_image)
        
    def save(self):
        print("save")
        if self.save_directory == "":
            # Open a directory        
            default_path = Utils.load_parameters()["save"]["path"]
            
            file_dialog = QFileDialog()
            current_file_path = file_dialog.getExistingDirectory(
                parent=self.view, 
                caption="Save Folder", 
                directory=default_path)
            
            if len(current_file_path) == 0: return

            data = Utils.load_parameters()
            data["save"]["path"] = current_file_path
            Utils.save_parameters(data)
            self.save_directory = current_file_path

        super().save()

    def load(self):
        print("load")
        default_path = Utils.load_parameters()["load"]["path"]
        
        file_dialog = QFileDialog()
        current_file_path = file_dialog.getExistingDirectory(
                parent=self.view, 
                caption="Open Folder", 
                directory=default_path)
        
        if len(current_file_path) == 0: return
        current_file_path = current_file_path + os.sep
        data = Utils.load_parameters()
        data["load"]["path"] = os.path.dirname(current_file_path)
        Utils.save_parameters(data)

        # Update the model with the good images
        # The model variables is update in this method: file_paths and image_items
        print("current_file_path:", current_file_path)
        current_files = [current_file_path+os.sep+f for f in os.listdir(current_file_path)]
        current_files_to_add = []
        print("current_files:", current_files)
        labels_json = None
        labels_images = []
        for file in current_files:
            print("file:", file)
            if file in self.file_paths:
                continue
            if file.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
                if KEYWORD_SAVE_LABEL in file:
                    # It is a label file  
                    labels_images.append(file)
                else:
                    # It is a image 
                    print("file2:", file)
                    self.file_paths.append(file)
                    self.image_items[file] = None
                    current_files_to_add.append(file)
            elif file.endswith("labels.json"):
                labels_json = file # Load it later 
        self.view.file_bar_add(current_files_to_add)

        # Activate previous and next buttons
        for button_name in self.view.buttons_file_bar:
            self.view.buttons_file_bar[button_name].setEnabled(True)

        # Select the first item in the list if we have some images and no image selected
        if self.view.file_bar_list.count() > 0 and self.view.file_bar_list.currentRow() == -1:
            self.view.file_bar_list.setCurrentRow(0) 

        if labels_images is not None:
            for label in labels_images:
                self.load_labels_images(file)

        #Load the labels only when all images and selection are initalize
        if labels_json is not None:
            self.load_labels_json(labels_json)


            
            


    
