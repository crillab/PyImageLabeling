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

class ProcessWorker(QThread):
    """Worker class to handle long processes with timeout"""
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, func, args=None, kwargs=None, timeout=10):
        super().__init__()
        self.func = func
        self.args = args or []
        self.kwargs = kwargs or {}
        self.timeout_value = timeout
        
        # Create a separate timer for timeout
        self.timeout_timer = QTimer()
        self.timeout_timer.setSingleShot(True)
        self.timeout_timer.timeout.connect(self._on_timeout)
    
    def run(self):
        """Thread's main function (automatically called by start())"""
        try:
            # Start the timeout timer
            self.timeout_timer.start(self.timeout_value * 1000)
            
            # Run the actual function
            result = self.func(*self.args, **self.kwargs)
            
            # Stop timer and emit result
            self.timeout_timer.stop()
            self.finished.emit(result)
        except Exception as e:
            self.timeout_timer.stop()
            self.error.emit(str(e))
    
    def _on_timeout(self):
        """Handle timeout event"""
        self.terminate()  # Terminate thread
        self.error.emit(f"Operation timed out after {self.timeout_value} seconds")