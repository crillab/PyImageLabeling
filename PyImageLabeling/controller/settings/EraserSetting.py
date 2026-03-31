from PyQt6.QtWidgets import QCheckBox, QColorDialog, QDialog, QSlider, QPushButton, QFormLayout, QDialogButtonBox, QSpinBox, QLabel, QHBoxLayout, QVBoxLayout, QComboBox, QGroupBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyImageLabeling.model.Utils import Utils

class EraserSetting(QDialog):
    def __init__(self, parent, model):
        super().__init__(parent)
        self.setWindowTitle("Eraser Settings")
        self.resize(500, 150)
        params = Utils.load_parameters()["eraser"]
        self.max_size = int(min(model.get_current_image_item().image_qrectf.width(), model.get_current_image_item().image_qrectf.height()))
        self.min_size = 2
        self.radius = params.get("size", 10)
        self.absolute_mode = params.get("absolute_mode", 0)
        self.eraser_mode = params.get("mode", "original")

        layout = QVBoxLayout()

        # Mode Group
        mode_group = QGroupBox("Eraser Mode")
        mode_layout = QVBoxLayout()
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Original Mode", "Absolute Mode", "Intelligent Mode"])
        mode_map = {"original": 0, "absolute": 1, "intelligent": 2}
        self.mode_combo.setCurrentIndex(mode_map.get(self.eraser_mode, 0))
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        mode_layout.addWidget(self.mode_combo)
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        # Radius Group
        self.radius_group = QGroupBox("Radius")
        radius_layout = QVBoxLayout()
        radius_label = QLabel("Set eraser radius:")
        radius_layout.addWidget(radius_label)

        radius_slider_layout = QHBoxLayout()
        initial_radius = self.ensure_even_value(self.radius)

        self.radius_slider = QSlider(Qt.Orientation.Horizontal)
        self.radius_slider.setRange(self.min_size, self.max_size)
        self.radius_slider.setSingleStep(2)
        self.radius_slider.setValue(initial_radius)
        self.radius_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        tick_interval = max(1, self.max_size // 20)
        self.radius_slider.setTickInterval(tick_interval)

        self.radius_spinbox = QSpinBox()
        self.radius_spinbox.setRange(self.min_size, self.max_size)
        self.radius_spinbox.setSingleStep(2)
        self.radius_spinbox.setValue(initial_radius)

        self.radius_spinbox.valueChanged.connect(self.radius_slider.setValue)
        self.radius_slider.valueChanged.connect(self.radius_spinbox.setValue)
        self.radius_slider.valueChanged.connect(self.update_radius)
        self.radius_spinbox.valueChanged.connect(self.update_radius)

        radius_slider_layout.addWidget(self.radius_slider)
        radius_slider_layout.addWidget(self.radius_spinbox)
        radius_layout.addLayout(radius_slider_layout)
        self.radius_group.setLayout(radius_layout)
        layout.addWidget(self.radius_group)

        # Threshold Group
        self.threshold_group = QGroupBox("Color Tolerance")
        threshold_layout = QVBoxLayout()
        threshold_label = QLabel("Set color tolerance (0-255):")
        threshold_layout.addWidget(threshold_label)

        threshold_slider_layout = QHBoxLayout()
        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setRange(0, 255)
        self.threshold_slider.setValue(params.get("tolerance", 10))
        self.threshold_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.threshold_slider.setTickInterval(32)

        self.threshold_spinbox = QSpinBox()
        self.threshold_spinbox.setRange(0, 255)
        self.threshold_spinbox.setValue(params.get("tolerance", 10))

        self.threshold_slider.valueChanged.connect(self.threshold_spinbox.setValue)
        self.threshold_spinbox.valueChanged.connect(self.threshold_slider.setValue)

        threshold_slider_layout.addWidget(self.threshold_slider)
        threshold_slider_layout.addWidget(self.threshold_spinbox)
        threshold_layout.addLayout(threshold_slider_layout)
        self.threshold_group.setLayout(threshold_layout)
        layout.addWidget(self.threshold_group)

        # Color Picker Group
        self.color_group = QGroupBox("Color to Keep")
        color_layout = QVBoxLayout()
        color_label = QLabel("Select the color to keep (click to pick):")
        color_layout.addWidget(color_label)

        self.color_button = QPushButton()
        self.color_button.setStyleSheet("background-color: rgba(0, 0, 0, 0); border: 1px solid black;")
        self.color_button.clicked.connect(self.pick_color)
        color_layout.addWidget(self.color_button)

        self.selected_color = QColor(0, 0, 0, 0)  # Default: transparent
        self.update_color_button()

        color_layout.addWidget(QLabel("Selected color will be kept; others will be erased."))
        self.color_group.setLayout(color_layout)
        layout.addWidget(self.color_group)

        # Buttons
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.setLayout(layout)
        self.on_mode_changed(self.mode_combo.currentIndex())

    def on_mode_changed(self, index):
        """Show/hide radius and value controls based on selected mode"""
        mode_names = ["original", "absolute", "intelligent"]
        self.eraser_mode = mode_names[index]

        if self.eraser_mode == "absolute":
            self.absolute_mode = 1
        else:
            self.absolute_mode = 0

        show_controls = index in [0, 1]
        show_threshold = index == 2
        show_color = index == 2
        self.radius_group.setVisible(show_controls)
        self.threshold_group.setVisible(show_threshold)
        self.color_group.setVisible(show_color)

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
        """Update internal radius value when slider changes"""
        self.radius = self.ensure_even_value(value)

    def pick_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.selected_color = color
            self.update_color_button()

    def update_color_button(self):
        self.color_button.setStyleSheet(
            f"background-color: {self.selected_color.name()}; "
            "border: 1px solid black; min-height: 30px;"
        )

    def accept(self):
        """Override accept to ensure settings are updated before closing"""
        self.radius = self.radius_spinbox.value()
        data = Utils.load_parameters()
        data["eraser"]["size"] = self.radius
        data["eraser"]["absolute_mode"] = self.absolute_mode
        data["eraser"]["mode"] = self.eraser_mode
        data["eraser"]["tolerance"] = self.threshold_spinbox.value() 
        data["eraser"]["keep_color"] = self.selected_color.name(QColor.NameFormat.HexArgb)
        Utils.save_parameters(data)
        return super().accept()
