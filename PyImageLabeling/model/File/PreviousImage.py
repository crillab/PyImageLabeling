
from model.Core import Core
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtGui import QPixmap
import os

class PreviousImage(Core):
    def __init__(self):
        super().__init__()

    def previous_image(self):
        current_row = self.view.file_bar_list.currentRow()
        total_images = len(self.loaded_image_paths)
        if  total_images ==1:
            pass
        else:
            # Calculate next row (with wrap-around)
            if current_row == -1:  # No selection
                next_row = total_images - 1
            else:
                next_row = (current_row - 1) % total_images
            
            # Select the next item in the list
            self.view.file_bar_list.setCurrentRow(next_row)
            
            # Load the next image
            file_path = self.loaded_image_paths[next_row]
            image = QPixmap(file_path)
            if not image.isNull():
                self.load_image(image)
                print(f"Next image loaded: {os.path.basename(file_path)}")
            else:
                self.error_message("Load Image", f"Could not load the image: {os.path.basename(file_path)}")