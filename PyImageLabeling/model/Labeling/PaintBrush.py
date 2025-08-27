from PyImageLabeling.model.Core import Core
import numpy as np
from PyQt6.QtWidgets import QGraphicsEllipseItem, QGraphicsRectItem, QGraphicsPathItem, QGraphicsItemGroup, QGraphicsScene
from PyQt6.QtGui import QPainterPath, QPen, QBrush, QImage, QPainter
from PyQt6.QtCore import QPointF, Qt

from PyImageLabeling.model.Utils import Utils

class PaintBrush(Core):
    def __init__(self):
        super().__init__()
        self.painter_path = None
        self.graphics_path_item = None
        self.last_point = None
        self.paint_brush_activation = False
        self.point_spacing = 2.0

    def paint_brush(self):
        self.checked_button = self.paint_brush.__name__

    
    
    def add_point(self, start_pos, new_overlay_image, size_paint_brush, color):
        
        if size_paint_brush <= 3:
            point_item = QGraphicsRectItem(
                int(start_pos.x() - size_paint_brush/2), 
                int(start_pos.y() - size_paint_brush/2), 
                size_paint_brush,  
                size_paint_brush   
            )
        else:
            point_item = QGraphicsEllipseItem(
                int(start_pos.x() - size_paint_brush/2), 
                int(start_pos.y() - size_paint_brush/2), 
                size_paint_brush,  
                size_paint_brush   
            )
        
        # Set color and style
        
        point_item.setBrush(QBrush(color))
        point_item.setPen(QPen(color, 0))

        # Add to scene
        self.graphics_scene.addItem(point_item)
        
        # Properly initialize and manage QPainter
        painter = QPainter()
        painter.begin(new_overlay_image)
        self.graphics_scene.render(painter)
        painter.end()
        
        self.update_overlay(new_overlay_image)
        

    def start_paint_brush(self, start_pos):
        #Initialize some data
        size_paint_brush = Utils.load_parameters()["paint_brush"]["size"] 
        color = self.labels[self.current_label]["color"]
        width, height = self.image_pixmap.width(), self.image_pixmap.height()
        new_overlay_image = QImage(width, height, QImage.Format.Format_Mono)
        new_overlay_image.fill(Qt.GlobalColor.color0)
        
        self.view.zoomable_graphics_view.change_cursor("paint")
        self.graphics_scene = QGraphicsScene()
        self.graphics_scene.setSceneRect(0, 0, width, height)
        self.add_point(start_pos, new_overlay_image, size_paint_brush, color)


        # Create a new path for this brush stroke
        self.painter_path = QPainterPath()
        self.painter_path.moveTo(start_pos)

        # Create the graphics item for this brush stroke
        self.graphics_path_item = QGraphicsPathItem(self.painter_path)
        pen = QPen(color, int(size_paint_brush))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap) 
        
        self.graphics_path_item.setPen(pen)

        self.graphics_scene.addItem(self.graphics_path_item)
        self.last_point = start_pos

    def move_paint_brush(self, current_pos):
        
        self.view.zoomable_graphics_view.change_cursor("paint")
        width, height = self.image_pixmap.width(), self.image_pixmap.height()
        new_overlay_image = QImage(width, height, QImage.Format.Format_Mono)
        new_overlay_image.fill(Qt.GlobalColor.color0)

        if self.painter_path is None or self.graphics_path_item is None:
            self.start_paint_brush(current_pos)
            return

        # Only add point if it's far enough from the last point
        if self.last_point is not None:
            distance = ((current_pos.x() - self.last_point.x()) ** 2 +
                        (current_pos.y() - self.last_point.y()) ** 2) ** 0.5
            if distance < self.point_spacing:
                return

        # Add line to the path
        self.painter_path.lineTo(current_pos)
        self.graphics_path_item.setPath(self.painter_path)

        # Properly initialize and manage QPainter
        painter = QPainter()
        painter.begin(new_overlay_image)
        self.graphics_scene.render(painter)
        painter.end()

        self.update_overlay(new_overlay_image)
        
        self.last_point = current_pos

    def end_paint_brush(self):
        self.painter_path = None
        self.graphics_path_item = None
        self.last_point = None
