from PyQt6.QtWidgets import QDialog, QSlider, QFormLayout, QDialogButtonBox, QSpinBox, QLabel, QVBoxLayout, QHBoxLayout, QGroupBox
from PyQt6.QtCore import Qt
from PyImageLabeling.model.Utils import Utils

class ContourFillingSetting(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Contour Filling Settings")
        self.resize(500, 200)
        self.tolerance = Utils.load_parameters()["contour_filling"]["tolerance"]

        layout = QVBoxLayout()

        # Tolerance Group
        tolerance_group = QGroupBox("Tolerance")
        tolerance_layout = QVBoxLayout()

        tolerance_label = QLabel("Set contour filling tolerance:")
        tolerance_layout.addWidget(tolerance_label)

        tolerance_slider_layout = QHBoxLayout()
        self.tolerance_slider = QSlider(Qt.Orientation.Horizontal)
        self.tolerance_slider.setRange(1, 20)
        self.tolerance_slider.setValue(self.tolerance)
        self.tolerance_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.tolerance_slider.setTickInterval(1)

        self.tolerance_spinbox = QSpinBox()
        self.tolerance_spinbox.setRange(1, 20)
        self.tolerance_spinbox.setValue(self.tolerance)

        self.tolerance_spinbox.valueChanged.connect(self.tolerance_slider.setValue)
        self.tolerance_slider.valueChanged.connect(self.tolerance_spinbox.setValue)
        self.tolerance_slider.valueChanged.connect(self.update_tolerance)
        self.tolerance_spinbox.valueChanged.connect(self.update_tolerance)

        tolerance_slider_layout.addWidget(self.tolerance_slider)
        tolerance_slider_layout.addWidget(self.tolerance_spinbox)
        tolerance_layout.addLayout(tolerance_slider_layout)

        self.tolerance_description_label = QLabel()
        self.update_tolerance_description()
        tolerance_layout.addWidget(self.tolerance_description_label)

        tolerance_group.setLayout(tolerance_layout)
        layout.addWidget(tolerance_group)

        # Buttons
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.setLayout(layout)

    def update_tolerance(self, value):
        """Update internal tolerance value when slider changes"""
        self.tolerance = value
        self.update_tolerance_description()

    def update_tolerance_description(self):
        """Update the tolerance description label based on the current tolerance level"""
        descriptions = {
            1:  "Level 1 – Ultra Precise: Detects only strong, clean, well-defined contours.",
            2:  "Level 2 – Very Precise: Ideal for high-contrast edges with minimal texture.",
            3:  "Level 3 – Precise: Detects clear boundaries and some fine details.",
            4:  "Level 4 – Moderately Precise: Keeps clarity while allowing slight variation.",
            5:  "Level 5 – Balanced (Default): Good overall trade-off for typical images.",
            6:  "Level 6 – Slightly Tolerant: Starts to capture faint or uneven edges.",
            7:  "Level 7 – Tolerant: Includes subtle contour variations and weak signals.",
            8:  "Level 8 – Broad Tolerance: Handles soft edges and low contrast areas.",
            9:  "Level 9 – Very Tolerant: Recovers most faint and fragmented contours.",
            10: "Level 10 – Adaptive: Balances faint edge capture with minimal noise.",
            11: "Level 11 – Gentle Expansion: More sensitive to soft and irregular boundaries.",
            12: "Level 12 – Enhanced Sensitivity: Detects dim textures, may include noise.",
            13: "Level 13 – High Sensitivity: Extracts nearly all visible edges.",
            14: "Level 14 – Deep Sensitivity: Useful for blurred or unevenly lit regions.",
            15: "Level 15 – Strongly Tolerant: Detects faint outlines even in noise.",
            16: "Level 16 – Very Strong: Focused on recovering missing weak structures.",
            17: "Level 17 – Aggressive: Captures nearly all gradient variations.",
            18: "Level 18 – High Noise Mode: Very faint features included, heavy post-filtering may be needed.",
            19: "Level 19 – Extreme Sensitivity: All possible edges detected, noise likely.",
            20: "Level 20 – Maximum Tolerance: Detects every possible contour, heavy cleanup required."
        }
        description = descriptions.get(self.tolerance, "Unknown tolerance level")
        self.tolerance_description_label.setText(description)

    def get_settings(self):
        """Return current settings from the UI controls"""
        tolerance = self.tolerance_slider.value()
        self.tolerance = tolerance
        return tolerance

    def accept(self):
        """Override accept to ensure settings are updated before closing"""
        self.tolerance = self.tolerance_slider.value()
        data = Utils.load_parameters()
        data["contour_filling"]["tolerance"] = self.tolerance
        Utils.save_parameters(data)
        return super().accept()
