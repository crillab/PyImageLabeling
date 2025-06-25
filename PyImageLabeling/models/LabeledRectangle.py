
import cv2
import numpy as np
import sys
import os
import time
from PyQt6.QtWidgets import (
    QGraphicsEllipseItem, QComboBox, QGraphicsRectItem, QInputDialog, QGraphicsItem, QGraphicsItemGroup, QGraphicsPixmapItem, QGraphicsOpacityEffect, QGraphicsView, QGraphicsScene, QApplication, QMainWindow, QLabel, QVBoxLayout, QPushButton, 
    QFileDialog, QWidget, QMessageBox, QHBoxLayout, QColorDialog, QDialog, QSlider, QFormLayout, QDialogButtonBox, QGridLayout, QProgressDialog, QCheckBox, QSpinBox, QSplashScreen, QMenu, QGraphicsTextItem
)
from PyQt6.QtGui import QPixmap, QMouseEvent, QImage, QPainter, QColor, QPen, QBrush, QCursor, QIcon, QPainterPath, QFont
from PyQt6.QtCore import Qt, QPoint, QPointF, QTimer,  QThread, pyqtSignal, QSize, QRectF, QObject, QLineF
import gc
import math
import traceback

class LabeledRectangle(QGraphicsRectItem):
    def __init__(self, x, y, width, height, label="", color = None):
        super().__init__(x, y, width, height)
        self.label = label
        self.color = color if color else QColor(255, 0, 0)   # Red outline

        self.setPen(QPen(QColor(self.color), 2))
        
        # Create label text item
        self.text_item = QGraphicsTextItem(self.label, self)
        self.text_item.setDefaultTextColor(QColor(255, 255, 255))
        self.text_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        # Position the text at the top-left corner of the rectangle
        self.text_item.setPos(x, y - 20)  # Slightly above the rectangle
        
        # Make the rectangle selectable and movable
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable, True)
    
    def set_color(self, color):
        """Update the rectangle color"""
        self.color = color
        self.setPen(QPen(QColor(self.color), 2))
    
    def set_label(self, label):
        """Update the rectangle label"""
        self.label = label
        if hasattr(self, 'text_item'):
            self.text_item.setPlainText(label)
            
    def set_thickness(self, thickness):
        """Update the rectangle thickness"""
        self.thickness = thickness
        self.setPen(QPen(QColor(self.color), self.thickness))
    
    def get_color(self):
        """Get the current color"""
        return self.color
    
    def get_label(self):
        """Get the current label"""
        return self.label
    
    def boundingRect(self):
        """Return the bounding rectangle including the text"""
        rect = super().boundingRect()
        if hasattr(self, 'text_item'):
            text_rect = self.text_item.boundingRect()
            text_rect.translate(self.text_item.pos())
            rect = rect.united(text_rect)
        return rect
    
    def contains(self, point):
        """Check if point is within the rectangle (for click detection)"""
        return super().contains(point)
    
    def itemChange(self, change, value):
        """Handle item changes (like position changes)"""
        if change == QGraphicsRectItem.GraphicsItemChange.ItemPositionChange and hasattr(self, 'text_item'):
            # Update text position when rectangle moves
            new_pos = value
            self.text_item.setPos(new_pos.x(), new_pos.y() - 20)
        return super().itemChange(change, value)