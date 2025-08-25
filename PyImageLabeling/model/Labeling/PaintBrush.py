from PyImageLabeling.model.Core import Core
import numpy as np
from PyQt6.QtWidgets import QGraphicsEllipseItem, QGraphicsPathItem, QGraphicsItemGroup, QGraphicsScene
from PyQt6.QtGui import QPainterPath, QPen, QBrush, QImage, QPainter
from PyQt6.QtCore import QPointF, Qt

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

    
    
    def add_point(self, scene_pos, new_overlay_image, graphics_scene):
        # Create a single point item with correct radius
        radius = self.view.point_radius
        
        point_item = QGraphicsEllipseItem(
            scene_pos.x() - radius, 
            scene_pos.y() - radius, 
            2 * radius,  
            2 * radius   
        )
        
        # Set color and style
        point_item.setBrush(QBrush(self.view.point_color))
        point_item.setPen(QPen(self.view.point_color, 0))

        # Add to scene
        # Initialize QGraphicsScene()
        self.graphics_scene = graphics_scene
        self.graphics_scene.addItem(point_item)

        # Properly initialize and manage QPainter
        painter = QPainter()
        if painter.begin(new_overlay_image):
            try:
                self.graphics_scene.render(painter)
            finally:
                painter.end()
        else:
            print("Failed to begin painting on overlay image")

        self.update_overlay(new_overlay_image)

        self.last_point = scene_pos

    def start_paint_brush(self, start_pos):
        #if not self.zoomable_graphics_view.sceneRect().contains(start_pos):
        #    return
        
        #Initialize some data
        width, height = self.image_pixmap.width(), self.image_pixmap.height()
        new_overlay_image = QImage(width, height, QImage.Format.Format_Mono)
        new_overlay_image.fill(Qt.GlobalColor.color0)

        

        self.view.zoomable_graphics_view.change_cursor("paint")
        self.view.point_color = self.labels[self.current_label]["color"]
        self.view.point_label = self.labels[self.current_label]["name"]

        self.graphics_scene = QGraphicsScene()
        self.graphics_scene.setSceneRect(0, 0, width, height)

        self.add_point(start_pos, new_overlay_image, self.graphics_scene)
        # Create a new path for this brush stroke
        #self.painter_path = QPainterPath()
        #self.painter_path.moveTo(start_pos)

        # Create the graphics item for this brush stroke
        #self.graphics_path_item = QGraphicsPathItem(self.painter_path)
        #pen = QPen(self.view.point_color, self.view.point_radius * 2.7)
        #pen.setCapStyle(Qt.PenCapStyle.RoundCap) 
        #self.graphics_path_item.setPen(pen)

        #self.graphics_scene.addItem(self.graphics_path_item)

        #painter = QPainter(new_overlay_image)
        #self.graphics_scene.render(painter)

        #self.update_overlay(new_overlay_image)




        # Add to scene
        #self.view.zoomable_graphics_view.scene.addItem(self.graphics_path_item)
        #self.view.zoomable_graphics_view.update()
        # self.last_point = start_pos

    def move_paint_brush(self, current_pos):
        if not self.zoomable_graphics_view.sceneRect().contains(current_pos):
            return
        
        self.view.zoomable_graphics_view.change_cursor("paint")
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
        self.view.zoomable_graphics_view.update()
        self.last_point = current_pos

    def end_paint_brush(self):
        self.painter_path = None
        self.graphics_path_item = None
        self.last_point = None
