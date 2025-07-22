
from PyQt6.QtWidgets import QDialog, QSlider, QFormLayout, QDialogButtonBox, QSpinBox, QLabel, QHBoxLayout, QVBoxLayout
from PyQt6.QtCore import Qt

class MagicPenSetting(QDialog):
    def __init__(self, parent, current_tolerance=50, current_max_points=500000):
        super().__init__(parent)
        self.setWindowTitle("Magic Pen Settings")

        self.tolerance = current_tolerance
        self.max_point = current_max_points

        layout = QVBoxLayout()
        form_layout = QFormLayout()

        # Tolerance slider and spinbox
        self.tolerance_slider = QSlider(Qt.Orientation.Horizontal)
        self.tolerance_slider.setRange(0, 100)
        self.tolerance_slider.setValue(self.tolerance)
        self.tolerance_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.tolerance_slider.setTickInterval(10)

        self.tolerance_spinbox = QSpinBox()
        self.tolerance_spinbox.setRange(0, 100)
        self.tolerance_spinbox.setValue(self.tolerance)

        self.tolerance_spinbox.valueChanged.connect(self.tolerance_slider.setValue)
        self.tolerance_slider.valueChanged.connect(self.tolerance_spinbox.setValue)

        form_layout.addRow("Color Tolerance:", self.tolerance_slider)
        form_layout.addRow("Value:", self.tolerance_spinbox)

        # Help text
        tolerance_help = QLabel("Lower = precise matching\nHigher = broader fill area")
        tolerance_help.setStyleSheet("color: #666; font-style: italic;")
        form_layout.addRow("", tolerance_help)

        layout.addLayout(form_layout)

        # Points limit setting
        points_limit_label = QLabel("Max Fill Points:")
        layout.addWidget(points_limit_label)

        points_slider_layout = QHBoxLayout()
        self.points_limit_slider = QSlider(Qt.Orientation.Horizontal)
        self.points_limit_slider.setRange(5000, 500000)
        self.points_limit_slider.setTickInterval(50000)
        self.points_limit_slider.setValue(self.max_point)

        self.points_limit_spinbox = QSpinBox()
        self.points_limit_spinbox.setRange(5000, 500000)
        self.points_limit_spinbox.setValue(self.max_point)
        self.points_limit_spinbox.setSingleStep(5000)

        self.points_limit_slider.valueChanged.connect(self.points_limit_spinbox.setValue)
        self.points_limit_spinbox.valueChanged.connect(self.points_limit_slider.setValue)

        points_slider_layout.addWidget(self.points_limit_slider)
        points_slider_layout.addWidget(self.points_limit_spinbox)

        layout.addLayout(points_slider_layout)

        points_limit_help = QLabel("Higher = larger areas but more memory usage")
        points_limit_help.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(points_limit_help)

        # Buttons
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.setLayout(layout)

    def get_settings(self):
        return {
            "tolerance": self.tolerance_slider.value(),
            "max_points": self.points_limit_spinbox.value()
        }
    
    def accept(self):
        return super().accept()
