

from model.Core import Core
from PyQt6.QtCore import Qt

class SaveLayer(Core):
    def __init__(self):
        super().__init__() 

    def set_view(self, view):
        super().set_view(view)
    
    def save_image(self, pixmap):
        pass
    
    
