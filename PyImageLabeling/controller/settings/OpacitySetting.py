from PyQt6.QtWidgets import QDialog, QSlider, QFormLayout, QDialogButtonBox, QSpinBox, QLabel, QHBoxLayout, QVBoxLayout
from PyQt6.QtCore import Qt

from PyImageLabeling.model.Utils import Utils

class OpacitySetting(QDialog):
    def __init__(self, zoomable_graphic_view):
        super().__init__(zoomable_graphic_view)
        self.setWindowTitle("Opacity Settings")
        self.resize(500, 100)
        self.min_opacity = 10
        self.max_opacity = 100
        
        self.opacity = Utils.load_parameters()["labeling_opacity"] 
        if not (self.min_opacity <= self.opacity <= self.max_opacity):
            self.opacity = 50

        layout = QVBoxLayout()
        label = QLabel("Percentage (between 10 and 100):")
        layout.addWidget(label)

        slider_layout = QHBoxLayout()

        # Tolerance slider and spinbox
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(self.min_opacity, self.max_opacity)
        self.opacity_slider.setValue(self.opacity)
        self.opacity_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.opacity_slider.setTickInterval(10)

        self.opacity_spinbox = QSpinBox()
        self.opacity_spinbox.setRange(self.min_opacity, self.max_opacity)
        self.opacity_spinbox.setValue(self.opacity)

        # Connect both ways to keep them synchronized
        self.opacity_spinbox.valueChanged.connect(self.opacity_slider.setValue)
        self.opacity_slider.valueChanged.connect(self.opacity_spinbox.setValue)
        
        # Update internal values when sliders change
        self.opacity_slider.valueChanged.connect(self.update_opacity)
        self.opacity_spinbox.valueChanged.connect(self.update_opacity)

        slider_layout.addWidget(self.opacity_slider)
        slider_layout.addWidget(self.opacity_spinbox)
        layout.addLayout(slider_layout)

        # Buttons
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.setLayout(layout)

    def update_opacity(self, value):
        """Update internal tolerance value when slider changes"""
        self.opacity = value

    def accept(self):
        """Override accept to ensure settings are updated before closing"""
        # Update internal values one final time
        self.opacity = self.opacity_slider.value()
        data = Utils.load_parameters()
        data["labeling_opacity"] = self.opacity
        Utils.save_parameters(data) 
        return super().accept()