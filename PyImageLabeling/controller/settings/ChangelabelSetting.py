from PyQt6.QtWidgets import (
    QDialog, QSlider, QFormLayout, QDialogButtonBox,
    QSpinBox, QLabel, QHBoxLayout, QVBoxLayout,
    QComboBox, QGroupBox
)
from PyQt6.QtCore import Qt
from PyImageLabeling.model.Utils import Utils


class ChangeLabelSetting(QDialog):
    def __init__(self, parent, model):
        super().__init__(parent)
        self.setWindowTitle("Change Label Settings")
        self.resize(400, 300)

        self.model = model

        # Load parameters (create defaults if missing)
        data = Utils.load_parameters()
        params = data.get("change_label", {})

        self.max_pixels = params.get("max_pixels", 200000)
        self.target_label_id = params.get("target_label_id", None)

        layout = QVBoxLayout()

        # -------------------------------------------------
        # Target Label Group
        # -------------------------------------------------
        target_group = QGroupBox("Target Label")
        target_layout = QVBoxLayout()

        target_label = QLabel("Select target label:")
        target_layout.addWidget(target_label)

        self.target_label_combobox = QComboBox()

        self.label_id_map = {}
        for label_id, label_item in self.model.get_label_items().items():
            text = f"{label_item.get_name()} (id={label_id})"
            self.label_id_map[text] = label_id
            self.target_label_combobox.addItem(text)

            if label_id == self.target_label_id:
                self.target_label_combobox.setCurrentText(text)

        self.target_label_combobox.currentTextChanged.connect(
            self.update_target_label
        )

        target_layout.addWidget(self.target_label_combobox)
        target_group.setLayout(target_layout)
        layout.addWidget(target_group)

        # -------------------------------------------------
        # Max Pixels Group
        # -------------------------------------------------
        max_pixels_group = QGroupBox("Max Pixels")
        max_pixels_layout = QVBoxLayout()

        max_pixels_label = QLabel("Maximum number of pixels:")
        max_pixels_layout.addWidget(max_pixels_label)

        slider_layout = QHBoxLayout()

        self.max_pixels_slider = QSlider(Qt.Orientation.Horizontal)
        self.max_pixels_slider.setRange(5000, 500000)
        self.max_pixels_slider.setTickInterval(50000)
        self.max_pixels_slider.setValue(self.max_pixels)

        self.max_pixels_spinbox = QSpinBox()
        self.max_pixels_spinbox.setRange(5000, 500000)
        self.max_pixels_spinbox.setSingleStep(5000)
        self.max_pixels_spinbox.setValue(self.max_pixels)

        self.max_pixels_slider.valueChanged.connect(self.max_pixels_spinbox.setValue)
        self.max_pixels_spinbox.valueChanged.connect(self.max_pixels_slider.setValue)
        self.max_pixels_slider.valueChanged.connect(self.update_max_pixels)

        slider_layout.addWidget(self.max_pixels_slider)
        slider_layout.addWidget(self.max_pixels_spinbox)

        max_pixels_layout.addLayout(slider_layout)
        max_pixels_group.setLayout(max_pixels_layout)
        layout.addWidget(max_pixels_group)

        # -------------------------------------------------
        # Buttons
        # -------------------------------------------------
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.setLayout(layout)

    # -------------------------------------------------
    # Updates
    # -------------------------------------------------
    def update_target_label(self, text):
        self.target_label_id = self.label_id_map.get(text)

    def update_max_pixels(self, value):
        self.max_pixels = value

    # -------------------------------------------------
    # Save
    # -------------------------------------------------
    def accept(self):
        data = Utils.load_parameters()

        if "change_label" not in data:
            data["change_label"] = {}

        data["change_label"]["max_pixels"] = self.max_pixels
        data["change_label"]["target_label_id"] = self.target_label_id

        Utils.save_parameters(data)
        super().accept()
