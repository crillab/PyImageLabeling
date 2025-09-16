from PyQt6.QtWidgets import QCheckBox, QDialog, QSlider, QFormLayout, QDialogButtonBox, QSpinBox, QLabel, QHBoxLayout, QVBoxLayout
from PyQt6.QtCore import Qt

from PyImageLabeling.model.Utils import Utils

class EraserSetting(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Eraser Settings")
        self.resize(500, 100)

        self.radius = Utils.load_parameters()["eraser"]["size"] 
        self.absolute_mode = Utils.load_parameters()["eraser"].get("absolute_mode", 0)

        layout = QVBoxLayout()
        form_layout = QFormLayout()

        # Tolerance slider and spinbox
        self.radius_slider = QSlider(Qt.Orientation.Horizontal)
        self.radius_slider.setRange(0, 100)
        self.radius_slider.setSingleStep(2)
        self.radius_slider.setValue(self.radius)
        self.radius_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.radius_slider.setTickInterval(10)

        self.radius_spinbox = QSpinBox()
        self.radius_spinbox.setRange(0, 100)
        self.radius_spinbox.setSingleStep(2)
        self.radius_spinbox.setValue(self.radius)

        self.absolute_checkbox = QCheckBox("Absolute mode")
        self.absolute_checkbox.setChecked(self.absolute_mode == 1)
        
        # Connect both ways to keep them synchronized
        self.radius_spinbox.valueChanged.connect(self.radius_slider.setValue)
        self.radius_slider.valueChanged.connect(self.radius_spinbox.setValue)
        
        # Update internal values when sliders change
        self.radius_slider.valueChanged.connect(self.update_radius)
        self.radius_spinbox.valueChanged.connect(self.update_radius)
        self.absolute_checkbox.stateChanged.connect(self.update_absolute_mode)

        form_layout.addRow("Radius:", self.radius_slider)
        form_layout.addRow("Value:", self.radius_spinbox)
        form_layout.addRow("", self.absolute_checkbox)


        layout.addLayout(form_layout)

        # Buttons
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.setLayout(layout)

    def ensure_even_value(self, value):
        """Ensure the value is even (pair). If odd, round to nearest even."""
        if value % 2 != 0:
            return value + 1
        return value
    
    def update_radius(self, value):
        """Update internal tolerance value when slider changes"""
        self.radius = self.ensure_even_value(value)
    
    def update_absolute_mode(self, state):
        """Update internal absolute mode value when checkbox changes"""
        self.absolute_mode = 1 if state == Qt.CheckState.Checked.value else 0
        
    def accept(self):
        """Override accept to ensure settings are updated before closing"""
        # Update internal values one final time
        self.radius= self.ensure_even_value(self.radius_slider.value())
        self.radius = self.ensure_even_value(self.radius_slider.value())
        data = Utils.load_parameters()
        data["eraser"]["size"] = self.radius
        data["eraser"]["absolute_mode"] = self.absolute_mode
        Utils.save_parameters(data) 
        return super().accept()