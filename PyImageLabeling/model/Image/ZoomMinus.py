

from PyImageLabeling.model.Core import Core

class ZoomMinus(Core):
    def __init__(self):
        super().__init__() 
    
    def zoom_minus(self):
        self.checked_button = self.zoom_minus.__name__

    def apply_zoom_minus(self):
        factor = 0.9  
        new_zoom_factor = self.view.zoom_factor * factor
        
        if 0.9 <= new_zoom_factor <= 40.0:
            self.view.zoom_factor = new_zoom_factor
            view = self.view.zoomable_graphics_view
            mouse_pos = view.mapFromGlobal(view.cursor().pos())
            
            scene_pos = view.mapToScene(mouse_pos)
            view.scale(factor, factor)

            new_viewport_pos = view.mapFromScene(scene_pos)
            
            delta = new_viewport_pos - mouse_pos
            view.horizontalScrollBar().setValue(view.horizontalScrollBar().value() + delta.x())
            view.verticalScrollBar().setValue(view.verticalScrollBar().value() + delta.y())
        