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
        
        # Basic properties
        self.view.zoom_factor = 1.0
        self.base_pixmap = None
        self.pixmap_item = None
        self.base_pixmap_item = None
        self.overlay_pixmap_item = None
        self.raw_image = None
        self.is_moving = False
        self.view.last_mouse_pos = None
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.view.layer_activation = False
        
        # Drawing properties
        self.points = []  # List of PointItem objects
        self.paint_mode = False
        self.erase_mode = False
        self.magic_pen_mode = False
        self.view.point_radius = 3
        self.view.point_color = QColor(255, 0, 0)
        self.point_opacity = 100
        self.view.point_label = ""
        self.eraser_size = 10
        self.absolute_erase_mode = False
        self.magic_pen_tolerance = 20
        self.max_points_limite = 100000
        self.shape_fill_mode = False
        
        self.view.magic_pen_tolerance = 50  # Color tolerance for magic pen
        self.view.max_points_limite = 500000  # Maximum points limit

    def clear(self):
        pass

    def change_cursor(self, name):
        cursor_pixmap = QPixmap(Utils.get_icon_path(name))
        print("*self.view.config[window_size][icon]:", *self.view.config["window_size"]["icon"])
        cursor_pixmap = cursor_pixmap.scaled(*self.view.config["window_size"]["icon"]) 
        cursor = QCursor(cursor_pixmap)
        self.viewport().setCursor(cursor)

           
    def wheelEvent(self, event):
        zoom_in = event.angleDelta().y() > 0
        factor = 1.1 if zoom_in else 0.9
        
        # Apply zoom factor limit
        new_zoom_factor = self.view.zoom_factor * factor
        if 0.9 <= new_zoom_factor <= 40.0:
            self.view.zoom_factor = new_zoom_factor
            
            # Get the scene position under the mouse
            mouse_pos = event.position().toPoint()
            scene_pos = self.mapToScene(mouse_pos)

            # Apply the scale
            self.scale(factor, factor)
            
            # Get the new position in viewport coordinates where scene_pos would show
            new_viewport_pos = self.mapFromScene(scene_pos)
            
            # Calculate the viewport delta and adjust the view
            delta = new_viewport_pos - mouse_pos
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() + delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() + delta.y())
        
        # Prevent standard event handling
        event.accept()

class OldZoomableGraphicsView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        
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
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        
        # Basic properties
        self.zoom_factor = 1.0
        self.base_pixmap = None
        self.pixmap_item = None
        self.base_pixmap_item = None
        self.overlay_pixmap_item = None
        self.raw_image = None
        self.is_moving = False
        self.last_mouse_pos = None
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # Drawing properties
        self.points = []  # List of PointItem objects
        self.paint_mode = False
        self.erase_mode = False
        self.magic_pen_mode = False
        self.point_radius = 3
        self.point_color = QColor(255, 0, 0)
        self.point_opacity = 100
        self.point_label = ""
        self.eraser_size = 10
        self.absolute_erase_mode = False
        self.magic_pen_tolerance = 20
        self.max_points_limite = 100000
        self.shape_fill_mode = False
        
        # Processing
        self.process_timeout = 10  # 10 seconds default timeout
        self.worker = None
        
        # Display properties
        self.overlay_opacity = 255
        self.points_opacity = 255
        self.opacity_dialog = None
        self.drawn_points_visible = True
        
        # History
        self.points_history = []
        self.current_stroke = []
        self.erased_points_history = []
        self.MAX_HISTORY_SIZE = 5
        
        # Memory management
        self.operation_count = 0
        self.memory_threshold = 10
        
        self.input_cooldown_timer = QTimer()
        self.input_cooldown_timer.setInterval(50)  # 50ms delay
        self.input_cooldown_timer.setSingleShot(True)
        self.input_cooldown_timer.timeout.connect(self.process_delayed_input)
        self.last_input_event = None
        
        self.gc_timer = QTimer()
        self.gc_timer.setInterval(10000)  # Every 10 seconds
        self.gc_timer.timeout.connect(gc.collect)
        self.gc_timer.start()
        
        self.rect_start = None
        self.current_rect = None
        self.rectangle_mode = False
        self.labeled_rectangles = []
        self.last_used_label = None 
        self.label_thickness = {}
        #self.label_properties_manager = LabelPropertiesManager()
        
        self.default_polygon_color = QColor(255, 0, 0)  # Green
        self.default_polygon_thickness = 2
        
        # Polygon creation state
        self.polygon_mode = False
        self.current_polygon_points = []
        self.current_polygon_lines = []
        self.current_polygon = None
        self.polygon_items = []
        self.labeled_polygons = []
        self.polygon_edit_mode = False
        self.editing_polygon = None
        self.polygon_point_items = []
        self.dragging_polygon_point = False
        self.dragged_point_item = None
            
        # Polygon manipulation modes
        self.close_distance_threshold = 10

        self.erase_timer = QTimer()
        self.erase_timer.setInterval(5)  # Mise à jour toutes les 50ms
        self.erase_timer.setSingleShot(True)
        self.erase_timer.timeout.connect(self.scene.update)
        
    def process_delayed_input(self):
        """Process stored input event after cooldown"""
        if isinstance(self.last_input_event, QMouseEvent):
            # Handle mouse movement (panning, zooming, drawing)
            pass
    
    def setBasePixmap(self, pixmap):
        """Set the base image pixmap"""
        self.base_pixmap = pixmap
        self.raw_image = pixmap.toImage()
        
        # Clear existing scene
        self.scene.clear()
        self.points = []
        
        # Create pixmap item
        self.pixmap_item = self.scene.addPixmap(pixmap)
        self.pixmap_item.setZValue(0)  # Base layer
        
        # Reset view
        self.setSceneRect(self.pixmap_item.boundingRect())
        self.fitInView(self.pixmap_item.boundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self.zoom_factor = 1.0
        
        # Reset transformations
        self.resetTransform()
    
    def wheelEvent(self, event):
        """Handle mouse wheel for zooming centered on cursor position"""
        if not self.base_pixmap:
            return
        
        # Calculate zoom factor
        zoom_in = event.angleDelta().y() > 0
        factor = 1.1 if zoom_in else 0.9
        
        # Apply zoom factor limit
        new_zoom_factor = self.zoom_factor * factor
        if 0.9 <= new_zoom_factor <= 40.0:
            self.zoom_factor = new_zoom_factor
            
            # Get the scene position under the mouse
            mouse_pos = event.position().toPoint()
            scene_pos = self.mapToScene(mouse_pos)
            
            # First reset the transformation anchor
            self.setTransformationAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
            
            # Apply the scale
            self.scale(factor, factor)
            
            # Get the new position in viewport coordinates where scene_pos would show
            new_viewport_pos = self.mapFromScene(scene_pos)
            
            # Calculate the viewport delta and adjust the view
            delta = new_viewport_pos - mouse_pos
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() + delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() + delta.y())
        
        # Prevent standard event handling
        event.accept()
    
    def mousePressEvent(self, event):
        """Handle mouse press events"""
        if not self.base_pixmap:
            return
            
        self.last_mouse_pos = event.position()
        scene_pos = self.mapToScene(int(event.position().x()), int(event.position().y()))
        
        if not self.input_cooldown_timer.isActive():
            self.input_cooldown_timer.start()
            
        if self.paint_mode and event.button() == Qt.MouseButton.LeftButton:
            self.add_point(scene_pos)
            self.is_painting = True
        elif self.magic_pen_mode and event.button() == Qt.MouseButton.LeftButton:
            self.fill_shape(scene_pos)
        elif self.erase_mode and event.button() == Qt.MouseButton.LeftButton:
            self.erase_point(scene_pos)
            self.is_erasing = True
        elif self.polygon_mode and hasattr(self, 'polygon_edit_mode') and self.polygon_edit_mode:
            if event.button() == Qt.MouseButton.RightButton:
                self.end_polygon_edit_mode()
                return
            elif event.button() == Qt.MouseButton.LeftButton:
                # Check if we clicked on a polygon point
                item = self.scene.itemAt(scene_pos, self.transform())
                if item and hasattr(item, 'vertex_index'):
                    self.dragging_polygon_point = True
                    self.dragged_point_item = item
                    return
        elif self.polygon_mode and event.button() == Qt.MouseButton.LeftButton:
            # Check if we're close to the first point to close the polygon
            if hasattr(self, "current_polygon_points") and len(self.current_polygon_points) >= 3:
                first_point = self.current_polygon_points[0]
                distance = math.sqrt((scene_pos.x() - first_point.x())**2 + 
                                   (scene_pos.y() - first_point.y())**2)
                
                if distance <= self.close_distance_threshold:
                    self.close_polygon()
                    label = PolygonTool.last_used_label if hasattr(PolygonTool, 'last_used_label') else None
                    color = self.default_polygon_color if hasattr(self, 'default_polygon_color') else QColor(0, 255, 0)
                    thickness = self.default_polygon_thickness if hasattr(self, 'default_polygon_thickness') else 2
                    self.show_polygon_label_properties(label, color, thickness)
                    return
            
            # Add new point to current polygon
            self.add_polygon_point(scene_pos)
            
        elif self.polygon_mode and event.button() == Qt.MouseButton.RightButton:
            # Right click to close polygon (if we have at least 3 points)
            if len(self.current_polygon_points) >= 3:
                self.close_polygon()
            else:
                # Cancel current polygon creation
                self.cancel_polygon_creation()

        elif self.rectangle_mode and event.button() == Qt.MouseButton.LeftButton:
            self.rect_start = self.mapToScene(event.pos())
        elif event.button() == Qt.MouseButton.LeftButton and not self.paint_mode and not self.erase_mode:
            self.is_moving = True
            self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            if hasattr(self, "shape_fill_mode") and self.shape_fill_mode:
                self.fill_contour()
                return 

            super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Handle mouse movement"""
        if not self.base_pixmap:
            return
            
        scene_pos = self.mapToScene(int(event.position().x()), int(event.position().y()))
        
        if self.paint_mode and event.buttons() & Qt.MouseButton.LeftButton:
            if self.last_mouse_pos:
                last_scene_pos = self.mapToScene(int(self.last_mouse_pos.x()), 
                                                 int(self.last_mouse_pos.y()))
                self.draw_continuous_line(last_scene_pos, scene_pos)
            self.last_mouse_pos = event.position()
        elif self.erase_mode and event.buttons() & Qt.MouseButton.LeftButton:
            self.erase_point(scene_pos)
        elif self.polygon_mode and hasattr(self, 'current_polygon_points ') and self.current_polygon_points:
            self.update_polygon_preview(scene_pos)
        elif self.rectangle_mode and self.rect_start:
            scene_pos = self.mapToScene(event.pos())
            rect = QRectF(self.rect_start, scene_pos).normalized()
            if self.current_rect:
                self.scene.removeItem(self.current_rect)
            self.current_rect = QGraphicsRectItem(rect)
            self.current_rect.setPen(QPen(QColor(0, 255, 0), 2))  # Green outline while drawing
            self.scene.addItem(self.current_rect)
        elif self.polygon_mode and hasattr(self, 'dragging_polygon_point') and self.dragging_polygon_point and self.dragged_point_item:
            # Move the dragged point to the new position
            new_pos = scene_pos - self.dragged_point_item.boundingRect().center()
            self.dragged_point_item.setPos(new_pos)
            self.update_polygon_from_points()
            return
    
        elif self.is_moving:
            super().mouseMoveEvent(event)

        elif hasattr(self, 'movement_mode') and self.movement_mode and hasattr(self, 'moving_rect'):
            # Move the rectangle
            scene_pos = self.mapToScene(event.pos())
            
            # Calculate the desired center position (mouse position minus stored offset)
            desired_center = QPointF(
                scene_pos.x() - self.mouse_offset.x(),
                scene_pos.y() - self.mouse_offset.y()
            )
            
            # For rotated rectangles, use setPos() instead of setRect()
            # Get the current rect center in local coordinates
            rect_center_local = self.moving_rect.rect().center()
            
            # Calculate where the rectangle's origin should be to center it at desired_center
            new_pos = QPointF(
                desired_center.x() - rect_center_local.x(),
                desired_center.y() - rect_center_local.y()
            )
            
            # Set the new position (this respects the rotation transformation)
            self.moving_rect.setPos(new_pos)

        elif hasattr(self, 'rotation_mode') and self.rotation_mode and hasattr(self, 'rotating_rect'):
            scene_pos = self.mapToScene(event.pos())
            line = QLineF(self.rect_center, scene_pos)
            current_mouse_angle = line.angle()

            # Calculate the delta from the initial mouse angle
            angle_delta = current_mouse_angle - self.initial_mouse_angle

            # Apply rotation relative to the initial rotation
            new_angle = self.initial_angle + angle_delta
            self.rotating_rect.setRotation(new_angle)

        elif hasattr(self, 'modification_mode') and self.modification_mode and self.modifying_rect:
            # Get current mouse position in scene coordinates
            mouse_pos = self.mapToScene(event.pos())

            # Calculate the movement delta
            delta = mouse_pos - self.initial_mouse_pos

            # Get the current rectangle
            current_rect = self.original_rect
            new_rect = QRectF(current_rect)

            # Modify rectangle based on which handle is being dragged
            if self.resize_handle == 'bottom_right':
                new_rect.setBottomRight(current_rect.bottomRight() + delta)
            elif self.resize_handle == 'top_left':
                new_rect.setTopLeft(current_rect.topLeft() + delta)
            elif self.resize_handle == 'top_right':
                new_rect.setTopRight(current_rect.topRight() + delta)
            elif self.resize_handle == 'bottom_left':
                new_rect.setBottomLeft(current_rect.bottomLeft() + delta)
            elif self.resize_handle == 'right':
                new_rect.setRight(current_rect.right() + delta.x())
            elif self.resize_handle == 'left':
                new_rect.setLeft(current_rect.left() + delta.x())
            elif self.resize_handle == 'bottom':
                new_rect.setBottom(current_rect.bottom() + delta.y())
            elif self.resize_handle == 'top':
                new_rect.setTop(current_rect.top() + delta.y())

            # Ensure minimum size (e.g., 10x10 pixels)
            min_size = 10
            if new_rect.width() < min_size:
                if self.resize_handle in ['left', 'top_left', 'bottom_left']:
                    new_rect.setLeft(new_rect.right() - min_size)
                else:
                    new_rect.setRight(new_rect.left() + min_size)

            if new_rect.height() < min_size:
                if self.resize_handle in ['top', 'top_left', 'top_right']:
                    new_rect.setTop(new_rect.bottom() - min_size)
                else:
                    new_rect.setBottom(new_rect.top() + min_size)

            # Apply the new rectangle size
            self.modifying_rect.setRect(new_rect)

            # Update the view
            self.update()

    def on_rectangle_properties_widget_clicked(self):
        """Handle click on rectangle properties widget to activate rectangle tool"""
        # Define the properties you want to set
        label = self.current_rectangle_label  # Use the current rectangle label
        color = self.current_rectangle_color  # Use the current rectangle color
        thickness = self.current_rectangle_thickness  # Use the current rectangle thickness

        # Call the method from main class to activate the rectangle tool
        if hasattr(self, 'main_window') and self.main_window:
            # If this dialog has a reference to main window
            self.main_window.activate_rectangle_tool_with_properties(label, color, thickness)
        elif hasattr(self, 'parent') and hasattr(self.parent(), 'activate_rectangle_tool_with_properties'):
            # If the parent has the method
            self.parent().activate_rectangle_tool_with_properties(label, color, thickness)
        else:
            app = QApplication.instance()
            if app:
                for widget in app.topLevelWidgets():
                    if hasattr(widget, 'activate_rectangle_tool_with_properties'):
                        widget.activate_rectangle_tool_with_properties(label, color, thickness)
                        break
 
    def on_polygon_properties_widget_clicked(self, widget):
        """Handle click on polygon properties widget to activate polygon tool"""
        # Define the properties you want to set from the widget
        label = widget.label_name.text().replace("Label: ", "")
        color = QColor(widget.label_color.text().replace("Color: ", ""))
        thickness = int(widget.label_thickness.text().replace("thickness: ", ""))

        # Call the method from main class to activate the polygon tool
        if hasattr(self, 'main_window') and self.main_window:
            # If this dialog has a reference to main window
            self.main_window.activate_polygon_tool_with_properties(label, color, thickness)
        elif hasattr(self, 'parent') and hasattr(self.parent(), 'activate_polygon_tool_with_properties'):
            # If the parent has the method
            self.parent().activate_polygon_tool_with_properties(label, color, thickness)
        else:
            app = QApplication.instance()
            if app:
                for widget in app.topLevelWidgets():
                    if hasattr(widget, 'activate_polygon_tool_with_properties'):
                        widget.activate_polygon_tool_with_properties(label, color, thickness)
                        break

    def show_label_properties(self, label_text, current_color, current_thickness, shape_type='rectangle'):
        # Choose the appropriate dictionary based on shape type
        if shape_type == 'polygon':
            if not hasattr(self, 'polygon_label_properties_dialogs_dict'):
                self.polygon_label_properties_dialogs_dict = {}
            dialogs_dict = self.polygon_label_properties_dialogs_dict
            current_label_attr = 'current_polygon_label'
            current_color_attr = 'current_polygon_color'
            current_thickness_attr = 'current_polygon_thickness'
        else:
            if not hasattr(self, 'rectangle_label_properties_dialogs_dict'):
                self.rectangle_label_properties_dialogs_dict = {}
            dialogs_dict = self.rectangle_label_properties_dialogs_dict
            current_label_attr = 'current_rectangle_label'
            current_color_attr = 'current_rectangle_color'
            current_thickness_attr = 'current_rectangle_thickness'

        # Store current properties
        setattr(self, current_label_attr, label_text)
        setattr(self, current_color_attr, current_color)
        setattr(self, current_thickness_attr, current_thickness)

        # Check if a dialog for this label already exists
        if label_text in dialogs_dict:
            # Get the existing dialog
            existing_dialog = dialogs_dict[label_text]

            # Check if the dialog still exists and is valid
            if existing_dialog and not existing_dialog.isHidden():
                # Update the existing dialog with current properties
                existing_dialog.update_properties(
                    label_text,
                    current_color,
                    current_thickness
                )
                # Bring the existing dialog to front
                existing_dialog.raise_()
                existing_dialog.activateWindow()
                return
            else:
                # Remove the invalid dialog from the dictionary
                del dialogs_dict[label_text]

        total_dialogs = len(dialogs_dict)
        if total_dialogs == 1 and hasattr(self.parent(), 'shortcut_button'):
            self.parent().shortcut_button.setText("Hide Shortcuts")

        if shape_type == 'polygon':
            label_properties_dialog = LabelPolygonPropertiesDialog(self)
            click_handler = lambda widget=label_properties_dialog: self.on_polygon_properties_widget_clicked(widget)
        else:
            label_properties_dialog = LabelRectanglePropertiesDialog(self)
            click_handler = self.on_rectangle_properties_widget_clicked

        # Update the properties
        label_properties_dialog.update_properties(
            label_text,
            current_color,
            current_thickness
        )

        # Store the dialog in the dictionary with the label as key
        dialogs_dict[label_text] = label_properties_dialog

        # Connect the dialog's close event to clean up the dictionary
        def on_dialog_closed():
            if label_text in dialogs_dict:
                del dialogs_dict[label_text]

        # Connect to the finished signal (emitted when dialog is closed)
        label_properties_dialog.finished.connect(on_dialog_closed)

        # Connect the click handler to the dialog
        label_properties_dialog.mousePressEvent = lambda event: click_handler()

        # Show the dialog
        label_properties_dialog.show()

        # Position the dialog at the top of the screen
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        x = screen_geometry.width() - label_properties_dialog.width() - 10

        # Calculate y position based on existing dialogs
        existing_dialogs = [d for d in dialogs_dict.values() if d and d.isVisible()]
        y = 10 + len(existing_dialogs) * (label_properties_dialog.height() + 10)

        label_properties_dialog.move(x, y)

    def show_rectangle_label_properties(self, label_text, current_color, current_thickness):
        """Show rectangle label properties - wrapper for backward compatibility"""
        self.show_label_properties(label_text, current_color, current_thickness, 'rectangle')

    # Add new method for polygons
    def show_polygon_label_properties(self, label_text, current_color, current_thickness):
        """Show polygon label properties"""
        self.show_label_properties(label_text, current_color, current_thickness, 'polygon')
        
    def mouseReleaseEvent(self, event):
        """Handle mouse release events"""
        print(f"Mouse release event detected with button: {event.button()}")  # Debug print

        if event.button() == Qt.MouseButton.LeftButton:
            print("Left mouse button released")  # Debug print
            self.is_moving = False
            self.is_painting = False
            self.is_erasing = False
            if self.polygon_mode and hasattr(self, 'dragging_polygon_point') and self.dragging_polygon_point:
               self.dragging_polygon_point = False
               self.dragged_point_item = None
               return
            if not (self.paint_mode or self.erase_mode):
                self.setDragMode(QGraphicsView.DragMode.NoDrag)
                self.setCursor(Qt.CursorShape.ArrowCursor)

            if self.current_stroke:
                self.points_history.append(self.current_stroke)
                if len(self.points_history) > self.MAX_HISTORY_SIZE:
                    self.points_history.pop(0)
                self.current_stroke = []

            if self.rectangle_mode and self.rect_start:
                scene_pos = self.mapToScene(event.pos())
                rect = QRectF(self.rect_start, scene_pos).normalized()

                if rect.width() > 5 and rect.height() > 5 and self.rectangle_mode_type == 'yolo':
                    labeled_rect = LabeledRectangle(rect.x(), rect.y(), rect.width(), rect.height(), "")
                    self.scene.addItem(labeled_rect)
                    self.labeled_rectangles.append(labeled_rect)

                elif rect.width() > 5 and rect.height() > 5 and self.rectangle_mode_type == 'classification':
                    # Initialize label colors and thickness dictionaries if not exists
                    label_text = ""
                    if not hasattr(self, 'label_colors'):
                        self.label_colors = {}
                    if not hasattr(self, 'label_thickness'):
                        self.label_thickness = {}
                    
                    # Show dialog with previous labels for quick selection
                    self.label_properties_manager.load_properties()
                    if hasattr(self.label_properties_manager, 'label_properties') and self.label_properties_manager.label_properties:
                        # Initialize dictionaries if they don't exist
                        if not hasattr(self, 'label_colors'):
                            self.label_colors = {}
                        if not hasattr(self, 'label_thickness'):
                            self.label_thickness = {}
                        if not hasattr(self, 'recent_labels'):
                            self.recent_labels = []
                        
                        # Update from loaded properties
                        for label_name, props in self.label_properties_manager.label_properties.items():
                            if label_name not in self.recent_labels:
                                self.recent_labels.append(label_name)
                            self.label_colors[label_name] = props['color'].name()  # Convert QColor to hex string
                            self.label_thickness[label_name] = props['thickness']

                    if hasattr(self, 'recent_labels') and self.recent_labels:
                        # Create the dialog
                        dialog = QDialog(self)
                        dialog.setWindowTitle("Select or Create Label")
                        dialog.setObjectName("CustomDialog")

                        layout = QVBoxLayout()

                        combo = QComboBox()
                        combo.addItems(self.recent_labels)
                        combo.setEditable(True)
                        
                        # Auto-select the last used label if it exists
                        if self.last_used_label and self.last_used_label in self.recent_labels:
                            combo.setCurrentText(self.last_used_label)
                        else:
                            combo.setCurrentIndex(-1)

                        label = QLabel("Select an existing label or type a new one:")
                        layout.addWidget(label)
                        layout.addWidget(combo)

                        # Add color selection button
                        color_frame = QFrame()
                        color_layout = QHBoxLayout(color_frame)
                        color_layout.setContentsMargins(0, 0, 0, 0)
                        
                        color_label = QLabel("Color:")
                        color_button = QPushButton("Choose Color")
                        color_button.setObjectName("ColorButton")
                        
                        # Set default color based on last used label or default red
                        if self.last_used_label and self.last_used_label in self.label_colors:
                            current_color = QColor(self.label_colors[self.last_used_label])
                        else:
                            current_color = QColor(255, 0, 0)  # Default red
                            
                        # Add thickness selection
                        thickness_frame = QFrame()
                        thickness_layout = QHBoxLayout(thickness_frame)
                        thickness_layout.setContentsMargins(0, 0, 0, 0)
                        
                        thickness_label = QLabel("Thickness:")
                        thickness_spinbox = QSpinBox()
                        thickness_spinbox.setMinimum(1)
                        thickness_spinbox.setMaximum(10)
                        thickness_spinbox.setSuffix(" px")
                        
                        # Set default thickness based on last used label or default 2
                        if self.last_used_label and self.last_used_label in self.label_thickness:
                            current_thickness = self.label_thickness[self.last_used_label]
                        else:
                            current_thickness = 2  # Default thickness
                        thickness_spinbox.setValue(current_thickness)
                        
                        color_button.setStyleSheet(f"""
                            QPushButton#ColorButton {{
                                background-color: {current_color.name()};
                                color: white;
                                border: 2px solid #666666;
                                border-radius: 5px;
                                padding: 6px 12px;
                                font-weight: bold;
                            }}
                            QPushButton#ColorButton:hover {{
                                border: 2px solid #888888;
                            }}
                        """)

                        def choose_color():
                            nonlocal current_color
                            color = QColorDialog.getColor(current_color, dialog, "Choose Rectangle Color")
                            if color.isValid():
                                current_color = color
                                color_button.setStyleSheet(f"""
                                    QPushButton#ColorButton {{
                                        background-color: {current_color.name()};
                                        color: white;
                                        border: 2px solid #666666;
                                        border-radius: 5px;
                                        padding: 6px 12px;
                                        font-weight: bold;
                                    }}
                                    QPushButton#ColorButton:hover {{
                                        border: 2px solid #888888;
                                    }}
                                """)
                        
                        def on_combo_change():
                            nonlocal current_color, current_thickness
                            selected_label = combo.currentText().strip()
                            if selected_label in self.label_colors:
                                current_color = QColor(self.label_colors[selected_label])
                                color_button.setStyleSheet(f"""
                                    QPushButton#ColorButton {{
                                        background-color: {current_color.name()};
                                        color: white;
                                        border: 2px solid #666666;
                                        border-radius: 5px;
                                        padding: 6px 12px;
                                        font-weight: bold;
                                    }}
                                    QPushButton#ColorButton:hover {{
                                        border: 2px solid #888888;
                                    }}
                                """)
                            if selected_label in self.label_thickness:
                                current_thickness = self.label_thickness[selected_label]
                                thickness_spinbox.setValue(current_thickness)
                        
                        def on_thickness_change():
                            nonlocal current_thickness
                            current_thickness = thickness_spinbox.value()
                        
                        color_button.clicked.connect(choose_color)
                        combo.currentTextChanged.connect(on_combo_change)
                        thickness_spinbox.valueChanged.connect(on_thickness_change)
                        
                        color_layout.addWidget(color_label)
                        color_layout.addWidget(color_button)
                        layout.addWidget(color_frame)
                        
                        thickness_layout.addWidget(thickness_label)
                        thickness_layout.addWidget(thickness_spinbox)
                        layout.addWidget(thickness_frame)

                        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                                    QDialogButtonBox.StandardButton.Cancel)
                        button_box.accepted.connect(dialog.accept)
                        button_box.rejected.connect(dialog.reject)
                        layout.addWidget(button_box)

                        dialog.setLayout(layout)
                        dialog.setStyleSheet("""
                            QDialog#CustomDialog {
                                background-color: #000000;
                                color: white;
                                font-size: 14px;
                                border: 1px solid #444444;
                            }
                            QLabel {
                                color: white;
                                background-color: transparent;
                            }
                            QFrame {
                                background-color: transparent;
                            }
                            QComboBox {
                                background-color: #111111;
                                color: white;
                                border: 1px solid #555555;
                                padding: 5px;
                            }
                            QComboBox QAbstractItemView {
                                background-color: #000000;
                                color: white;
                                selection-background-color: #222222;
                            }
                            QPushButton {
                                background-color: #111111;
                                color: white;
                                border: 1px solid #666666;
                                border-radius: 5px;
                                padding: 6px 12px;
                            }
                            QPushButton:hover {
                                background-color: #222222;
                            }
                            QDialogButtonBox QPushButton {
                                background-color: #111111;
                                color: white;
                                border: 1px solid #666666;
                            }
                            QDialog {
                                background-color: #000000;
                                color: white;
                                font-size: 14px;
                                border: 1px solid #444444;
                            }
                            QLabel {
                                color: white;
                                background-color: transparent;
                                font-size: 12px;
                            }
                            QSpinBox {
                                background-color: #111111;
                                color: white;
                                border: 1px solid #555555;
                                padding: 5px;
                            }
                            QSpinBox:focus {
                                border: 1px solid #666666;
                            }
                            QPushButton {
                                background-color: #111111;
                                color: white;
                                border: 1px solid #666666;
                                border-radius: 5px;
                                padding: 6px 12px;
                            }
                            QPushButton:hover {
                                background-color: #222222;
                            }
                            QPushButton:pressed {
                                background-color: #333333;
                            }
                            QGroupBox {
                                color: white;
                                font-weight: bold;
                                border: 1px solid #444444;
                                margin-top: 10px;
                                padding-top: 10px;
                                background-color: transparent;
                            }
                            QGroupBox::title {
                                subcontrol-origin: margin;
                                left: 10px;
                                padding: 0 5px 0 5px;
                                color: white;
                            }
                            QDialogButtonBox QPushButton {
                                background-color: #111111;
                                color: white;
                                border: 1px solid #666666;
                                min-width: 80px;
                                padding: 6px 12px;
                            }
                            QDialogButtonBox QPushButton:hover {
                                background-color: #222222;
                            }                              
                        """)

                        # Execute the dialog
                        if dialog.exec() == QDialog.DialogCode.Accepted:
                            label_text = combo.currentText().strip()
                            if label_text:
                                # Update last used label
                                self.last_used_label = label_text
                                
                                # Store the color and thickness for this label
                                self.label_colors[label_text] = current_color.name()
                                self.label_thickness[label_text] = current_thickness
                                
                                labeled_rect = LabeledRectangle(rect.x(), rect.y(), rect.width(), rect.height(), label_text)
                                # Set the rectangle color and thickness
                                labeled_rect.set_color(current_color)
                                labeled_rect.set_thickness(current_thickness)  # Add this method to LabeledRectangle
                                self.scene.addItem(labeled_rect)
                                self.labeled_rectangles.append(labeled_rect)
                                self.save_rectangle_to_jpeg(labeled_rect)
                                self.show_rectangle_label_properties(label_text, current_color, current_thickness)

                                # Make sure this label is in recent_labels
                                if label_text not in self.recent_labels:
                                    self.recent_labels.append(label_text)

                    else:
                        # Fall back to standard text input if no recent labels (similar changes needed here)
                        self.label_properties_manager.load_properties()
                        if hasattr(self.label_properties_manager, 'label_properties') and self.label_properties_manager.label_properties:
                            # Initialize dictionaries if they don't exist
                            if not hasattr(self, 'label_colors'):
                                self.label_colors = {}
                            if not hasattr(self, 'label_thickness'):
                                self.label_thickness = {}
                            if not hasattr(self, 'recent_labels'):
                                self.recent_labels = []
                            
                            # Update from loaded properties
                            for label_name, props in self.label_properties_manager.label_properties.items():
                                if label_name not in self.recent_labels:
                                    self.recent_labels.append(label_name)
                                self.label_colors[label_name] = props['color'].name()  # Convert QColor to hex string
                                self.label_thickness[label_name] = props['thickness']

                        input_dialog = QDialog(self)
                        input_dialog.setWindowTitle("Label Rectangle")
                        input_dialog.setObjectName("CustomInputDialog")
                        
                        layout = QVBoxLayout()
                        
                        label_input = QLineEdit()
                        # Pre-fill with last used label if available
                        if self.last_used_label:
                            label_input.setText(self.last_used_label)
                        label_input.setPlaceholderText("Enter label:")
                        
                        label = QLabel("Enter label:")
                        layout.addWidget(label)
                        layout.addWidget(label_input)
                        
                        # Add color selection
                        color_frame = QFrame()
                        color_layout = QHBoxLayout(color_frame)
                        color_layout.setContentsMargins(0, 0, 0, 0)
                        
                        color_label = QLabel("Color:")
                        color_button = QPushButton("Choose Color")
                        color_button.setObjectName("ColorButton")
                        
                        # Add thickness selection
                        thickness_frame = QFrame()
                        thickness_layout = QHBoxLayout(thickness_frame)
                        thickness_layout.setContentsMargins(0, 0, 0, 0)
                        
                        thickness_label = QLabel("Thickness:")
                        thickness_spinbox = QSpinBox()
                        thickness_spinbox.setMinimum(1)
                        thickness_spinbox.setMaximum(10)
                        thickness_spinbox.setSuffix(" px")
                        
                        # Set default color and thickness based on last used label or defaults
                        if self.last_used_label and hasattr(self, 'label_colors') and self.last_used_label in self.label_colors:
                            current_color = QColor(self.label_colors[self.last_used_label])
                        else:
                            current_color = QColor(255, 0, 0)  # Default red
                            
                        if self.last_used_label and hasattr(self, 'label_thickness') and self.last_used_label in self.label_thickness:
                            current_thickness = self.label_thickness[self.last_used_label]
                        else:
                            current_thickness = 2  # Default thickness
                        thickness_spinbox.setValue(current_thickness)
                            
                        color_button.setStyleSheet(f"""
                            QPushButton#ColorButton {{
                                background-color: {current_color.name()};
                                color: white;
                                border: 2px solid #666666;
                                border-radius: 5px;
                                padding: 6px 12px;
                                font-weight: bold;
                            }}
                            QPushButton#ColorButton:hover {{
                                border: 2px solid #888888;
                            }}
                        """)
                        
                        def choose_color():
                            nonlocal current_color
                            color = QColorDialog.getColor(current_color, input_dialog, "Choose Rectangle Color")
                            if color.isValid():
                                current_color = color
                                color_button.setStyleSheet(f"""
                                    QPushButton#ColorButton {{
                                        background-color: {current_color.name()};
                                        color: white;
                                        border: 2px solid #666666;
                                        border-radius: 5px;
                                        padding: 6px 12px;
                                        font-weight: bold;
                                    }}
                                    QPushButton#ColorButton:hover {{
                                        border: 2px solid #888888;
                                    }}
                                """)
                        
                        def on_thickness_change():
                            nonlocal current_thickness
                            current_thickness = thickness_spinbox.value()
                        
                        color_button.clicked.connect(choose_color)
                        thickness_spinbox.valueChanged.connect(on_thickness_change)
                        
                        color_layout.addWidget(color_label)
                        color_layout.addWidget(color_button)
                        layout.addWidget(color_frame)
                        
                        thickness_layout.addWidget(thickness_label)
                        thickness_layout.addWidget(thickness_spinbox)
                        layout.addWidget(thickness_frame)
                        
                        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                                    QDialogButtonBox.StandardButton.Cancel)
                        button_box.accepted.connect(input_dialog.accept)
                        button_box.rejected.connect(input_dialog.reject)
                        layout.addWidget(button_box)
                        
                        input_dialog.setLayout(layout)
                        
                        # Apply existing stylesheet (same as before)
                        input_dialog.setStyleSheet("""
                            QDialog#CustomInputDialog {
                                background-color: #000000;
                                color: white;
                                font-size: 14px;
                                border: 1px solid #444444;
                            }
                            QLabel {
                                color: white;
                                background-color: transparent;
                            }
                            QFrame {
                                background-color: transparent;
                            }
                            QLineEdit {
                                background-color: #222222;
                                color: white;
                                border: 1px solid #555555;
                                padding: 5px;
                            }
                            QPushButton {
                                background-color: #111111;
                                color: white;
                                border: 1px solid #666666;
                                border-radius: 5px;
                                padding: 6px 12px;
                            }
                            QPushButton:hover {
                                background-color: #222222;
                            }
                            QDialog {
                                background-color: #000000;
                                color: white;
                                font-size: 14px;
                                border: 1px solid #444444;
                            }
                            QLabel {
                                color: white;
                                background-color: transparent;
                                font-size: 12px;
                            }
                            QSpinBox {
                                background-color: #111111;
                                color: white;
                                border: 1px solid #555555;
                                padding: 5px;
                            }
                            QSpinBox:focus {
                                border: 1px solid #666666;
                            }
                            QPushButton {
                                background-color: #111111;
                                color: white;
                                border: 1px solid #666666;
                                border-radius: 5px;
                                padding: 6px 12px;
                            }
                            QPushButton:hover {
                                background-color: #222222;
                            }
                            QPushButton:pressed {
                                background-color: #333333;
                            }
                            QGroupBox {
                                color: white;
                                font-weight: bold;
                                border: 1px solid #444444;
                                margin-top: 10px;
                                padding-top: 10px;
                                background-color: transparent;
                            }
                            QGroupBox::title {
                                subcontrol-origin: margin;
                                left: 10px;
                                padding: 0 5px 0 5px;
                                color: white;
                            }
                            QDialogButtonBox QPushButton {
                                background-color: #111111;
                                color: white;
                                border: 1px solid #666666;
                                min-width: 80px;
                                padding: 6px 12px;
                            }
                            QDialogButtonBox QPushButton:hover {
                                background-color: #222222;
                            }                              
                        """)

                        if input_dialog.exec() == QDialog.DialogCode.Accepted:
                            label_text = label_input.text().strip()
                            if label_text:
                                # Update last used label
                                self.last_used_label = label_text
                                
                                # Initialize label colors and thickness dictionaries if not exists
                                if not hasattr(self, 'label_colors'):
                                    self.label_colors = {}
                                if not hasattr(self, 'label_thickness'):
                                    self.label_thickness = {}
                                
                                # Store the color and thickness for this label
                                self.label_colors[label_text] = current_color.name()
                                self.label_thickness[label_text] = current_thickness
                                
                                labeled_rect = LabeledRectangle(rect.x(), rect.y(), rect.width(), rect.height(), label_text)
                                # Set the rectangle color and thickness
                                labeled_rect.set_color(current_color)
                                labeled_rect.set_thickness(current_thickness)  # Add this method to LabeledRectangle
                                self.scene.addItem(labeled_rect)
                                self.labeled_rectangles.append(labeled_rect)
                                self.save_rectangle_to_jpeg(labeled_rect)
                                self.show_rectangle_label_properties(label_text, current_color, current_thickness)

                                # Initialize recent_labels if needed
                                if not hasattr(self, 'recent_labels'):
                                    self.recent_labels = []
                                if label_text not in self.recent_labels:
                                    self.recent_labels.append(label_text)
                        if label_text:
                            self.label_properties_manager.add_label_property(label_text, current_color, current_thickness)

                # Clean up the temporary rectangle regardless of whether we saved it
                if self.current_rect:
                    self.scene.removeItem(self.current_rect)
                self.rect_start = None
                self.current_rect = None

        elif self.rectangle_mode and event.button() == Qt.MouseButton.RightButton:
            # Handle right-click on rectangles
            scene_pos = self.mapToScene(int(event.position().x()), int(event.position().y()))
            item = self.scene.itemAt(scene_pos, self.transform())

            # Check if the clicked item is a LabeledRectangle or if we need to check all rectangles
            if item and isinstance(item, LabeledRectangle):
                self.show_rectangle_context_menu(item, event.globalPosition().toPoint())
                return
            else:
                # Alternative approach: check all rectangles to see if click is inside any of them
                for rect in self.labeled_rectangles:
                    if rect.contains(scene_pos):
                        self.show_rectangle_context_menu(rect, event.globalPosition().toPoint())
                        return
                print("No rectangle found at click position")

        elif self.polygon_mode and event.button() == Qt.MouseButton.RightButton:
            # Handle right-click on rectangles
            scene_pos = self.mapToScene(int(event.position().x()), int(event.position().y()))
            item = self.scene.itemAt(scene_pos, self.transform())
            if item and hasattr(item, 'polygon'):
                self.show_polygon_context_menu(item, event.globalPosition().toPoint())
            else:
                print("No polygon found at click position")
        super().mouseReleaseEvent(event)

    def undo_last_stroke(self):
        """
        Optimized method to remove the last stroke/operation with improved performance
        """
        if not self.points_history:
            return
            
        # Get the last stroke to undo
        last_stroke = self.points_history.pop()
        
        # Check if this is an erase operation
        is_erase_operation = (isinstance(last_stroke[0], tuple) and 
                              last_stroke[0][0] == 'erase')
        
        if is_erase_operation:
            # For erase operations, restore the erased points
            restored_points = []
            for op_type, point_item in last_stroke:  # Fixed syntax error here
                # Add point back to our points list
                self.points.append(point_item)
                restored_points.append(point_item)
                
                # Re-add to scene efficiently without redundant checks
                if point_item.scene() is None:
                    self.scene.addItem(point_item)
                    
                # Keep invisible as we use overlay for rendering
                point_item.setVisible(False)
        else:
            # For regular strokes, remove the points
            points_to_remove = set(last_stroke)  # Use set for O(1) lookups
            
            # Batch remove from points list (much faster than removing one by one)
            self.points = [p for p in self.points if p not in points_to_remove]
            
            # Batch remove from scene (more efficient)
            for point_item in last_stroke:
                if point_item.scene() == self.scene:
                    self.scene.removeItem(point_item)
        
        # Force a complete redraw of the points overlay
        if hasattr(self, 'points_pixmap') and self.points_pixmap is not None:
            self.points_pixmap.fill(Qt.GlobalColor.transparent)
        self.last_rendered_points_count = 0
        
        # Update the overlay in one operation instead of per-point
        self.update_points_overlay()
        
        # Force a scene update to ensure changes are visible
        if hasattr(self, 'points_overlay_item') and self.points_overlay_item is not None:
            self.scene.update(self.points_overlay_item.boundingRect())
        
        # Force garbage collection to free up memory
        gc.collect()
    
    def reset_view(self):
        """Reset view to original state"""
        if self.base_pixmap:
            self.resetTransform()
            self.zoom_factor = 1.0
            self.setSceneRect(self.pixmap_item.boundingRect())
            self.fitInView(self.pixmap_item.boundingRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def keyPressEvent(self, event):
        """Handle key press events"""
        step = int(20 / self.zoom_factor)  # Convert to integer with int()
        
        if event.key() == Qt.Key.Key_Left:
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - step)
        elif event.key() == Qt.Key.Key_Right:
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() + step)
        elif event.key() == Qt.Key.Key_Up:
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - step)
        elif event.key() == Qt.Key.Key_Down:
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() + step)
        else:
            super().keyPressEvent(event)

        # Apply the new opacity to the overlay
        if hasattr(self, 'points_overlay_item') and self.points_overlay_item:
            self.points_overlay_item.setOpacity(value / 255.0)
        
        # Update the existing overlay opacity if it exists (different from points overlay)
        if self.overlay_pixmap_item:
            self.overlay_opacity = value
            self.overlay_pixmap_item.setOpacity(value / 255.0)
        
        # Force scene update
        self.scene.update() 