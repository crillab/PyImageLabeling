from PyQt6.QtWidgets import QDialog, QSlider, QFormLayout, QDialogButtonBox, QSpinBox, QLabel, QHBoxLayout, QVBoxLayout, QComboBox
from PyQt6.QtCore import Qt

from PyImageLabeling.model.Utils import Utils

class MagicPenSetting(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Magic Pen Settings")
        self.resize(500, 500)

        self.tolerance = Utils.load_parameters()["magic_pen"]["tolerance"] 
        self.max_pixels = Utils.load_parameters()["magic_pen"]["max_pixels"]
        self.method = Utils.load_parameters()["magic_pen"]["method"]

        layout = QVBoxLayout()
        
        
        #########################################################################################################
        
        form_layout = QHBoxLayout()
        tolerance_label = QLabel("Tolerance (percentage):")
        layout.addWidget(tolerance_label)
        layout.setSpacing(10)
        # Tolerance slider and spinbox
        self.tolerance_slider = QSlider(Qt.Orientation.Horizontal)
        self.tolerance_slider.setRange(0, 100)
        self.tolerance_slider.setValue(self.tolerance)
        self.tolerance_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.tolerance_slider.setTickInterval(10)

        self.tolerance_spinbox = QSpinBox()
        self.tolerance_spinbox.setRange(0, 100)
        self.tolerance_spinbox.setValue(self.tolerance)

        # Connect both ways to keep them synchronized
        self.tolerance_spinbox.valueChanged.connect(self.tolerance_slider.setValue)
        self.tolerance_slider.valueChanged.connect(self.tolerance_spinbox.setValue)
        
        # Update internal values when sliders change
        self.tolerance_slider.valueChanged.connect(self.update_tolerance)
        self.tolerance_spinbox.valueChanged.connect(self.update_tolerance)

        form_layout.addWidget(self.tolerance_slider)
        form_layout.addWidget(self.tolerance_spinbox)

        layout.addLayout(form_layout)
        
        #########################################################################################################

        # Points limit setting
        points_limit_label = QLabel("Maximum number of pixels (integer):")
        layout.addWidget(points_limit_label)

        points_slider_layout = QHBoxLayout()
        self.points_limit_slider = QSlider(Qt.Orientation.Horizontal)
        self.points_limit_slider.setRange(5000, 500000)
        self.points_limit_slider.setTickInterval(50000)
        self.points_limit_slider.setValue(self.max_pixels)

        self.points_limit_spinbox = QSpinBox()
        self.points_limit_spinbox.setRange(5000, 500000)
        self.points_limit_spinbox.setValue(self.max_pixels)
        self.points_limit_spinbox.setSingleStep(5000)

        # Connect both ways to keep them synchronized
        self.points_limit_slider.valueChanged.connect(self.points_limit_spinbox.setValue)
        self.points_limit_spinbox.valueChanged.connect(self.points_limit_slider.setValue)
        
        # Update internal values when sliders change
        self.points_limit_slider.valueChanged.connect(self.update_max_pixels)
        self.points_limit_spinbox.valueChanged.connect(self.update_max_pixels)

        points_slider_layout.addWidget(self.points_limit_slider)
        points_slider_layout.addWidget(self.points_limit_spinbox)

        layout.addLayout(points_slider_layout)
        
        #########################################################################################################

        method_label = QLabel("Method:")
        layout.addWidget(method_label)
        
        self.method_combobox = QComboBox()
        self.method_combobox.addItem('RGB AVG')
        self.method_combobox.addItem('RGB MIN')
        self.method_combobox.addItem('HSV AVG')
        self.method_combobox.addItem('HSV MIN')
        self.method_combobox.addItem('HSV SPE')
        
        self.method_combobox.setCurrentText(self.method)
        self.method_combobox.currentTextChanged.connect(self.update_method)

        layout.addWidget(self.method_combobox)
        
        
        #########################################################################################################
        method_label = QLabel(None)
        layout.addWidget(method_label)

        # Buttons
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.setLayout(layout)

    def update_tolerance(self, value):
        """Update internal tolerance value when slider changes"""
        self.tolerance = value

    def update_max_pixels(self, value):
        """Update internal max points value when slider changes"""
        self.max_pixels = value

    def update_method(self, value):
        """Update method when the combobox changes"""
        self.method = value

    def accept(self):
        """Override accept to ensure settings are updated before closing"""
        # Update internal values one final time
        self.tolerance, self.max_pixels, self.method = self.tolerance_slider.value(), self.points_limit_slider.value(), self.method_combobox.currentText()
        data = Utils.load_parameters()
        data["magic_pen"]["tolerance"], data["magic_pen"]["max_pixels"], data["magic_pen"]["method"] = self.tolerance, self.max_pixels, self.method
        Utils.save_parameters(data)    
        return super().accept()