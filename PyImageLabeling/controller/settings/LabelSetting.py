from PyQt6.QtWidgets import QComboBox, QPushButton, QHBoxLayout, QColorDialog, QDialog, QSlider, QFormLayout, QDialogButtonBox, QSpinBox

from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt
import random

class LabelSetting(QDialog):

    def __init__(self, parent, name=None, labeling_mode=None, color=None):
        super().__init__(parent)

        labeling_mode_pixel = parent.view.config["labeling_bar"]["pixel"]["name_view"]
        labeling_mode_geometric = parent.view.config["labeling_bar"]["geometric"]["name_view"]
        automatic_name = "label "+str(parent.view.controller.model.get_static_label_id()+1)

        self.name = automatic_name if name is None else name
        self.color = QColor(random.choice(QColor.colorNames())) if color is None else color
        self.labeling_mode = labeling_mode_pixel if labeling_mode is None else labeling_mode

        self.setWindowTitle("Label Setting")
        
        layout = QFormLayout()
        
        label_layout = QHBoxLayout()
        
        self.label_combo = QComboBox()
        self.label_combo.setEditable(True)
        self.label_combo.setPlaceholderText("Enter new label or select existing")
        
        # Populate combo box with saved labels
        self.label_combo.addItem("")  # Empty option for new labels
        #for label in self.label_manager.get_all_labels():
        #    self.label_combo.addItem(label)
            
        # Set current label if provided
        #if self.label:
        #    index = self.label_combo.findText(self.label)
        #    if index >= 0:
        #        self.label_combo.setCurrentIndex(index)
        #    else:
        #        self.label_combo.setCurrentText(self.label)
        self.label_combo.setCurrentText(self.name)

        self.label_combo.currentTextChanged.connect(self.name_update)
        label_layout.addWidget(self.label_combo)
        
        layout.addRow("Label:", label_layout)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems([labeling_mode_pixel, labeling_mode_geometric])
        self.mode_combo.setCurrentText(self.labeling_mode)
        self.mode_combo.currentTextChanged.connect(self.mode_update)
        layout.addRow("Labeling Mode:", self.mode_combo)

        # Color selection
        self.color_button = QPushButton("Choose Color")
        self.color_button.clicked.connect(self.select_color)
        self.color_update(self.color)  
        layout.addRow("Color:", self.color_button)
        
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept) 
        self.buttons.rejected.connect(self.reject)
        layout.addRow(self.buttons)
        
        self.setLayout(layout)

    def name_update(self, name):
        self.name = name

    def mode_update(self, labeling_mode):
        self.labeling_mode = labeling_mode

    def color_update(self, color):
        """Update color button appearance to show current color"""
        self.color = color
        color_style = f"background-color: rgb({self.color.red()}, {self.color.green()}, {self.color.blue()}); color: {'white' if self.color.lightness() < 128 else 'black'};"
        self.color_button.setStyleSheet(color_style)
        self.color_button.setText(f"Color: {self.color.name()}")
        
    def select_color(self):
        color = QColorDialog.getColor(initial=self.color)
        if color.isValid(): self.color_update(color)

    def accept(self):
        """Override accept to ensure settings are updated before closing"""
        self.name = self.label_combo.currentText()
        self.labeling_mode = self.mode_combo.currentText()
        return super().accept()

   