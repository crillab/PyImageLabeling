from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
)
from PyQt6.QtCore import Qt, QPoint


class ContourFillingApplyCancel(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint)
        self.setObjectName("apply_cancel_bar")
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
    
