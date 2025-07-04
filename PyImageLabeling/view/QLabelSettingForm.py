from PyQt6.QtWidgets import QComboBox, QPushButton, QHBoxLayout, QColorDialog, QDialog, QSlider, QFormLayout, QDialogButtonBox, QSpinBox

from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt

class QLabelSettingForm(QDialog):

    def __init__(self, parent, builder, name="", color=QColor(246, 97, 81)):
        print("HERE")
        super().__init__(parent)
        self.builder = builder
        self.name = name
        self.color = color

        self.setWindowTitle("Label Setting")
        
        layout = QFormLayout()
        
        label_layout = QHBoxLayout()
        
        self.label_combo = QComboBox()
        self.label_combo.setEditable(True)
        self.label_combo.setPlaceholderText("Enter new label or select existing")
        
        # Populate combo box with saved labels
        self.label_combo.addItem("")  # Empty option for new labels
        #for label in self.label_manager.get_all_labels():
        #    self.label_combo.addItem(label)
            
        # Set current label if provided
        #if self.label:
        #    index = self.label_combo.findText(self.label)
        #    if index >= 0:
        #        self.label_combo.setCurrentIndex(index)
        #    else:
        #        self.label_combo.setCurrentText(self.label)
        
        self.label_combo.currentTextChanged.connect(self.name_update)
        label_layout.addWidget(self.label_combo)
        
        layout.addRow("Label:", label_layout)

        # Color selection
        self.color_button = QPushButton("Choose Color")
        self.color_button.clicked.connect(self.select_color)
        self.update_color(self.color)  
        layout.addRow("Color:", self.color_button)
        
        
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        #self.buttons.accepted.connect(self.accept)
        self.buttons.accepted.connect(self.ok_event) 
        self.buttons.rejected.connect(self.reject)
        layout.addRow(self.buttons)
        
        self.setLayout(layout)

    def name_update(self, text):
        self.name = text
        return 
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
    
    
    def ok_event(self):
        self.accept()
        self.builder.build_new_layer_layer_bar(self.name, self.color)



    def update_color(self, color):
        """Update color button appearance to show current color"""
        self.color = color

        color_style = f"background-color: rgb({self.color.red()}, {self.color.green()}, {self.color.blue()}); color: {'white' if self.color.lightness() < 128 else 'black'};"
        self.color_button.setStyleSheet(color_style)
        self.color_button.setText(f"Color: {self.color.name()}")
        
    def select_color(self):
        color = QColorDialog.getColor(initial=self.color)
        if color.isValid(): self.update_color(color)

    #def get_settings(self):
    #    self.radius = self.radius_slider.value()
    #    self.label = self.label_combo.currentText().strip()
        
        # Save label settings if label is not empty - NEW FUNCTIONALITY
    #    if self.label:
    #        self.label_manager.add_label_property(self.label, self.color, self.radius, self.opacity)
        
    #    return self.color, self.radius, self.opacity, self.label
    
    # Not here => in the model part
    # def add_overlay(self, overlay_pixmap):
    #     """Add an overlay pixmap that stays aligned with the base image"""
    #     if not self.base_pixmap:
    #         return False
            
    #     # Remove existing overlay if any
    #     self.remove_overlay()
        
    #     # Ensure overlay matches base image dimensions
    #     base_size = self.base_pixmap.size()
    #     if overlay_pixmap.size() != base_size:
    #         overlay_pixmap = overlay_pixmap.scaled(
    #             base_size, 
    #             Qt.AspectRatioMode.IgnoreAspectRatio,
    #             Qt.TransformationMode.SmoothTransformation
    #         )
        
    #     # Create overlay pixmap item
    #     self.overlay_pixmap_item = self.scene.addPixmap(overlay_pixmap)
    #     self.overlay_pixmap_item.setZValue(1)  # Above base image
    #     self.overlay_pixmap_item.setPos(0, 0)  # Same position as base image
        
    #     # Set opacity (default 50%)
    #     if not hasattr(self, 'overlay_opacity'):
    #         self.overlay_opacity = 128
    #     self.overlay_pixmap_item.setOpacity(self.overlay_opacity / 255.0)
        
    #     # Update scene
    #     self.scene.update()
    #     return True
    
    # def set_overlay_opacity(self, opacity):
    #     """Set opacity of the overlay layer (0-255)"""
    #     if self.overlay_pixmap_item:
    #         self.overlay_opacity = max(0, min(255, opacity))
    #         self.overlay_pixmap_item.setOpacity(self.overlay_opacity / 255.0)
    #         self.scene.update()
    #         return True
    #     return False
    
    # def toggle_overlay_visibility(self):
    #     """Toggle visibility of the overlay"""
    #     if self.overlay_pixmap_item:
    #         is_visible = self.overlay_pixmap_item.isVisible()
    #         self.overlay_pixmap_item.setVisible(not is_visible)
    #         self.scene.update()
    #         return not is_visible
    #     return False
    
    # def remove_overlay(self):
    #     """Remove overlay if exists"""
    #     if self.overlay_pixmap_item:
    #         self.scene.removeItem(self.overlay_pixmap_item)
    #         self.overlay_pixmap_item = None
    #         self.scene.update()
    #         return True
    #     return False