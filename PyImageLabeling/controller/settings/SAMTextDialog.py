from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QDoubleSpinBox, QPushButton, QApplication, QSlider,
)
from PyQt6.QtCore import Qt


class SAMTextDialog(QDialog):
    """Text-to-mask, single window.

    Text + Generate, threshold slider (live refilter, no recompute),
    Previous / Next mask, OK (validate) / Cancel (discard).

    The overlay always uses the selected label color and always shows
    exactly what OK will paint. Closing discards the pending preview.
    """

    def __init__(self, parent, model):
        super().__init__(parent)
        self.model = model
        self.setWindowTitle("Text-to-mask (local)")
        self.resize(480, 230)

        layout = QVBoxLayout()

        layout.addWidget(QLabel("Describe the object to mask:"))
        self.text_edit = QLineEdit()
        self.text_edit.setPlaceholderText(
            'ex: "chien rouge à gauche" / "red dog on the left"')
        self.text_edit.returnPressed.connect(self._generate)
        layout.addWidget(self.text_edit)

        # threshold bar: instant refilter of cached zones
        thr_row = QHBoxLayout()
        thr_row.addWidget(QLabel("Threshold:"))
        self.thr_slider = QSlider(Qt.Orientation.Horizontal)
        self.thr_slider.setRange(1, 95)
        self.thr_slider.setValue(15)
        self.thr_slider.setToolTip(
            "Lower = more zones (permissive), "
            "higher = fewer zones (strict). Zones stay the same.")
        self.thr_slider.valueChanged.connect(self._on_slider_changed)
        thr_row.addWidget(self.thr_slider)
        self.thr_spinbox = QDoubleSpinBox()
        self.thr_spinbox.setRange(0.01, 0.95)
        self.thr_spinbox.setSingleStep(0.05)
        self.thr_spinbox.setDecimals(2)
        self.thr_spinbox.setValue(0.15)
        self.thr_spinbox.valueChanged.connect(self._on_spinbox_changed)
        thr_row.addWidget(self.thr_spinbox)
        layout.addLayout(thr_row)

        # candidates row
        cand_row = QHBoxLayout()
        self.prev_btn = QPushButton("Previous")
        self.prev_btn.setToolTip("Show previous zone")
        self.prev_btn.clicked.connect(lambda: self._cycle(-1))
        cand_row.addWidget(self.prev_btn)
        self.next_btn = QPushButton("Next mask")
        self.next_btn.setToolTip("Show next zone")
        self.next_btn.clicked.connect(lambda: self._cycle(1))
        cand_row.addWidget(self.next_btn)
        self.gen_btn = QPushButton("Generate")
        self.gen_btn.setToolTip("Detect zones for the description")
        self.gen_btn.clicked.connect(self._generate)
        cand_row.addWidget(self.gen_btn)
        cand_row.addStretch()
        layout.addLayout(cand_row)

        self.status_label = QLabel(
            "Tip: English nouns work best "
            "('dog' > 'chien'). Positions and colors accept French.")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self._on_ok)
        self.buttons.rejected.connect(self._on_cancel)
        layout.addWidget(self.buttons)

        self.setLayout(layout)

    # ------------------------------------------------------------------
    def _say(self, msg, ok):
        self.status_label.setText(msg)
        self.status_label.setStyleSheet(
            "color: green;" if ok else "color: red;")

    def _busy(self, fn):
        self.setEnabled(False)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            QApplication.processEvents()
            fn()
        finally:
            QApplication.restoreOverrideCursor()
            self.setEnabled(True)

    def _generate(self):
        text = self.text_edit.text().strip()
        if not text:
            self._say("Type a description first.", False)
            return

        def work():
            ok, msg = self.model.sam_text_generate(
                text, self.thr_spinbox.value())
            self._say(msg, ok)

        self._busy(work)

    def _on_slider_changed(self, value):
        self.thr_spinbox.blockSignals(True)
        self.thr_spinbox.setValue(value / 100.0)
        self.thr_spinbox.blockSignals(False)
        self._apply_threshold()

    def _on_spinbox_changed(self, value):
        self.thr_slider.blockSignals(True)
        self.thr_slider.setValue(int(value * 100))
        self.thr_slider.blockSignals(False)
        self._apply_threshold()

    def _apply_threshold(self):
        ok, msg = self.model.sam_text_apply_threshold(
            self.thr_spinbox.value())
        self._say(msg, ok)

    def _cycle(self, step):
        ok, msg = self.model.sam_text_cycle(step)
        self._say(msg, ok)

    def _on_ok(self):
        # validate exactly what is displayed, then close
        self.model.sam_accept_session()
        super().accept()

    def _on_cancel(self):
        self.model.sam_clear_session()
        super().reject()

    def reject(self):
        # X button behaves like Cancel: no orphan preview left behind
        try:
            self.model.sam_clear_session()
        except Exception:
            pass
        super().reject()
