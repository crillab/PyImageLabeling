

from PyImageLabeling.model.Core import Core
import numpy as np

class PaintBrush(Core):
    def __init__(self):
        super().__init__() 
    
    def paint_brush(self):
        self.checked_button = self.paint_brush.__name__

    def draw_continuous_line(self, start_pos, end_pos):
        self.view.point_color = self.labels[self.current_label]["color"]
        self.view.point_label = self.labels[self.current_label]["name"]
        distance = ((end_pos.x() - start_pos.x()) ** 2 + (end_pos.y() - start_pos.y()) ** 2) ** 0.5
        num_steps = max(int(distance * 2), 1)
        t_values = np.linspace(0, 1, num_steps + 1)
        for t in t_values:
            x = start_pos.x() + t * (end_pos.x() - start_pos.x())
            y = start_pos.y() + t * (end_pos.y() - start_pos.y())
            point_item = self.view.create_point_item(self.view.point_label, x, y, self.view.point_color)
            
            # Add to scene and configure
            self.view.zoomable_graphics_view.scene.addItem(point_item)
