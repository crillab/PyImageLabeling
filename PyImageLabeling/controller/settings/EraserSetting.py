from PyQt6.QtWidgets import QCheckBox, QDialog, QSlider, QFormLayout, QDialogButtonBox, QSpinBox, QLabel, QHBoxLayout, QVBoxLayout, QComboBox
from PyQt6.QtCore import Qt

from PyImageLabeling.model.Utils import Utils

class EraserSetting(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Eraser Settings")
        self.resize(500, 150)

        params = Utils.load_parameters()["eraser"]
        self.radius = params.get("size", 10)
        self.absolute_mode = params.get("absolute_mode", 0)
        self.eraser_mode = params.get("mode", "original")  # original, absolute, or intelligent

        layout = QVBoxLayout()
        form_layout = QFormLayout()

        # Mode selector
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Original Mode", "Absolute Mode", "Intelligent Mode"])
        
        # Set current mode
        mode_map = {"original": 0, "absolute": 1, "intelligent": 2}
        self.mode_combo.setCurrentIndex(mode_map.get(self.eraser_mode, 0))
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        
        form_layout.addRow("Eraser Mode:", self.mode_combo)

        # Radius controls
        initial_radius = self.ensure_even_value(self.radius)
        
        self.radius_label = QLabel("Radius:")
        self.radius_slider = QSlider(Qt.Orientation.Horizontal)
        self.radius_slider.setRange(0, 100)
        self.radius_slider.setSingleStep(2)
        self.radius_slider.setValue(initial_radius)
        self.radius_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.radius_slider.setTickInterval(10)

        self.value_label = QLabel("Value:")
        self.radius_spinbox = QSpinBox()
        self.radius_spinbox.setRange(0, 100)
        self.radius_spinbox.setSingleStep(2)
        self.radius_spinbox.setValue(initial_radius)
        
        # Connect both ways to keep them synchronized
        self.radius_spinbox.valueChanged.connect(self.radius_slider.setValue)
        self.radius_slider.valueChanged.connect(self.radius_spinbox.setValue)
        
        # Update internal values when sliders change
        self.radius_slider.valueChanged.connect(self.update_radius)
        self.radius_spinbox.valueChanged.connect(self.update_radius)

        form_layout.addRow(self.radius_label, self.radius_slider)
        form_layout.addRow(self.value_label, self.radius_spinbox)

        layout.addLayout(form_layout)

        # Buttons
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.setLayout(layout)
        
        # Initialize visibility based on current mode
        self.on_mode_changed(self.mode_combo.currentIndex())

    def on_mode_changed(self, index):
        """Show/hide radius and value controls based on selected mode"""
        mode_names = ["original", "absolute", "intelligent"]
        self.eraser_mode = mode_names[index]
        
        # Update absolute_mode flag based on selection
        if self.eraser_mode == "absolute":
            self.absolute_mode = 1
        else:
            self.absolute_mode = 0
        
        # Show radius/value controls for original and absolute modes only
        show_controls = index in [0, 1]  # Original or Absolute
        
        self.radius_label.setVisible(show_controls)
        self.radius_slider.setVisible(show_controls)
        self.value_label.setVisible(show_controls)
        self.radius_spinbox.setVisible(show_controls)
        
        # Adjust dialog size based on visibility
        if show_controls:
            self.resize(500, 150)
        else:
            self.resize(500, 100)

    def ensure_even_value(self, value):
        """Ensure the value is even (pair). If odd, round to nearest even."""
        if value % 2 != 0:
            return value + 1
        return value
    
    def update_radius(self, value):
        """Update internal tolerance value when slider changes"""
        self.radius = self.ensure_even_value(value)
        
    def accept(self):
        """Override accept to ensure settings are updated before closing"""
        # Update internal values one final time
        self.radius = self.radius_spinbox.value()
        data = Utils.load_parameters()
        data["eraser"]["size"] = self.radius
        data["eraser"]["absolute_mode"] = self.absolute_mode
        data["eraser"]["mode"] = self.eraser_mode
        Utils.save_parameters(data) 
        return super().accept()