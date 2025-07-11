

from PyImageLabeling.model.Core import Core

class ZoomMinus(Core):
    def __init__(self):
        super().__init__() 
    
    def zoom_minus(self):
        self.checked_button = self.zoom_minus.__name__

    def apply_zoom_minus(self):
        print("apply_zoom_minus")
        