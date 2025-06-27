from PyQt6.QtCore import Qt, QRectF, QPointF, QLineF
from PyQt6.QtGui import QPen, QColor, QCursor, QImage, QPainter, QPolygonF
from PyQt6.QtWidgets import (QInputDialog, QDialog, QVBoxLayout, QComboBox, QLabel, 
                            QDialogButtonBox, QMenu, QColorDialog, QSpinBox, QHBoxLayout,
                            QPushButton, QGroupBox, QFormLayout, QGraphicsItem, QGraphicsEllipseItem, QLineEdit)
import os
import time
import math

class LabelPolygonPropertiesDialog(QDialog):
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
                background-color: #000000;
                border: none;
            }
            """)

        layout = QVBoxLayout()

        self.label_name = QLabel("Label: ")
        self.label_color = QLabel("Color: ")
        self.label_thickness= QLabel("thickness: ")

        layout.addWidget(self.label_name)
        layout.addWidget(self.label_color)
        layout.addWidget(self.label_thickness)

        self.setLayout(layout)

    def update_properties(self, label, color, thickness):
        self.label_name.setText(f"Label: {label}")
        self.label_color.setText(f"Color: {color.name()}")
        self.label_thickness.setText(f"thickness: {thickness}")

class DraggableVertex(QGraphicsEllipseItem):
    """Custom draggable vertex point for polygon editing"""
    def __init__(self, x, y, vertex_index, polygon_tool, polygon_item):
        super().__init__(x - 4, y - 4, 8, 8)
        self.vertex_index = vertex_index
        self.polygon_tool = polygon_tool
        self.polygon_item = polygon_item
        
        # Visual appearance
        self.setPen(QPen(QColor(255, 255, 0), 2))  # Yellow outline
        self.setBrush(QColor(255, 0, 0))  # Red fill
        
        # Make it draggable and send position changes
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsScenePositionChanges, True)
        self.setZValue(1000)  # Ensure points are on top
    
    def itemChange(self, change, value):
        """Handle item changes, particularly position changes"""
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            # Update the polygon when this vertex moves
            if self.polygon_tool and hasattr(self.polygon_tool, 'update_polygon_from_vertex'):
                # Get the center of the item in scene coordinates
                new_pos = self.mapToScene(value)
                self.polygon_tool.update_polygon_from_vertex(self.vertex_index, new_pos)
                return value  # Return the original value to ensure it is set correctly

        return super().itemChange(change, value)

    
class CustomizePolygonDialog(QDialog):
    """Dialog for customizing polygon appearance"""
    def __init__(self, current_color=None, current_thickness=2, properties_manager=None, parent=None):
        super().__init__(parent)
        self.properties_manager = properties_manager
        self.setWindowTitle("Customize Polygon")
        self.setModal(True)
        self.resize(300, 300)  # Increased height for label selection

        # CONSISTENT DARK THEME STYLESHEET
        self.setStyleSheet("""
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
        """)

        layout = QVBoxLayout(self)

        # Label selection group
        if self.properties_manager:
            label_group = QGroupBox("Label")
            label_layout = QFormLayout()

            self.label_combo = QComboBox()
            self.label_combo.addItem("")  # Empty option
            self.label_combo.addItems(self.properties_manager.get_all_labels())
            self.label_combo.setEditable(True)
            self.label_combo.currentTextChanged.connect(self.update_properties_from_label)

            label_layout.addRow("Label:", self.label_combo)
            label_group.setLayout(label_layout)
            layout.addWidget(label_group)

        # Color selection group
        color_group = QGroupBox("Polygon Color")
        color_layout = QFormLayout()

        # Color selection
        color_selection_layout = QHBoxLayout()
        self.color_button = QPushButton("Choose Color")
        self.color_button.clicked.connect(self.choose_color)

        # Set initial color
        self.selected_color = current_color if current_color else QColor(0, 255, 0)  # Default green
        self.update_color_button()

        color_selection_layout.addWidget(self.color_button)
        color_selection_layout.addStretch()

        color_layout.addRow("Color:", color_selection_layout)
        color_group.setLayout(color_layout)
        layout.addWidget(color_group)

        # Thickness selection group
        thickness_group = QGroupBox("Polygon Thickness")
        thickness_layout = QFormLayout()

        self.thickness_spinbox = QSpinBox()
        self.thickness_spinbox.setMinimum(1)
        self.thickness_spinbox.setMaximum(10)
        self.thickness_spinbox.setValue(current_thickness)
        self.thickness_spinbox.setSuffix(" px")

        thickness_layout.addRow("Thickness:", self.thickness_spinbox)
        thickness_group.setLayout(thickness_layout)
        layout.addWidget(thickness_group)

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout.addWidget(button_box)

    def update_properties_from_label(self, label):
        """Update color and thickness based on the selected label"""
        if not label or not self.properties_manager:
            return

        props = self.properties_manager.get_label_property(label)
        if props:
            self.selected_color = props['color']
            self.update_color_button()
            self.thickness_spinbox.setValue(props['thickness'])
            
            # UPDATE PARENT'S DEFAULT VALUES IF PARENT IS POLYGON TOOL
            if hasattr(self.parent(), 'default_polygon_color'):
                self.parent().default_polygon_color = props['color']
                self.parent().default_polygon_thickness = props['thickness']

    def get_settings(self):
        """Return the selected color, thickness, and label"""
        color = self.selected_color
        thickness = self.thickness_spinbox.value()
        label = self.label_combo.currentText().strip() if hasattr(self, 'label_combo') else None
        return color, thickness, label

    def choose_color(self):
        """Open color dialog to choose polygon color"""
        color_dialog = QColorDialog(self.selected_color, self)
        color_dialog.setStyleSheet("""
            QColorDialog {
                background-color: #000000;
                color: white;
            }
            QColorDialog QLabel {
                color: white;
                background-color: transparent;
            }
            QColorDialog QPushButton {
                background-color: #111111;
                color: white;
                border: 1px solid #666666;
                border-radius: 5px;
                padding: 6px 12px;
            }
            QColorDialog QPushButton:hover {
                background-color: #222222;
            }
            QColorDialog QSpinBox {
                background-color: #111111;
                color: white;
                border: 1px solid #555555;
                padding: 5px;
            }
            QColorDialog QLineEdit {
                background-color: #222222;
                color: white;
                border: 1px solid #555555;
                padding: 5px;
            }
        """)

        if color_dialog.exec() == QDialog.DialogCode.Accepted:
            self.selected_color = color_dialog.currentColor()
            self.update_color_button()

    def update_color_button(self):
        """Update the color button to show the selected color"""
        color_name = self.selected_color.name()
        self.color_button.setText(f"Color: {color_name}")
        text_color = 'white' if self.selected_color.lightness() < 128 else 'black'
        self.color_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color_name};
                color: {text_color};
                border: 1px solid #555555;
                padding: 6px 12px;
                border-radius: 5px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                border: 2px solid #777777;
                background-color: {color_name};
            }}
        """)
    
    def get_settings(self):
        """Return the selected color, thickness, and label"""
        color = self.selected_color
        thickness = self.thickness_spinbox.value()
        label = self.label_combo.currentText().strip() if hasattr(self, 'label_combo') else None
        return color, thickness, label


class PolygonTool:
    last_used_label = None
    def __init__(self):
        # Default polygon appearance settings
        self.default_polygon_color = QColor(0, 255, 0)  # Green
        self.default_polygon_thickness = 2
    def add_polygon_point(self, point):
        """Add a point to the current polygon being created"""
        self.current_polygon_points.append(point)
        
        # Draw a small circle at the point
        circle_radius = 3
        circle = self.scene.addEllipse(
            point.x() - circle_radius, point.y() - circle_radius,
            circle_radius * 2, circle_radius * 2,
            QPen(self.default_polygon_color, 1)
        )
        
        # Connect to previous point with a line
        if len(self.current_polygon_points) > 1:
            prev_point = self.current_polygon_points[-2]
            line = self.scene.addLine(
                prev_point.x(), prev_point.y(),
                point.x(), point.y(),
                QPen(self.default_polygon_color, self.default_polygon_thickness)
            )
            self.current_polygon_lines.append(line)
        
        self.current_polygon_lines.append(circle)
    
    def update_polygon_preview(self, current_pos):
        """Update the preview line showing where the next polygon edge will be"""
        if not self.current_polygon_points:
            return
        
        # Remove existing preview line
        if hasattr(self, 'preview_line') and self.preview_line:
            self.scene.removeItem(self.preview_line)
        
        # Create new preview line from last point to current mouse position
        last_point = self.current_polygon_points[-1]
        self.preview_line = self.scene.addLine(
            last_point.x(), last_point.y(),
            current_pos.x(), current_pos.y(),
            QPen(self.default_polygon_color, 1, Qt.PenStyle.DashLine)
        )
        
        # If we have at least 3 points, also show a line to the first point
        if len(self.current_polygon_points) >= 3:
            if hasattr(self, 'close_preview_line') and self.close_preview_line:
                self.scene.removeItem(self.close_preview_line)
            
            first_point = self.current_polygon_points[0]
            distance = math.sqrt((current_pos.x() - first_point.x())**2 + 
                               (current_pos.y() - first_point.y())**2)
            
            # Show close preview line if mouse is close to first point
            if distance <= self.close_distance_threshold:
                self.close_preview_line = self.scene.addLine(
                    current_pos.x(), current_pos.y(),
                    first_point.x(), first_point.y(),
                    QPen(QColor(255, 255, 0), 2)  # Yellow line to indicate close
                )
    
    def close_polygon(self):
        """Close the current polygon and create a polygon item"""
        if len(self.current_polygon_points) < 3:
            return

        # Remove preview lines
        if hasattr(self, 'preview_line') and self.preview_line:
            self.scene.removeItem(self.preview_line)
            self.preview_line = None
        if hasattr(self, 'close_preview_line') and self.close_preview_line:
            self.scene.removeItem(self.close_preview_line)
            self.close_preview_line = None

        # Remove temporary drawing elements
        for item in self.current_polygon_lines:
            self.scene.removeItem(item)

        # Create the final polygon
        polygon = QPolygonF(self.current_polygon_points)

        # Use last used label's properties if available
        if PolygonTool.last_used_label and hasattr(self, 'label_properties_manager'):
            props = self.label_properties_manager.get_label_property(PolygonTool.last_used_label)
            if props:
                color = props['color']
                thickness = props['thickness']
            else:
                color = self.default_polygon_color
                thickness = self.default_polygon_thickness
        else:
            color = self.default_polygon_color
            thickness = self.default_polygon_thickness

        dialog = CustomizePolygonDialog(color, thickness, self.label_properties_manager if hasattr(self, 'label_properties_manager') else None, self)
        dialog.setWindowTitle("Customize Polygon")

        # Set the label combo box to the last used label if available
        if PolygonTool.last_used_label:
            dialog.label_combo.setCurrentText(PolygonTool.last_used_label)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_color, new_thickness, new_label = dialog.get_settings()

            # UPDATE DEFAULT VALUES TO MATCH SELECTED VALUES
            self.default_polygon_color = new_color
            self.default_polygon_thickness = new_thickness

            pen = QPen(new_color, new_thickness)
            polygon_item = self.scene.addPolygon(polygon, pen)

            # Store custom settings on the polygon
            polygon_item.custom_color = new_color
            polygon_item.custom_thickness = new_thickness
            polygon_item.label_name = new_label  # Store the label name
            polygon_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
            polygon_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)

            # Save the label properties if a new label was created
            if new_label and hasattr(self, 'label_properties_manager'):
                self.label_properties_manager.add_label_property(new_label, new_color, new_thickness)

            # Add to polygon items list
            self.polygon_items.append(polygon_item)

            # Update the last used label
            if new_label:
                PolygonTool.last_used_label = new_label

        # Reset polygon creation state
        self.current_polygon_points = []
        self.current_polygon_lines = []

        return polygon_item if 'polygon_item' in locals() else None
        
    def cancel_polygon_creation(self):
        """Cancel the current polygon creation"""
        # Remove preview lines
        if hasattr(self, 'preview_line') and self.preview_line:
            self.scene.removeItem(self.preview_line)
            self.preview_line = None
        if hasattr(self, 'close_preview_line') and self.close_preview_line:
            self.scene.removeItem(self.close_preview_line)
            self.close_preview_line = None
        
        # Remove temporary drawing elements
        for item in self.current_polygon_lines:
            self.scene.removeItem(item)
        
        # Reset state
        self.current_polygon_points = []
        self.current_polygon_lines = []
        
        print("Polygon creation cancelled")
    
    def show_polygon_context_menu(self, labeled_polygon, global_pos):
        """Show context menu for polygon manipulation"""
        context_menu = QMenu(self)
        
        # CONSISTENT DARK THEME FOR CONTEXT MENU
        context_menu.setStyleSheet("""
            QMenu {
                background-color: #000000;
                color: white;
                border: 1px solid #444444;
                font-size: 14px;
            }
            QMenu::item {
                padding: 8px 20px;
                background-color: transparent;
            }
            QMenu::item:selected {
                background-color: #222222;
            }
            QMenu::separator {
                height: 1px;
                background-color: #444444;
                margin: 2px 0px;
            }
        """)

        custom_action = context_menu.addAction("Custom")
        modify_action = context_menu.addAction("Modify")
        context_menu.addSeparator()
        delete_action = context_menu.addAction("Delete")
        
        # Execute the menu and handle the selected action
        action = context_menu.exec(global_pos)

        if action == custom_action:
            self.customize_polygon(labeled_polygon)
        elif action == modify_action:
            self.start_polygon_edit_mode(labeled_polygon)
        elif action == delete_action:
            self.delete_polygon(labeled_polygon)
    
    def customize_polygon(self, labeled_polygon):
        """Show dialog to customize polygon appearance"""
        current_pen = labeled_polygon.pen()
        current_color = current_pen.color()
        current_thickness = current_pen.width()
        current_label = getattr(labeled_polygon, 'label_name', '')

        dialog = CustomizePolygonDialog(
            current_color,
            current_thickness,
            self.label_properties_manager if hasattr(self, 'label_properties_manager') else None,
            self
        )

        if hasattr(dialog, 'label_combo'):
            dialog.label_combo.setCurrentText(current_label)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_color, new_thickness, new_label = dialog.get_settings()
            new_pen = QPen(new_color, new_thickness)

            self.default_polygon_color = new_color
            self.default_polygon_thickness = new_thickness

            if not hasattr(labeled_polygon, 'original_pen'):
                labeled_polygon.original_pen = current_pen

            labeled_polygon.setPen(new_pen)
            labeled_polygon.custom_color = new_color
            labeled_polygon.custom_thickness = new_thickness

            # Update label if changed
            if new_label:
                labeled_polygon.label_name = new_label
                PolygonTool.last_used_label = new_label

                # Update label properties if this is a new label
                if hasattr(self, 'label_properties_manager') and new_label:
                    self.label_properties_manager.add_label_property(
                        new_label, new_color, new_thickness
                    )

            self.scene.update()

    
    def delete_polygon(self, labeled_polygon):
        """Delete the selected polygon"""
        if labeled_polygon in self.polygon_items:
            self.polygon_items.remove(labeled_polygon)
        if labeled_polygon in self.labeled_polygons:
            self.labeled_polygons.remove(labeled_polygon)
        self.scene.removeItem(labeled_polygon)
    
    def save_polygon_to_jpeg(self, labeled_polygon):
        """Save the polygon selection area to a JPEG file"""
        # Get the bounding rectangle of the polygon
        bounding_rect = labeled_polygon.boundingRect()

        # Create a QImage with the size of the bounding rectangle
        image = QImage(int(bounding_rect.width()), int(bounding_rect.height()), QImage.Format.Format_RGB888)
        image.fill(Qt.GlobalColor.white)

        # Create a painter for the image
        painter = QPainter(image)

        # Render the scene portion
        source_rect = bounding_rect
        target_rect = QRectF(0, 0, bounding_rect.width(), bounding_rect.height())
        self.scene.render(painter, target_rect, source_rect)

        # Draw the polygon on the image
        pen = QPen(labeled_polygon.pen().color(), labeled_polygon.pen().width())
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        polygon = labeled_polygon.polygon()
        polygon_translated = QPolygonF()
        for point in polygon:
            polygon_translated.append(QPointF(point.x() - bounding_rect.x(), point.y() - bounding_rect.y()))
        painter.drawPolygon(polygon_translated)

        painter.end()

        # Save the image
        save_dir = os.path.join(os.getcwd(), 'save', 'polygons')
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        file_name = f"polygon_{int(bounding_rect.x())}_{int(bounding_rect.y())}.jpeg"
        file_path = os.path.join(save_dir, file_name)

        if image.save(file_path, "JPEG"):
            print(f"Polygon selection saved successfully at {file_path}")
        else:
            print("Failed to save the polygon selection.")
    
    def toggle_polygon_mode(self, enabled):
        """Toggle polygon selection mode on/off"""
        self.polygon_mode = enabled
        
        if not enabled:
            # Cancel any current polygon creation
            self.cancel_polygon_creation()

    def clear_polygons(self):
        """Remove all polygon selections from the scene"""
        if hasattr(self, 'polygon_items') and self.polygon_items:
            for item in self.polygon_items:
                if item in self.scene.items():
                    self.scene.removeItem(item)
            self.polygon_items = []
        
        if hasattr(self, 'labeled_polygons') and self.labeled_polygons:
            for item in self.labeled_polygons:
                if item in self.scene.items():
                    self.scene.removeItem(item)
            self.labeled_polygons = []
        
        # Cancel any current polygon creation
        self.cancel_polygon_creation()
        
        self.scene.update()
    
    def set_default_polygon_style(self):
        """Show dialog to set default polygon style"""
        dialog = CustomizePolygonDialog(self.default_polygon_color, 
                                       self.default_polygon_thickness, self)
        dialog.setWindowTitle("Set Default Polygon Style")
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.default_polygon_color, self.default_polygon_thickness = dialog.get_settings()
            print(f"Default polygon style updated: Color={self.default_polygon_color.name()}, Thickness={self.default_polygon_thickness}px")

    def save_entire_image_with_polygons(self):
        """Save the entire image with rectangles and polygons drawn on it."""
        if not hasattr(self, 'base_pixmap') or self.base_pixmap is None:
            print("No base image to save.")
            return False

        # Create a QImage with the same size as the base pixmap
        image = QImage(self.base_pixmap.size(), QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)  # Start with a transparent background

        # Create a painter for the image
        painter = QPainter(image)

        # Draw the base image
        painter.drawPixmap(0, 0, self.base_pixmap)

        # Draw all polygons with their custom colors and thickness
        if hasattr(self, 'polygon_items'):
            for polygon_item in self.polygon_items:
                polygon = polygon_item.polygon()
                pen = polygon_item.pen()
                painter.setPen(pen)  # Use the polygon's custom pen
                painter.drawPolygon(polygon)
                
        if hasattr(self, 'labeled_rectangles'):
            for rect_item in self.labeled_rectangles:
                rect = rect_item.rect()
                pen = rect_item.pen()
                painter.setPen(pen)  # Use the rectangle's custom pen
                painter.drawRect(rect)

        if hasattr(self, 'rectangle_items'):
            for rect_item in self.rectangle_items:
                rect = rect_item.rect()
                pen = rect_item.pen()
                painter.setPen(pen)  # Use the rectangle's custom pen
                painter.drawRect(rect)

        painter.end()

        # Create the folder to save the image
        save_dir = os.path.join(os.getcwd(), 'save')
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        # Generate a unique file name
        file_name = f"entire_image_with_shapes_{int(time.time())}.png"
        file_path = os.path.join(save_dir, file_name)

        # Save the image as PNG
        if image.save(file_path, "PNG"):
            print(f"Image saved successfully at {file_path}")
            return True
        else:
            print("Failed to save the image.")
            return False
        
    def start_polygon_edit_mode(self, polygon_item):
        """Start editing mode for the polygon with draggable vertices"""
        if hasattr(self, 'polygon_edit_mode') and self.polygon_edit_mode:
            self.end_polygon_edit_mode()

        self.polygon_edit_mode = True
        self.editing_polygon = polygon_item
        self.polygon_point_items = []

        # Create draggable vertex points for each vertex
        polygon = polygon_item.polygon()
        for i, point in enumerate(polygon):
            vertex_item = DraggableVertex(point.x(), point.y(), i, self, polygon_item)
            self.scene.addItem(vertex_item)
            self.polygon_point_items.append(vertex_item)

        # Make the polygon itself non-movable during edit
        polygon_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)

    def update_polygon_from_vertex(self, vertex_index, new_position):
        """Update the polygon shape when a vertex is moved"""
        if not self.polygon_edit_mode or not self.editing_polygon:
            return
        
        # Get current polygon
        current_polygon = self.editing_polygon.polygon()
        
        # Update the specific vertex
        if 0 <= vertex_index < len(current_polygon):
            # Create new polygon with updated vertex
            new_points = []
            for i, point in enumerate(current_polygon):
                if i == vertex_index:
                    new_points.append(new_position)
                else:
                    new_points.append(point)
            
            # Update the polygon
            new_polygon = QPolygonF(new_points)
            self.editing_polygon.setPolygon(new_polygon)

    def update_polygon_from_points(self):
        """Update the polygon shape based on current point positions"""
        if not hasattr(self, 'polygon_edit_mode') or not self.polygon_edit_mode or not self.editing_polygon:
            return
        
        # Get current positions of all points
        new_points = []
        for point_item in self.polygon_point_items:
            # Get the center of the point item in scene coordinates
            point_center = point_item.boundingRect().center()
            scene_center = point_item.mapToScene(point_center)
            new_points.append(QPointF(scene_center.x(), scene_center.y()))
        
        # Update the polygon
        new_polygon = QPolygonF(new_points)
        self.editing_polygon.setPolygon(new_polygon)

    def end_polygon_edit_mode(self):
        """End polygon editing mode"""
        if not hasattr(self, 'polygon_edit_mode') or not self.polygon_edit_mode:
            return
        
        # Remove all point items
        for point_item in self.polygon_point_items:
            self.scene.removeItem(point_item)
        self.polygon_point_items = []
        
        # Make the polygon movable again
        if self.editing_polygon:
            self.editing_polygon.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        
        self.polygon_edit_mode = False
        self.editing_polygon = None
        self.dragging_polygon_point = False
        self.dragged_point_item = None
        
        print("Polygon edit mode ended.")

    # Add this method to handle mouse events during polygon editing:
    def handle_polygon_edit_mouse_move(self, event):
        """Handle mouse move events during polygon editing"""
        if self.polygon_edit_mode:
            self.update_polygon_from_points()

    def handle_polygon_edit_mouse_press(self, event):
        """Handle mouse press events during polygon editing"""
        if self.polygon_edit_mode and event.button() == Qt.MouseButton.RightButton:
            self.end_polygon_edit_mode()
            return True  # Event handled
        return False  # Event not handled
    