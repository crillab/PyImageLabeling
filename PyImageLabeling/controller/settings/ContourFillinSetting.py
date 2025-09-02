from PyQt6.QtWidgets import QDialog, QSlider, QFormLayout, QDialogButtonBox, QSpinBox, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt

from model.Utils import Utils

class ContourFillingSetting(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Paint Brush Settings")
        self.resize(500, 100)

        self.tolerance = Utils.load_parameters()["contour_filling"]["tolerance"] 

        layout = QVBoxLayout()
        form_layout = QFormLayout()

        # Tolerance slider and spinbox
        self.tolerance_slider = QSlider(Qt.Orientation.Horizontal)
        self.tolerance_slider.setRange(1, 10)
        self.tolerance_slider.setValue(self.tolerance)
        self.tolerance_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.tolerance_slider.setTickInterval(1)

        self.tolerance_spinbox = QSpinBox()
        self.tolerance_spinbox.setRange(1, 10)
        self.tolerance_spinbox.setValue(self.tolerance)

        # Connect both ways to keep them synchronized
        self.tolerance_spinbox.valueChanged.connect(self.tolerance_slider.setValue)
        self.tolerance_slider.valueChanged.connect(self.tolerance_spinbox.setValue)

        # Update internal values when sliders change
        self.tolerance_slider.valueChanged.connect(self.update_tolerance)
        self.tolerance_spinbox.valueChanged.connect(self.update_tolerance)

        form_layout.addRow("Tolerance:", self.tolerance_slider)
        form_layout.addRow("Value:", self.tolerance_spinbox)

        # Label to display the tolerance description
        self.tolerance_description_label = QLabel()
        self.update_tolerance_description()
        form_layout.addRow("Description:", self.tolerance_description_label)

        # Help text
        tolerance_help = QLabel("Select the tolerance of your contouring")
        tolerance_help.setStyleSheet("color: #666; font-style: italic;")
        form_layout.addRow("", tolerance_help)

        layout.addLayout(form_layout)

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
            1: "Most Precise - Only very clear, well-defined contours",
            2: "Very Precise - Clear contours with minimal noise",
            3: "Precise - Well-defined contours, some fine details",
            4: "Moderately Precise - Good balance, cleaner results",
            5: "Balanced - Default setting, good for most images",
            6: "Moderately Tolerant - Captures more subtle edges",
            7: "Tolerant - Finds more contours, including faint ones",
            8: "Very Tolerant - Detects subtle features and textures",
            9: "Highly Tolerant - Captures most edge information",
            10: "Most Tolerant - Maximum sensitivity, may include noise"
        }
        description = descriptions.get(self.tolerance, "Unknown tolerance level")
        self.tolerance_description_label.setText(description)

    def get_settings(self):
        """Return current settings from the UI controls"""
        # Get values directly from the controls to ensure we have the latest values
        tolerance = self.tolerance_slider.value()

        # Also update internal variables for consistency
        self.tolerance = tolerance
        return tolerance

    def accept(self):
        """Override accept to ensure settings are updated before closing"""
        # Update internal values one final time
        self.tolerance = self.tolerance_slider.value()
        data = Utils.load_parameters()
        data["contour_filling"]["tolerance"] = self.tolerance
        Utils.save_parameters(data) 
        return super().accept()
    
