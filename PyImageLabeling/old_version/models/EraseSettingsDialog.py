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

class EraseSettingsDialog(QDialog):
    def __init__(self, parent=None, current_eraser_size=None, absolute_mode=False):
        super().__init__(parent)
        self.setWindowTitle("Eraser Settings")
        self.eraser_size = current_eraser_size or 10
        self.absolute_mode = absolute_mode
        
        layout = QFormLayout()
        
        # Eraser size slider
        self.eraser_slider = QSlider(Qt.Orientation.Horizontal)
        self.eraser_slider.setRange(1, 100)
        self.eraser_slider.setValue(self.eraser_size)
        layout.addRow("Eraser Size:", self.eraser_slider)
        self.eraser_spinbox = QSpinBox()
        
        self.eraser_spinbox.setRange(1, 100)
        self.eraser_spinbox.setValue(self.eraser_size)
        self.eraser_spinbox.valueChanged.connect(self.eraser_slider.setValue)
        self.eraser_slider.valueChanged.connect(self.eraser_spinbox.setValue)
        layout.addRow("", self.eraser_spinbox)
        
        # Add absolute mode checkbox
        self.absolute_checkbox = QCheckBox("Absolute Mode")
        self.absolute_checkbox.setChecked(self.absolute_mode)
        layout.addRow("", self.absolute_checkbox)
        
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addRow(self.buttons)
        
        self.setLayout(layout)
    
    def get_settings(self):
        return self.eraser_slider.value(), self.absolute_checkbox.isChecked()