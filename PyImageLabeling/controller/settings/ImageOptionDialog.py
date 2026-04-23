from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSlider, QListWidget,
    QGroupBox, QColorDialog, QCheckBox, QFormLayout, QDialogButtonBox, QFileDialog, QInputDialog, QSpinBox, QComboBox,
    QScrollArea, QWidget
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QPixmap, QImage, QColor, QDesktopServices
import cv2
import numpy as np
import json
import os

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

        self.has_alpha = self.original_pixmap.hasAlpha()
        self.original_image = self._load_cv2_from_file(self.original_path, self.has_alpha)
        self.modified_image = self.original_image.copy()

        self.invert_colors   = False
        self.grayscale       = False
        self.brightness      = 0
        self.contrast        = 1.0
        self.gamma           = 100
        self.r_level         = 0
        self.g_level         = 0
        self.b_level         = 0
        self.hue_shift       = 0
        self.saturation      = 100
        self.value_shift     = 0
        self.sharpness       = 0

        self.color_replace_enabled = False
        self.source_color    = None
        self.target_color    = None
        self.color_tolerance = 30
        self.color_replacements = []

        self.setWindowTitle("Image Options")
        self.setModal(True)
        self.resize(500, 650)
        self.init_ui()

    # ------------------------------------------------------------------
    # Image I/O helpers
    # ------------------------------------------------------------------

    def _load_cv2_from_file(self, path, has_alpha):
        img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if img is None:
            return self._qpixmap_to_cv2_safe(QPixmap(path))
        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        elif img.shape[2] == 4 and not has_alpha:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        return img

    def _qpixmap_to_cv2_safe(self, pixmap):
        has_alpha = pixmap.hasAlpha()
        fmt = QImage.Format.Format_RGBA8888 if has_alpha else QImage.Format.Format_RGB888
        qimage = pixmap.toImage().convertToFormat(fmt)
        channels = 4 if has_alpha else 3
        raw_bytes = bytes(qimage.bits().asarray(qimage.sizeInBytes()))
        arr = np.frombuffer(raw_bytes, dtype=np.uint8).reshape(
            (qimage.height(), qimage.width(), channels))
        return cv2.cvtColor(arr, cv2.COLOR_RGBA2BGRA if has_alpha else cv2.COLOR_RGB2BGR)

    def _cv2_to_pixmap(self, image):
        if image.shape[2] == 4:
            converted = cv2.cvtColor(image, cv2.COLOR_BGRA2RGBA)
            fmt = QImage.Format.Format_RGBA8888
        else:
            converted = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            fmt = QImage.Format.Format_RGB888
        h, w, ch = converted.shape
        qimage = QImage(converted.tobytes(), w, h, ch * w, fmt)
        return QPixmap.fromImage(qimage)

    def _process_bgr_only(self, image, fn):
        if image.shape[2] == 4:
            result = image.copy()
            result[:, :, :3] = fn(image[:, :, :3].copy())
            return result
        return fn(image)
    
    # JSON PRESET 

    def get_current_settings(self):
        return {
            "invert_colors": self.invert_colors,
            "grayscale": self.grayscale,
            "brightness": self.brightness,
            "contrast": self.contrast,
            "gamma": self.gamma,
            "r_level": self.r_level,
            "g_level": self.g_level,
            "b_level": self.b_level,
            "hue_shift": self.hue_shift,
            "saturation": self.saturation,
            "value_shift": self.value_shift,
            "sharpness": self.sharpness,
            "color_replacements": self.color_replacements,
            "color_tolerance": self.color_tolerance
        }

    def save_preset(self, name):
        os.makedirs("presets", exist_ok=True)
        path = os.path.join("presets", f"{name}.json")

        with open(path, "w") as f:
            json.dump(self.get_current_settings(), f, indent=4)

        self.parent.statusBar().showMessage(f"Preset '{name}' saved")

    def load_preset(self, filepath):
        with open(filepath, "r") as f:
            settings = json.load(f)
        self.apply_settings(settings)

    def apply_settings(self, s):
        for w in self._all_widgets():
            w.blockSignals(True)

        self.invert_checkbox.setChecked(s["invert_colors"])
        self.grayscale_checkbox.setChecked(s["grayscale"])
        self.brightness_slider.setValue(s["brightness"])
        self.contrast_slider.setValue(int(s["contrast"] * 100))
        self.gamma_slider.setValue(s["gamma"])
        self.r_slider.setValue(s["r_level"])
        self.g_slider.setValue(s["g_level"])
        self.b_slider.setValue(s["b_level"])
        self.hue_slider.setValue(s["hue_shift"])
        self.sat_slider.setValue(s["saturation"])
        self.val_slider.setValue(s["value_shift"])
        self.sharpness_slider.setValue(s["sharpness"])
        self.tolerance_slider.setValue(s.get("color_tolerance", 30))

        self.color_replacements = s.get("color_replacements", [])
        self.color_replacements_list.clear()

        for rep in self.color_replacements:
            sc = QColor(rep['source'][2], rep['source'][1], rep['source'][0])
            tc = QColor(rep['target'][2], rep['target'][1], rep['target'][0])
            self.color_replacements_list.addItem(
                f"{sc.name()} → {tc.name()} (tol: {rep['tolerance']})"
            )

        for w in self._all_widgets():
            w.blockSignals(False)

        # sync internal values
        self.__dict__.update(s)

        self.update_preview()

    # UI  

    def _slider_row(self, minimum, maximum, default, tick_interval=25):
        """Return (QHBoxLayout, QSlider, QSpinBox) matching original style."""
        row = QHBoxLayout()
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(minimum)
        slider.setMaximum(maximum)
        slider.setValue(default)
        slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        slider.setTickInterval(tick_interval)
        spinbox = QSpinBox()
        spinbox.setRange(minimum, maximum)
        spinbox.setValue(default)
        slider.valueChanged.connect(spinbox.setValue)
        spinbox.valueChanged.connect(slider.setValue)
        row.addWidget(slider)
        row.addWidget(spinbox)
        return row, slider, spinbox

    def init_ui(self):
        # Outer layout holds a scroll area + the button box at the bottom
        outer_layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)   # invisible frame = original feel
        container = QWidget()
        layout = QVBoxLayout(container)
        scroll.setWidget(container)
        outer_layout.addWidget(scroll)

        # Invert Colors 
        invert_group = QGroupBox("Invert Colors")
        invert_layout = QVBoxLayout()
        self.invert_checkbox = QCheckBox("Invert image colors")
        self.invert_checkbox.stateChanged.connect(self.on_invert_changed)
        invert_layout.addWidget(self.invert_checkbox)
        invert_group.setLayout(invert_layout)
        layout.addWidget(invert_group)

        # Grayscale 
        gray_group = QGroupBox("Grayscale")
        gray_layout = QVBoxLayout()
        self.grayscale_checkbox = QCheckBox("Convert to grayscale")
        self.grayscale_checkbox.stateChanged.connect(self.on_grayscale_changed)
        gray_layout.addWidget(self.grayscale_checkbox)
        gray_group.setLayout(gray_layout)
        layout.addWidget(gray_group)

        # Brightness 
        brightness_group = QGroupBox("Brightness")
        brightness_layout = QVBoxLayout()
        brightness_layout.addWidget(QLabel("Adjust image brightness:"))
        row, self.brightness_slider, self.brightness_spinbox = \
            self._slider_row(-100, 100, 0, 25)
        self.brightness_slider.valueChanged.connect(self.on_brightness_changed)
        brightness_layout.addLayout(row)
        brightness_group.setLayout(brightness_layout)
        layout.addWidget(brightness_group)

        # Contrast 
        contrast_group = QGroupBox("Contrast")
        contrast_layout = QVBoxLayout()
        contrast_layout.addWidget(QLabel("Adjust image contrast:"))
        row, self.contrast_slider, self.contrast_spinbox = \
            self._slider_row(0, 200, 100, 25)
        self.contrast_slider.valueChanged.connect(self.on_contrast_changed)
        contrast_layout.addLayout(row)
        contrast_group.setLayout(contrast_layout)
        layout.addWidget(contrast_group)

        # Gamma
        gamma_group = QGroupBox("Gamma")
        gamma_layout = QVBoxLayout()
        gamma_layout.addWidget(QLabel("Adjust gamma curve (100 = neutral):"))
        row, self.gamma_slider, self.gamma_spinbox = \
            self._slider_row(10, 300, 100, 25)
        self.gamma_slider.valueChanged.connect(self.on_gamma_changed)
        gamma_layout.addLayout(row)
        gamma_group.setLayout(gamma_layout)
        layout.addWidget(gamma_group)

        # RGB Channel Levels
        rgb_group = QGroupBox("RGB Channel Levels")
        rgb_layout = QVBoxLayout()
        rgb_layout.addWidget(QLabel("Boost or cut individual colour channels:"))

        rgb_layout.addWidget(QLabel("Red:"))
        row, self.r_slider, self.r_spinbox = self._slider_row(-100, 100, 0, 25)
        self.r_slider.valueChanged.connect(self.on_r_changed)
        rgb_layout.addLayout(row)

        rgb_layout.addWidget(QLabel("Green:"))
        row, self.g_slider, self.g_spinbox = self._slider_row(-100, 100, 0, 25)
        self.g_slider.valueChanged.connect(self.on_g_changed)
        rgb_layout.addLayout(row)

        rgb_layout.addWidget(QLabel("Blue:"))
        row, self.b_slider, self.b_spinbox = self._slider_row(-100, 100, 0, 25)
        self.b_slider.valueChanged.connect(self.on_b_changed)
        rgb_layout.addLayout(row)

        rgb_group.setLayout(rgb_layout)
        layout.addWidget(rgb_group)

        # Hue / Saturation / Value 
        hsv_group = QGroupBox("Hue / Saturation / Value")
        hsv_layout = QVBoxLayout()

        hsv_layout.addWidget(QLabel("Hue shift (degrees):"))
        row, self.hue_slider, self.hue_spinbox = self._slider_row(-180, 180, 0, 30)
        self.hue_slider.valueChanged.connect(self.on_hue_changed)
        hsv_layout.addLayout(row)

        hsv_layout.addWidget(QLabel("Saturation (100 = original):"))
        row, self.sat_slider, self.sat_spinbox = self._slider_row(0, 300, 100, 25)
        self.sat_slider.valueChanged.connect(self.on_saturation_changed)
        hsv_layout.addLayout(row)

        hsv_layout.addWidget(QLabel("Value (brightness) shift:"))
        row, self.val_slider, self.val_spinbox = self._slider_row(-100, 100, 0, 25)
        self.val_slider.valueChanged.connect(self.on_value_changed)
        hsv_layout.addLayout(row)

        hsv_group.setLayout(hsv_layout)
        layout.addWidget(hsv_group)

        # Sharpen / Blur 
        sharp_group = QGroupBox("Sharpen / Blur")
        sharp_layout = QVBoxLayout()
        sharp_layout.addWidget(QLabel("Negative = blur, zero = original, positive = sharpen:"))
        row, self.sharpness_slider, self.sharpness_spinbox = \
            self._slider_row(-10, 10, 0, 2)
        self.sharpness_slider.valueChanged.connect(self.on_sharpness_changed)
        sharp_layout.addLayout(row)
        sharp_group.setLayout(sharp_layout)
        layout.addWidget(sharp_group)

        # Color Replacement
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

        # preset
        preset_layout = QHBoxLayout()

        save_btn = QPushButton("Save Preset")
        load_btn = QPushButton("Load Preset")
        manage_btn = QPushButton("Manage Presets")

        save_btn.clicked.connect(self.save_preset_dialog)
        load_btn.clicked.connect(self.load_preset_dialog)
        manage_btn.clicked.connect(self.open_preset_manager)

        preset_layout.addWidget(save_btn)
        preset_layout.addWidget(load_btn)
        preset_layout.addWidget(manage_btn)

        layout.addLayout(preset_layout)

        # buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        # Dialog buttons (outside scroll, always visible) 
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.Reset
        )
        self.buttons.accepted.connect(self.apply_changes)
        self.buttons.rejected.connect(self.reject)
        self.buttons.button(QDialogButtonBox.StandardButton.Reset).clicked.connect(self.reset_image)
        outer_layout.addWidget(self.buttons)

        self.setLayout(outer_layout)

    # ------------------------------------------------------------------
    # Signal handlers
    # ------------------------------------------------------------------

    def on_invert_changed(self, state):
        self.invert_colors = state == Qt.CheckState.Checked.value
        self.update_preview()

    def on_grayscale_changed(self, state):
        self.grayscale = state == Qt.CheckState.Checked.value
        self.update_preview()

    def on_brightness_changed(self, value):
        self.brightness = value
        self.update_preview()

    def on_contrast_changed(self, value):
        self.contrast = value / 100.0
        self.update_preview()

    def on_gamma_changed(self, value):
        self.gamma = value
        self.update_preview()

    def on_r_changed(self, value):
        self.r_level = value
        self.update_preview()

    def on_g_changed(self, value):
        self.g_level = value
        self.update_preview()

    def on_b_changed(self, value):
        self.b_level = value
        self.update_preview()

    def on_hue_changed(self, value):
        self.hue_shift = value
        self.update_preview()

    def on_saturation_changed(self, value):
        self.saturation = value
        self.update_preview()

    def on_value_changed(self, value):
        self.value_shift = value
        self.update_preview()

    def on_sharpness_changed(self, value):
        self.sharpness = value
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

    def apply_color_replacement(self):
        if self.source_color and self.target_color:
            self.color_replacements.append({
                'source': self.source_color,
                'target': self.target_color,
                'tolerance': self.color_tolerance
            })
            sc = QColor(self.source_color[2], self.source_color[1], self.source_color[0])
            tc = QColor(self.target_color[2], self.target_color[1], self.target_color[0])
            self.color_replacements_list.addItem(
                f"{sc.name()} → {tc.name()} (tol: {self.color_tolerance})")
            self.source_color = None
            self.target_color = None
            self.source_color_btn.setStyleSheet("")
            self.target_color_btn.setStyleSheet("")
            self.apply_color_btn.setEnabled(False)
            self.update_preview()
            self.parent.statusBar().showMessage(
                f"Color replacement added ({len(self.color_replacements)} total)")
    
    def save_preset_dialog(self):
        name, ok = QInputDialog.getText(self, "Save Preset", "Preset name:")
        if ok and name:
            self.save_preset(name)

    def load_preset_dialog(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "Load Preset", "presets", "JSON (*.json)"
        )
        if file:
            self.load_preset(file)

    def open_preset_manager(self):
        folder = os.path.abspath("presets")
        os.makedirs(folder, exist_ok=True)

        QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    # ------------------------------------------------------------------
    # Image processing
    # ------------------------------------------------------------------

    def _apply_gamma(self, bgr):
        g = self.gamma / 100.0
        lut = np.array([
            min(255, int((i / 255.0) ** (1.0 / g) * 255))
            for i in range(256)
        ], dtype=np.uint8)
        return cv2.LUT(bgr, lut)

    def _apply_rgb_levels(self, bgr):
        result = bgr.astype(np.int16)
        result[:, :, 0] = np.clip(result[:, :, 0] + self.b_level, 0, 255)
        result[:, :, 1] = np.clip(result[:, :, 1] + self.g_level, 0, 255)
        result[:, :, 2] = np.clip(result[:, :, 2] + self.r_level, 0, 255)
        return result.astype(np.uint8)

    def _apply_hsv(self, bgr):
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).astype(np.int32)
        hsv[:, :, 0] = (hsv[:, :, 0] + int(self.hue_shift / 2)) % 180
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * self.saturation / 100, 0, 255)
        hsv[:, :, 2] = np.clip(hsv[:, :, 2] + self.value_shift, 0, 255)
        return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

    def _apply_sharpness(self, bgr):
        v = self.sharpness
        if v == 0:
            return bgr
        if v > 0:
            blurred = cv2.GaussianBlur(bgr, (0, 0), sigmaX=3)
            return cv2.addWeighted(bgr, 1 + v * 0.3, blurred, -v * 0.3, 0)
        else:
            k = abs(v) * 2 + 1
            return cv2.GaussianBlur(bgr, (k, k), 0)

    def update_preview(self):
        if not self.is_valid:
            return

        image = self.original_image.copy()

        image = self._process_bgr_only(
            image,
            lambda bgr: cv2.convertScaleAbs(bgr, alpha=self.contrast, beta=self.brightness)
        )

        if self.gamma != 100:
            image = self._process_bgr_only(image, self._apply_gamma)

        if self.r_level != 0 or self.g_level != 0 or self.b_level != 0:
            image = self._process_bgr_only(image, self._apply_rgb_levels)

        if self.hue_shift != 0 or self.saturation != 100 or self.value_shift != 0:
            image = self._process_bgr_only(image, self._apply_hsv)

        if self.sharpness != 0:
            image = self._process_bgr_only(image, self._apply_sharpness)

        if self.grayscale:
            image = self._process_bgr_only(
                image,
                lambda bgr: cv2.cvtColor(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR)
            )

        if self.invert_colors:
            image = self._process_bgr_only(image, cv2.bitwise_not)

        for rep in self.color_replacements:
            image = self.replace_color(image, rep['source'], rep['target'], rep['tolerance'])
        if self.color_replace_enabled and self.source_color and self.target_color:
            image = self.replace_color(image, self.source_color, self.target_color, self.color_tolerance)

        self.modified_image = image
        self.image_item.image_item.setPixmap(self._cv2_to_pixmap(self.modified_image))
        self.parent.zoomable_graphics_view.scene.update()
        self.parent.zoomable_graphics_view.viewport().update()

    def replace_color(self, image, source_color, target_color, tolerance):
        result = image.copy()
        lower = np.array([max(0,   source_color[i] - tolerance) for i in range(3)], dtype=np.uint8)
        upper = np.array([min(255, source_color[i] + tolerance) for i in range(3)], dtype=np.uint8)
        mask = cv2.inRange(result[:, :, :3], lower, upper)
        result[mask > 0, :3] = np.array(target_color[:3], dtype=np.uint8)
        return result

    def clear_color_replacements(self):
        self.color_replacements = []
        self.color_replacements_list.clear()
        self.update_preview()
        self.parent.statusBar().showMessage("All color replacements cleared")

    # ------------------------------------------------------------------
    # Dialog actions
    # ------------------------------------------------------------------

    def _all_widgets(self):
        return [
            self.brightness_slider, self.brightness_spinbox,
            self.contrast_slider,   self.contrast_spinbox,
            self.gamma_slider,      self.gamma_spinbox,
            self.r_slider,          self.r_spinbox,
            self.g_slider,          self.g_spinbox,
            self.b_slider,          self.b_spinbox,
            self.hue_slider,        self.hue_spinbox,
            self.sat_slider,        self.sat_spinbox,
            self.val_slider,        self.val_spinbox,
            self.sharpness_slider,  self.sharpness_spinbox,
            self.tolerance_slider,  self.tolerance_spinbox,
            self.invert_checkbox,   self.grayscale_checkbox,
            self.color_replace_checkbox,
        ]

    def reset_image(self):
        if not self.is_valid:
            return

        for w in self._all_widgets():
            w.blockSignals(True)

        self.invert_checkbox.setChecked(False)
        self.grayscale_checkbox.setChecked(False)
        self.brightness_slider.setValue(0)
        self.contrast_slider.setValue(100)
        self.gamma_slider.setValue(100)
        self.r_slider.setValue(0)
        self.g_slider.setValue(0)
        self.b_slider.setValue(0)
        self.hue_slider.setValue(0)
        self.sat_slider.setValue(100)
        self.val_slider.setValue(0)
        self.sharpness_slider.setValue(0)
        self.tolerance_slider.setValue(30)
        self.color_replace_checkbox.setChecked(False)
        self.source_color = None
        self.target_color = None
        self.source_color_btn.setStyleSheet("")
        self.target_color_btn.setStyleSheet("")
        self.color_replacements = []
        self.color_replacements_list.clear()

        for w in self._all_widgets():
            w.blockSignals(False)

        self.invert_colors = False
        self.grayscale     = False
        self.brightness    = 0
        self.contrast      = 1.0
        self.gamma         = 100
        self.r_level       = 0
        self.g_level       = 0
        self.b_level       = 0
        self.hue_shift     = 0
        self.saturation    = 100
        self.value_shift   = 0
        self.sharpness     = 0

        self.original_pixmap = QPixmap(self.original_path)
        self.has_alpha = self.original_pixmap.hasAlpha()
        self.original_image = self._load_cv2_from_file(self.original_path, self.has_alpha)
        self.modified_image = self.original_image.copy()

        self.image_item.image_pixmap = self.original_pixmap.copy()
        self.image_item.image_item.setPixmap(self.original_pixmap)
        self.image_item.image_numpy_pixels_rgb = None
        self.parent.zoomable_graphics_view.scene.update()
        self.parent.zoomable_graphics_view.viewport().update()
        self.parent.statusBar().showMessage("Reset to original image")

    def apply_changes(self):
        final_pixmap = self._cv2_to_pixmap(self.modified_image)
        self.image_item.image_pixmap = final_pixmap.copy()
        self.image_item.image_numpy_pixels_rgb = None
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
        return self._cv2_to_pixmap(self.modified_image)
