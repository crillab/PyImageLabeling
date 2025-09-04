from PyImageLabeling.model.Core import Core
import numpy as np
from PyQt6.QtWidgets import QGraphicsEllipseItem, QGraphicsRectItem, QGraphicsPathItem, QGraphicsItemGroup, QGraphicsScene, QGraphicsItem
from PyQt6.QtGui import QPainterPath, QPen, QBrush, QImage, QPainter, QPixmap, QColor
from PyQt6.QtCore import QPointF, Qt, QRectF, QRect

from PyImageLabeling.model.Utils import Utils

class PaintBrushItemOld(QGraphicsItem):

    def __init__(self, core, x, y, color, size):
        super().__init__()
        self.x = x
        self.y = y
        self.color = color
        self.size = size
        self.labeling_overlay_painter = core.get_labeling_overlay().get_painter()
        self.image_pixmap = core.image_pixmap

        self.qrectf = QRectF(int(self.x)-(self.size/2)-5, int(self.y)-(self.size/2)-5, self.size+10, self.size+10)
        self.qrectf = self.qrectf.intersected(core.image_qrectf)
        alpha_color = Utils.load_parameters()["load_image"]["alpha_color"] 

        self.texture = QPixmap(self.size, self.size) 
        #self.image_pixmap.fill(Qt.GlobalColor.transparent)
        self.texture.fill(Qt.GlobalColor.transparent)
        
        

        painter = QPainter(self.texture)
        self.pen = QPen(color, self.size)
        self.pen.setCapStyle(Qt.PenCapStyle.RoundCap) 
        #painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Xor)
        painter.setPen(self.pen)
        painter.drawPoint(int(self.size/2), int(self.size/2))
        painter.end()
    
        
    def boundingRect(self):
        return self.qrectf

    def paint(self, painter, option, widget):
        #painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationAtop)
        #self.pen = QPen(self.color, self.size)
        #self.pen.setCapStyle(Qt.PenCapStyle.RoundCap) 
        #painter.setPen(self.pen)
        #painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationOver)
        #painter.drawPoint(int(self.x), int(self.y))
        
    
        #print("pp:", painter.device(), self)
        painter.drawPixmap(int(self.x-(self.size/2)), int(self.y-(self.size/2)), self.texture) 
        #painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        #painter.end()
        
        self.labeling_overlay_painter.drawPixmap(int(self.x-(self.size/2)), int(self.y-(self.size/2)), self.texture) 

class PaintBrushItem(QGraphicsItem):

    def __init__(self, core, x, y, color, size):
        super().__init__()
        
        # Initialize the variable of the first point
        self.core = core
        self.x = x
        self.y = y
        self.color = color
        self.size = size
        self.labeling_overlay_painter = self.core.get_labeling_overlay().get_painter()
        self.image_pixmap = self.core.image_pixmap
        self.position_x = int(self.x-(self.size/2))
        self.position_y = int(self.y-(self.size/2))
        self.bounding_rect = QRectF(self.position_x, self.position_y, self.size, self.size)

        # Create the image of the first point
        self.texture = QPixmap(self.size, self.size) 
        self.texture.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(self.texture)
        self.pen = QPen(color, self.size)
        self.pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        
        painter.setPen(self.pen)
        painter.drawPoint(int(self.size/2), int(self.size/2))

        # Remove the existing pixel label already colored 
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationOut)
        painter.drawPixmap(QRect(0, 0, self.size, self.size), self.core.get_labeling_overlay().labeling_overlay_pixmap, self.bounding_rect.toRect())
        
        painter.end()
        
        
        
        
        
        
        
    def add_point(self, new_x, new_y):
        # Compute the bounding rect of the new point 
        new_position_x = int(new_x-(self.size/2))
        new_position_y = int(new_y-(self.size/2))
        new_bounding_rect = QRectF(new_position_x, new_position_y, self.size, self.size)

        # Do the union of the two bounding rects 
        self.united_bounding_rect = self.bounding_rect.united(new_bounding_rect)

        # Create a new texture 
        new_texture = QPixmap(int(self.united_bounding_rect.width()), int(self.united_bounding_rect.height()))
        new_texture.fill(Qt.GlobalColor.transparent)
        
        # Add the new point in the texture  
        painter = QPainter(new_texture)  
        self.pen = QPen(self.color, self.size)
        self.pen.setCapStyle(Qt.PenCapStyle.RoundCap) 
        painter.setPen(self.pen)
        #painter.setOpacity(1)

        
        painter.drawPoint(int(new_position_x-self.united_bounding_rect.x()+(self.size/2)), int(new_position_y-self.united_bounding_rect.y()+(self.size/2)))
        #painter.setOpacity(0)
        
        # Copy the old texture in the new texture 
        #painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Xor)
        painter.drawPixmap(int(self.bounding_rect.x()-self.united_bounding_rect.x()), int(self.bounding_rect.y()-self.united_bounding_rect.y()), self.texture)
        
        # Remove the existing pixel label already colored 
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationOut)
        painter.drawPixmap(QRect(0, 0, int(self.united_bounding_rect.width()), int(self.united_bounding_rect.height())), self.core.get_labeling_overlay().labeling_overlay_pixmap, self.united_bounding_rect.toRect())
        
        
        painter.end()

        # Update the good variable for the painter 
        self.texture = new_texture
        self.bounding_rect = self.united_bounding_rect
        self.position_x = int(self.bounding_rect.x())
        self.position_y = int(self.bounding_rect.y())
        
    def boundingRect(self):
        return self.bounding_rect

    def paint(self, painter, option, widget):
        painter.setOpacity(self.core.get_labeling_overlay().get_opacity())
        painter.drawPixmap(self.position_x, self.position_y, self.texture) 
        
        
    def labeling_overlay_paint(self):
        #self.labeling_overlay_painter.setOpacity(0.7)
        self.labeling_overlay_painter.drawPixmap(self.position_x, self.position_y, self.texture) 
    

class PaintBrush(Core):
    def __init__(self):
        super().__init__()
        self.last_position_x, self.last_position_y = None, None
        self.point_spacing = 2
        self.paint_brush_items = []
        self.previous_pixmap = None

    def paint_brush(self):
        self.checked_button = self.paint_brush.__name__      

    def start_paint_brush(self, current_position):
        self.view.zoomable_graphics_view.change_cursor("paint")
        
        self.current_position_x = int(current_position.x())
        self.current_position_y = int(current_position.y())

        self.size_paint_brush = Utils.load_parameters()["paint_brush"]["size"] 
        self.color = self.get_labeling_overlay().get_color()
        
        self.paint_brush_item = PaintBrushItem(self, self.current_position_x, self.current_position_y, self.color, self.size_paint_brush)
        self.paint_brush_item.setZValue(2) # To place in the top of the item
        self.zoomable_graphics_view.scene.addItem(self.paint_brush_item) # update is already call in this method
        
        self.last_position_x, self.last_position_y = self.current_position_x, self.current_position_y

    def move_paint_brush(self, current_position):
        self.current_position_x = int(current_position.x())
        self.current_position_y = int(current_position.y())

        if Utils.compute_diagonal(self.current_position_x, self.current_position_y, self.last_position_x, self.last_position_y) < self.point_spacing:
            return 
        
        self.paint_brush_item.add_point(self.current_position_x, self.current_position_y)
        self.paint_brush_item.update()

        #paint_brush_item = PaintBrushItem(self, self.current_position_x, self.current_position_y, self.color, self.size_paint_brush)
        #paint_brush_item.setZValue(3) # To place in the top of the item
        #self.zoomable_graphics_view.scene.addItem(paint_brush_item) # update is already call in this method
        #self.paint_brush_items.append(paint_brush_item)
        
        self.last_position_x, self.last_position_y = self.current_position_x, self.current_position_y

    def end_paint_brush(self):  
        # Paint the good pixmap 
        self.paint_brush_item.labeling_overlay_paint()

        # Display it :) 
        self.update_labeling_overlay()

        # Romeve the fake item 
        self.zoomable_graphics_view.scene.removeItem(self.paint_brush_item)
        

