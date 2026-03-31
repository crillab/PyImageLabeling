from PyQt6.QtWidgets import QCheckBox, QColorDialog, QDialog, QSlider, QPushButton, QFormLayout, QDialogButtonBox, QSpinBox, QLabel, QHBoxLayout, QVBoxLayout, QComboBox, QGroupBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPen, QPainterPath, QPixmap
from PyImageLabeling.model.Utils import Utils
import numpy as np


class DynamicEraserDialog(QDialog):
    def __init__(self, parent, img_arr, shape_mask, keep_rgba, initial_tolerance, original_pixmap):
        super().__init__(parent)

        self.img_arr = img_arr
        self.shape_mask = shape_mask
        self.keep_rgba = keep_rgba
        self.original_pixmap = original_pixmap
        self.last_erase_mask = None

        self.setWindowTitle("Adjust Pixels to Keep")
        self.setMinimumWidth(600)

        layout = QVBoxLayout()

        # Preview Label
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(1, 1)
        self.preview_label.setScaledContents(True)
        layout.addWidget(self.preview_label)

        # Tolerance Slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 255)
        self.slider.setValue(initial_tolerance)
        self.slider.valueChanged.connect(self.update_preview)
        layout.addWidget(self.slider)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)
        self.update_preview(initial_tolerance)

    def update_preview(self, tolerance):
        preview_pixmap = self.original_pixmap.copy()

        diff = np.abs(self.img_arr.astype(np.int16) - self.keep_rgba.astype(np.int16))
        match_mask = np.all(diff <= tolerance, axis=2)
        erase_mask = self.shape_mask & (~match_mask)

        self.last_erase_mask = erase_mask

        painter = QPainter(preview_pixmap)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)

        ys, xs = np.where(erase_mask)
        for y_pixel, x_pixel in zip(ys, xs):
            painter.eraseRect(x_pixel, y_pixel, 1, 1)

        painter.end()

        # Scale pixmap to fit label
        self.preview_label.setPixmap(
            preview_pixmap.scaled(
                self.preview_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        )

    def get_final_erase_mask(self):
        return self.last_erase_mask

    def resizeEvent(self, event):
        # Update preview when dialog is resized
        if hasattr(self, 'preview_label') and self.preview_label.pixmap():
            self.preview_label.setPixmap(
                self.preview_label.pixmap().scaled(
                    self.preview_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            )
        super().resizeEvent(event)

    def on_tolerance_changed(self, value):
        self.current_tolerance = value
        self.update_preview(value)
    
    def reset_preview(self):
        """Reset preview cleanly"""

        initial_tolerance = Utils.load_parameters()["eraser"].get("tolerance", 10)
        self.current_tolerance = initial_tolerance

        # Prevent double trigger
        self.tolerance_slider.blockSignals(True)
        self.tolerance_spinbox.blockSignals(True)

        self.tolerance_slider.setValue(initial_tolerance)
        self.tolerance_spinbox.setValue(initial_tolerance)

        self.tolerance_slider.blockSignals(False)
        self.tolerance_spinbox.blockSignals(False)

        self.update_preview(initial_tolerance)

class EraserSetting(QDialog):
    def __init__(self, parent, model):
        super().__init__(parent)
        self.setWindowTitle("Eraser Settings")
        self.resize(500, 150)
        params = Utils.load_parameters()["eraser"]
        self.max_size = int(min(model.get_current_image_item().image_qrectf.width(), model.get_current_image_item().image_qrectf.height()))
        self.min_size = 2
        self.radius = params.get("size", 10)
        self.absolute_mode = params.get("absolute_mode", 0)
        self.eraser_mode = params.get("mode", "original")

        layout = QVBoxLayout()

        # Mode Group
        mode_group = QGroupBox("Eraser Mode")
        mode_layout = QVBoxLayout()
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Original Mode", "Absolute Mode", "Intelligent Mode"])
        mode_map = {"original": 0, "absolute": 1, "intelligent": 2}
        self.mode_combo.setCurrentIndex(mode_map.get(self.eraser_mode, 0))
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        mode_layout.addWidget(self.mode_combo)
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        # Radius Group
        self.radius_group = QGroupBox("Radius")
        radius_layout = QVBoxLayout()
        radius_label = QLabel("Set eraser radius:")
        radius_layout.addWidget(radius_label)

        radius_slider_layout = QHBoxLayout()
        initial_radius = self.ensure_even_value(self.radius)

        self.radius_slider = QSlider(Qt.Orientation.Horizontal)
        self.radius_slider.setRange(self.min_size, self.max_size)
        self.radius_slider.setSingleStep(2)
        self.radius_slider.setValue(initial_radius)
        self.radius_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        tick_interval = max(1, self.max_size // 20)
        self.radius_slider.setTickInterval(tick_interval)

        self.radius_spinbox = QSpinBox()
        self.radius_spinbox.setRange(self.min_size, self.max_size)
        self.radius_spinbox.setSingleStep(2)
        self.radius_spinbox.setValue(initial_radius)

        self.radius_spinbox.valueChanged.connect(self.radius_slider.setValue)
        self.radius_slider.valueChanged.connect(self.radius_spinbox.setValue)
        self.radius_slider.valueChanged.connect(self.update_radius)
        self.radius_spinbox.valueChanged.connect(self.update_radius)

        radius_slider_layout.addWidget(self.radius_slider)
        radius_slider_layout.addWidget(self.radius_spinbox)
        radius_layout.addLayout(radius_slider_layout)
        self.radius_group.setLayout(radius_layout)
        layout.addWidget(self.radius_group)

        # Threshold Group
        self.threshold_group = QGroupBox("Color Tolerance")
        threshold_layout = QVBoxLayout()
        threshold_label = QLabel("Set color tolerance (0-255):")
        threshold_layout.addWidget(threshold_label)

        threshold_slider_layout = QHBoxLayout()
        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setRange(0, 255)
        self.threshold_slider.setValue(params.get("tolerance", 10))
        self.threshold_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.threshold_slider.setTickInterval(32)

        self.threshold_spinbox = QSpinBox()
        self.threshold_spinbox.setRange(0, 255)
        self.threshold_spinbox.setValue(params.get("tolerance", 10))

        self.threshold_slider.valueChanged.connect(self.threshold_spinbox.setValue)
        self.threshold_spinbox.valueChanged.connect(self.threshold_slider.setValue)

        threshold_slider_layout.addWidget(self.threshold_slider)
        threshold_slider_layout.addWidget(self.threshold_spinbox)
        threshold_layout.addLayout(threshold_slider_layout)
        self.threshold_group.setLayout(threshold_layout)
        layout.addWidget(self.threshold_group)

        # Color Picker Group
        self.color_group = QGroupBox("Color to Keep")
        color_layout = QVBoxLayout()
        color_label = QLabel("Select the color to keep (click to pick):")
        color_layout.addWidget(color_label)

        self.color_button = QPushButton()
        self.color_button.setStyleSheet("background-color: rgba(0, 0, 0, 0); border: 1px solid black;")
        self.color_button.clicked.connect(self.pick_color)
        color_layout.addWidget(self.color_button)

        self.selected_color = QColor(params.get("keep_color", "#00000000"))
        self.update_color_button()

        color_layout.addWidget(QLabel("Selected color will be kept; others will be erased."))
        self.color_group.setLayout(color_layout)
        layout.addWidget(self.color_group)

        # Dynamic Adjustment Group
        self.dynamic_group = QGroupBox("Dynamic Adjustment")
        dynamic_layout = QVBoxLayout()
        self.dynamic_checkbox = QCheckBox("Enable dynamic pixel adjustment")
        self.dynamic_checkbox.setChecked(params.get("dynamic_adjust", False))
        dynamic_layout.addWidget(self.dynamic_checkbox)
        dynamic_layout.addWidget(QLabel("When enabled, you can interactively adjust which pixels\nto keep after clicking on a shape."))
        self.dynamic_group.setLayout(dynamic_layout)
        layout.addWidget(self.dynamic_group)

        # Buttons
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.setLayout(layout)
        self.on_mode_changed(self.mode_combo.currentIndex())

    def on_mode_changed(self, index):
        """Show/hide controls based on selected mode"""
        mode_names = ["original", "absolute", "intelligent"]
        self.eraser_mode = mode_names[index]

        if self.eraser_mode == "absolute":
            self.absolute_mode = 1
        else:
            self.absolute_mode = 0

        show_controls = index in [0, 1]
        show_intelligent = index == 2
        
        self.radius_group.setVisible(show_controls)
        self.threshold_group.setVisible(show_intelligent)
        self.color_group.setVisible(show_intelligent)
        self.dynamic_group.setVisible(show_intelligent)

        if show_controls:
            self.resize(500, 150)
        else:
            self.resize(500, 350)

    def ensure_even_value(self, value):
        """Ensure the value is even (pair). If odd, round to nearest even."""
        if value % 2 != 0:
            return value + 1
        return value

    def update_radius(self, value):
        """Update internal radius value when slider changes"""
        self.radius = self.ensure_even_value(value)

    def pick_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.selected_color = color
            self.update_color_button()

    def update_color_button(self):
        self.color_button.setStyleSheet(
            f"background-color: {self.selected_color.name()}; "
            "border: 1px solid black; min-height: 30px;"
        )

    def accept(self):
        """Override accept to ensure settings are updated before closing"""
        self.radius = self.radius_spinbox.value()
        data = Utils.load_parameters()
        data["eraser"]["size"] = self.radius
        data["eraser"]["absolute_mode"] = self.absolute_mode
        data["eraser"]["mode"] = self.eraser_mode
        data["eraser"]["tolerance"] = self.threshold_spinbox.value() 
        data["eraser"]["keep_color"] = self.selected_color.name(QColor.NameFormat.HexArgb)
        data["eraser"]["dynamic_adjust"] = self.dynamic_checkbox.isChecked()
        Utils.save_parameters(data)
        return super().accept()