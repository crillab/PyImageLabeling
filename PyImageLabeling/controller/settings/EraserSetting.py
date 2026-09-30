from PyQt6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QDialog,
    QSlider,
    QPushButton,
    QDialogButtonBox,
    QSpinBox,
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
    QComboBox,
    QGroupBox,
    QApplication,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QImage
from PyImageLabeling.model.Utils import Utils
import numpy as np


class DynamicEraserDialog(QDialog):
    """Interactive preview: adjust the tolerance and watch what is erased.

    The keep-colour can be changed from here with a colour button, and the
    whole colour criterion can be switched off to erase the closed shape
    exactly as it is.
    """

    def __init__(self, parent, img_arr, shape_mask, keep_rgba,
                 initial_tolerance, overlay_pixmap, base_pixmap,
                 model=None):
        super().__init__(parent)

        self.model = model
        self.img_arr = img_arr
        self.shape_mask = shape_mask
        self.base_pixmap = base_pixmap
        self.overlay_pixmap = overlay_pixmap
        self.last_erase_mask = None
        self.tolerance = int(initial_tolerance)
        self._initial_tolerance = int(initial_tolerance)
        self.use_color = True
        if keep_rgba is not None:
            self.keep_rgba = np.array(keep_rgba, dtype=np.int16)
        else:
            self.keep_rgba = np.array([0, 0, 0, 255], dtype=np.int16)

        self.setWindowTitle("Intelligent Eraser — adjust what to keep")
        self.setMinimumWidth(640)

        layout = QVBoxLayout()

        # Preview Label
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(1, 1)
        self.preview_label.setScaledContents(True)
        layout.addWidget(self.preview_label)

        # Tolerance row: slider + spinbox kept in sync
        tol_row = QHBoxLayout()
        tol_row.addWidget(QLabel("Colour tolerance:"))
        self.tolerance_slider = QSlider(Qt.Orientation.Horizontal)
        self.tolerance_slider.setRange(0, 255)
        self.tolerance_slider.setValue(self.tolerance)
        self.tolerance_slider.setTickPosition(
            QSlider.TickPosition.TicksBelow)
        self.tolerance_slider.setTickInterval(32)
        self.tolerance_slider.valueChanged.connect(self._on_tolerance)
        tol_row.addWidget(self.tolerance_slider, 1)

        self.tolerance_spinbox = QSpinBox()
        self.tolerance_spinbox.setRange(0, 255)
        self.tolerance_spinbox.setValue(self.tolerance)
        self.tolerance_spinbox.valueChanged.connect(self._on_tolerance)
        tol_row.addWidget(self.tolerance_spinbox)
        layout.addLayout(tol_row)

        # Keep-colour row
        color_row = QHBoxLayout()
        self.use_color_checkbox = QCheckBox("Match colour (off = erase the "
                                            "closed shape as it is)")
        self.use_color_checkbox.setChecked(True)
        self.use_color_checkbox.toggled.connect(self._on_use_color)
        color_row.addWidget(self.use_color_checkbox, 1)

        self.color_button = QPushButton()
        self.color_button.setFixedSize(46, 26)
        self.color_button.setToolTip(
            "Colour to keep. The masks are hidden while the picker is open "
            "so you see the real image, and restored when it closes.")
        self.color_button.clicked.connect(self.pick_color)
        color_row.addWidget(self.color_button)

        self.reset_button = QPushButton("Reset")
        self.reset_button.clicked.connect(self.reset_preview)
        color_row.addWidget(self.reset_button)
        layout.addLayout(color_row)

        self.info_label = QLabel()
        self.info_label.setStyleSheet("color: gray;")
        layout.addWidget(self.info_label)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)
        self._update_color_button()
        self.update_preview(self.tolerance)

    # -- keep colour ----------------------------------------------------
    def _update_color_button(self):
        r, g, b = (int(self.keep_rgba[0]), int(self.keep_rgba[1]),
                   int(self.keep_rgba[2]))
        self.color_button.setStyleSheet(
            f"background-color: rgb({r}, {g}, {b}); border: 1px solid black;")

    def _set_masks_visible(self, visible):
        """Hide every mask while the colour picker is open (see
        EraserSetting._set_masks_visible). No-op if we have no model."""
        if self.model is None:
            return
        try:
            item = self.model.get_current_image_item()
            for overlay in item.get_labeling_overlays():
                overlay.set_visible(visible)
        except Exception:
            pass

    def pick_color(self):
        self._set_masks_visible(False)
        QApplication.processEvents()
        try:
            color = QColorDialog.getColor(
                QColor(int(self.keep_rgba[0]), int(self.keep_rgba[1]),
                       int(self.keep_rgba[2])), self)
        finally:
            self._set_masks_visible(True)
        if color.isValid():
            self.keep_rgba = np.array(
                [color.red(), color.green(), color.blue(), 255],
                dtype=np.int16)
            self._update_color_button()
            self.update_preview(self.tolerance)

    # -- react to the controls -----------------------------------------
    def _set_controls_enabled(self):
        on = self.use_color
        self.tolerance_slider.setEnabled(on)
        self.tolerance_spinbox.setEnabled(on)
        self.color_button.setEnabled(on)

    def _sync_tolerance(self, value):
        """Push a tolerance into both widgets without re-entering signals."""
        for widget in (self.tolerance_slider, self.tolerance_spinbox):
            if widget.value() != value:
                widget.blockSignals(True)
                widget.setValue(value)
                widget.blockSignals(False)
        self.tolerance = int(value)
        self.update_preview(value)

    def _on_tolerance(self, value):
        self._sync_tolerance(int(value))

    def _on_use_color(self, checked):
        self.use_color = bool(checked)
        self._set_controls_enabled()
        self.update_preview(self.tolerance)

    def get_tolerance(self):
        return self.tolerance
    # -- preview --------------------------------------------------------
    def update_preview(self, tolerance):
        """Base image + overlay, with the pixels to erase tinted red.

        The tint used to be one drawRect per pixel (226 ms per slider move
        on a 1024x1024 shape); it is now a single drawImage of the mask.
        """
        preview_pixmap = self.base_pixmap.copy()
        painter = QPainter(preview_pixmap)
        painter.drawPixmap(0, 0, self.overlay_pixmap)

        if self.use_color:
            h, w = self.shape_mask.shape
            diff = np.abs(self.img_arr[:h, :w].astype(np.int16)
                           - self.keep_rgba)
            match = np.all(diff <= tolerance, axis=2)
            erase_mask = self.shape_mask & ~match
        else:
            erase_mask = self.shape_mask

        self.last_erase_mask = erase_mask

        h, w = erase_mask.shape
        rgba = np.zeros((h, w, 4), np.uint8)
        rgba[erase_mask] = (255, 0, 0, 90)
        qimg = QImage(rgba.data, w, h, w * 4,
                      QImage.Format.Format_RGBA8888).copy()
        painter.setCompositionMode(
            QPainter.CompositionMode.CompositionMode_SourceOver)
        painter.drawImage(0, 0, qimg)
        painter.end()

        scaled = preview_pixmap.scaled(
            460, 460,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation
        )
        self.preview_label.setPixmap(scaled)

        n_erase = int(np.count_nonzero(erase_mask))
        n_shape = int(np.count_nonzero(self.shape_mask))
        if self.use_color:
            self.info_label.setText(
                f"shape {n_shape} px — {n_erase} px will be erased, "
                f"{n_shape - n_erase} px kept (colour to keep: "
                f"rgb({int(self.keep_rgba[0])}, {int(self.keep_rgba[1])}, "
                f"{int(self.keep_rgba[2])}, tolerance {tolerance})")
        else:
            self.info_label.setText(
                f"shape {n_shape} px — {n_erase} px will be erased, "
                f"no colour check")

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

    def reset_preview(self):
        """Back to the tolerance we were opened with, colour check on."""
        self.use_color_checkbox.blockSignals(True)
        self.use_color_checkbox.setChecked(True)
        self.use_color_checkbox.blockSignals(False)
        self.use_color = True
        self._set_controls_enabled()
        self._sync_tolerance(self._initial_tolerance)

class EraserSetting(QDialog):
    def __init__(self, parent, model):
        super().__init__(parent)
        # keep a reference: the eyedropper needs to arm the model, and the
        # dialog is the only holder of it
        self.model = model
        self.view = parent
        self.setWindowTitle("Eraser Settings")
        self.resize(500, 150)
        params = Utils.load_parameters()["eraser"]
        self.max_size = int(min(model.get_current_image_item().image_qrectf.width(), model.get_current_image_item().image_qrectf.height()))
        self.min_size = 2
        self.radius = params.get("size", 10)
        self.absolute_mode = params.get("absolute_mode", 0)
        self.eraser_mode = params.get("mode", "original")
        self.use_color = bool(params.get("use_color", True))

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
        self.color_group = QGroupBox("Colour to keep")
        color_layout = QVBoxLayout()
        color_label = QLabel("Select the colour to keep (others are erased):")
        color_layout.addWidget(color_label)

        color_row = QHBoxLayout()
        self.color_button = QPushButton()
        self.color_button.setFixedSize(46, 26)
        self.color_button.setStyleSheet("background-color: rgba(0, 0, 0, 0); border: 1px solid black;")
        self.color_button.setToolTip(
            "Colour to keep. While the picker is open every mask is hidden, "
            "so you see the real image; they come back when you close it.")
        self.color_button.clicked.connect(self.pick_color)
        color_row.addWidget(self.color_button)
        color_row.addStretch()
        color_layout.addLayout(color_row)

        self.use_color_checkbox = QCheckBox(
            "Match colour (off = erase the closed shape as it is)")
        self.use_color_checkbox.setChecked(self.use_color)
        self.use_color_checkbox.setToolTip(
            "With this off, the whole closed shape you clicked is erased, "
            "whatever its colour.")
        self.use_color_checkbox.toggled.connect(self._on_use_color_toggled)
        color_layout.addWidget(self.use_color_checkbox)

        self.selected_color = QColor(params.get("keep_color", "#00000000"))
        self.update_color_button()
        color_layout.addWidget(QLabel(
            "Selected colour is kept; the others are erased."))
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

        if show_intelligent:
            # the colour criterion only makes sense in intelligent mode
            self.use_color_checkbox.setEnabled(True)
            self.color_button.setEnabled(True)
            self.threshold_slider.setEnabled(self.use_color_checkbox.isChecked())
            self.threshold_spinbox.setEnabled(self.use_color_checkbox.isChecked())
            self.dynamic_checkbox.setEnabled(self.use_color_checkbox.isChecked())

        if show_controls:
            self.resize(500, 150)
        else:
            self.resize(500, 420)

    def ensure_even_value(self, value):
        """Ensure the value is even (pair). If odd, round to nearest even."""
        if value % 2 != 0:
            return value + 1
        return value

    def update_radius(self, value):
        """Update internal radius value when slider changes"""
        self.radius = self.ensure_even_value(value)

    def _on_use_color_toggled(self, checked):
        """Grey out the colour controls when the criterion is off."""
        self.threshold_slider.setEnabled(checked)
        self.threshold_spinbox.setEnabled(checked)
        self.color_button.setEnabled(checked)
        self.dynamic_checkbox.setEnabled(checked)

    def _set_masks_visible(self, visible):
        """Show/hide every mask overlay of the current image.

        Used around the colour picker: with the masks hidden you see the
        real image, so the colour you choose is the one you meant. The
        current label is untouched, and the masks come back on close.
        """
        try:
            item = self.model.get_current_image_item()
            for overlay in item.get_labeling_overlays():
                overlay.set_visible(visible)
        except Exception:
            pass

    def pick_color(self):
        self._set_masks_visible(False)
        QApplication.processEvents()
        try:
            color = QColorDialog.getColor(self.selected_color, self)
        finally:
            # always restore, even if the dialog was closed abruptly
            self._set_masks_visible(True)
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
        data["eraser"]["keep_color"] = self.selected_color.name(
            QColor.NameFormat.HexArgb)
        data["eraser"]["dynamic_adjust"] = self.dynamic_checkbox.isChecked()
        data["eraser"]["use_color"] = self.use_color_checkbox.isChecked()
        Utils.save_parameters(data)
        return super().accept()