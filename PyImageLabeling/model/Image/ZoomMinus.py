

from model.Core import Core
from PyQt6.QtCore import QTimer

class ZoomMinus(Core):
    def __init__(self):
        super().__init__() 
        self.current_zoom_type = None

    def zoom_minus(self):
        self.checked_button = self.zoom_minus.__name__
        
    def start_zoom_minus(self):
        self.view.zoomable_graphics_view.change_cursor("zoom_minus")
        self.view.zoomable_graphics_view.zoom(self.view.minus_zoom_factor-0.2)

        #self.apply_zoom_minus()
        #self.zoom_timer_plus.start()

    

    #def end_zoom_minus(self):
    #    self.view.zoomable_graphics_view.change_cursor("zoom_minus")
    #    self.zoom_timer_plus.stop()