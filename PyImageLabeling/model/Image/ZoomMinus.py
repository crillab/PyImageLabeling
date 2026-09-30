

from PyImageLabeling.model.Core import Core

class ZoomMinus(Core):
    def zoom_minus(self):
        self.checked_button = self.zoom_minus.__name__
        
    def start_zoom_minus(self):
        self.view.zoomable_graphics_view.change_cursor("zoom_minus")
        self.view.zoomable_graphics_view.zoom(self.view.minus_zoom_factor-0.2)


    
