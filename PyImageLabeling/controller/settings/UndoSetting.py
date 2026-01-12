from PyQt6.QtWidgets import QCheckBox, QDialog, QSlider, QFormLayout, QDialogButtonBox, QSpinBox, QLabel, QHBoxLayout, QVBoxLayout, QGroupBox
from PyQt6.QtCore import Qt
from PyImageLabeling.model.Utils import Utils

class UndoSetting(QDialog):
    def __init__(self, parent, model):
        super().__init__(parent)
        self.model = model
        self.setWindowTitle("Undo Settings")
        self.resize(500, 150)
        self.depth = Utils.load_parameters()["undo"]["depth"]

        layout = QVBoxLayout()

        # Memory Depth Group
        depth_group = QGroupBox("Memory Depth")
        depth_layout = QVBoxLayout()
        depth_label = QLabel("Set undo memory depth:")
        depth_layout.addWidget(depth_label)

        depth_slider_layout = QHBoxLayout()
        initial_depth = self.ensure_even_value(self.depth)

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

        self.depth_spinbox.valueChanged.connect(self.depth_slider.setValue)
        self.depth_slider.valueChanged.connect(self.depth_spinbox.setValue)
        self.depth_slider.valueChanged.connect(self.update_depth)
        self.depth_spinbox.valueChanged.connect(self.update_depth)

        depth_slider_layout.addWidget(self.depth_slider)
        depth_slider_layout.addWidget(self.depth_spinbox)
        depth_layout.addLayout(depth_slider_layout)
        depth_group.setLayout(depth_layout)
        layout.addWidget(depth_group)

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
        """Update internal depth value when slider changes"""
        self.depth = self.ensure_even_value(value)

    def accept(self):
        """Override accept to ensure settings are updated before closing"""
        self.depth = self.depth_spinbox.value()
        data = Utils.load_parameters()
        data["undo"]["depth"] = self.depth
        Utils.save_parameters(data)
        self.model.get_current_image_item().get_labeling_overlay().resize_undo_deque(self.depth)

        return super().accept()
