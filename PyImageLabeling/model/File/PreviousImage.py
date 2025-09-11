
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
        total_images = len(self.image_items)
        if  total_images == 1: return
        
        next_row = total_images - 1 if current_row == -1 else (current_row - 1) % total_images
        self.view.file_bar_list.setCurrentRow(next_row)

