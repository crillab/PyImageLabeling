
from PyImageLabeling.controller.Events import Events

from PyQt6.QtWidgets import QFileDialog
from PyQt6.QtGui import QPixmap, QImage

class FileEvents(Events):
    def __init__(self):
        super().__init__()
        
    def set_view(self, view):
        super().set_view(view)

    def set_model(self, model):
        super().set_model(model)
        
    def load_images(self):
        self.all_events(self.load_images.__name__)
        self.model.init_load_image()
        print("load_images")
   
    def next_image(self):
        self.all_events(self.next_image.__name__)
        self.model.next_image()

    def previous_image(self):
        self.all_events(self.previous_image.__name__)
        self.model.previous_image()
