import cv2
import numpy as np
import sys
import os
import time
from PyQt6.QtWidgets import (
    QGraphicsEllipseItem, QComboBox, QGraphicsRectItem, QInputDialog, QGraphicsItem, QGraphicsItemGroup, QGraphicsPixmapItem, QGraphicsOpacityEffect, QGraphicsView, QGraphicsScene, QApplication, QMainWindow, QLabel, QVBoxLayout, QPushButton, 
    QFileDialog, QWidget, QMessageBox, QHBoxLayout, QColorDialog, QDialog, QSlider, QFormLayout, QDialogButtonBox, QGridLayout, QProgressDialog, QCheckBox, QSpinBox, QSplashScreen, QMenu
)
from PyQt6.QtGui import QPixmap, QMouseEvent, QImage, QPainter, QColor, QPen, QBrush, QCursor, QIcon, QPainterPath, QFont
from PyQt6.QtCore import Qt, QPoint, QPointF, QTimer,  QThread, pyqtSignal, QSize, QRectF, QObject, QLineF
import gc
import math
import traceback

class PointItem(QGraphicsEllipseItem):
    """Custom graphics item for representing a point/dot with fixed size"""
    def __init__(self, label, x, y, radius, color, opacity=100):
        # Store properties
        self.fixed_label = label
        self.fixed_x = x
        self.fixed_y = y
        self._fixed_radius = radius 
        self.fixed_color = QColor(color)
        self.fixed_opacity = int(255 * opacity / 100)
        
        # Create the ellipse using the fixed radius
        super().__init__(x - radius, y - radius, radius * 2, radius * 2)
        
        self.setPen(QPen(Qt.PenStyle.NoPen))
        self.fixed_color.setAlpha(self.fixed_opacity)
        self.setBrush(QBrush(self.fixed_color))
        self.setZValue(10)  # Ensure it's drawn above the image
        
        # Disable any modifications
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
    
    def get_position(self):
        """Always return the original center point"""
        return QPointF(self.fixed_x, self.fixed_y)
    
    def boundingRect(self):
        """Always return the original bounding rect with fixed radius"""
        return QRectF(self.fixed_x - self._fixed_radius, 
                      self.fixed_y - self._fixed_radius, 
                      self._fixed_radius * 2, 
                      self._fixed_radius * 2)
    
    def shape(self):
        """Ensure the shape remains fixed"""
        path = QPainterPath()
        path.addEllipse(QRectF(self.fixed_x - self._fixed_radius, 
                                self.fixed_y - self._fixed_radius, 
                                self._fixed_radius * 2, 
                                self._fixed_radius * 2))
        return path
    
    def paint(self, painter, option, widget=None):
        """Recreate the original ellipse with fixed radius and color"""
        painter.setBrush(QBrush(self.fixed_color))
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        painter.drawEllipse(QRectF(self.fixed_x - self._fixed_radius, 
                                   self.fixed_y - self._fixed_radius, 
                                   self._fixed_radius * 2, 
                                   self._fixed_radius * 2))
