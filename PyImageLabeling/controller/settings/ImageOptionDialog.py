from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSlider, QListWidget,
    QGroupBox, QColorDialog, QCheckBox, QFormLayout, QDialogButtonBox, QSpinBox, QComboBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QImage
import cv2
import numpy as np

class ImageOptionDialog(QDialog):
    def __init__(self, parent, image_item):
        super().__init__(parent)
        self.parent = parent
        self.image_item = image_item
        self.original_path = image_item.path_image

        # Load original image from the image_item
        self.original_pixmap = QPixmap(self.original_path)

        # Convert pixmap to cv2 format
        qimage = self.original_pixmap.toImage()
        qimage = qimage.convertToFormat(QImage.Format.Format_RGB888)
        width = qimage.width()
        height = qimage.height()
        ptr = qimage.bits()
        ptr.setsize(qimage.sizeInBytes())
        arr = np.frombuffer(ptr, dtype=np.uint8).reshape((height, width, 3))
        self.original_image = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

        self.modified_image = self.original_image.copy()

        # Settings
        self.invert_colors = False
        self.brightness = 0
        self.contrast = 1.0
        self.color_replace_enabled = False
        self.source_color = None
        self.target_color = None
        self.color_tolerance = 30
        self.color_replacements = [] 

        self.setWindowTitle("Image Options")
        self.setModal(True)
        self.resize(500, 300)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # Invert Colors
        self.invert_checkbox = QCheckBox("Invert image colors")
        self.invert_checkbox.stateChanged.connect(self.on_invert_changed)
        form_layout.addRow("Invert Colors:", self.invert_checkbox)

        # Brightness
        self.brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self.brightness_slider.setMinimum(-100)
        self.brightness_slider.setMaximum(100)
        self.brightness_slider.setValue(0)
        self.brightness_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.brightness_slider.setTickInterval(25)
        self.brightness_slider.valueChanged.connect(self.on_brightness_changed)

        self.brightness_spinbox = QSpinBox()
        self.brightness_spinbox.setRange(-100, 100)
        self.brightness_spinbox.setValue(0)
        self.brightness_spinbox.valueChanged.connect(self.brightness_slider.setValue)
        self.brightness_slider.valueChanged.connect(self.brightness_spinbox.setValue)

        form_layout.addRow("Brightness:", self.brightness_slider)
        form_layout.addRow("Brightness Value:", self.brightness_spinbox)

        # Contrast
        self.contrast_slider = QSlider(Qt.Orientation.Horizontal)
        self.contrast_slider.setMinimum(0)
        self.contrast_slider.setMaximum(200)
        self.contrast_slider.setValue(100)
        self.contrast_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.contrast_slider.setTickInterval(25)
        self.contrast_slider.valueChanged.connect(self.on_contrast_changed)

        self.contrast_spinbox = QSpinBox()
        self.contrast_spinbox.setRange(0, 200)
        self.contrast_spinbox.setValue(100)
        self.contrast_spinbox.valueChanged.connect(self.contrast_slider.setValue)
        self.contrast_slider.valueChanged.connect(self.contrast_spinbox.setValue)

        form_layout.addRow("Contrast:", self.contrast_slider)
        form_layout.addRow("Contrast Value:", self.contrast_spinbox)

        # Color Replacement
        self.color_replace_checkbox = QCheckBox("Enable color replacement")
        self.color_replace_checkbox.stateChanged.connect(self.on_color_replace_enabled)
        form_layout.addRow("Color Replacement:", self.color_replace_checkbox)

        color_buttons_layout = QHBoxLayout()
        self.source_color_btn = QPushButton("Select Source Color")
        self.source_color_btn.clicked.connect(self.select_source_color)
        self.source_color_btn.setEnabled(False)
        color_buttons_layout.addWidget(self.source_color_btn)

        self.target_color_btn = QPushButton("Select Target Color")
        self.target_color_btn.clicked.connect(self.select_target_color)
        self.target_color_btn.setEnabled(False)
        color_buttons_layout.addWidget(self.target_color_btn)

        form_layout.addRow("", color_buttons_layout)

        tolerance_layout = QHBoxLayout()
        tolerance_layout.addWidget(QLabel("Tolerance:"))

        self.tolerance_slider = QSlider(Qt.Orientation.Horizontal)
        self.tolerance_slider.setMinimum(0)
        self.tolerance_slider.setMaximum(100)
        self.tolerance_slider.setValue(30)
        self.tolerance_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.tolerance_slider.setTickInterval(10)
        self.tolerance_slider.valueChanged.connect(self.on_tolerance_changed)
        self.tolerance_slider.setEnabled(False)

        self.tolerance_spinbox = QSpinBox()
        self.tolerance_spinbox.setRange(0, 100)
        self.tolerance_spinbox.setValue(30)
        self.tolerance_spinbox.valueChanged.connect(self.tolerance_slider.setValue)
        self.tolerance_slider.valueChanged.connect(self.tolerance_spinbox.setValue)

        tolerance_layout.addWidget(self.tolerance_slider)
        tolerance_layout.addWidget(self.tolerance_spinbox)

        form_layout.addRow("", tolerance_layout)

        # Add button to apply current color replacement
        self.apply_color_btn = QPushButton("Add Color Replacement")
        self.apply_color_btn.clicked.connect(self.apply_color_replacement)
        self.apply_color_btn.setEnabled(False)
        form_layout.addRow("", self.apply_color_btn)
        
        # List of applied color replacements
        self.color_replacements_list = QListWidget()
        self.color_replacements_list.setMaximumHeight(100)
        form_layout.addRow("", self.color_replacements_list)

        # Clear all replacements button
        clear_colors_btn = QPushButton("Clear All Replacements")
        clear_colors_btn.clicked.connect(self.clear_color_replacements)
        form_layout.addRow("", clear_colors_btn)

        layout.addLayout(form_layout)

        # Buttons
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.Reset
        )
        self.buttons.accepted.connect(self.apply_changes)
        self.buttons.rejected.connect(self.reject)
        self.buttons.button(QDialogButtonBox.StandardButton.Reset).clicked.connect(self.reset_image)
        layout.addWidget(self.buttons)

        self.setLayout(layout)

    def on_invert_changed(self, state):
        self.invert_colors = state == Qt.CheckState.Checked.value
        self.update_preview()

    def on_brightness_changed(self, value):
        self.brightness = value
        self.update_preview()

    def on_contrast_changed(self, value):
        self.contrast = value / 100.0
        self.update_preview()

    def on_color_replace_enabled(self, state):
        enabled = state == Qt.CheckState.Checked.value
        self.color_replace_enabled = enabled
        self.source_color_btn.setEnabled(enabled)
        self.target_color_btn.setEnabled(enabled)
        self.tolerance_slider.setEnabled(enabled)
        if not enabled:
            self.source_color = None
            self.target_color = None
        self.update_preview()

    def on_tolerance_changed(self, value):
        self.color_tolerance = value
        self.update_preview()

    def apply_color_replacement(self):
        if self.source_color and self.target_color:
            # Store the replacement
            self.color_replacements.append({
                'source': self.source_color,
                'target': self.target_color,
                'tolerance': self.color_tolerance
            })
            
            # Add to list widget for display
            from PyQt6.QtGui import QColor
            source_qcolor = QColor(self.source_color[2], self.source_color[1], self.source_color[0])
            target_qcolor = QColor(self.target_color[2], self.target_color[1], self.target_color[0])
            list_text = f"{source_qcolor.name()} → {target_qcolor.name()} (tol: {self.color_tolerance})"
            self.color_replacements_list.addItem(list_text)
            
            # Reset current selection
            self.source_color = None
            self.target_color = None
            self.source_color_btn.setStyleSheet("")
            self.target_color_btn.setStyleSheet("")
            self.apply_color_btn.setEnabled(False)
            
            # Update preview with new replacement applied
            self.update_preview()
            self.parent.statusBar().showMessage(f"Color replacement added ({len(self.color_replacements)} total)")
            
    def on_color_replace_enabled(self, state):
        enabled = state == Qt.CheckState.Checked.value
        self.color_replace_enabled = enabled
        self.source_color_btn.setEnabled(enabled)
        self.target_color_btn.setEnabled(enabled)
        self.tolerance_slider.setEnabled(enabled)
        self.apply_color_btn.setEnabled(enabled)

    def select_source_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.source_color = (color.blue(), color.green(), color.red())
            self.source_color_btn.setStyleSheet(f"background-color: {color.name()};")
            if self.target_color:
                self.apply_color_btn.setEnabled(True)
                
    def select_target_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.target_color = (color.blue(), color.green(), color.red())
            self.target_color_btn.setStyleSheet(f"background-color: {color.name()};")
            if self.source_color:
                self.apply_color_btn.setEnabled(True)

    def update_preview(self):
        # Start with original image
        image = self.original_image.copy()
        
        # Apply brightness and contrast
        image = cv2.convertScaleAbs(image, alpha=self.contrast, beta=self.brightness)
        
        # Apply color inversion
        if self.invert_colors:
            image = cv2.bitwise_not(image)
        
        # Apply all stored color replacements
        for replacement in self.color_replacements:
            image = self.replace_color(image, replacement['source'], replacement['target'], replacement['tolerance'])
        
        # Apply current color replacement preview (if both colors selected)
        if self.color_replace_enabled and self.source_color and self.target_color:
            image = self.replace_color(image, self.source_color, self.target_color, self.color_tolerance)
        
        self.modified_image = image
        
        # Update the display in real-time
        preview_pixmap = self.get_modified_pixmap()
        self.image_item.image_item.setPixmap(preview_pixmap)
        self.parent.zoomable_graphics_view.scene.update()
        self.parent.zoomable_graphics_view.viewport().update()

    def clear_color_replacements(self):
        self.color_replacements = []
        self.color_replacements_list.clear()
        self.update_preview()
        self.parent.statusBar().showMessage("All color replacements cleared")

    def replace_color(self, image, source_color, target_color, tolerance):
        result = image.copy()
        lower = np.array([max(0, source_color[i] - tolerance) for i in range(3)], dtype=np.uint8)
        upper = np.array([min(255, source_color[i] + tolerance) for i in range(3)], dtype=np.uint8)
        mask = cv2.inRange(result, lower, upper)
        result[mask > 0] = target_color
        
        return result

    def reset_image(self):
        """Reset to original image"""
        # Reset all sliders and checkboxes
        self.invert_checkbox.setChecked(False)
        self.brightness_slider.setValue(0)
        self.contrast_slider.setValue(100)
        self.color_replace_checkbox.setChecked(False)
        self.source_color = None
        self.target_color = None
        self.source_color_btn.setStyleSheet("")
        self.target_color_btn.setStyleSheet("")
        self.tolerance_slider.setValue(30)
        self.color_replacements = []
        self.color_replacements_list.clear()
        
        # Reload original image from file
        self.original_pixmap = QPixmap(self.original_path)
        
        # Immediately update the displayed image to original
        self.image_item.image_pixmap = self.original_pixmap.copy()
        self.image_item.image_item.setPixmap(self.original_pixmap)
        self.image_item.image_numpy_pixels_rgb = None
        
        # Reload cv2 image
        qimage = self.original_pixmap.toImage()
        qimage = qimage.convertToFormat(QImage.Format.Format_RGB888)
        width = qimage.width()
        height = qimage.height()
        ptr = qimage.bits()
        ptr.setsize(qimage.sizeInBytes())
        arr = np.frombuffer(ptr, dtype=np.uint8).reshape((height, width, 3))
        self.original_image = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        self.modified_image = self.original_image.copy()
        
        # Force scene refresh
        self.parent.zoomable_graphics_view.scene.update()
        self.parent.zoomable_graphics_view.viewport().update()
        
        self.parent.statusBar().showMessage("Reset to original image")

    def apply_changes(self):
        self.accept()

    def reject(self):
        # Restore original image when canceling
        self.image_item.image_pixmap = self.original_pixmap.copy()
        self.image_item.image_item.setPixmap(self.original_pixmap)
        self.image_item.image_numpy_pixels_rgb = None
        self.parent.zoomable_graphics_view.scene.update()
        self.parent.zoomable_graphics_view.viewport().update()
        super().reject()

    def get_modified_pixmap(self):
        rgb_image = cv2.cvtColor(self.modified_image, cv2.COLOR_BGR2RGB)
        height, width, channel = rgb_image.shape
        bytes_per_line = 3 * width
        qimage = QImage(rgb_image.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
        return QPixmap.fromImage(qimage)
