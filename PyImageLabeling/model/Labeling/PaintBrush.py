from PyImageLabeling.model.Core import Core
import numpy as np
from PyQt6.QtWidgets import QGraphicsEllipseItem, QGraphicsPathItem, QGraphicsItemGroup
from PyQt6.QtGui import QPainterPath, QPen, QBrush
from PyQt6.QtCore import QPointF, Qt

class PaintBrush(Core):
    def __init__(self):
        super().__init__()
        self.current_stroke_group = None
        self.stroke_path = None
        self.stroke_item = None
        self.point_spacing = 2.0
        self.last_point = None

    def paint_brush(self):
        self.checked_button = self.paint_brush.__name__

    def add_point(self, scene_pos):
        self.view.point_color = self.labels[self.current_label]["color"]
        self.view.point_label = self.labels[self.current_label]["name"]

        x = scene_pos.x()
        y = scene_pos.y()

        # Create a single point item
        point_item = self.view.create_point_item(self.view.point_label, x, y, self.view.point_color)
        self.view.zoomable_graphics_view.scene.addItem(point_item)
        self.last_point = scene_pos

    def start_stroke(self, start_pos):
        self.view.point_color = self.labels[self.current_label]["color"]
        self.view.point_label = self.labels[self.current_label]["name"]

        # Create a new path for this stroke
        self.stroke_path = QPainterPath()
        self.stroke_path.moveTo(start_pos)

        # Create the graphics item for this stroke
        self.stroke_item = QGraphicsPathItem(self.stroke_path)
        pen = QPen(self.view.point_color, self.view.point_radius * 2.7)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap) 
        self.stroke_item.setPen(pen)

        # Add to scene
        self.view.zoomable_graphics_view.scene.addItem(self.stroke_item)
        self.last_point = start_pos

    def continue_stroke(self, current_pos):
        if self.stroke_path is None or self.stroke_item is None:
            self.start_stroke(current_pos)
            return

        # Only add point if it's far enough from the last point
        if self.last_point is not None:
            distance = ((current_pos.x() - self.last_point.x()) ** 2 +
                        (current_pos.y() - self.last_point.y()) ** 2) ** 0.5
            if distance < self.point_spacing:
                return

        # Add line to the path
        self.stroke_path.lineTo(current_pos)
        self.stroke_item.setPath(self.stroke_path)
        self.last_point = current_pos

    def end_stroke(self):
        self.stroke_path = None
        self.stroke_item = None
        self.last_point = None
