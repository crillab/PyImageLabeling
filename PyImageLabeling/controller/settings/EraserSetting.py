from PyQt6.QtWidgets import QCheckBox, QDialog, QSlider, QFormLayout, QDialogButtonBox, QSpinBox, QLabel, QHBoxLayout, QVBoxLayout, QComboBox, QGroupBox
from PyQt6.QtCore import Qt
from PyImageLabeling.model.Utils import Utils

class EraserSetting(QDialog):
    def __init__(self, parent, model):
        super().__init__(parent)
        self.setWindowTitle("Eraser Settings")
        self.resize(500, 150)
        params = Utils.load_parameters()["eraser"]
        self.max_size = int(min(model.get_current_image_item().image_qrectf.width(), model.get_current_image_item().image_qrectf.height()))
        self.min_size = 1
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
        self.radius_group.setVisible(show_controls)

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

    def accept(self):
        """Override accept to ensure settings are updated before closing"""
        self.radius = self.radius_spinbox.value()
        data = Utils.load_parameters()
        data["eraser"]["size"] = self.radius
        data["eraser"]["absolute_mode"] = self.absolute_mode
        data["eraser"]["mode"] = self.eraser_mode
        Utils.save_parameters(data)
        return super().accept()
