from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSlider,
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

        # Load original image from the image_item
        self.original_pixmap = image_item.image_pixmap.copy()

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
        self.brightness_slider.valueChanged.connect(self.on_brightness_changed)
        self.brightness_label = QLabel("0")
        form_layout.addRow("Brightness:", self.brightness_slider)
        form_layout.addRow("Brightness Value:", self.brightness_label)

        # Contrast
        self.contrast_slider = QSlider(Qt.Orientation.Horizontal)
        self.contrast_slider.setMinimum(0)
        self.contrast_slider.setMaximum(200)
        self.contrast_slider.setValue(100)
        self.contrast_slider.valueChanged.connect(self.on_contrast_changed)
        self.contrast_label = QLabel("1.0")
        form_layout.addRow("Contrast:", self.contrast_slider)
        form_layout.addRow("Contrast Value:", self.contrast_label)

        # Color Replacement
        self.color_replace_checkbox = QCheckBox("Enable color replacement")
        self.color_replace_checkbox.stateChanged.connect(self.on_color_replace_enabled)
        form_layout.addRow("Color Replacement:", self.color_replace_checkbox)

        self.source_color_btn = QPushButton("Select Source Color")
        self.source_color_btn.clicked.connect(self.select_source_color)
        self.source_color_btn.setEnabled(False)
        self.target_color_btn = QPushButton("Select Target Color")
        self.target_color_btn.clicked.connect(self.select_target_color)
        self.target_color_btn.setEnabled(False)

        color_button_layout = QHBoxLayout()
        color_button_layout.addWidget(self.source_color_btn)
        color_button_layout.addWidget(self.target_color_btn)
        form_layout.addRow("Colors:", color_button_layout)

        self.tolerance_slider = QSlider(Qt.Orientation.Horizontal)
        self.tolerance_slider.setMinimum(0)
        self.tolerance_slider.setMaximum(100)
        self.tolerance_slider.setValue(30)
        self.tolerance_slider.valueChanged.connect(self.on_tolerance_changed)
        self.tolerance_slider.setEnabled(False)
        self.tolerance_label = QLabel("30")
        form_layout.addRow("Tolerance:", self.tolerance_slider)
        form_layout.addRow("Tolerance Value:", self.tolerance_label)

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
        self.brightness_label.setText(str(value))
        self.update_preview()

    def on_contrast_changed(self, value):
        self.contrast = value / 100.0
        self.contrast_label.setText(f"{self.contrast:.2f}")
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
        self.tolerance_label.setText(str(value))
        self.update_preview()

    def select_source_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.source_color = (color.blue(), color.green(), color.red())
            self.source_color_btn.setStyleSheet(f"background-color: {color.name()};")
            self.update_preview()

    def select_target_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.target_color = (color.blue(), color.green(), color.red())
            self.target_color_btn.setStyleSheet(f"background-color: {color.name()};")
            self.update_preview()

    def update_preview(self):
        image = self.original_image.copy()
        image = cv2.convertScaleAbs(image, alpha=self.contrast, beta=self.brightness)
        if self.invert_colors:
            image = cv2.bitwise_not(image)
        if self.color_replace_enabled and self.source_color and self.target_color:
            image = self.replace_color(image, self.source_color, self.target_color, self.color_tolerance)
        self.modified_image = image

    def replace_color(self, image, source_color, target_color, tolerance):
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        source_hsv = cv2.cvtColor(np.uint8([[source_color]]), cv2.COLOR_BGR2HSV)[0][0]
        lower = np.array([max(0, source_hsv[0] - tolerance//2), 50, 50])
        upper = np.array([min(179, source_hsv[0] + tolerance//2), 255, 255])
        mask = cv2.inRange(hsv, lower, upper)
        result = image.copy()
        result[mask > 0] = target_color
        return result

    def reset_image(self):
        """Reset all settings and restore the original image immediately."""
        # Reset UI controls
        self.invert_checkbox.setChecked(False)
        self.brightness_slider.setValue(0)
        self.contrast_slider.setValue(100)
        self.color_replace_checkbox.setChecked(False)
        self.source_color = None
        self.target_color = None
        self.source_color_btn.setStyleSheet("")
        self.target_color_btn.setStyleSheet("")
        self.tolerance_slider.setValue(30)

        # Reset internal state
        self.invert_colors = False
        self.brightness = 0
        self.contrast = 1.0
        self.color_replace_enabled = False
        self.color_tolerance = 30
        self.modified_image = self.original_image.copy()

        # Restore the original pixmap to the image_item
        self.image_item.image_pixmap = self.original_pixmap
        self.image_item.image_item.setPixmap(self.original_pixmap)

        # Force scene refresh
        self.parent.zoomable_graphics_view.update()
        self.parent.zoomable_graphics_view.viewport().update()

        self.parent.statusBar().showMessage("Reset to original image")

    def apply_changes(self):
        self.accept()

    def get_modified_pixmap(self):
        rgb_image = cv2.cvtColor(self.modified_image, cv2.COLOR_BGR2RGB)
        height, width, channel = rgb_image.shape
        bytes_per_line = 3 * width
        qimage = QImage(rgb_image.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
        return QPixmap.fromImage(qimage)
