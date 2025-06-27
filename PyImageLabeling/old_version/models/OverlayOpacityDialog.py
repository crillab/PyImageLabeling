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

class OverlayOpacityDialog(QDialog):
    def __init__(self, parent=None, current_opacity=255):
        super().__init__(parent)
        self.setWindowTitle("Overlay Opacity")
        
        layout = QFormLayout()

        # Opacity slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 255)
        self.slider.setValue(current_opacity)
        self.slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider.setTickInterval(25)
        layout.addRow("Opacity:", self.slider)
        
        # Opacity spinbox
        self.opacity_spinbox = QSpinBox()
        self.opacity_spinbox.setRange(0, 255)
        self.opacity_spinbox.setValue(current_opacity)
        layout.addRow("", self.opacity_spinbox)
        
        # Sync slider and spinbox
        self.opacity_spinbox.valueChanged.connect(self.slider.setValue)
        self.slider.valueChanged.connect(self.opacity_spinbox.setValue)

        # Preset buttons layout
        preset_layout = QHBoxLayout()
        presets = [(25, "25%"), (50, "50%"), (75, "75%"), (100, "100%")]
        for value, label in presets:
            btn = QPushButton(label)
            btn.setFixedHeight(25)
            btn.setProperty("class", "preset")
            btn.clicked.connect(lambda checked, v=value: self.set_preset(v))
            preset_layout.addWidget(btn)
        layout.addRow("", preset_layout)
        
        # Buttons
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addRow(self.buttons)

        self.setLayout(layout)

    def set_preset(self, percentage):
        """Set opacity to a preset percentage value"""
        value = int((percentage / 100) * 255)
        self.slider.setValue(value)