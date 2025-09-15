from PyQt6.QtWidgets import QDialog, QSlider, QFormLayout, QDialogButtonBox, QSpinBox, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QRect, QPoint

from model.Utils import Utils

class ContourFillingApplyCancel(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        #self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setObjectName("apply_cancel_bar")
        #self.setGeometry(QRect(100,100, 300, 70))
        self.move(parent.mapToGlobal(QPoint(10,10)))
        layout = QVBoxLayout()
        form_layout = QFormLayout()

        # Help text
        tolerance_help = QLabel("Click on the area to fill and apply")
        form_layout.addRow("", tolerance_help)

        layout.addLayout(form_layout)

        # Buttons
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        for button in self.buttons.buttons():
            button.setObjectName("dialog")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.setLayout(layout)

    def accept(self):
        """Override accept to ensure settings are updated before closing"""
        # Update internal values one final time
        return super().accept()
    
