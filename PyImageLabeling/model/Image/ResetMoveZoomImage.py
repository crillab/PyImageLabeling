
from PyImageLabeling.model.Core import Core

class ResetMoveZoomImage (Core):
    def __init__(self):
        super().__init__() 

    def set_view(self, view):
        super().set_view(view)
    
    def reset_move_zoom_image(self):
        print("reset_move_zoom_image")