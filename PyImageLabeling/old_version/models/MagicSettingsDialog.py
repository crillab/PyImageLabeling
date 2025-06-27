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

class MagicSettingsDialog(QDialog):
    def __init__(self, parent=None, current_tolerance=20, current_timeout=5, current_max_points=100000):
        super().__init__(parent)
        self.setWindowTitle("Magic Pen Settings")
        self.tolerance = current_tolerance
        self.max_point = current_max_points
        layout = QVBoxLayout()
        
        # Create a form layout for the controls
        form_layout = QFormLayout()
        
        # Tolerance slider
        self.tolerance_slider = QSlider(Qt.Orientation.Horizontal)
        self.tolerance_slider.setRange(0, 100)
        self.tolerance_slider.setValue(self.tolerance)
        self.tolerance_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.tolerance_slider.setTickInterval(10)
        form_layout.addRow("Tolerance:", self.tolerance_slider)
        
        # Tolerance spinbox
        self.tolerance_spinbox = QSpinBox()
        self.tolerance_spinbox.setRange(0, 100)
        self.tolerance_spinbox.setValue(self.tolerance)
        
        # Connect slider and spinbox
        self.tolerance_spinbox.valueChanged.connect(self.tolerance_slider.setValue)
        self.tolerance_slider.valueChanged.connect(self.tolerance_spinbox.setValue)
        
        form_layout.addRow("Value:", self.tolerance_spinbox)
        
        # Add a description of what different tolerance values mean
        tolerance_help = QLabel("Lower values = more precise color matching\nHigher values = more inclusive fill")
        tolerance_help.setStyleSheet("color: #666; font-style: italic;")
        form_layout.addRow("", tolerance_help)
        
        # Add form layout to main layout
        layout.addLayout(form_layout)
        
        # Add timeout setting
        timeout_layout = QHBoxLayout()
        timeout_label = QLabel("Timeout (seconds):")
        self.timeout_spinbox = QSpinBox()
        self.timeout_spinbox.setRange(1, 60)
        self.timeout_spinbox.setValue(current_timeout)
        timeout_layout.addWidget(timeout_label)
        timeout_layout.addWidget(self.timeout_spinbox)
        layout.addLayout(timeout_layout)
        
        # Add MAX_POINTS_LIMIT setting
        layout.addSpacing(10)
        points_limit_layout = QVBoxLayout()
        
        points_limit_label = QLabel("Maximum Points Limit:")
        points_limit_layout.addWidget(points_limit_label)
        
        points_slider_layout = QHBoxLayout()
        
        # Points limit slider
        self.points_limit_slider = QSlider(Qt.Orientation.Horizontal)
        self.points_limit_slider.setRange(5000, 500000)
        self.points_limit_slider.setValue(self.max_point)
        self.points_limit_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.points_limit_slider.setTickInterval(50000)
        
        # Points limit spinbox
        self.points_limit_spinbox = QSpinBox()
        self.points_limit_spinbox.setRange(5000, 500000)
        self.points_limit_spinbox.setValue(self.max_point)
        self.points_limit_spinbox.setSingleStep(5000)
        
        # Connect slider and spinbox
        self.points_limit_spinbox.valueChanged.connect(self.points_limit_slider.setValue)
        self.points_limit_slider.valueChanged.connect(self.points_limit_spinbox.setValue)
        
        points_slider_layout.addWidget(self.points_limit_slider)
        points_slider_layout.addWidget(self.points_limit_spinbox)
        points_limit_layout.addLayout(points_slider_layout)
        
        # Add description for points limit
        points_limit_help = QLabel("Higher values allow filling larger areas but may use more memory")
        points_limit_help.setStyleSheet("color: #666; font-style: italic;")
        points_limit_layout.addWidget(points_limit_help)
        
        layout.addLayout(points_limit_layout)
        
        # Add spacer
        layout.addSpacing(10)
        
        # Add buttons
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        
        self.setLayout(layout)
        
    def get_tolerance(self):
        return self.tolerance_slider.value()
        
    def get_timeout(self):
        return self.timeout_spinbox.value()
        
    def get_max_points_limit(self):
        return self.points_limit_spinbox.value()