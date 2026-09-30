

from PyImageLabeling.model.Core import Core

class ZoomPlus(Core):
    def zoom_plus(self):
        self.checked_button = self.zoom_plus.__name__
        
    def start_zoom_plus(self):
        self.view.zoomable_graphics_view.change_cursor("zoom_plus")
        self.view.zoomable_graphics_view.zoom(self.view.plus_zoom_factor+0.2)
        