
from PyImageLabeling.model.Core import Core

class PreviousImage(Core):
    def __init__(self):
        super().__init__()

    def previous_image(self):
        current_row = self.view.file_bar_list.currentRow()
        total_images = len(self.image_items)
        if  total_images == 1: return
        
        next_row = total_images - 1 if current_row == -1 else (current_row - 1) % total_images
        self.view.file_bar_list.setCurrentRow(next_row)

