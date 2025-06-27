from PyQt6.QtCore import Qt
from models.PointItem import PointItem
import numpy as np

class PaintTool:
    def add_point(self, scene_pos):
        current_radius = self.point_radius
        current_color = self.point_color
        current_opacity = self.point_opacity
        current_label = self.point_label
        point_item = PointItem(
            current_label,
            scene_pos.x(), scene_pos.y(),
            current_radius,
            current_color,
            current_opacity
        )
        self.scene.addItem(point_item)
        point_item.setVisible(False)
        self.points.append(point_item)
        self.current_stroke.append(point_item)
        self.update_points_overlay()

    def draw_continuous_line(self, start_pos, end_pos):
        if not start_pos or not end_pos:
            return
        current_point_radius = self.point_radius
        current_point_color = self.point_color
        current_point_opacity = self.point_opacity
        current_point_label = self.point_label
        distance = ((end_pos.x() - start_pos.x()) ** 2 + (end_pos.y() - start_pos.y()) ** 2) ** 0.5
        num_steps = max(int(distance * 2), 1)
        t_values = np.linspace(0, 1, num_steps + 1)
        for t in t_values:
            x = start_pos.x() + t * (end_pos.x() - start_pos.x())
            y = start_pos.y() + t * (end_pos.y() - start_pos.y())
            point_item = PointItem(
                current_point_label,
                x, y,
                current_point_radius,
                current_point_color,
                current_point_opacity
            )
            self.scene.addItem(point_item)
            point_item.setVisible(self.drawn_points_visible)
            self.points.append(point_item)
            self.current_stroke.append(point_item)
        self.update_points_overlay()

    def toggle_paint_mode(self, enabled):
        self.paint_mode = enabled
        if enabled:
            self.erase_mode = False
            self.magic_pen_mode = False
            self.setCursor(Qt.CursorShape.CrossCursor)
            self.setDragMode(self.DragMode.NoDrag)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.setDragMode(self.DragMode.ScrollHandDrag)

    def clear_points(self):
        self.points_history.append(self.points[:])
        self.points = []
        if hasattr(self, 'points_overlay_item') and self.points_overlay_item:
            self.scene.removeItem(self.points_overlay_item)
            self.points_overlay_item = None
        self.points_pixmap = None
        self.last_rendered_points_count = 0