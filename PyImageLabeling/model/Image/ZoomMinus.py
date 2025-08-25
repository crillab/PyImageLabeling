

from PyImageLabeling.model.Core import Core
from PyQt6.QtCore import QTimer

class ZoomMinus(Core):
    def __init__(self):
        super().__init__() 
        self.zoom_timer_plus = QTimer()
        self.zoom_timer_plus.timeout.connect(self.apply_zoom_minus)
        self.zoom_timer_plus.setInterval(100)  
        self.current_zoom_type = None

    def zoom_minus(self):
        self.checked_button = self.zoom_minus.__name__

    def start_zoom_minus(self):
        self.view.zoomable_graphics_view.change_cursor("zoom_minus")
        self.apply_zoom_minus()
        self.zoom_timer_plus.start()

    def apply_zoom_minus(self):
        factor = 0.9
        new_zoom_factor = self.view.zoom_factor * factor

        view = self.view.zoomable_graphics_view
        scene = view.scene 
        if not scene:
            return
        
        # Size of the full image
        scene_rect = scene.itemsBoundingRect()
        image_width = scene_rect.width()
        image_height = scene_rect.height()
        
        # Size of the viewport
        viewport_width = view.viewport().width()
        viewport_height = view.viewport().height()
        
        # Adaptive limits
        min_zoom = min(viewport_width / image_width, viewport_height / image_height)
        max_zoom = min_zoom * 40  

        if min_zoom <= new_zoom_factor <= max_zoom:
            self.view.zoom_factor = new_zoom_factor   
            mouse_pos = view.mapFromGlobal(view.cursor().pos())

            scene_pos = view.mapToScene(mouse_pos)
            view.scale(factor, factor)
            
            new_viewport_pos = view.mapFromScene(scene_pos)
            
            delta = new_viewport_pos - mouse_pos
            view.horizontalScrollBar().setValue(view.horizontalScrollBar().value() + delta.x())
            view.verticalScrollBar().setValue(view.verticalScrollBar().value() + delta.y())

    def end_zoom_minus(self):
        self.view.zoomable_graphics_view.change_cursor("zoom_minus")
        self.zoom_timer_plus.stop()