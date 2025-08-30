from PyImageLabeling.model.Core import Core
import numpy as np
from PyQt6.QtWidgets import QGraphicsEllipseItem, QGraphicsRectItem, QGraphicsPathItem, QGraphicsItemGroup, QGraphicsScene, QGraphicsItem
from PyQt6.QtGui import QPainterPath, QPen, QBrush, QImage, QPainter, QPixmap 
from PyQt6.QtCore import QPointF, Qt, QRectF

from PyImageLabeling.model.Utils import Utils

class PaintBrushItem(QGraphicsItem):

    def __init__(self, x, y, color, size, labeling_overlay_painter):
        super().__init__()
        self.x = x
        self.y = y
        self.color = color
        self.size = size
        self.labeling_overlay_painter = labeling_overlay_painter
        self.qrectf = QRectF(int(self.x)-(self.size/2)-5, int(self.y)-(self.size/2)-5, self.size+10, self.size+10)
        
        self.image_pixmap = QPixmap(self.size, self.size) 
        self.image_pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(self.image_pixmap)
        self.pen = QPen(color, self.size)
        self.pen.setCapStyle(Qt.PenCapStyle.RoundCap) 
        painter.setPen(self.pen)
        painter.drawPoint(int(self.size/2), int(self.size/2))
        painter.end()
        
    def boundingRect(self):
        return self.qrectf

    def paint(self, painter, option, widget):
        painter.drawPixmap(int(self.x-(self.size/2)), int(self.y-(self.size/2)), self.image_pixmap) 
        self.labeling_overlay_painter.drawPixmap(int(self.x-(self.size/2)), int(self.y-(self.size/2)), self.image_pixmap) 

class PaintBrush(Core):
    def __init__(self):
        super().__init__()
        self.last_position_x, self.last_position_y = None, None
        self.point_spacing = 2
        self.paint_brush_items = []

    def paint_brush(self):
        self.checked_button = self.paint_brush.__name__      

    def start_paint_brush(self, current_position):
        self.view.zoomable_graphics_view.change_cursor("paint")
        
        self.current_position_x = int(current_position.x())
        self.current_position_y = int(current_position.y())

        self.size_paint_brush = Utils.load_parameters()["paint_brush"]["size"] 
        self.color = self.labels[self.current_label]["color"]
        
        paint_brush_item = PaintBrushItem(self.current_position_x, self.current_position_y, self.color, self.size_paint_brush, self.labeling_overlay_painter)
        paint_brush_item.setZValue(2) # To place in the top of the item
        self.zoomable_graphics_view.scene.addItem(paint_brush_item) # update is already call in this method
        self.paint_brush_items.append(paint_brush_item)
        
        self.last_position_x, self.last_position_y = self.current_position_x, self.current_position_y

    def move_paint_brush(self, current_position):
        self.current_position_x = int(current_position.x())
        self.current_position_y = int(current_position.y())

        if Utils.compute_diagonal(self.current_position_x, self.current_position_y, self.last_position_x, self.last_position_y) < self.point_spacing:
            return 
        
        paint_brush_item = PaintBrushItem(self.current_position_x, self.current_position_y, self.color, self.size_paint_brush, self.labeling_overlay_painter)
        paint_brush_item.setZValue(2) # To place in the top of the item
        self.zoomable_graphics_view.scene.addItem(paint_brush_item) # update is already call in this method
        self.paint_brush_items.append(paint_brush_item)
        
        self.last_position_x, self.last_position_y = self.current_position_x, self.current_position_y

    def end_paint_brush(self):  
        # Remove the dislay of all these item
        for item in self.paint_brush_items:
            self.zoomable_graphics_view.scene.removeItem(item)
        self.paint_brush_items.clear()

        # Display the good pixmap :) 
        self.update_labeling_overlay()
        

