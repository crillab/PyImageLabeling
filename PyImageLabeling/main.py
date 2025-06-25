# -*- coding: utf-8 -*-
"""
Created on Tue Jun 10 10:22:00 2025

@author: pimfa
"""

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
from PyQt6.QtCore import Qt, QPoint, QPointF, QTimer,  QThread, pyqtSignal, QSize, QRectF, QObject, QLineF, QDateTime
import gc
import math
import traceback

from models.ZoomableGraphicsView import ZoomableGraphicsView
from models.OverlayOpacityDialog import OverlayOpacityDialog
from models.PaintSettingsDialog import PaintSettingsDialog, LabelPaintPropertiesDialog
from models.EraseSettingsDialog import EraseSettingsDialog
from models.MagicSettingsDialog import MagicSettingsDialog
from models.tools.PolygonTool import PolygonTool

class ImageViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyImageLabeling")
        self.label_properties_dialogs = []
        # Get screen information
        self.screen = QApplication.primaryScreen()
        self.screen_geometry = self.screen.availableGeometry()
        self.screen_width = self.screen_geometry.width()
        self.screen_height = self.screen_geometry.height()
        
        # Calculate dynamic window size based on screen dimensions
        self.window_width = int(self.screen_width * 0.85)  # Use 85% of screen width
        self.window_height = int(self.screen_height * 0.85)  # Use 85% of screen height
        
        # Set window position and size
        self.setGeometry(
            (self.screen_width - self.window_width) // 2,  # Center horizontally
            (self.screen_height - self.window_height) // 2,  # Center vertically
            self.window_width,
            self.window_height
        )
        
        # Dynamic sizing for components
        self.calculate_component_sizes()
        
        # Icon
        self.setWindowIcon(QIcon(self.get_icon_path("maia2")))
        
        # Central widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Main layout with dynamic stretch factors
        self.main_layout = QHBoxLayout(self.central_widget)
        
        # Initialize UI
        self.setup_ui()
        
        # Current settings
        self.current_image_path = None
        self.current_color = QColor(255, 0, 0)
        self.current_radius = self.calculate_scaled_value(3)  # Scale brush size
        self.current_opacity = 255
        self.current_label = ""
        self.magic_pen_tolerance = 20
        self.max_points_limite = 100000
        self.eraser_size = self.calculate_scaled_value(10)  # Scale eraser size
        self.process_timeout = 10

        self.shortcuts_visible = True
        self.label_properties_dialogs_dict = {}
        self.rectangle_label_properties_dialogs_dict = {}
        self.polygon_label_properties_dialogs_dict = {}

    def calculate_component_sizes(self):
        """Calculate dynamic sizes for UI components based on screen resolution"""
        # Base sizes on screen dimensions with better minimum values
        base_scale = min(self.window_width / 1920, self.window_height / 1080)
        
        # Dynamic grid cells
        self.cell_width = max(100, int(self.window_width / 10))
        self.cell_height = max(80, int(self.window_height / 10))
        
        # Dynamic image container size (scales with window)
        self.image_container_width = int(self.window_width * 0.75)
        self.image_container_height = int(self.window_height * 0.8)
        
        # Dynamic button sizes - ensure reasonable minimums
        self.button_height = max(40, int(self.window_height * 0.05))
        self.button_icon_size = max(24, int(self.button_height * 0.7))
        self.button_min_width = max(80, int(self.window_width * 0.06))
        
        # Control panel width - more adaptive
        self.control_panel_width = max(120, int(self.window_width * 0.12))
        
        # Dynamic spacing - more proportional to screen size
        self.layout_spacing = max(8, int(self.window_width * 0.008))
        
        # Font scaling with better minimum
        self.base_font_size = max(9, int(self.window_width / 180))
        self.app_font = QFont()
        self.app_font.setPointSize(self.base_font_size)
        QApplication.setFont(self.app_font)
        
    def get_icon_path(self, icon_name):
        # Assuming icons are stored in an 'icons' folder next to the script
        icon_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icon')
        return os.path.join(icon_dir, f"{icon_name}.png")
    
    def calculate_scaled_value(self, base_value):
        """Scale a value based on screen resolution"""
        # Calculate a scaling factor based on resolution
        scale_factor = min(self.screen_width / 1920, self.screen_height / 1080)
        scaled_value = max(1, int(base_value * scale_factor))
        return scaled_value
    
    def setup_ui(self):
        # Create central widget with dynamic layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Use a more flexible layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(self.layout_spacing, self.layout_spacing, 
                                      self.layout_spacing, self.layout_spacing)
        main_layout.setSpacing(self.layout_spacing)
        
        # Left side - image area
        image_container = QWidget()
        image_layout = QVBoxLayout(image_container)
        
        # Top buttons row
        button_row = QHBoxLayout()
        
        # Load button with dynamic height
        self.load_button = QPushButton("Load Image")
        self.load_button.setFixedHeight(self.button_height)
        self.load_button.setMinimumWidth(self.button_min_width)
        self.load_button.clicked.connect(self.load_image)
        self.load_button.setToolTip("Click to load an image into the viewer. This will allow you to select an image file from your system to display.")  # Detailed tooltip
        button_row.addWidget(self.load_button)
        
        # Load Layer button with dynamic height
        self.load_layer_button = QPushButton("Load Layer")
        self.load_layer_button.setFixedHeight(self.button_height)
        self.load_layer_button.setMinimumWidth(self.button_min_width)
        self.load_layer_button.clicked.connect(self.load_layer)
        self.load_layer_button.setToolTip("Click to load a new layer on top of the existing image. This allows you to add additional content or annotations to the image.")  # Detailed tooltip
        button_row.addWidget(self.load_layer_button)
        
        # Unload Layer button with dynamic height
        self.unload_layer_button = QPushButton("Unload Layer")
        self.unload_layer_button.setFixedHeight(self.button_height)
        self.unload_layer_button.setMinimumWidth(self.button_min_width)
        self.unload_layer_button.clicked.connect(self.toggle_layer)
        self.unload_layer_button.setToolTip("Click to remove the currently selected layer from the image. This will leave only the base image or other layers you wish to keep.")  # Detailed tooltip
        button_row.addWidget(self.unload_layer_button)
        
        # Save button with dynamic height
        self.save_button = QPushButton("Save Layer")
        self.save_button.setFixedHeight(self.button_height)
        self.save_button.setMinimumWidth(self.button_min_width)
        self.save_button.clicked.connect(self.save_image)
        self.save_button.setToolTip("Click to save the current layer to a file. This will store the layer as a separate image file on your system.")  # Detailed tooltip
        button_row.addWidget(self.save_button)

        self.shortcut_button = QPushButton("Shortcut")
        self.shortcut_button.setFixedHeight(self.button_height)
        self.shortcut_button.setMinimumWidth(self.button_min_width)
        self.shortcut_button.clicked.connect(self.toggle_shortcuts)
        self.shortcut_button.setToolTip("Click to hide/show all label property dialogs or select specific ones.")
        button_row.addWidget(self.shortcut_button)
        
        button_row.addStretch(1)
        image_layout.addLayout(button_row)
        
        # Image display with dynamic sizing
        self.image_label = ZoomableGraphicsView()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("background-color: #ccc; border: 1px solid #000;")
        self.image_label.setMinimumSize(self.image_container_width, self.image_container_height)
        image_layout.addWidget(self.image_label, 1)  # Give it stretch priority
        
        main_layout.addWidget(image_container, 4)  # Set stretch factor for image area
        
        control_panel = QWidget()
        control_panel.setMinimumWidth(self.control_panel_width)
        control_panel.setMaximumWidth(max(200, int(self.window_width * 0.15)))
        
        control_layout = QVBoxLayout(control_panel)
        control_layout.setSpacing(max(8, int(self.button_height * 0.2)))  # Fixed spacing for buttons
        
        # Move Tools Section
        move_tools_label = QLabel("Move Tools")
        move_tools_label.setStyleSheet("font-weight: bold; margin-bottom: 5px;")
        control_layout.addWidget(move_tools_label)
        
        move_tools = [
            ("Move", self.activate_move_mode, True, "move"),
            ("Reset Move/zoom", self.image_label.reset_view, False, "reset"),
        ]
        
        self.tool_buttons = {}
        
        for button_text, callback, checkable, icon_name in move_tools :
            button = QPushButton(button_text)  # Include text for better accessibility
            button.setFixedHeight(self.button_height)
            
            # Add scaled icon to button
            icon_path = self.get_icon_path(icon_name)
            if os.path.exists(icon_path):
                button.setIcon(QIcon(icon_path))
                button.setIconSize(QSize(self.button_icon_size, self.button_icon_size))
            
            # Consistent padding based on button height
            padding = max(4, int(self.button_height * 0.1))
            border_radius = max(4, int(self.button_height * 0.1))
            
            # Enhanced styling with dynamic values but consistent minimums
            button.setStyleSheet(f"""
                QPushButton {{
                    padding: {padding}px;
                    padding-left: {padding * 2}px;
                    padding-right: {padding * 2}px;
                    border: 1px solid #bbb;
                    border-radius: {border_radius}px;
                    background-color: #f0f0f0;
                    color: black;
                    font-size: {self.base_font_size}pt;
                    text-align: left;
                }}
                QPushButton:hover {{
                    background-color: #e0e0e0;
                }}
                QPushButton:pressed {{
                    background-color: #d0d0d0;
                }}
                QPushButton:checked {{
                    background-color: #c0c0c0;
                    border: 2px solid #808080;
                }}
            """)
            
            if checkable:
                button.setCheckable(True)
            
            # Set tooltip for Move tools with specific function explanation
            if button_text == "Move":
                button.setToolTip("Click to activate Move mode. This allows you to move the image around in the viewer by dragging it.")
            elif button_text == "Reset Move/zoom":
                button.setToolTip("Click to reset the image's position and zoom level to the default view.")
            
            button.clicked.connect(callback)
            control_layout.addWidget(button)
            
            # Store reference in dictionary for easy access
            self.tool_buttons[button_text] = button
        
        # Separator (for better UI clarity)
        control_layout.addSpacing(10)
        separator = QLabel("──────────────────")  # Fake visual separator
        separator.setStyleSheet("color: gray;")
        control_layout.addWidget(separator)
        
        # Layer Tools Section
        layer_tools_label = QLabel("Layer Tools")
        layer_tools_label.setStyleSheet("font-weight: bold; margin-bottom: 5px;")
        control_layout.addWidget(layer_tools_label)
        
        layer_tools = [
            ("Undo", self.undo_last_stroke, False, "back"),
            ("Opacity", self.toggle_opacity_mode, False, "opacity"),
            ("Contour Filling", self.toggle_contour_mode, True, "fill"),
            ("Paintbrush", self.toggle_paint_mode, True, "paint"),
            ("Magic Pen", self.toggle_magic_pen, True, "magic"),
            ("Rectangle", self.toggle_rectangle_select, True, "select"),
            ("Polygon", self.toggle_polygon_select, True, "polygon"),
            ("Eraser", self.toggle_erase_mode, True, "eraser"),
            ("Clear All", self.toggle_clear, False, "cleaner"),
        ]
        
        for button_text, callback, checkable, icon_name in layer_tools :
            button = QPushButton(button_text)  # Include text for better accessibility
            button.setFixedHeight(self.button_height)
            
            # Add scaled icon to button
            icon_path = self.get_icon_path(icon_name)
            if os.path.exists(icon_path):
                button.setIcon(QIcon(icon_path))
                button.setIconSize(QSize(self.button_icon_size, self.button_icon_size))
            
            # Consistent padding based on button height
            padding = max(4, int(self.button_height * 0.1))
            border_radius = max(4, int(self.button_height * 0.1))
            
            # Enhanced styling with dynamic values but consistent minimums
            button.setStyleSheet(f"""
                QPushButton {{
                    padding: {padding}px;
                    padding-left: {padding * 2}px;
                    padding-right: {padding * 2}px;
                    border: 1px solid #bbb;
                    border-radius: {border_radius}px;
                    background-color: #f0f0f0;
                    color: black;
                    font-size: {self.base_font_size}pt;
                    text-align: left;
                }}
                QPushButton:hover {{
                    background-color: #e0e0e0;
                }}
                QPushButton:pressed {{
                    background-color: #d0d0d0;
                }}
                QPushButton:checked {{
                    background-color: #c0c0c0;
                    border: 2px solid #808080;
                }}
            """)
            
            if checkable:
                button.setCheckable(True)
            
            # Set tooltips for Layer tools with specific explanations
            if button_text == "Undo":
                button.setToolTip("Click to undo the last drawing action or modification.")
            elif button_text == "Opacity":
                button.setToolTip("Click to toggle opacity mode, allowing you to adjust the transparency of layers.")
            elif button_text == "Contour Filling":
                button.setToolTip("Click to activate contour filling mode, which lets you fill in outlines of objects.")
            elif button_text == "Paintbrush":
                button.setToolTip("Click to activate paintbrush mode, allowing you to draw freely on the image.")
            elif button_text == "Magic Pen":
                button.setToolTip("Click to activate the Magic Pen mode for drawing precise, automated strokes.")
            elif button_text == "Rectangle":
                button.setToolTip("Click to activate the rectangle select tool for creating rectangular selections.")
            elif button_text == "Polygon":
                button.setToolTip("Click to activate the polygon select tool for creating polygon selections.")
            elif button_text == "Eraser":
                button.setToolTip("Click to activate the eraser tool, allowing you to erase parts of the image or layer.")
            elif button_text == "Clear All":
                button.setToolTip("Click to clear all layers and reset the image to its original state.")
            
            button.clicked.connect(callback)
            control_layout.addWidget(button)
            
            # Store reference in dictionary for easy access
            self.tool_buttons[button_text] = button
        
        control_layout.addStretch(1)
        main_layout.addWidget(control_panel, 1)  # Set appropriate stretch factor

        
        # Store references to toggleable buttons using the dictionary
        self.paint_button = self.tool_buttons["Paintbrush"]
        self.eraser_button = self.tool_buttons["Eraser"]
        self.magic_pen_button = self.tool_buttons["Magic Pen"]
        self.contour_button = self.tool_buttons["Contour Filling"]
        self.select = self.tool_buttons["Rectangle"]
        self.polygon = self.tool_buttons["Polygon"]
        self.move_button = self.tool_buttons["Move"]
        # Apply high DPI scaling
        self.handle_high_dpi_screens()

    
    def handle_high_dpi_screens(self):
        """Apply additional adjustments for high DPI screens"""
        # Check if we're on a high DPI screen
        dpi = self.screen.logicalDotsPerInch()
        if dpi > 120:  # Higher than standard DPI
            # Calculate DPI scaling factor
            dpi_scale = dpi / 96.0
            
            # Adjust button sizes based on DPI
            for button in self.findChildren(QPushButton):
                current_height = button.height()
                scaled_height = max(current_height, int(current_height * dpi_scale * 0.8))
                button.setMinimumHeight(scaled_height)
            
            # Make scrollbars more touchable on high DPI screens
            scrollbar_width = max(12, int(16 * dpi_scale))
            self.image_label.setStyleSheet(
                self.image_label.styleSheet() + 
                f"""
                QScrollBar:vertical {{
                    width: {scrollbar_width}px;
                }}
                QScrollBar:horizontal {{
                    height: {scrollbar_width}px;
                }}
                """
            )
    
    def resizeEvent(self, event):
        """Handle window resize events to adjust layout"""
        super().resizeEvent(event)
        
        # Recalculate component sizes based on new window size
        self.window_width = self.width()
        self.window_height = self.height()
        self.calculate_component_sizes()
        
        # Update sizes of critical components
        if hasattr(self, 'image_label'):
            self.image_label.setMinimumSize(self.image_container_width, self.image_container_height)
        
        # Update button styling
        if hasattr(self, 'tool_buttons'):
            for button in self.tool_buttons.values():
                padding = max(4, int(self.button_height * 0.1))
                border_radius = max(4, int(self.button_height * 0.1))
                button.setStyleSheet(f"""
                    QPushButton {{
                        padding: {padding}px;
                        padding-left: {padding * 2}px;
                        padding-right: {padding * 2}px;
                        border: 1px solid #bbb;
                        border-radius: {border_radius}px;
                        background-color: #f0f0f0;
                        color: black;
                        font-size: {self.base_font_size}pt;
                        text-align: left;
                    }}
                    QPushButton:hover {{
                        background-color: #e0e0e0;
                    }}
                    QPushButton:pressed {{
                        background-color: #d0d0d0;
                    }}
                    QPushButton:checked {{
                        background-color: #c0c0c0;
                        border: 2px solid #808080;
                    }}
                """)
                button.setFixedHeight(self.button_height)
                button.setIconSize(QSize(self.button_icon_size, self.button_icon_size))
        
        # Update the UI
        self.update()
    
    def toggle_contour_mode(self):
        """Toggles between applying contour and filling contour on click."""
        if not hasattr(self.image_label, 'base_pixmap') or self.image_label.base_pixmap is None:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Error")
            msg_box.setText("No image loaded.")
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #000000;  /* Pure black background */
                    color: white;  /* White text */
                    font-size: 14px;
                    border: 1px solid #444444;
                }
                QLabel {
                    color: white;  /* Ensures the message text is white */
                    background-color: #000000;
                }
                QPushButton {
                    background-color: #000000;  /* Black buttons */
                    color: white;
                    border: 1px solid #555555;
                    border-radius: 5px;
                    padding: 5px 10px;
                }
                QPushButton:hover {
                    background-color: #222222;  /* Slightly lighter on hover */
                }
            """)
            msg_box.exec() 
            return
    
        if not hasattr(self, "contour_mode_active"):
            self.contour_mode_active = False  # Initialize state
    
        if self.contour_mode_active:
            # If contour mode is active, turn it off
            self.image_label.remove_overlay()  
            self.contour_mode_active = False
            self.image_label.shape_fill_mode = False  
            self.activate_move_mode(True)
        else:
            # If contour mode is off, turn it on
            self.image_label.apply_contour()  # Apply contour detection
            self.contour_mode_active = True
            self.image_label.shape_fill_mode = True  # Enable filling behavior
            self.contour_button.setChecked(True)
            
            self.paint_button.setChecked(False)
            self.eraser_button.setChecked(False)   
            self.magic_pen_button.setChecked(False)
            self.select.setChecked(False)  
            self.image_label.paint_mode = False
            self.image_label.erase_mode = False
            self.image_label.toggle_rectangle_mode(False)
            self.move_button.setChecked(False)
            
    def activate_move_mode(self, checked=None):
        """Activates move mode and disables other tools."""
        if checked is None:
            checked = not self.move_button.isChecked()  # Toggle if not explicitly set
        
        if checked:
            # When enabling move mode, disable all other tool buttons
            self.paint_button.setChecked(False)
            self.eraser_button.setChecked(False)
            self.magic_pen_button.setChecked(False)
            self.contour_button.setChecked(False)
            self.select.setChecked(False)
            self.polygon.setChecked(False)
            
            # Disable other modes in the image label
            self.image_label.paint_mode = False
            self.image_label.erase_mode = False
            self.image_label.magic_pen_mode = False
            self.image_label.shape_fill_mode = False
            self.image_label.toggle_rectangle_mode(False)
            self.move_button.setChecked(True)
        else:
            # Disable drag mode when move is turned off
            self.image_label.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.move_button.setChecked(False)
            
    def initialize_move_mode(self):
        """Set move mode as the default when application starts"""
        self.activate_move_mode(True) 
        
    def finalize_setup(self):
        # Call this at the end of setup_ui
        self.activate_move_mode(True) 
        
    def toggle_magic_pen(self, enabled): 
        if enabled:
            settings_dialog = MagicSettingsDialog(self, current_tolerance=self.magic_pen_tolerance, current_timeout=self.process_timeout, current_max_points=self.max_points_limite)
            if settings_dialog.exec():
                # Store selected tolerance
                self.image_label.magic_pen_tolerance = settings_dialog.get_tolerance()
                self.image_label.process_timeout = settings_dialog.get_timeout()
                self.image_label.max_points_limite= settings_dialog.get_max_points_limit()
                
                self.image_label.toggle_magic_pen(True)
                
                self.paint_button.setChecked(False)
                self.eraser_button.setChecked(False)   
                self.select.setChecked(False)  
                self.contour_button.setChecked(False)
                self.move_button.setChecked(False)
                self.polygon.setChecked(False)

                self.image_label.paint_mode = False
                self.image_label.erase_mode = False
                self.image_label.toggle_rectangle_mode(False)
            else:
                self.magic_pen_button.setChecked(False) 
                self.activate_move_mode(True)
        else:
            self.image_label.toggle_magic_pen(False)
            self.activate_move_mode(True)
        
    def toggle_paint_mode(self, enabled):
        if enabled:
            settings_dialog = PaintSettingsDialog(
                self,
                current_color=self.current_color,
                current_radius=self.current_radius,
                current_opacity=self.current_opacity,
                current_label=self.current_label
            )
            if settings_dialog.exec():
                # Store the settings
                self.current_color, self.current_radius, self.current_opacity, self.current_label = settings_dialog.get_settings()
                
                # Apply settings to the image label
                self.image_label.point_color = self.current_color
                self.image_label.point_radius = self.current_radius
                self.image_label.point_opacity = self.current_opacity
                self.image_label.point_label = self.current_label
                
                self.image_label.toggle_paint_mode(True)
                self.eraser_button.setChecked(False)
                self.magic_pen_button.setChecked(False)
                self.select.setChecked(False)  
                self.contour_button.setChecked(False)
                self.move_button.setChecked(False)
                self.polygon.setChecked(False)

                self.image_label.erase_mode = False
                self.image_label.magic_pen_mode = False
                self.image_label.toggle_rectangle_mode(False)

                self.show_label_properties()
            else:
                self.paint_button.setChecked(False)
                self.activate_move_mode(True)
        else:
            self.image_label.toggle_paint_mode(False)
            self.activate_move_mode(True)

    def activate_paint_tool_with_properties(self, label, color, radius, opacity):
        """Activate paint tool with specific label properties"""
        # Set the current properties
        self.current_label = label
        self.current_color = color
        self.current_radius = radius
        self.current_opacity = opacity
        
        # Apply settings to the image label
        if hasattr(self, 'image_label'):
            self.image_label.point_color = color
            self.image_label.point_radius = radius
            self.image_label.point_opacity = opacity
            self.image_label.point_label = label
            
            # Activate paint mode
            self.image_label.toggle_paint_mode(True)
            
            # Deactivate other modes
            self.image_label.erase_mode = False
            self.image_label.magic_pen_mode = False
            self.image_label.toggle_rectangle_mode(False)
            self.image_label.toggle_polygon_mode(False)
        
        # Update UI buttons
        if hasattr(self, 'paint_button'):
            self.paint_button.setChecked(True)
        if hasattr(self, 'eraser_button'):
            self.eraser_button.setChecked(False)
        if hasattr(self, 'magic_pen_button'):  
            self.magic_pen_button.setChecked(False)
        if hasattr(self, 'select'):
            self.select.setChecked(False)
        if hasattr(self, 'contour_button'):
            self.contour_button.setChecked(False)
        if hasattr(self, 'move_button'):  
            self.move_button.setChecked(False)
        if hasattr(self, 'polygon'):
            self.polygon.setChecked(False)

    def on_label_properties_widget_clicked(self):
        """Handle click on label properties widget to activate paint tool"""
        # Define the properties you want to set
        label = self.current_label  # Use the current label
        color = self.current_color  # Use the current color
        radius = self.current_radius  # Use the current radius
        opacity = self.current_opacity  # Use the current opacity

        # Call the method to activate the paint tool with the specified properties
        self.activate_paint_tool_with_properties(label, color, radius, opacity)
        
        # Optional: Print debug info to verify the click is registered
        print(f"Activating paint tool with: Label={label}, Color={color}, Radius={radius}, Opacity={opacity}")
        
    def toggle_paint_mode(self, enabled):
        if enabled:
            settings_dialog = PaintSettingsDialog(
                self,
                current_color=self.current_color,
                current_radius=self.current_radius,
                current_opacity=self.current_opacity,
                current_label=self.current_label
            )
            if settings_dialog.exec():
                # Store the settings
                self.current_color, self.current_radius, self.current_opacity, self.current_label = settings_dialog.get_settings()
                
                # Apply settings to the image label
                self.image_label.point_color = self.current_color
                self.image_label.point_radius = self.current_radius
                self.image_label.point_opacity = self.current_opacity
                self.image_label.point_label = self.current_label
                
                self.image_label.toggle_paint_mode(True)
                self.eraser_button.setChecked(False)
                self.magic_pen_button.setChecked(False)
                self.select.setChecked(False)  
                self.contour_button.setChecked(False)
                self.move_button.setChecked(False)
                self.polygon.setChecked(False)

                self.image_label.erase_mode = False
                self.image_label.magic_pen_mode = False
                self.image_label.toggle_rectangle_mode(False)

                self.show_label_properties()
            else:
                self.paint_button.setChecked(False)
                self.activate_move_mode(True)
        else:
            self.image_label.toggle_paint_mode(False)
            self.activate_move_mode(True)

    def activate_paint_tool_with_properties(self, label, color, radius, opacity):
        """Activate paint tool with specific label properties"""
        # Set the current properties
        self.current_label = label
        self.current_color = color
        self.current_radius = radius
        self.current_opacity = opacity
        
        # Apply settings to the image label
        if hasattr(self, 'image_label'):
            self.image_label.point_color = color
            self.image_label.point_radius = radius
            self.image_label.point_opacity = opacity
            self.image_label.point_label = label
            
            # Activate paint mode
            self.image_label.toggle_paint_mode(True)
            
            # Deactivate other modes
            self.image_label.erase_mode = False
            self.image_label.magic_pen_mode = False
            self.image_label.toggle_rectangle_mode(False)
        
        # Update UI buttons
        if hasattr(self, 'paint_button'):
            self.paint_button.setChecked(True)
        if hasattr(self, 'eraser_button'):
            self.eraser_button.setChecked(False)
        if hasattr(self, 'magic_pen_button'):  
            self.magic_pen_button.setChecked(False)
        if hasattr(self, 'select'):
            self.select.setChecked(False)
        if hasattr(self, 'contour_button'):
            self.contour_button.setChecked(False)
        if hasattr(self, 'move_button'):  
            self.move_button.setChecked(False)
        if hasattr(self, 'polygon'):
            self.polygon.setChecked(False)

    def on_label_properties_widget_clicked(self):
        """Handle click on label properties widget to activate paint tool"""
        # Define the properties you want to set
        label = self.current_label  # Use the current label
        color = self.current_color  # Use the current color
        radius = self.current_radius  # Use the current radius
        opacity = self.current_opacity  # Use the current opacity

        # Call the method to activate the paint tool with the specified properties
        self.activate_paint_tool_with_properties(label, color, radius, opacity)
        
        # Optional: Print debug info to verify the click is registered
        print(f"Activating paint tool with: Label={label}, Color={color}, Radius={radius}, Opacity={opacity}")

    def show_label_properties(self):
        # Initialize the dictionary if it doesn't exist
        if not hasattr(self, 'label_properties_dialogs_dict'):
            self.label_properties_dialogs_dict = {}
        
        # Check if a dialog for this label already exists
        if self.current_label in self.label_properties_dialogs_dict:
            # Get the existing dialog
            existing_dialog = self.label_properties_dialogs_dict[self.current_label]
            
            # Check if the dialog still exists and is valid
            if existing_dialog and not existing_dialog.isHidden():
                # Update the existing dialog with current properties
                existing_dialog.update_properties(
                    self.current_label,
                    self.current_color,
                    self.current_radius,
                    self.current_opacity
                )
                # Bring the existing dialog to front
                existing_dialog.raise_()
                existing_dialog.activateWindow()
                return
            else:
                # Remove the invalid dialog from the dictionary
                del self.label_properties_dialogs_dict[self.current_label]

        total_dialogs = len(self.label_properties_dialogs_dict) + len(self.rectangle_label_properties_dialogs_dict)
        if total_dialogs == 0:
            self.shortcut_button.setText("Hide Shortcuts")
        elif not self.label_properties_dialogs_dict:
            self.shortcut_button.setText("Hide Shortcuts")

        # Create a new dialog only if one doesn't exist for this label
        label_properties_dialog = LabelPaintPropertiesDialog(self)
        
        # Update the properties
        label_properties_dialog.update_properties(
            self.current_label,
            self.current_color,
            self.current_radius,
            self.current_opacity
        )
        
        # Store the dialog in the dictionary with the label as key
        self.label_properties_dialogs_dict[self.current_label] = label_properties_dialog
        
        # Connect the dialog's close event to clean up the dictionary
        def on_dialog_closed():
            if self.current_label in self.label_properties_dialogs_dict:
                del self.label_properties_dialogs_dict[self.current_label]
        
        # Connect to the finished signal (emitted when dialog is closed)
        label_properties_dialog.finished.connect(on_dialog_closed)

        widgets_to_try = [
            'properties_widget',
            'label_widget', 
            'paint_widget',
            'main_widget',
            'content_widget',
            'central_widget'
        ]
        
        connected = False
        for widget_name in widgets_to_try:
            if hasattr(label_properties_dialog, widget_name):
                widget = getattr(label_properties_dialog, widget_name)
                if hasattr(widget, 'clicked'):
                    try:
                        widget.clicked.disconnect()
                    except:
                        pass
                    widget.clicked.connect(self.on_label_properties_widget_clicked)
                    print(f"Connected click signal to {widget_name} for label: {self.current_label}")
                    connected = True
                    break
                elif hasattr(widget, 'mousePressEvent'):
                    # For non-button widgets, override mousePressEvent
                    widget.mousePressEvent = lambda event: self.on_label_properties_widget_clicked()
                    print(f"Connected mouse press event to {widget_name} for label: {self.current_label}")
                    connected = True
                    break
        
        if not connected:
            print("Warning: Could not find clickable widget in dialog")
            print(f"Available attributes: {[attr for attr in dir(label_properties_dialog) if not attr.startswith('_')]}")
            
            # Fallback: Make the entire dialog clickable
            original_mouse_press = label_properties_dialog.mousePressEvent
            def dialog_mouse_press(event):
                self.on_label_properties_widget_clicked()
                if original_mouse_press:
                    original_mouse_press(event)
            label_properties_dialog.mousePressEvent = dialog_mouse_press
            print("Using fallback: entire dialog is now clickable")
        
        # Show the dialog
        label_properties_dialog.show()
        
        # Position the dialog at the top of the screen
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        x = screen_geometry.width() - label_properties_dialog.width() - 10
        
        # Calculate y position based on existing dialogs
        existing_dialogs = [d for d in self.label_properties_dialogs_dict.values() if d and d.isVisible()]
        y = 10 + len(existing_dialogs) * (label_properties_dialog.height() + 10)
        
        label_properties_dialog.move(x, y)

    def toggle_shortcuts(self):
        """Toggle visibility of all label properties dialogs or show selection menu"""
        # Get dictionaries safely - they might be in different objects
        paint_dialogs = getattr(self, 'label_properties_dialogs_dict', {})
        rectangle_dialogs = getattr(self, 'rectangle_label_properties_dialogs_dict', {})
        polygon_dialogs = getattr(self, 'polygon_label_properties_dialogs_dict', {})
        
        # Also check if rectangle dialogs are in another object (like ZoomableGraphicsView)
        if hasattr(self, 'image_label') and hasattr(self.image_label, 'rectangle_label_properties_dialogs_dict'):
            rectangle_dialogs = self.image_label.rectangle_label_properties_dialogs_dict
        if hasattr(self, 'image_label') and hasattr(self.image_label, 'polygon_label_properties_dialogs_dict'):
            polygon_dialogs = self.image_label.polygon_label_properties_dialogs_dict
        
        total_dialogs = len(paint_dialogs) + len(rectangle_dialogs) + len(polygon_dialogs)
        
        if total_dialogs == 0:
            QMessageBox.information(self, "No Labels", "No label properties dialogs are currently open.")
            return
        
        # If more than 3 dialogs total, show selection menu
        if total_dialogs > 3:
            self.show_shortcut_selection_menu()
        else:
            # Simple toggle for few dialogs
            if self.shortcuts_visible:
                self.hide_all_shortcuts()
            else:
                self.show_all_shortcuts()

    def show_shortcut_selection_menu(self):
        """Show a menu to select which dialogs to show/hide"""
        menu = QMenu(self)
        
        # Get dictionaries safely
        paint_dialogs = getattr(self, 'label_properties_dialogs_dict', {})
        rectangle_dialogs = getattr(self, 'rectangle_label_properties_dialogs_dict', {})
        polygon_dialogs = getattr(self, 'polygon_label_properties_dialogs_dict', {})
        
        # Check if rectangle dialogs are in another object
        if hasattr(self, 'image_label') and hasattr(self.image_label, 'rectangle_label_properties_dialogs_dict'):
            rectangle_dialogs = self.image_label.rectangle_label_properties_dialogs_dict
        if hasattr(self, 'image_label') and hasattr(self.image_label, 'polygon_label_properties_dialogs_dict'):
            polygon_dialogs = self.image_label.polygon_label_properties_dialogs_dict

        # Add "Toggle All" option
        toggle_all_action = menu.addAction("Toggle All")
        toggle_all_action.triggered.connect(self.toggle_all_shortcuts)
        menu.addSeparator()
        
        # Add paint label options
        if paint_dialogs:
            paint_submenu = menu.addMenu("Paint Labels")
            for label, dialog in paint_dialogs.items():
                if dialog and not dialog.isHidden():
                    action = paint_submenu.addAction(f"Hide: {label}")
                    action.triggered.connect(lambda checked, l=label, t="paint": self.hide_specific_shortcut(l, t))
                else:
                    action = paint_submenu.addAction(f"Show: {label}")
                    action.triggered.connect(lambda checked, l=label, t="paint": self.show_specific_shortcut(l, t))
        
        # Add rectangle label options
        if rectangle_dialogs:
            rectangle_submenu = menu.addMenu("Rectangle Labels")
            for label, dialog in rectangle_dialogs.items():
                if dialog and not dialog.isHidden():
                    action = rectangle_submenu.addAction(f"Hide: {label}")
                    action.triggered.connect(lambda checked, l=label, t="rectangle": self.hide_specific_shortcut(l, t))
                else:
                    action = rectangle_submenu.addAction(f"Show: {label}")
                    action.triggered.connect(lambda checked, l=label, t="rectangle": self.show_specific_shortcut(l, t))

        if polygon_dialogs:
            polygon_submenu = menu.addMenu("Polygon Labels")
            for label, dialog in polygon_dialogs.items():
                if dialog and not dialog.isHidden():
                    action = polygon_submenu.addAction(f"Hide: {label}")
                    action.triggered.connect(lambda checked, l=label, t="polygon": self.hide_specific_shortcut(l, t))
                else:
                    action = polygon_submenu.addAction(f"Show: {label}")
                    action.triggered.connect(lambda checked, l=label, t="polygon": self.show_specific_shortcut(l, t))
        
        # Show menu at button position
        button_pos = self.shortcut_button.mapToGlobal(self.shortcut_button.rect().bottomLeft())
        menu.exec(button_pos)

    def toggle_all_shortcuts(self):
        """Toggle all shortcuts at once"""
        if self.shortcuts_visible:
            self.hide_all_shortcuts()
        else:
            self.show_all_shortcuts()

    def hide_all_shortcuts(self):
        """Hide all label properties dialogs"""
        # Hide paint dialogs
        paint_dialogs = getattr(self, 'label_properties_dialogs_dict', {})
        for dialog in paint_dialogs.values():
            if dialog and dialog.isVisible():
                dialog.hide()
        
        # Hide rectangle dialogs
        rectangle_dialogs = getattr(self, 'rectangle_label_properties_dialogs_dict', {})
        if hasattr(self, 'image_label') and hasattr(self.image_label, 'rectangle_label_properties_dialogs_dict'):
            rectangle_dialogs = self.image_label.rectangle_label_properties_dialogs_dict
        
        for dialog in rectangle_dialogs.values():
            if dialog and dialog.isVisible():
                dialog.hide()
        
        polygon_dialogs = getattr(self, 'polygon_label_properties_dialogs_dict', {})
        if hasattr(self, 'image_label') and hasattr(self.image_label, 'polygon_label_properties_dialogs_dict'):
            polygon_dialogs = self.image_label.polygon_label_properties_dialogs_dict
        
        for dialog in polygon_dialogs.values():
            if dialog and dialog.isVisible():
                dialog.hide()

        self.shortcuts_visible = False
        self.shortcut_button.setText("Show Shortcuts")

    def show_all_shortcuts(self):
        """Show all label properties dialogs"""
        # Show paint dialogs
        paint_dialogs = getattr(self, 'label_properties_dialogs_dict', {})
        for dialog in paint_dialogs.values():
            if dialog:
                dialog.show()
        
        # Show rectangle dialogs
        rectangle_dialogs = getattr(self, 'rectangle_label_properties_dialogs_dict', {})
        if hasattr(self, 'image_label') and hasattr(self.image_label, 'rectangle_label_properties_dialogs_dict'):
            rectangle_dialogs = self.image_label.rectangle_label_properties_dialogs_dict
        
        for dialog in rectangle_dialogs.values():
            if dialog:
                dialog.show()
        
        polygon_dialogs = getattr(self, 'polygon_label_properties_dialogs_dict', {})
        if hasattr(self, 'image_label') and hasattr(self.image_label, 'polygon_label_properties_dialogs_dict'):
            polygon_dialogs = self.image_label.polygon_label_properties_dialogs_dict
        
        for dialog in polygon_dialogs.values():
            if dialog:
                dialog.show()

        self.shortcuts_visible = True
        self.shortcut_button.setText("Hide Shortcuts")

    def hide_specific_shortcut(self, label, dialog_type="paint"):
        """Hide a specific label properties dialog"""
        if dialog_type == "paint":
            paint_dialogs = getattr(self, 'label_properties_dialogs_dict', {})
            if label in paint_dialogs:
                dialog = paint_dialogs[label]
                if dialog:
                    dialog.hide()

        elif dialog_type == "rectangle":
            rectangle_dialogs = getattr(self, 'rectangle_label_properties_dialogs_dict', {})
            if hasattr(self, 'image_label') and hasattr(self.image_label, 'rectangle_label_properties_dialogs_dict'):
                rectangle_dialogs = self.image_label.rectangle_label_properties_dialogs_dict
            
            if label in rectangle_dialogs:
                dialog = rectangle_dialogs[label]
                if dialog:
                    dialog.hide()

        elif dialog_type == "polygon":
            polygon_dialogs = getattr(self, 'polygon_label_properties_dialogs_dict', {})
            if hasattr(self, 'image_label') and hasattr(self.image_label, 'polygon_label_properties_dialogs_dict'):
                polygon_dialogs = self.image_label.polygon_label_properties_dialogs_dict
            
            if label in polygon_dialogs:
                dialog = polygon_dialogs[label]
                if dialog:
                    dialog.hide()

    def show_specific_shortcut(self, label, dialog_type="paint"):
        """Show a specific label properties dialog"""
        if dialog_type == "paint":
            paint_dialogs = getattr(self, 'label_properties_dialogs_dict', {})
            if label in paint_dialogs:
                dialog = paint_dialogs[label]
                if dialog:
                    dialog.show()
        elif dialog_type == "rectangle":
            rectangle_dialogs = getattr(self, 'rectangle_label_properties_dialogs_dict', {})
            if hasattr(self, 'image_label') and hasattr(self.image_label, 'rectangle_label_properties_dialogs_dict'):
                rectangle_dialogs = self.image_label.rectangle_label_properties_dialogs_dict
            
            if label in rectangle_dialogs:
                dialog = rectangle_dialogs[label]
                if dialog:
                    dialog.show()
        elif dialog_type == "polygon":
            polygon_dialogs = getattr(self, 'polygon_label_properties_dialogs_dict', {})
            if hasattr(self, 'image_label') and hasattr(self.image_label, 'polygon_label_properties_dialogs_dict'):
                polygon_dialogs = self.image_label.polygon_label_properties_dialogs_dict
            
            if label in polygon_dialogs:
                dialog = polygon_dialogs[label]
                if dialog:
                    dialog.show()

    def toggle_erase_mode(self, enabled):
        if enabled :
            settings_dialog = EraseSettingsDialog(self, current_eraser_size=self.eraser_size, absolute_mode=getattr(self.image_label, 'absolute_erase_mode', False))
            if settings_dialog.exec():
                self.eraser_size, absolute_mode = settings_dialog.get_settings()
                self.image_label.eraser_size = self.eraser_size
                self.image_label.absolute_erase_mode = absolute_mode
                self.image_label.toggle_erase_mode(True)
                self.paint_button.setChecked(False)
                self.select.setChecked(False)  
                self.contour_button.setChecked(False)
                self.magic_pen_button.setChecked(False)
                self.move_button.setChecked(False)
                self.polygon.setChecked(False)

                self.image_label.paint_mode = False
                self.image_label.magic_pen_mode = False
                self.image_label.toggle_rectangle_mode(False)
            else:
                self.eraser_button.setChecked(False)
                self.activate_move_mode(True)
        else:
            self.image_label.toggle_erase_mode(False)
            self.activate_move_mode(True)
            
    def toggle_opacity_mode(self, enabled):
        settings_dialog = OverlayOpacityDialog(self, current_opacity=self.image_label.overlay_opacity)
        
        # Aperçu en temps réel pendant que l'utilisateur bouge le slider
        settings_dialog.slider.valueChanged.connect(
            lambda value: self.image_label.update_overlay_opacity(value)
        )
        
        if settings_dialog.exec():
            new_opacity = settings_dialog.slider.value()
            self.image_label.update_overlay_opacity(new_opacity)
        else:
            # Si l'utilisateur annule, remet l'ancienne valeur
            self.image_label.update_overlay_opacity(self.image_label.overlay_opacity)
    
    def toggle_rectangle_select(self, checked):
        """Toggle rectangle selection mode and deactivate other tools"""
        if checked:
            # Show dialog to choose between YOLO and Classification
            choice_dialog = QDialog(self)
            choice_dialog.setWindowTitle("Rectangle Mode Selection")
            choice_dialog.setMinimumWidth(300)
            choice_dialog.setStyleSheet("""
                QDialog {
                    background-color: #000000;
                    color: white;
                    border: 1px solid #444444;
                }
                QLabel {
                    color: white;
                    font-size: 14px;
                }
                QPushButton {
                    background-color: #000000;
                    color: white;
                    border: 1px solid #555555;
                    border-radius: 5px;
                    padding: 5px 10px;
                    margin: 5px;
                }
                QPushButton:hover {
                    background-color: #222222;
                }
            """)

            layout = QVBoxLayout()
            layout.addWidget(QLabel("Select rectangle mode:"))
            
            button_layout = QHBoxLayout()
            yolo_button = QPushButton("Label-free")
            classification_button = QPushButton("Labelisation")
            cancel_button = QPushButton("Cancel")
            
            button_layout.addWidget(yolo_button)
            button_layout.addWidget(classification_button)
            button_layout.addWidget(cancel_button)
            
            layout.addLayout(button_layout)
            choice_dialog.setLayout(layout)
            
            # Track which mode was selected
            selected_mode = None
            
            def select_yolo():
                nonlocal selected_mode
                selected_mode = "yolo"
                choice_dialog.accept()
            
            def select_classification():
                nonlocal selected_mode
                selected_mode = "classification"
                choice_dialog.accept()
            
            # Connect buttons
            yolo_button.clicked.connect(select_yolo)
            classification_button.clicked.connect(select_classification)
            cancel_button.clicked.connect(choice_dialog.reject)
            
            # Show dialog and get result
            result = choice_dialog.exec()
            
            if result != 1 or selected_mode is None:  # User cancelled or closed dialog
                self.select.setChecked(False)  # Uncheck the rectangle button
                return
            
            # Store the selected mode
            self.rectangle_mode_type = selected_mode
            
            # First, uncheck all other tool buttons
            self.paint_button.setChecked(False)
            self.eraser_button.setChecked(False)
            self.magic_pen_button.setChecked(False)
            self.contour_button.setChecked(False)
            self.move_button.setChecked(False)
            self.polygon.setChecked(False)
            
            self.image_label.paint_mode = False
            self.image_label.erase_mode = False
            self.image_label.magic_pen_mode = False
            self.image_label.toggle_polygon_mode(False)
            
            # Enable rectangle mode
            self.image_label.toggle_rectangle_mode(True)
            
            # Set the rectangle mode type in the image_label
            self.image_label.rectangle_mode_type = selected_mode
            
        else:
            # When turning off rectangle mode, clear all active selections
            self.image_label.toggle_rectangle_mode(False)
            self.image_label.clear_rectangles() 
            self.activate_move_mode(True)

    def activate_rectangle_tool_with_properties(self, label, color, thickness):
        """Activate rectangle tool with specific label properties"""
        # Set the current properties
        self.current_rectangle_label = label
        self.current_rectangle_color = color
        self.current_rectangle_thickness = thickness
        
        # Apply settings to the image label
        if hasattr(self, 'image_label'):
            self.image_label.rectangle_color = color
            self.image_label.rectangle_thickness = thickness
            self.image_label.rectangle_label = label
            
            # Activate rectangle mode
            self.image_label.toggle_rectangle_mode(True)
            
            # Deactivate other modes
            self.image_label.toggle_paint_mode(False)
            self.image_label.toggle_polygon_mode(False)
            self.image_label.erase_mode = False
            self.image_label.magic_pen_mode = False
        
        # Update UI buttons
        if hasattr(self, 'select'):  
            self.select.setChecked(True)
        if hasattr(self, 'paint_button'):
            self.paint_button.setChecked(False)
        if hasattr(self, 'eraser_button'):
            self.eraser_button.setChecked(False)
        if hasattr(self, 'magic_pen_button'):  
            self.magic_pen_button.setChecked(False)
        if hasattr(self, 'contour_button'):
            self.contour_button.setChecked(False)
        if hasattr(self, 'move_button'):  
            self.move_button.setChecked(False)
        if hasattr(self, 'polygon'):
            self.polygon.setChecked(False)
        
        print(f"Rectangle tool activated with: Label={label}, Color={color}, Thickness={thickness}")
    
    def activate_polygon_tool_with_properties(self, label, color, thickness):
            """Activate rectangle tool with specific label properties"""
            # Set the current properties
            self.current_polygon_label = label
            self.current_polygon_color = color
            self.current_polygon_thickness = thickness
            
            # Apply settings to the image label
            if hasattr(self, 'image_label'):
                PolygonTool.default_polygon_color = color
                PolygonTool.default_polygon_thickness = thickness
                PolygonTool.last_used_label = label
                
                # Activate rectangle mode
                self.image_label.toggle_polygon_mode(True)
                
                # Deactivate other modes
                self.image_label.toggle_paint_mode(False)
                self.image_label.toggle_rectangle_mode(False)
                self.image_label.erase_mode = False
                self.image_label.magic_pen_mode = False
            
            # Update UI buttons
            if hasattr(self, 'select'):  
                self.select.setChecked(False)
            if hasattr(self, 'paint_button'):
                self.paint_button.setChecked(False)
            if hasattr(self, 'eraser_button'):
                self.eraser_button.setChecked(False)
            if hasattr(self, 'magic_pen_button'):  
                self.magic_pen_button.setChecked(False)
            if hasattr(self, 'contour_button'):
                self.contour_button.setChecked(False)
            if hasattr(self, 'move_button'):  
                self.move_button.setChecked(False)
            if hasattr(self, 'polygon'):
                self.polygon.setChecked(True)
            
            print(f"Polygon tool activated with: Label={label}, Color={color}, Thickness={thickness}")

    def toggle_polygon_select(self, checked):
        """Toggle rectangle selection mode and deactivate other tools"""
        if checked:
            # First, uncheck all other tool buttons
            self.paint_button.setChecked(False)
            self.eraser_button.setChecked(False)
            self.magic_pen_button.setChecked(False)
            self.contour_button.setChecked(False)
            self.move_button.setChecked(False)
            self.select.setChecked(False)

            self.image_label.paint_mode = False
            self.image_label.erase_mode = False
            self.image_label.magic_pen_mode = False
            self.image_label.toggle_rectangle_mode(False)

            # Enable rectangle mode
            self.image_label.toggle_polygon_mode(True)

        else:
            # When turning off rectangle mode, clear all active selections
            self.image_label.toggle_polygon_mode(False)
            self.image_label.clear_polygons()
            self.activate_move_mode(True)
    
    def toggle_clear(self):
        """Display a confirmation dialog before clearing all points."""
        confirm_dialog = QMessageBox(self)
        confirm_dialog.setWindowTitle("Confirm Clear All")
        confirm_dialog.setText("Are you sure you want to clear all points?")
        confirm_dialog.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        confirm_dialog.setDefaultButton(QMessageBox.StandardButton.No)
        
        # For better UX, use an icon
        confirm_dialog.setIcon(QMessageBox.Icon.Question)
        
        # Get the user's response
        response = confirm_dialog.exec()
        
        # If user confirmed, clear all points
        if response == QMessageBox.StandardButton.Yes:
            self.image_label.clear_points()
        
    def load_image(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self, "Open Image", "", "Images (*.png *.xpm *.jpg *.jpeg *.bmp *.gif)"
        )
        
        if file_path:
            image = QImage(file_path)
            if not image.isNull():
                self.image_label.clear_rectangles() 
                self.image_label.clear_points()
                self.current_image_path = file_path
                pixmap = QPixmap.fromImage(image)
                self.image_label.setBasePixmap(pixmap)
                self.image_label.reset_view()
                self.activate_move_mode(True)
            else:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Error")
                msg_box.setText("Could not load layer.")
                msg_box.setStyleSheet("""
                    QMessageBox {
                        background-color: #000000;  /* Pure black background */
                        color: white;  /* White text */
                        font-size: 14px;
                        border: 1px solid #444444;
                    }
                    QLabel {
                        color: white;  /* Ensures the message text is white */
                        background-color: #000000;
                    }
                    QPushButton {
                        background-color: #000000;  /* Black buttons */
                        color: white;
                        border: 1px solid #555555;
                        border-radius: 5px;
                        padding: 5px 10px;
                    }
                    QPushButton:hover {
                        background-color: #222222;  /* Slightly lighter on hover */
                    }
                """)
                msg_box.exec() 
                
    def load_layer(self):
        """Load an overlay layer and align it with the base image"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Layer", "", "Images (*.png *.xpm *.jpg *.jpeg *.bmp *.gif)"
        )
        if not file_path:
            return
    
        try:
            # Load the overlay image
            overlay_image = QImage(file_path)
            if overlay_image.isNull():
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Error")
                msg_box.setText("Failed to load layer.")
                msg_box.setStyleSheet("""
                    QMessageBox {
                        background-color: #000000;  /* Pure black background */
                        color: white;  /* White text */
                        font-size: 14px;
                        border: 1px solid #444444;
                    }
                    QLabel {
                        color: white;  /* Ensures the message text is white */
                        background-color: #000000;
                    }
                    QPushButton {
                        background-color: #000000;  /* Black buttons */
                        color: white;
                        border: 1px solid #555555;
                        border-radius: 5px;
                        padding: 5px 10px;
                    }
                    QPushButton:hover {
                        background-color: #222222;  /* Slightly lighter on hover */
                    }
                """)
                msg_box.exec() 
                return
                
            # Remove any existing overlay
            if hasattr(self.image_label, 'remove_overlay'):
                self.image_label.remove_overlay()
                
            # Create pixmap from image
            overlay_pixmap = QPixmap.fromImage(overlay_image)
            
            # Add overlay to scene in ZoomableGraphicsView
            if hasattr(self.image_label, 'add_overlay'):
                self.image_label.add_overlay(overlay_pixmap)
            else:
                # Assuming image_label is ZoomableGraphicsView
                self._add_overlay_to_graphics_view(overlay_pixmap)
                
            # Add to UI (toolbar or status bar)
            self.statusBar().showMessage(f"Layer loaded: {os.path.basename(file_path)}", 3000)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load layer: {str(e)}")
    
    def _add_overlay_to_graphics_view(self, overlay_pixmap):
        """Add an overlay to ZoomableGraphicsView with proper alignment"""
        if not hasattr(self.image_label, 'scene') or not self.image_label.base_pixmap:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Error")
            msg_box.setText("Please loade a bas image first.")
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #000000;  /* Pure black background */
                    color: white;  /* White text */
                    font-size: 14px;
                    border: 1px solid #444444;
                }
                QLabel {
                    color: white;  /* Ensures the message text is white */
                    background-color: #000000;
                }
                QPushButton {
                    background-color: #000000;  /* Black buttons */
                    color: white;
                    border: 1px solid #555555;
                    border-radius: 5px;
                    padding: 5px 10px;
                }
                QPushButton:hover {
                    background-color: #222222;  /* Slightly lighter on hover */
                }
            """)
            msg_box.exec() 
            return
            
        # Resize overlay to match base image size if needed
        base_size = self.image_label.base_pixmap.size()
        if overlay_pixmap.size() != base_size:
            overlay_pixmap = overlay_pixmap.scaled(
                base_size, 
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        
        # Create the overlay pixmap item and add to scene
        overlay_item = self.image_label.scene.addPixmap(overlay_pixmap)
        overlay_item.setZValue(1)  # Layer above base image (which is at Z=0)
        overlay_item.setPos(0, 0)  # Align with base image
        
        # Store reference to overlay item
        self.image_label.overlay_pixmap_item = overlay_item
        
        # Set initial opacity
        self.image_label.overlay_opacity = 128  # 50% opacity by default
        overlay_item.setOpacity(self.image_label.overlay_opacity / 255.0)
        
        # Update the view
        self.image_label.scene.update()
    
    def toggle_layer(self):
        if self.image_label.remove_overlay():
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Layer Remove")
            msg_box.setText("Layer has been removed.")
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #000000;  /* Pure black background */
                    color: white;  /* White text */
                    font-size: 14px;
                    border: 1px solid #444444;
                }
                QLabel {
                    color: white;  /* Ensures the message text is white */
                    background-color: #000000;
                }
                QPushButton {
                    background-color: #000000;  /* Black buttons */
                    color: white;
                    border: 1px solid #555555;
                    border-radius: 5px;
                    padding: 5px 10px;
                }
                QPushButton:hover {
                    background-color: #222222;  /* Slightly lighter on hover */
                }
            """)
            msg_box.exec() 
        else:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Layer Remove")
            msg_box.setText("No Layer loaded to remove.")
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #000000;  /* Pure black background */
                    color: white;  /* White text */
                    font-size: 14px;
                    border: 1px solid #444444;
                }
                QLabel {
                    color: white;  /* Ensures the message text is white */
                    background-color: #000000;
                }
                QPushButton {
                    background-color: #000000;  /* Black buttons */
                    color: white;
                    border: 1px solid #555555;
                    border-radius: 5px;
                    padding: 5px 10px;
                }
                QPushButton:hover {
                    background-color: #222222;  /* Slightly lighter on hover */
                }
            """)
            msg_box.exec() 
            
    def undo_last_stroke(self):
        self.image_label.undo_last_stroke()
        
    def save_image(self):
        # Check if there are rectangles to save (for YOLO mode)
        has_rectangles = (hasattr(self.image_label, 'labeled_rectangles') and
                        self.image_label.labeled_rectangles) or \
                        (hasattr(self.image_label, 'rectangle_items') and
                        self.image_label.rectangle_items)
        has_polygons = (hasattr(self.image_label, 'polygon_items') and
                        self.image_label.polygon_items)

        # Check if there are drawing points
        has_drawings = hasattr(self.image_label, 'points') and self.image_label.points

        if not has_drawings and not has_rectangles and not has_polygons:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Error")
            msg_box.setText("No drawing or rectangles or polygons to save.")
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #000000;
                    color: white;
                    font-size: 14px;
                    border: 1px solid #444444;
                }
                QLabel {
                    color: white;
                    background-color: #000000;
                }
                QPushButton {
                    background-color: #000000;
                    color: white;
                    border: 1px solid #555555;
                    border-radius: 5px;
                    padding: 5px 10px;
                }
                QPushButton:hover {
                    background-color: #222222;
                }
            """)
            msg_box.exec()
            return

        # Show dialog to choose save type
        save_type_dialog = QDialog(self)
        save_type_dialog.setWindowTitle("Save Type")
        save_type_dialog.setMinimumWidth(350)
        save_type_dialog.setStyleSheet("""
            QDialog {
                background-color: #000000;
                color: white;
                border: 1px solid #444444;
            }
            QLabel {
                color: white;
                font-size: 14px;
            }
            QPushButton {
                background-color: #000000;
                color: white;
                border: 1px solid #555555;
                border-radius: 5px;
                padding: 5px 10px;
                margin: 5px;
            }
            QPushButton:hover {
                background-color: #222222;
            }
        """)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Select save type:"))

        button_layout = QHBoxLayout()
        save_image_button = QPushButton("Save as Image")
        save_coordinates_button = QPushButton("Save Coordinates")
        cancel_button = QPushButton("Cancel")

        button_layout.addWidget(save_image_button)
        button_layout.addWidget(save_coordinates_button)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)
        save_type_dialog.setLayout(layout)

        # Track which type was selected
        save_type = None

        def save_as_image():
            nonlocal save_type
            save_type = "image"
            save_type_dialog.accept()

        def save_as_coordinates():
            nonlocal save_type
            save_type = "coordinates"
            save_type_dialog.accept()

        # Connect buttons
        save_image_button.clicked.connect(save_as_image)
        save_coordinates_button.clicked.connect(save_as_coordinates)
        cancel_button.clicked.connect(save_type_dialog.reject)

        # Show dialog and get result
        result = save_type_dialog.exec()

        if result != 1 or save_type is None:  # User cancelled or closed dialog
            return

        # Handle coordinate saving
        if save_type == "coordinates":
            self.save_coordinates()
            return

        # Original image saving logic continues here...
        # If we have rectangles, save the entire image with rectangles
        if has_rectangles:
            success = self.image_label.save_entire_image_with_rectangles()
            if success:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Success")
                msg_box.setText("Saved the entire image with shapes successfully.")
                msg_box.setStyleSheet("""
                    QMessageBox {
                        background-color: #000000;
                        color: white;
                        font-size: 14px;
                        border: 1px solid #444444;
                    }
                    QLabel {
                        color: white;
                        background-color: #000000;
                    }
                    QPushButton {
                        background-color: #000000;
                        color: white;
                        border: 1px solid #555555;
                        border-radius: 5px;
                        padding: 5px 10px;
                    }
                    QPushButton:hover {
                        background-color: #222222;
                    }
                """)
                msg_box.exec()
            return
        
        if has_polygons:
            success = self.image_label.save_entire_image_with_polygons()
            if success:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Success")
                msg_box.setText("Saved the entire image with shapes successfully.")
                msg_box.setStyleSheet("""
                    QMessageBox {
                        background-color: #000000;
                        color: white;
                        font-size: 14px;
                        border: 1px solid #444444;
                    }
                    QLabel {
                        color: white;
                        background-color: #000000;
                    }
                    QPushButton {
                        background-color: #000000;
                        color: white;
                        border: 1px solid #555555;
                        border-radius: 5px;
                        padding: 5px 10px;
                    }
                    QPushButton:hover {
                        background-color: #222222;
                    }
                """)
                msg_box.exec()
            return

        # Original drawing save logic (if no rectangles but has drawings)
        if has_drawings:
            # Show dialog to choose save mode
            save_mode_dialog = QDialog(self)
            save_mode_dialog.setWindowTitle("Save Mode")
            save_mode_dialog.setMinimumWidth(300)
            save_mode_dialog.setStyleSheet("""
                QDialog {
                    background-color: #000000;
                    color: white;
                    border: 1px solid #444444;
                }
                QLabel {
                    color: white;
                    font-size: 14px;
                }
                QPushButton {
                    background-color: #000000;
                    color: white;
                    border: 1px solid #555555;
                    border-radius: 5px;
                    padding: 5px 10px;
                    margin: 5px;
                }
                QPushButton:hover {
                    background-color: #222222;
                }
            """)

            layout = QVBoxLayout()
            layout.addWidget(QLabel("Select save mode:"))

            button_layout = QHBoxLayout()
            drawing_only_button = QPushButton("Drawing Only")
            all_layers_button = QPushButton("All Layers")
            cancel_button = QPushButton("Cancel")

            button_layout.addWidget(drawing_only_button)
            button_layout.addWidget(all_layers_button)
            button_layout.addWidget(cancel_button)

            layout.addLayout(button_layout)
            save_mode_dialog.setLayout(layout)

            # Track which mode was selected
            save_mode = None

            def save_drawing_only():
                nonlocal save_mode
                save_mode = "drawing_only"
                save_mode_dialog.accept()

            def save_all_layers():
                nonlocal save_mode
                save_mode = "all_layers"
                save_mode_dialog.accept()

            # Connect buttons
            drawing_only_button.clicked.connect(save_drawing_only)
            all_layers_button.clicked.connect(save_all_layers)
            cancel_button.clicked.connect(save_mode_dialog.reject)

            # Show dialog and get result
            result = save_mode_dialog.exec()

            if result != 1 or save_mode is None:  # User cancelled or closed dialog
                return

            # Prepare save directory
            save_dir = os.path.join(os.getcwd(), 'save')
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)

            base_name = os.path.basename(self.current_image_path) if self.current_image_path else "untitled"
            name, ext = os.path.splitext(base_name)

            # Set filename based on save mode
            if save_mode == "all_layers":
                save_path = os.path.join(save_dir, f"{name}_all_layers.png")
            else:
                save_path = os.path.join(save_dir, f"{name}_drawing_only.png")

            # Get the scene bounding rectangle
            scene_rect = self.image_label.scene.itemsBoundingRect()
            width, height = int(scene_rect.width()), int(scene_rect.height())

            if width <= 0 or height <= 0:
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Error")
                msg_box.setText("Drawing area is empty.")
                msg_box.setStyleSheet("""
                    QMessageBox {
                        background-color: #000000;
                        color: white;
                        font-size: 14px;
                        border: 1px solid #444444;
                    }
                    QLabel {
                        color: white;
                        background-color: #000000;
                    }
                    QPushButton {
                        background-color: #000000;
                        color: white;
                        border: 1px solid #555555;
                        border-radius: 5px;
                        padding: 5px 10px;
                    }
                    QPushButton:hover {
                        background-color: #222222;
                    }
                """)
                msg_box.exec()
                return

            # Create an image with a transparent background
            final_image = QImage(width, height, QImage.Format.Format_ARGB32)
            final_image.fill(Qt.GlobalColor.transparent)

            painter = QPainter(final_image)

            # Store current opacity to restore it later
            current_opacity = self.image_label.overlay_opacity

            if save_mode == "all_layers":
                # For "all layers" mode, make sure the background is visible
                if self.image_label.pixmap_item:
                    self.image_label.pixmap_item.setVisible(True)
            else:
                # For "drawing only" mode, hide the background
                if self.image_label.pixmap_item:
                    self.image_label.pixmap_item.setVisible(False)
                
                # Make drawing fully opaque for "drawing only" mode
                self.image_label.update_overlay_opacity(255)

            # Render the scene
            self.image_label.scene.render(painter, QRectF(0, 0, width, height), scene_rect)

            # Restore the background image visibility and original opacity
            if self.image_label.pixmap_item:
                self.image_label.pixmap_item.setVisible(True)

            # Restore the original opacity if it was changed
            if save_mode == "drawing_only":
                self.image_label.update_overlay_opacity(current_opacity)

            painter.end()

            # Save the final image
            final_image.save(save_path)
            QMessageBox.information(self, "Success", f"Image saved to {save_path}")

    def save_coordinates(self):
        """Save coordinates and labeling data to JSON file"""
        import json
        
        # Prepare save directory
        save_dir = os.path.join(os.getcwd(), 'save')
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        base_name = os.path.basename(self.current_image_path) if self.current_image_path else "untitled"
        name, ext = os.path.splitext(base_name)
        save_path = os.path.join(save_dir, f"{name}_coordinates.json")

        data = {
            "image_path": self.current_image_path,
            "timestamp": str(QDateTime.currentDateTime().toString()),
            "drawings": [],
            "rectangles": [],
            "polygons": []
        }

        # Save drawing points
        points_to_save = []
        if hasattr(self.image_label, 'points') and self.image_label.points:
            points_to_save = self.image_label.points
        elif hasattr(self, 'points') and self.points:
            points_to_save = self.points

        if points_to_save:
            for point in points_to_save:
                # Get position safely
                pos = point.get_position()

                label_val = ""
                try:
                    if hasattr(point, 'fixed_label'):
                        label_val = point.fixed_label
                except:
                    label_val = ""          

                # Get color as string safely
                color_str = "#000000"
                try:
                    if hasattr(point, 'fixed_color') and point.fixed_color:
                        color_str = point.fixed_color.name()
                except:
                    color_str = "#000000"

                # Get opacity safely
                opacity_val = 1.0
                try:
                    if hasattr(point, 'fixed_opacity'):
                        opacity_val = float(point.fixed_opacity) / 255.0
                except:
                    opacity_val = 1.0

                # Get radius safely
                radius_val = 0
                try:
                    if hasattr(point, '_fixed_radius'):
                        radius_val = float(point._fixed_radius)
                except:
                    radius_val = 0

                data["drawings"].append({
                    "x": float(pos.x()),
                    "y": float(pos.y()),
                    "Label": label_val,
                    "radius": radius_val,
                    "color": color_str,
                    "opacity": opacity_val,
                    "type": "drawing_point"
                })

        with open(save_path, 'w') as f:
            json.dump(data, f, indent=4)

        # Save rectangles
        if hasattr(self.image_label, 'labeled_rectangles') and self.image_label.labeled_rectangles:
            for rect_data in self.image_label.labeled_rectangles:
                rect = rect_data.rect()
                data["rectangles"].append({
                    "x": rect.x(),
                    "y": rect.y(),
                    "width": rect.width(),
                    "height": rect.height(),
                    "label": rect_data.get_label(),
                    "color": rect_data.get_color().name(),
                    "type": "rectangle"
                })
        elif hasattr(self.image_label, 'rectangle_items') and self.image_label.rectangle_items:
            for rect_item in self.image_label.rectangle_items:
                rect = rect_item.rect()
                data["rectangles"].append({
                    "x": rect.x(),
                    "y": rect.y(),
                    "width": rect.width(),
                    "height": rect.height(),
                    "type": "rectangle"
                })

        # Save polygons
        if hasattr(self.image_label, 'polygon_items') and self.image_label.polygon_items:
            for poly_item in self.image_label.polygon_items:
                polygon = poly_item.polygon()
                points = []
                for i in range(polygon.count()):
                    point = polygon.at(i)
                    points.append({"x": point.x(), "y": point.y()})
                data["polygons"].append({
                    "points": points,
                    "type": "polygon"
                })

        # Save to JSON file
        try:
            with open(save_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Success")
            msg_box.setText(f"Coordinates saved to {save_path}")
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #000000;
                    color: white;
                    font-size: 14px;
                    border: 1px solid #444444;
                }
                QLabel {
                    color: white;
                    background-color: #000000;
                }
                QPushButton {
                    background-color: #000000;
                    color: white;
                    border: 1px solid #555555;
                    border-radius: 5px;
                    padding: 5px 10px;
                }
                QPushButton:hover {
                    background-color: #222222;
                }
            """)
            msg_box.exec()
            
        except Exception as e:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Error")
            msg_box.setText(f"Failed to save coordinates: {str(e)}")
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: #000000;
                    color: white;
                    font-size: 14px;
                    border: 1px solid #444444;
                }
                QLabel {
                    color: white;
                    background-color: #000000;
                }
                QPushButton {
                    background-color: #000000;
                    color: white;
                    border: 1px solid #555555;
                    border-radius: 5px;
                    padding: 5px 10px;
                }
                QPushButton:hover {
                    background-color: #222222;
                }
            """)
            msg_box.exec()

def main():
    app = QApplication(sys.argv)
    
    # Splash screen
    splash_pix = QPixmap(get_icon_path("logoMAIA")) 
    splash = QSplashScreen(splash_pix, Qt.WindowType.SplashScreen)
    splash.show()

    time.sleep(2)
    
    viewer = ImageViewer()
    viewer.show()
    
    # Close the splash screen and start the main application
    splash.close()
    
    sys.exit(app.exec())

def get_icon_path(icon_name):
    # Assuming icons are stored in an 'icons' folder next to the script
    icon_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icon')
    return os.path.join(icon_dir, f"{icon_name}.png")

if __name__ == "__main__":
    main()
