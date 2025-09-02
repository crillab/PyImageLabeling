from PyQt6.QtWidgets import QDialog, QSlider, QFormLayout, QDialogButtonBox, QSpinBox, QLabel, QHBoxLayout, QVBoxLayout
from PyQt6.QtCore import Qt

from PyImageLabeling.model.Utils import Utils

class EraserSetting(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Eraser Settings")
        self.resize(500, 100)

        self.radius = Utils.load_parameters()["eraser"]["size"] 

        layout = QVBoxLayout()
        form_layout = QFormLayout()

        # Tolerance slider and spinbox
        self.radius_slider = QSlider(Qt.Orientation.Horizontal)
        self.radius_slider.setRange(0, 100)
        self.radius_slider.setValue(self.radius)
        self.radius_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.radius_slider.setTickInterval(10)

        self.radius_spinbox = QSpinBox()
        self.radius_spinbox.setRange(0, 100)
        self.radius_spinbox.setValue(self.radius)

        # Connect both ways to keep them synchronized
        self.radius_spinbox.valueChanged.connect(self.radius_slider.setValue)
        self.radius_slider.valueChanged.connect(self.radius_spinbox.setValue)
        
        # Update internal values when sliders change
        self.radius_slider.valueChanged.connect(self.update_radius)
        self.radius_spinbox.valueChanged.connect(self.update_radius)

        form_layout.addRow("Radius:", self.radius_slider)
        form_layout.addRow("Value:", self.radius_spinbox)

        # Help text
        radius_help = QLabel("Select the radius of your paintbrush")
        radius_help.setStyleSheet("color: #666; font-style: italic;")
        form_layout.addRow("", radius_help)

        layout.addLayout(form_layout)

        # Buttons
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.setLayout(layout)

    def update_radius(self, value):
        """Update internal tolerance value when slider changes"""
        self.radius = value
        
    def accept(self):
        """Override accept to ensure settings are updated before closing"""
        # Update internal values one final time
        self.radius= self.radius_slider.value()
        self.radius = self.radius_slider.value()
        data = Utils.load_parameters()
        data["eraser"]["size"] = self.radius
        Utils.save_parameters(data) 
        return super().accept()