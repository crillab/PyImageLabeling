from PyQt6.QtWidgets import QCheckBox, QDialog, QSlider, QFormLayout, QDialogButtonBox, QSpinBox, QLabel, QHBoxLayout, QVBoxLayout
from PyQt6.QtCore import Qt

from PyImageLabeling.model.Utils import Utils

class UndoSetting(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Undo Settings")
        self.resize(500, 100)

        self.depth = Utils.load_parameters()["undo"]["depth"] 

        layout = QVBoxLayout()
        form_layout = QFormLayout()

        initial_depth = self.ensure_even_value(self.depth)
        # Tolerance slider and spinbox
        self.depth_slider = QSlider(Qt.Orientation.Horizontal)
        self.depth_slider.setRange(0, 100)
        self.depth_slider.setSingleStep(2)
        self.depth_slider.setValue(initial_depth)
        self.depth_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.depth_slider.setTickInterval(10)

        self.depth_spinbox = QSpinBox()
        self.depth_spinbox.setRange(0, 100)
        self.depth_spinbox.setSingleStep(2)
        self.depth_spinbox.setValue(initial_depth)

        # Connect both ways to keep them synchronized
        self.depth_spinbox.valueChanged.connect(self.depth_slider.setValue)
        self.depth_slider.valueChanged.connect(self.depth_spinbox.setValue)
        
        # Update internal values when sliders change
        self.depth_slider.valueChanged.connect(self.update_depth)
        self.depth_spinbox.valueChanged.connect(self.update_depth)

        form_layout.addRow("Memory depth:", self.depth_slider)
        form_layout.addRow("Value:", self.depth_spinbox)


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
    
    def update_depth(self, value):
        """Update internal tolerance value when slider changes"""
        self.depth = self.ensure_even_value(value)
    
    def update_absolute_mode(self, state):
        """Update internal absolute mode value when checkbox changes"""
        self.absolute_mode = 1 if state == Qt.CheckState.Checked.value else 0
        
    def accept(self):
        """Override accept to ensure settings are updated before closing"""
        # Update internal values one final time
        self.depth= self.depth_slider.value()
        self.depth = self.depth_spinbox.value()
        data = Utils.load_parameters()
        data["undo"]["depth"] = self.depth
        Utils.save_parameters(data) 
        return super().accept()