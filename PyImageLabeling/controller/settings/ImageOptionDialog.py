from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSlider, QListWidget,
    QGroupBox, QColorDialog, QCheckBox, QFormLayout, QDialogButtonBox, QSpinBox, QComboBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QImage, QColor
import cv2
import numpy as np

class ImageOptionDialog(QDialog):
    def __init__(self, parent, image_item):
        super().__init__(parent)
        self.parent = parent
        self.image_item = image_item
        self.is_valid = False

        if image_item is None or not hasattr(image_item, 'path_image'):
            self.reject()
            return

        self.is_valid = True
        self.original_path = image_item.path_image
        self.original_pixmap = QPixmap(self.original_path)
        qimage = self.original_pixmap.toImage()
        qimage = qimage.convertToFormat(QImage.Format.Format_RGB888)
        width = qimage.width()
        height = qimage.height()
        ptr = qimage.bits()
        ptr.setsize(qimage.sizeInBytes())
        arr = np.frombuffer(ptr, dtype=np.uint8).reshape((height, width, 3))
        self.original_image = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        self.modified_image = self.original_image.copy()

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
        self.resize(500, 500)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Invert Colors Group
        invert_group = QGroupBox("Invert Colors")
        invert_layout = QVBoxLayout()
        self.invert_checkbox = QCheckBox("Invert image colors")
        self.invert_checkbox.stateChanged.connect(self.on_invert_changed)
        invert_layout.addWidget(self.invert_checkbox)
        invert_group.setLayout(invert_layout)
        layout.addWidget(invert_group)

        # Brightness Group
        brightness_group = QGroupBox("Brightness")
        brightness_layout = QVBoxLayout()
        brightness_label = QLabel("Adjust image brightness:")
        brightness_layout.addWidget(brightness_label)

        brightness_slider_layout = QHBoxLayout()
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

        brightness_slider_layout.addWidget(self.brightness_slider)
        brightness_slider_layout.addWidget(self.brightness_spinbox)
        brightness_layout.addLayout(brightness_slider_layout)
        brightness_group.setLayout(brightness_layout)
        layout.addWidget(brightness_group)

        # Contrast Group
        contrast_group = QGroupBox("Contrast")
        contrast_layout = QVBoxLayout()
        contrast_label = QLabel("Adjust image contrast:")
        contrast_layout.addWidget(contrast_label)

        contrast_slider_layout = QHBoxLayout()
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

        contrast_slider_layout.addWidget(self.contrast_slider)
        contrast_slider_layout.addWidget(self.contrast_spinbox)
        contrast_layout.addLayout(contrast_slider_layout)
        contrast_group.setLayout(contrast_layout)
        layout.addWidget(contrast_group)

        # Color Replacement Group
        color_group = QGroupBox("Color Replacement")
        color_layout = QVBoxLayout()
        self.color_replace_checkbox = QCheckBox("Enable color replacement")
        self.color_replace_checkbox.stateChanged.connect(self.on_color_replace_enabled)
        color_layout.addWidget(self.color_replace_checkbox)

        color_buttons_layout = QHBoxLayout()
        self.source_color_btn = QPushButton("Select Source Color")
        self.source_color_btn.clicked.connect(self.select_source_color)
        self.source_color_btn.setEnabled(False)
        color_buttons_layout.addWidget(self.source_color_btn)

        self.target_color_btn = QPushButton("Select Target Color")
        self.target_color_btn.clicked.connect(self.select_target_color)
        self.target_color_btn.setEnabled(False)
        color_buttons_layout.addWidget(self.target_color_btn)
        color_layout.addLayout(color_buttons_layout)

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
        color_layout.addLayout(tolerance_layout)

        self.apply_color_btn = QPushButton("Add Color Replacement")
        self.apply_color_btn.clicked.connect(self.apply_color_replacement)
        self.apply_color_btn.setEnabled(False)
        color_layout.addWidget(self.apply_color_btn)

        self.color_replacements_list = QListWidget()
        self.color_replacements_list.setMaximumHeight(100)
        color_layout.addWidget(self.color_replacements_list)

        clear_colors_btn = QPushButton("Clear All Replacements")
        clear_colors_btn.clicked.connect(self.clear_color_replacements)
        color_layout.addWidget(clear_colors_btn)

        color_group.setLayout(color_layout)
        layout.addWidget(color_group)

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
        self.apply_color_btn.setEnabled(enabled)

    def on_tolerance_changed(self, value):
        self.color_tolerance = value
        self.update_preview()

    def apply_color_replacement(self):
        if self.source_color and self.target_color:
            self.color_replacements.append({
                'source': self.source_color,
                'target': self.target_color,
                'tolerance': self.color_tolerance
            })

            source_qcolor = QColor(self.source_color[2], self.source_color[1], self.source_color[0])
            target_qcolor = QColor(self.target_color[2], self.target_color[1], self.target_color[0])
            list_text = f"{source_qcolor.name()} → {target_qcolor.name()} (tol: {self.color_tolerance})"
            self.color_replacements_list.addItem(list_text)

            self.source_color = None
            self.target_color = None
            self.source_color_btn.setStyleSheet("")
            self.target_color_btn.setStyleSheet("")
            self.apply_color_btn.setEnabled(False)

            self.update_preview()
            self.parent.statusBar().showMessage(f"Color replacement added ({len(self.color_replacements)} total)")

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
        if not self.is_valid:
            return

        image = self.original_image.copy()
        image = cv2.convertScaleAbs(image, alpha=self.contrast, beta=self.brightness)

        if self.invert_colors:
            image = cv2.bitwise_not(image)

        for replacement in self.color_replacements:
            image = self.replace_color(image, replacement['source'], replacement['target'], replacement['tolerance'])

        if self.color_replace_enabled and self.source_color and self.target_color:
            image = self.replace_color(image, self.source_color, self.target_color, self.color_tolerance)

        self.modified_image = image
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
        if not self.is_valid:
            return

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

        self.original_pixmap = QPixmap(self.original_path)
        self.image_item.image_pixmap = self.original_pixmap.copy()
        self.image_item.image_item.setPixmap(self.original_pixmap)
        self.image_item.image_numpy_pixels_rgb = None

        qimage = self.original_pixmap.toImage()
        qimage = qimage.convertToFormat(QImage.Format.Format_RGB888)
        width = qimage.width()
        height = qimage.height()
        ptr = qimage.bits()
        ptr.setsize(qimage.sizeInBytes())
        arr = np.frombuffer(ptr, dtype=np.uint8).reshape((height, width, 3))
        self.original_image = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        self.modified_image = self.original_image.copy()

        self.parent.zoomable_graphics_view.scene.update()
        self.parent.zoomable_graphics_view.viewport().update()
        self.parent.statusBar().showMessage("Reset to original image")

    def apply_changes(self):
        self.accept()

    def reject(self):
        if not self.is_valid:
            super().reject()
            return

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
