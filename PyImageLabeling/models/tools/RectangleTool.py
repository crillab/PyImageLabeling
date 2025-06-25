from PyQt6.QtCore import Qt, QRectF, QPointF, QLineF
from PyQt6.QtGui import QPen, QColor, QCursor, QImage, QPainter
from PyQt6.QtWidgets import (QInputDialog, QDialog, QVBoxLayout, QComboBox, QLabel, 
                            QDialogButtonBox, QMenu, QColorDialog, QSpinBox, QHBoxLayout,
                            QPushButton, QGroupBox, QFormLayout, QMessageBox, QListWidget, QListWidgetItem)
import os
import time
import json

class LabelRectanglePropertiesDialog(QDialog):
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

class LabelPropertiesManager:
    """Manages saving and loading of label properties"""
    
    def __init__(self, properties_file="label_rectangle_properties.json"):
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
                    'thickness': props['thickness']
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
                        'thickness': props['thickness']
                    }
            return True
        except Exception as e:
            print(f"Error loading label properties: {e}")
            return False
    
    def add_label_property(self, label, color, thickness):
        """Add or update a label property"""
        self.label_properties[label] = {
            'color': color,
            'thickness': thickness
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


class ManageLabelPropertiesDialog(QDialog):
    """Dialog for managing saved label properties"""
    
    def __init__(self, properties_manager, parent=None):
        super().__init__(parent)
        self.properties_manager = properties_manager
        self.parent_widget = parent  # Store reference to parent widget
        self.setWindowTitle("Manage Label Properties")
        self.setModal(True)
        self.resize(400, 300)
        
        # Apply dark theme
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
            QListWidget {
                background-color: #111111;
                color: white;
                border: 1px solid #555555;
                selection-background-color: #333333;
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
        
        layout = QVBoxLayout(self)
        
        # Instructions
        instructions = QLabel("Manage your saved label properties:")
        layout.addWidget(instructions)
        
        # List widget to show saved labels
        self.labels_list = QListWidget()
        self.populate_labels_list()
        layout.addWidget(self.labels_list)
        
        # Buttons for managing labels
        buttons_layout = QHBoxLayout()
        
        self.edit_button = QPushButton("Edit Selected")
        self.edit_button.clicked.connect(self.edit_selected_label)
        buttons_layout.addWidget(self.edit_button)
        
        self.delete_button = QPushButton("Delete Selected")
        self.delete_button.clicked.connect(self.delete_selected_label)
        buttons_layout.addWidget(self.delete_button)
        
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.populate_labels_list)
        buttons_layout.addWidget(self.refresh_button)
        
        layout.addLayout(buttons_layout)
        
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.accept)
        layout.addWidget(button_box)
    
    def populate_labels_list(self):
        """Populate the list with saved labels and their properties"""
        self.labels_list.clear()
        
        for label in self.properties_manager.get_all_labels():
            props = self.properties_manager.get_label_property(label)
            if props:
                color_name = props['color'].name()
                thickness = props['thickness']
                
                item_text = f"{label} (Color: {color_name}, Thickness: {thickness}px)"
                item = QListWidgetItem(item_text)
                
                # Set the item's background color to match the label color
                item.setBackground(props['color'])
                
                # Set text color based on background brightness
                text_color = QColor('white' if props['color'].lightness() < 128 else 'black')
                item.setForeground(text_color)
                
                # Store the label name for easy access
                item.setData(Qt.ItemDataRole.UserRole, label)
                
                self.labels_list.addItem(item)
    
    def edit_selected_label(self):
        """Edit the selected label's properties"""
        current_item = self.labels_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select a label to edit.")
            return
        
        label = current_item.data(Qt.ItemDataRole.UserRole)
        props = self.properties_manager.get_label_property(label)
        
        if props:
            dialog = CustomizeRectangleDialog(props['color'], props['thickness'], self)
            dialog.setWindowTitle(f"Edit Properties for '{label}'")
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_color, new_thickness = dialog.get_settings()
                self.properties_manager.add_label_property(label, new_color, new_thickness)
                
                # Update all existing rectangles with this label
                self.update_rectangles_with_label(label, new_color, new_thickness)
                
                self.populate_labels_list()
                QMessageBox.information(self, "Success", f"Properties for '{label}' updated successfully!")
    
    def update_rectangles_with_label(self, label, new_color, new_thickness):
        """Update all existing rectangles that have the specified label"""
        if hasattr(self.parent_widget, 'labeled_rectangles'):
            for rect_item in self.parent_widget.labeled_rectangles:
                if hasattr(rect_item, 'get_label') and rect_item.get_label() == label:
                    # Update the rectangle's appearance
                    new_pen = QPen(new_color, new_thickness)
                    rect_item.setPen(new_pen)
                    
                    # Update stored properties on the rectangle
                    rect_item.set_color(new_color)
                    rect_item.set_thickness(new_thickness)
            
            # Update the scene to reflect changes
            self.parent_widget.scene.update()
    
    def delete_selected_label(self):
        """Delete the selected label's properties"""
        current_item = self.labels_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select a label to delete.")
            return
        
        label = current_item.data(Qt.ItemDataRole.UserRole)
        
        reply = QMessageBox.question(self, "Confirm Deletion", 
                                   f"Are you sure you want to delete the properties for '{label}'?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                   QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.properties_manager.remove_label_property(label):
                self.populate_labels_list()
                QMessageBox.information(self, "Success", f"Properties for '{label}' deleted successfully!")
            else:
                QMessageBox.warning(self, "Error", f"Failed to delete properties for '{label}'.")

class CustomizeRectangleDialog(QDialog):
    """Dialog for customizing rectangle appearance"""
    def __init__(self, current_color=None, current_thickness=2, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Customize Rectangle")
        self.setModal(True)
        self.resize(300, 200)
        
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
        """)
        
        layout = QVBoxLayout(self)
        
        # Color selection group
        color_group = QGroupBox("Rectangle Color")
        color_layout = QFormLayout()
        
        # Color selection
        color_selection_layout = QHBoxLayout()
        self.color_button = QPushButton("Choose Color")
        self.color_button.clicked.connect(self.choose_color)
        
        # Set initial color
        self.selected_color = current_color if current_color else QColor(255, 0, 0)  # Default red
        self.update_color_button()
        
        color_selection_layout.addWidget(self.color_button)
        color_selection_layout.addStretch()
        
        color_layout.addRow("Color:", color_selection_layout)
        color_group.setLayout(color_layout)
        layout.addWidget(color_group)
        
        # Thickness selection group
        thickness_group = QGroupBox("Rectangle Thickness")
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
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | 
                                     QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(button_box)
    
    def choose_color(self):
        """Open color dialog to choose rectangle color"""
        # Apply dark theme to color dialog
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
        # Use inline style for color button to override the general button style
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
        """Return the selected color and thickness"""
        return self.selected_color, self.thickness_spinbox.value()

class RectangleTool:
    def __init__(self):
        # Default rectangle appearance settings
        self.default_rect_color = QColor(255, 0, 0)  # Red
        self.default_rect_thickness = 2

    def load_label_properties_to_dicts(self):
        """Load saved label properties into the label_colors and label_thickness dictionaries"""
        for label in self.label_properties_manager.get_all_labels():
            props = self.label_properties_manager.get_label_property(label)
            if props:
                self.label_colors[label] = props['color']
                self.label_thickness[label] = props['thickness']

    def mouseDoubleClickEvent(self, event):
        """Handle double click to exit movement, rotation, or modification mode"""
        if hasattr(self, 'movement_mode') and self.movement_mode:
            self.movement_mode = False
            self.setCursor(Qt.CursorShape.ArrowCursor)

            # Restore original pen
            if hasattr(self, 'moving_rect') and hasattr(self.moving_rect, 'original_pen'):
                self.moving_rect.setPen(self.moving_rect.original_pen)
            self.moving_rect = None

        elif hasattr(self, 'rotation_mode') and self.rotation_mode:
            self.rotation_mode = False
            self.setCursor(Qt.CursorShape.ArrowCursor)

            # Restore original pen
            if hasattr(self, 'rotating_rect') and hasattr(self.rotating_rect, 'original_pen'):
                self.rotating_rect.setPen(self.rotating_rect.original_pen)
            self.rotating_rect = None

        elif hasattr(self, 'modification_mode') and self.modification_mode:
            # Exit modification mode on double click
            self.finish_modification()
    
    def show_rectangle_context_menu(self, labeled_rect, global_pos):
        """Show context menu with Move, Rotate, Delete, Custom, and Change Label options for a rectangle"""
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

        # Create actions
        move_action = context_menu.addAction("Move")
        rotate_action = context_menu.addAction("Rotate")
        modify_action = context_menu.addAction("Modify")
        context_menu.addSeparator()
        custom_action = context_menu.addAction("Custom")
        if self.rectangle_mode_type == 'classification':
            change_label_action = context_menu.addAction("Change Label")
            context_menu.addSeparator()
            manage_labels_action = context_menu.addAction("Manage Label Properties")
        context_menu.addSeparator()
        delete_action = context_menu.addAction("Delete")

        # Execute the menu and handle the selected action
        action = context_menu.exec(global_pos)

        if action == move_action:
            self.enable_rectangle_movement(labeled_rect)
        elif action == rotate_action:
            self.enable_rectangle_rotation(labeled_rect)
        elif action == modify_action:
            self.enable_rectangle_modification(labeled_rect)
        elif action == custom_action:
            self.customize_rectangle(labeled_rect)
        elif action == delete_action:
            self.delete_rectangle(labeled_rect)
        elif self.rectangle_mode_type == 'classification':
            if action == manage_labels_action:
                self.manage_label_properties()
            if action == change_label_action:
                self.change_rectangle_label(labeled_rect)

    def manage_label_properties(self):
            """Show dialog to manage saved label properties"""
            dialog = ManageLabelPropertiesDialog(self.label_properties_manager, self)
            dialog.exec()
            
            # Reload properties into dictionaries after management
            self.load_label_properties_to_dicts()

    def change_rectangle_label(self, labeled_rect):
        """Show dialog to change the label of the rectangle and update its color"""
        # Get the current label
        current_label = labeled_rect.get_label() if hasattr(labeled_rect, 'get_label') else ""

        # Create a dialog to select a new label from existing labels
        dialog = QDialog(self)
        dialog.setWindowTitle("Change Label")
        dialog.setObjectName("CustomDialog")

        layout = QVBoxLayout()

        # Add a combo box with existing labels
        combo = QComboBox()
        if hasattr(self, 'recent_labels') and self.recent_labels:
            combo.addItems(self.recent_labels)
        combo.setEditable(True)
        combo.setCurrentText(current_label)

        label = QLabel("Select an existing label or type a new one:")
        layout.addWidget(label)
        layout.addWidget(combo)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        dialog.setLayout(layout)

        # Apply black theme stylesheet
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
            new_label = combo.currentText().strip()
            if new_label:
                # Update the label
                labeled_rect.set_label(new_label)

                # Define color mapping logic
                new_color = self.label_colors.get(new_label, labeled_rect.get_color())
                labeled_rect.set_color(new_color)

                new_thickness = self.label_thickness.get(new_label)
                labeled_rect.set_thickness(new_thickness)

                self.label_properties_manager.add_label_property(new_label, new_color, new_thickness)

                self.scene.update()

                self.save_rectangle_to_jpeg(labeled_rect)

    def customize_rectangle(self, labeled_rect):
        """Show dialog to customize rectangle color and thickness"""
        # Get current rectangle settings
        current_pen = labeled_rect.pen()
        current_color = current_pen.color()
        current_thickness = current_pen.width()
        
        # Show customization dialog
        dialog = CustomizeRectangleDialog(current_color, current_thickness, self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Apply the new settings
            new_color, new_thickness = dialog.get_settings()
            new_pen = QPen(new_color, new_thickness)
            
            # Store the original pen if not already stored
            if not hasattr(labeled_rect, 'original_pen'):
                labeled_rect.original_pen = current_pen
            
            # Apply the new pen
            labeled_rect.setPen(new_pen)
            
            # Store the custom settings on the rectangle for future reference
            labeled_rect.custom_color = new_color
            labeled_rect.custom_thickness = new_thickness
            
            # Update the scene
            self.scene.update()

    def set_default_rectangle_style(self):
        """Show dialog to set default rectangle color and thickness for new rectangles"""
        dialog = CustomizeRectangleDialog(self.default_rect_color, self.default_rect_thickness, self)
        dialog.setWindowTitle("Set Default Rectangle Style")
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.default_rect_color, self.default_rect_thickness = dialog.get_settings()
            print(f"Default rectangle style updated: Color={self.default_rect_color.name()}, Thickness={self.default_rect_thickness}px")

    def create_rectangle_with_default_style(self, rect):
        """Create a rectangle with the current default style"""
        pen = QPen(self.default_rect_color, self.default_rect_thickness)
        rectangle_item = self.scene.addRect(rect, pen)
        
        # Store the default settings on the rectangle
        rectangle_item.custom_color = self.default_rect_color
        rectangle_item.custom_thickness = self.default_rect_thickness
        
        return rectangle_item

    def enable_rectangle_movement(self, labeled_rect):
        """Enable movement mode for the selected rectangle"""
        # Store the rectangle being moved
        self.moving_rect = labeled_rect
        self.movement_mode = True

        # Change cursor to indicate movement mode
        self.setCursor(Qt.CursorShape.SizeAllCursor)

        # Store original pen to restore later
        if not hasattr(labeled_rect, 'original_pen'):
            labeled_rect.original_pen = labeled_rect.pen()

        # Highlight the rectangle being moved
        highlight_pen = QPen(QColor(255, 255, 0), 2)  # Yellow highlight
        labeled_rect.setPen(highlight_pen)
        
        # Store the rectangle's current center in scene coordinates
        # This accounts for any rotation or transformation
        rect_center_local = labeled_rect.rect().center()
        self.rect_center_scene = labeled_rect.mapToScene(rect_center_local)
        
        # Store current mouse position
        current_mouse_pos = self.mapToScene(self.mapFromGlobal(QCursor.pos()))
        self.mouse_offset = QPointF(
            current_mouse_pos.x() - self.rect_center_scene.x(),
            current_mouse_pos.y() - self.rect_center_scene.y()
        )

    def enable_rectangle_modification(self, labeled_rect):
        """Enable modification mode for the selected rectangle (resize)"""
        # Store the rectangle being modified
        self.modifying_rect = labeled_rect
        self.modification_mode = True

        # Change cursor to indicate modification mode
        self.setCursor(Qt.CursorShape.SizeFDiagCursor)

        # Store original pen to restore later
        if not hasattr(labeled_rect, 'original_pen'):
            labeled_rect.original_pen = labeled_rect.pen()

        # Highlight the rectangle being modified with a different color
        highlight_pen = QPen(QColor(0, 255, 255), 2)  # Cyan highlight for modify mode
        labeled_rect.setPen(highlight_pen)

        # Store the original rectangle dimensions and position
        self.original_rect = labeled_rect.rect()
        self.original_scene_rect = labeled_rect.sceneBoundingRect()
        
        # Store the initial mouse position
        mouse_pos = self.mapToScene(self.mapFromGlobal(QCursor.pos()))
        self.initial_mouse_pos = mouse_pos
        
        # Determine which corner/edge is closest to the mouse for resizing
        rect_scene = labeled_rect.sceneBoundingRect()
        self.resize_handle = self.get_resize_handle(mouse_pos, rect_scene)

    def get_resize_handle(self, mouse_pos, rect_scene):
        """Determine which resize handle (corner/edge) is closest to the mouse"""
        # Define resize handles (corners and edges)
        handles = {
            'top_left': rect_scene.topLeft(),
            'top_right': rect_scene.topRight(),
            'bottom_left': rect_scene.bottomLeft(),
            'bottom_right': rect_scene.bottomRight(),
            'top': QPointF(rect_scene.center().x(), rect_scene.top()),
            'bottom': QPointF(rect_scene.center().x(), rect_scene.bottom()),
            'left': QPointF(rect_scene.left(), rect_scene.center().y()),
            'right': QPointF(rect_scene.right(), rect_scene.center().y())
        }
        
        # Find the closest handle
        min_distance = float('inf')
        closest_handle = 'bottom_right'  # Default to bottom-right corner
        
        for handle_name, handle_pos in handles.items():
            distance = QLineF(mouse_pos, handle_pos).length()
            if distance < min_distance:
                min_distance = distance
                closest_handle = handle_name
        
        return closest_handle

    def enable_rectangle_movement(self, labeled_rect):
        """Enable movement mode for the selected rectangle"""
        # Store the rectangle being moved
        self.moving_rect = labeled_rect
        self.movement_mode = True

        # Change cursor to indicate movement mode
        self.setCursor(Qt.CursorShape.SizeAllCursor)

        # Store original pen to restore later
        if not hasattr(labeled_rect, 'original_pen'):
            labeled_rect.original_pen = labeled_rect.pen()

        # Highlight the rectangle being moved
        highlight_pen = QPen(QColor(255, 255, 0), 2)  # Yellow highlight
        labeled_rect.setPen(highlight_pen)
        
        # Store the rectangle's current center in scene coordinates
        # This accounts for any rotation or transformation
        rect_center_local = labeled_rect.rect().center()
        self.rect_center_scene = labeled_rect.mapToScene(rect_center_local)
        
        # Store current mouse position
        current_mouse_pos = self.mapToScene(self.mapFromGlobal(QCursor.pos()))
        self.mouse_offset = QPointF(
            current_mouse_pos.x() - self.rect_center_scene.x(),
            current_mouse_pos.y() - self.rect_center_scene.y()
        )

    def enable_rectangle_rotation(self, labeled_rect):
        """Enable rotation mode for the selected rectangle"""
        # Store the rectangle being rotated
        self.rotating_rect = labeled_rect
        self.rotation_mode = True

        # Change cursor to indicate rotation mode
        self.setCursor(Qt.CursorShape.CrossCursor)

        # Store original pen to restore later
        if not hasattr(labeled_rect, 'original_pen'):
            labeled_rect.original_pen = labeled_rect.pen()

        # Highlight the rectangle being rotated
        highlight_pen = QPen(QColor(255, 255, 0), 2)  # Yellow highlight
        labeled_rect.setPen(highlight_pen)

        # Calculate the center of the rectangle (intersection of diagonals)
        rect = labeled_rect.rect()
        center_local = rect.center()
        
        # Set the transformation origin to the center of the rectangle
        # This is crucial for proper rotation around the center
        labeled_rect.setTransformOriginPoint(center_local)
        
        # Convert center to scene coordinates for mouse angle calculations
        self.rect_center = labeled_rect.mapToScene(center_local)

        # Store the initial angle of the rectangle
        self.initial_angle = labeled_rect.rotation()

        # Store the initial angle between center and mouse
        mouse_pos = self.mapToScene(self.mapFromGlobal(QCursor.pos()))
        line = QLineF(self.rect_center, mouse_pos)
        self.initial_mouse_angle = line.angle()

    def delete_rectangle(self, labeled_rect):
        """Delete the selected rectangle"""
        if labeled_rect in self.labeled_rectangles:
            self.labeled_rectangles.remove(labeled_rect)
        self.scene.removeItem(labeled_rect)

    def finish_modification(self):
        """Finish the modification operation"""
        if self.modifying_rect:
            # Restore original pen
            if hasattr(self.modifying_rect, 'original_pen'):
                self.modifying_rect.setPen(self.modifying_rect.original_pen)
            
            # Clear modification state
            self.modifying_rect = None
            self.modification_mode = False
            self.resize_handle = None
            
            # Restore normal cursor
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def save_rectangle_to_jpeg(self, labeled_rect):
        """Save the selected rectangle portion of the image to a JPEG file"""
        # Get the bounding rectangle
        rect = labeled_rect.rect()
        
        # Convert scene coordinates to pixmap coordinates
        scene_rect = QRectF(rect)
        
        # Create a QImage with the exact size of the rectangle
        image = QImage(int(rect.width()), int(rect.height()), QImage.Format.Format_RGB888)
        image.fill(Qt.GlobalColor.white)  # Set background color
        
        # Create a painter for the image
        painter = QPainter(image)
        
        # Set up the rendering to extract just the portion we want
        source_rect = scene_rect
        target_rect = QRectF(0, 0, rect.width(), rect.height())
        
        # Render only the portion of the scene we want
        self.scene.render(painter, target_rect, source_rect)
        painter.end()
        
        # Check rectangle mode type for different saving behavior
        if hasattr(self, 'rectangle_mode_type'):
            if self.rectangle_mode_type == "classification":
                # Classification mode - use label for folder structure
                save_dir = os.path.join(os.getcwd(), 'save', labeled_rect.label)
                if not os.path.exists(save_dir):
                    os.makedirs(save_dir)
                
                # Generate a unique file name with label
                file_name = f"{labeled_rect.label}_{int(rect.x())}_{int(rect.y())}.jpeg"
                file_path = os.path.join(save_dir, file_name)
                
                # Store the label for reuse
                if hasattr(self, 'recent_labels'):
                    if labeled_rect.label not in self.recent_labels:
                        self.recent_labels.append(labeled_rect.label)
                else:
                    self.recent_labels = [labeled_rect.label]
                    
            elif self.rectangle_mode_type == "yolo":
                # YOLO mode - save in general yolo folder without label
                save_dir = os.path.join(os.getcwd(), 'save', 'yolo')
                if not os.path.exists(save_dir):
                    os.makedirs(save_dir)
                
                # Generate a unique file name without label
                file_name = f"yolo_{int(rect.x())}_{int(rect.y())}.jpeg"
                file_path = os.path.join(save_dir, file_name)
        else:
            # Fallback to original behavior
            save_dir = os.path.join(os.getcwd(), 'save', 'default')
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            file_name = f"rect_{int(rect.x())}_{int(rect.y())}.jpeg"
            file_path = os.path.join(save_dir, file_name)
        
        # Save the image as JPEG
        if image.save(file_path, "JPEG"):
            print(f"Image saved successfully at {file_path}")
        else:
            print("Failed to save the image.")

    def save_entire_image_with_rectangles(self):
        """Save the entire image with rectangles drawn on it."""
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

        # Draw all rectangles with their custom colors and thickness
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

        if hasattr(self, 'polygon_items'):
            for polygon_item in self.polygon_items:
                polygon = polygon_item.polygon()
                pen = polygon_item.pen()
                painter.setPen(pen)  # Use the polygon's custom pen
                painter.drawPolygon(polygon)

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

    def toggle_rectangle_mode(self, enabled):
        """Toggle rectangle selection mode on/off and clear any active selection"""
        self.rectangle_mode = enabled
        
        # Clear any active rectangle selection when toggling the mode
        if self.current_rect:
            self.scene.removeItem(self.current_rect)
            self.current_rect = None
        
        # Reset the starting point
        self.rect_start = None
        
    def clear_rectangles(self):
        """Remove all rectangle selections from the scene"""
        # Clear rectangle_items if it exists
        if hasattr(self, 'rectangle_items') and self.rectangle_items:
            for item in self.rectangle_items:
                if item in self.scene.items():
                    self.scene.removeItem(item)
            self.rectangle_items = []
        
        # Clear labeled_rectangles
        if hasattr(self, 'labeled_rectangles') and self.labeled_rectangles:
            for item in self.labeled_rectangles:
                if item in self.scene.items():
                    self.scene.removeItem(item)
            self.labeled_rectangles = []
        
        # Clear any temporary rectangle being drawn
        if hasattr(self, 'current_rect') and self.current_rect:
            if self.current_rect in self.scene.items():
                self.scene.removeItem(self.current_rect)
            self.current_rect = None
        
        # Update the scene to reflect the changes
        self.scene.update()