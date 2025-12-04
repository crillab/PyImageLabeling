from PyQt6.QtWidgets import QDialog, QSlider, QFormLayout, QDialogButtonBox, QSpinBox, QLabel, QHBoxLayout, QVBoxLayout, QComboBox, QGroupBox
from PyQt6.QtCore import Qt
from PyImageLabeling.model.Utils import Utils

class MagicPenSetting(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Magic Pen Settings")
        self.resize(500, 500)
        params = Utils.load_parameters()["magic_pen"]
        self.tolerance = params["tolerance"]
        self.max_pixels = params["max_pixels"]
        self.method = params["method"]
        self.logic = params["logic"]

        layout = QVBoxLayout()

        # Tolerance Group
        tolerance_group = QGroupBox("Tolerance")
        tolerance_layout = QVBoxLayout()
        tolerance_label = QLabel("Tolerance (percentage):")
        tolerance_layout.addWidget(tolerance_label)

        tolerance_slider_layout = QHBoxLayout()
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
        self.tolerance_slider.valueChanged.connect(self.update_tolerance)
        self.tolerance_spinbox.valueChanged.connect(self.update_tolerance)

        tolerance_slider_layout.addWidget(self.tolerance_slider)
        tolerance_slider_layout.addWidget(self.tolerance_spinbox)
        tolerance_layout.addLayout(tolerance_slider_layout)
        tolerance_group.setLayout(tolerance_layout)
        layout.addWidget(tolerance_group)

        # Max Pixels Group
        max_pixels_group = QGroupBox("Max Pixels")
        max_pixels_layout = QVBoxLayout()
        max_pixels_label = QLabel("Maximum number of pixels (integer):")
        max_pixels_layout.addWidget(max_pixels_label)

        max_pixels_slider_layout = QHBoxLayout()
        self.points_limit_slider = QSlider(Qt.Orientation.Horizontal)
        self.points_limit_slider.setRange(5000, 500000)
        self.points_limit_slider.setTickInterval(50000)
        self.points_limit_slider.setValue(self.max_pixels)

        self.points_limit_spinbox = QSpinBox()
        self.points_limit_spinbox.setRange(5000, 500000)
        self.points_limit_spinbox.setValue(self.max_pixels)
        self.points_limit_spinbox.setSingleStep(5000)

        self.points_limit_slider.valueChanged.connect(self.points_limit_spinbox.setValue)
        self.points_limit_spinbox.valueChanged.connect(self.points_limit_slider.setValue)
        self.points_limit_slider.valueChanged.connect(self.update_max_pixels)
        self.points_limit_spinbox.valueChanged.connect(self.update_max_pixels)

        max_pixels_slider_layout.addWidget(self.points_limit_slider)
        max_pixels_slider_layout.addWidget(self.points_limit_spinbox)
        max_pixels_layout.addLayout(max_pixels_slider_layout)
        max_pixels_group.setLayout(max_pixels_layout)
        layout.addWidget(max_pixels_group)

        # Method Group
        method_group = QGroupBox("Method")
        method_layout = QVBoxLayout()
        method_label = QLabel("Select method:")
        method_layout.addWidget(method_label)

        self.method_combobox = QComboBox()
        self.method_combobox.addItems(["RGB", "HSV"])
        current_index = self.method_combobox.findText(self.method)
        if current_index >= 0:
            self.method_combobox.setCurrentIndex(current_index)
        self.method_combobox.currentTextChanged.connect(self.update_method)
        method_layout.addWidget(self.method_combobox)
        method_group.setLayout(method_layout)
        layout.addWidget(method_group)

        # Logic Group
        logic_group = QGroupBox("Logic")
        logic_layout = QVBoxLayout()
        logic_label = QLabel("Select logic:")
        logic_layout.addWidget(logic_label)

        self.logic_labeling_combobox = QComboBox()
        self.logic_labeling_combobox.addItems(["Pen logic", "All color logic"])
        current_index = self.logic_labeling_combobox.findText(self.logic)
        if current_index >= 0:
            self.logic_labeling_combobox.setCurrentIndex(current_index)
        self.logic_labeling_combobox.currentTextChanged.connect(self.update_logic)
        logic_layout.addWidget(self.logic_labeling_combobox)
        logic_group.setLayout(logic_layout)
        layout.addWidget(logic_group)

        # Buttons
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.setLayout(layout)

    def update_tolerance(self, value):
        self.tolerance = value

    def update_max_pixels(self, value):
        self.max_pixels = value

    def update_method(self, value):
        self.method = value

    def update_logic(self, value):
        self.logic = value

    def accept(self):
        self.tolerance = self.tolerance_slider.value()
        self.max_pixels = self.points_limit_slider.value()
        self.method = self.method_combobox.currentText()
        self.logic = self.logic_labeling_combobox.currentText()

        data = Utils.load_parameters()
        data["magic_pen"]["tolerance"] = self.tolerance
        data["magic_pen"]["max_pixels"] = self.max_pixels
        data["magic_pen"]["method"] = self.method
        data["magic_pen"]["logic"] = self.logic
        Utils.save_parameters(data)

        return super().accept()
