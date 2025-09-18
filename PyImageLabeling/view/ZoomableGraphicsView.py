import cv2
import numpy as np
import sys
import os
import time
from PyQt6.QtWidgets import (
    QGraphicsEllipseItem, QComboBox, QGraphicsRectItem, QInputDialog, QGraphicsItem, QGraphicsItemGroup, QGraphicsPixmapItem, QGraphicsOpacityEffect, QGraphicsView, QGraphicsScene, QApplication, QMainWindow, QLabel, QVBoxLayout, QPushButton, 
    QFileDialog, QWidget, QMessageBox, QHBoxLayout, QColorDialog, QDialog, QSlider, QFormLayout, QDialogButtonBox, QGridLayout, QProgressDialog, QCheckBox, QSpinBox, QSplashScreen, QMenu, QLineEdit, QFrame
)
from PyQt6.QtGui import QPixmap, QMouseEvent, QImage, QPainter, QColor, QPen, QBrush, QCursor, QIcon, QPainterPath, QFont
from PyQt6.QtCore import Qt, QPoint, QPointF, QTimer,  QThread, pyqtSignal, QSize, QRectF, QObject, QLineF
import gc
import math
import traceback

from PyImageLabeling.model.Utils import Utils

#from models.LabeledRectangle import LabeledRectangle
#from models.PointItem import PointItem
#from models.ProcessWorker import ProcessWorker
#from models.OverlayOpacityDialog import OverlayOpacityDialog
#from models.tools.PaintTool import PaintTool
#from models.tools.EraserTool import EraserTool
#from models.tools.MagicPenTool import MagicPenTool
#from models.tools.OverlayTool import OverlayTool
#from models.tools.RectangleTool import RectangleTool, LabelPropertiesManager, LabelRectanglePropertiesDialog
#from models.tools.ContourTool import ContourTool
#from models.tools.PolygonTool import PolygonTool, LabelPolygonPropertiesDialog

#class ZoomableGraphicsView(QGraphicsView, PaintTool, EraserTool, MagicPenTool, OverlayTool, RectangleTool, ContourTool, PolygonTool):

class ZoomableGraphicsView(QGraphicsView):
    def __init__(self, view, parent=None):
        super().__init__(parent)
        
        self.view = view
        # Create scene
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        # Setup view properties for best performance
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontAdjustForAntialiasing, True)
        self.setOptimizationFlag(QGraphicsView.OptimizationFlag.DontSavePainterState, True)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.MinimalViewportUpdate)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        #self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        #self.setCacheMode(QGraphicsView.CacheModeFlag.CacheBackground)

        self.data_parameters = Utils.load_parameters() # To use only for recuparate constant values (not save)

        # Zoom properties
        self.view.zoom_factor = 0        
        self.view.min_zoom = self.data_parameters["zoom"]["min_zoom"]
        self.view.max_zoom = self.data_parameters["zoom"]["max_zoom"]
        self.view.plus_zoom_factor = self.data_parameters["zoom"]["plus_zoom_factor"]
        self.view.minus_zoom_factor = self.data_parameters["zoom"]["minus_zoom_factor"]

        self.view.layer_activation = False
        
    def change_cursor(self, name):
        cursor_pixmap = QPixmap(Utils.get_icon_path(name))
        cursor_pixmap = cursor_pixmap.scaled(*self.view.config["window_size"]["icon"]) 
        cursor = QCursor(cursor_pixmap)
        self.viewport().setCursor(cursor)
        return cursor.pixmap().width(), cursor.pixmap().height()
    
    def change_cursor_n(self, name):
        cursor_pixmap = QPixmap(Utils.get_icon_path(name))
        cursor_pixmap = cursor_pixmap.scaled(*self.view.config["window_size"]["icon"])
        
        # Create a new pixmap with border
        border_width = 2
        new_size = cursor_pixmap.size() + QSize(border_width * 2, border_width * 2)
        bordered_pixmap = QPixmap(new_size)
        bordered_pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(bordered_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw border/outline
        pen = QPen(Qt.GlobalColor.white, border_width)  # or Qt.black for dark border
        painter.setPen(pen)
        painter.drawRect(border_width//2, border_width//2, 
                        cursor_pixmap.width() + border_width, 
                        cursor_pixmap.height() + border_width)
        
        # Draw original cursor on top
        painter.drawPixmap(border_width, border_width, cursor_pixmap)
        painter.end()
        
        cursor = QCursor(bordered_pixmap)
        self.viewport().setCursor(cursor)
        return cursor.pixmap().width(), cursor.pixmap().height()

    def zoom(self, factor):
        if self.view.min_zoom <= self.view.zoom_factor*factor <= self.view.max_zoom:
            view = self.view.zoomable_graphics_view
            self.view.zoom_factor = self.view.zoom_factor * factor
            #self.view.controller.model.get_current_image_item().set_zoom_factor(self.view.zoom_factor)
            mouse_pos = view.mapFromGlobal(view.cursor().pos())
            scene_pos = view.mapToScene(mouse_pos)
            view.scale(factor, factor)
            new_viewport_pos = view.mapFromScene(scene_pos)
            delta = new_viewport_pos - mouse_pos
            view.horizontalScrollBar().setValue(view.horizontalScrollBar().value() + delta.x())
            view.verticalScrollBar().setValue(view.verticalScrollBar().value() + delta.y())
        
    
           
    def wheelEvent(self, event):
        zoom_in = event.angleDelta().y() > 0
        if zoom_in is True:
            self.zoom(self.view.plus_zoom_factor)
        else:
            self.zoom(self.view.minus_zoom_factor)
