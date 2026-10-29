
from PyImageLabeling.model.Base import Base

class ResetMoveZoomImage (Base):
    def __init__(self):
        super().__init__() 

    def set_view(self, view):
        super().set_view(view)
    
    def reset_move_zoom_image(self):
        self.zoomable_graphics_view.resetTransform()
        self.zoomable_graphics_view.setSceneRect(self.get_current_image_item().get_qrectf())
        self.view.zoom_factor = self.view.initial_zoom_factor 
