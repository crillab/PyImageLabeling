import cv2
import numpy as np
import sys
import os
import time
from PyQt6.QtWidgets import (
    QGraphicsEllipseItem, QComboBox, QGraphicsRectItem, QInputDialog, QGraphicsItem, QGraphicsItemGroup, QGraphicsPixmapItem, QGraphicsOpacityEffect, QGraphicsView, QGraphicsScene, QApplication, QMainWindow, QLabel, QVBoxLayout, QPushButton, 
    QFileDialog, QWidget, QMessageBox, QHBoxLayout, QColorDialog, QDialog, QSlider, QFormLayout, QDialogButtonBox, QGridLayout, QProgressDialog, QCheckBox, QSpinBox, QSplashScreen, QMenu, QLineEdit
)
from PyQt6.QtGui import QPixmap, QMouseEvent, QImage, QPainter, QColor, QPen, QBrush, QCursor, QIcon, QPainterPath, QFont
from PyQt6.QtCore import Qt, QPoint, QPointF, QTimer,  QThread, pyqtSignal, QSize, QRectF, QObject, QLineF
import gc
import math
import traceback
import json

class LabelPaintPropertiesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Label Properties")
        self.setMinimumWidth(300)
        self.setStyleSheet("""
            QDialog {
                background-color: #000000;
                color: white;
                border: 1px solid #444444;
            }
            QLabel {
                color: white;
                font-size: 14px;
            }
        """)

        layout = QVBoxLayout()

        self.label_name = QLabel("Label: ")
        self.label_color = QLabel("Color: ")
        self.label_radius = QLabel("Radius: ")
        self.label_opacity = QLabel("Opacity: ")

        layout.addWidget(self.label_name)
        layout.addWidget(self.label_color)
        layout.addWidget(self.label_radius)
        layout.addWidget(self.label_opacity)

        self.setLayout(layout)

    def update_properties(self, label, color, radius, opacity):
        self.label_name.setText(f"Label: {label}")
        self.label_color.setText(f"Color: {color.name()}")
        self.label_radius.setText(f"Radius: {radius}")
        self.label_opacity.setText(f"Opacity: {opacity}")

class LabelPropertiesManager:
    """Manages saving and loading of label properties"""
    
    def __init__(self, properties_file="label_paint_properties.json"):
        self.properties_file = properties_file
        self.label_properties = {}
        self.load_properties()
    
    def save_properties(self):
        """Save label properties to JSON file"""
        try:
            # Convert QColor objects to serializable format
            serializable_props = {}
            for label, props in self.label_properties.items():
                color = props['color']
                if isinstance(color, str):
                    color = QColor(color)  # Convert string to QColor if needed
                serializable_props[label] = {
                    'color': color.name(),  # Safely get hex color
                    'radius': props['radius'],
                    'opacity': props['opacity']
                }
            
            with open(self.properties_file, 'w') as f:
                json.dump(serializable_props, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving label properties: {e}")
            return False
    
    def load_properties(self):
        """Load label properties from JSON file"""
        try:
            if os.path.exists(self.properties_file):
                with open(self.properties_file, 'r') as f:
                    data = json.load(f)
                
                # Convert hex strings back to QColor objects
                for label, props in data.items():
                    self.label_properties[label] = {
                        'color': QColor(props['color']),
                        'radius': props['radius'],
                        'opacity': props['opacity']
                    }
            return True
        except Exception as e:
            print(f"Error loading label properties: {e}")
            return False
    
    def add_label_property(self, label, color, radius, opacity):
        """Add or update a label property"""
        self.label_properties[label] = {
            'color': color,
            'radius': radius,
            'opacity': opacity
        }
        self.save_properties()
    
    def get_label_property(self, label):
        """Get properties for a specific label"""
        return self.label_properties.get(label, None)
    
    def get_all_labels(self):
        """Get all saved label names"""
        return list(self.label_properties.keys())
    
    def remove_label_property(self, label):
        """Remove a label property"""
        if label in self.label_properties:
            del self.label_properties[label]
            self.save_properties()
            return True
        return False

class PaintSettingsDialog(QDialog):
    saved_labels = {}
    label_manager = LabelPropertiesManager()
    def __init__(self, parent=None, current_color=None, current_radius=None, current_opacity=None, current_label=None):
        super().__init__(parent)
        self.setWindowTitle("Paint Settings")
        
        # Initialize with current values or defaults
        self.color = current_color if current_color else QColor(255, 0, 0)
        self.radius = current_radius if current_radius else 3
        self.opacity = current_opacity if current_opacity else 255
        self.label = current_label if current_label else ""
        
        layout = QFormLayout()
        
        # Label selection/input - MODIFIED
        label_layout = QHBoxLayout()
        
        self.label_combo = QComboBox()
        self.label_combo.setEditable(True)
        self.label_combo.setPlaceholderText("Enter new label or select existing")
        
        # Populate combo box with saved labels
        self.label_combo.addItem("")  # Empty option for new labels
        for label in self.label_manager.get_all_labels():
            self.label_combo.addItem(label)
            
        # Set current label if provided
        if self.label:
            index = self.label_combo.findText(self.label)
            if index >= 0:
                self.label_combo.setCurrentIndex(index)
            else:
                self.label_combo.setCurrentText(self.label)
        
        self.label_combo.currentTextChanged.connect(self.on_label_selected)
        label_layout.addWidget(self.label_combo)
        
        layout.addRow("Label:", label_layout)

        # Color selection
        self.color_button = QPushButton("Choose Color")
        self.color_button.clicked.connect(self.choose_color)
        self.update_color_button()  # NEW METHOD CALL
        layout.addRow("Color:", self.color_button)
        
        # Radius slider
        self.radius_slider = QSlider(Qt.Orientation.Horizontal)
        self.radius_slider.setRange(1, 100)
        self.radius_slider.setValue(self.radius)
        self.radius_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.radius_slider.setTickInterval(10)
        layout.addRow("Radius:", self.radius_slider)
        
        self.radius_spinbox = QSpinBox()
        self.radius_spinbox.setRange(1, 100)
        self.radius_spinbox.setValue(self.radius)
        self.radius_spinbox.valueChanged.connect(self.radius_slider.setValue)
        self.radius_slider.valueChanged.connect(self.radius_spinbox.setValue)
        layout.addRow("", self.radius_spinbox)
        
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addRow(self.buttons)
        
        self.setLayout(layout)

    def on_label_selected(self, text):
        """Handle label selection from combo box"""
        if text:
            label_props = self.label_manager.get_label_property(text)
            if label_props:
                # Load saved settings for this label
                self.color = label_props['color']
                self.radius = label_props['radius']
                self.opacity = label_props['opacity']
                
                # Update UI elements
                self.radius_slider.setValue(self.radius)
                self.radius_spinbox.setValue(self.radius)
                self.update_color_button()
    
    def update_color_button(self):
        """Update color button appearance to show current color"""
        color_style = f"background-color: rgb({self.color.red()}, {self.color.green()}, {self.color.blue()}); color: {'white' if self.color.lightness() < 128 else 'black'};"
        self.color_button.setStyleSheet(color_style)
        self.color_button.setText(f"Color: {self.color.name()}")

    def choose_color(self):
        color = QColorDialog.getColor(initial=self.color)
        if color.isValid():
            self.color = color
            self.update_color_button()  # NEW METHOD CALL

    def get_settings(self):
        self.radius = self.radius_slider.value()
        self.label = self.label_combo.currentText().strip()
        
        # Save label settings if label is not empty - NEW FUNCTIONALITY
        if self.label:
            self.label_manager.add_label_property(self.label, self.color, self.radius, self.opacity)
        
        return self.color, self.radius, self.opacity, self.label
    
    def add_overlay(self, overlay_pixmap):
        """Add an overlay pixmap that stays aligned with the base image"""
        if not self.base_pixmap:
            return False
            
        # Remove existing overlay if any
        self.remove_overlay()
        
        # Ensure overlay matches base image dimensions
        base_size = self.base_pixmap.size()
        if overlay_pixmap.size() != base_size:
            overlay_pixmap = overlay_pixmap.scaled(
                base_size, 
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        
        # Create overlay pixmap item
        self.overlay_pixmap_item = self.scene.addPixmap(overlay_pixmap)
        self.overlay_pixmap_item.setZValue(1)  # Above base image
        self.overlay_pixmap_item.setPos(0, 0)  # Same position as base image
        
        # Set opacity (default 50%)
        if not hasattr(self, 'overlay_opacity'):
            self.overlay_opacity = 128
        self.overlay_pixmap_item.setOpacity(self.overlay_opacity / 255.0)
        
        # Update scene
        self.scene.update()
        return True
    
    def set_overlay_opacity(self, opacity):
        """Set opacity of the overlay layer (0-255)"""
        if self.overlay_pixmap_item:
            self.overlay_opacity = max(0, min(255, opacity))
            self.overlay_pixmap_item.setOpacity(self.overlay_opacity / 255.0)
            self.scene.update()
            return True
        return False
    
    def toggle_overlay_visibility(self):
        """Toggle visibility of the overlay"""
        if self.overlay_pixmap_item:
            is_visible = self.overlay_pixmap_item.isVisible()
            self.overlay_pixmap_item.setVisible(not is_visible)
            self.scene.update()
            return not is_visible
        return False
    
    def remove_overlay(self):
        """Remove overlay if exists"""
        if self.overlay_pixmap_item:
            self.scene.removeItem(self.overlay_pixmap_item)
            self.overlay_pixmap_item = None
            self.scene.update()
            return True
        return False