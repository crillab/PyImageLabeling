
from PyImageLabeling.model.Core import Core
from PyQt6.QtCore import Qt

class ResetMoveZoomImage (Core):
    def __init__(self):
        super().__init__() 

    def set_view(self, view):
        super().set_view(view)
    
    def reset_move_zoom_image(self):
        self.zoomable_graphics_view.resetTransform()
        self.zoomable_graphics_view.setSceneRect(self.get_current_image_item().get_qrectf())
        self.view.zoom_factor = self.view.initial_zoom_factor 
        #self.zoomable_graphics_view.fitInView(self.pixmap_item.boundingRect(), Qt.AspectRatioMode.KeepAspectRatio)