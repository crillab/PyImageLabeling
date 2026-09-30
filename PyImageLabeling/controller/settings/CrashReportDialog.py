from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QVBoxLayout, QHBoxLayout, QLabel,
    QPlainTextEdit, QPushButton, QMessageBox, QApplication,
)
from PyQt6.QtGui import QGuiApplication

from PyImageLabeling.model.SAM import crash_report


class CrashReportDialog(QDialog):
    """Shows the crash summary and offers a one-click copy for bug reports."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Crash Report & Logs")
        self.setMinimumSize(760, 560)

        layout = QVBoxLayout(self)

        header = QLabel(
            "Native crashes leave no Python traceback, so this report pairs "
            "the fault log with the actions logged just before it.")
        header.setWordWrap(True)
        layout.addWidget(header)

        self.text_edit = QPlainTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.NoWrap)
        self.text_edit.setPlainText(crash_report.build_report())
        layout.addWidget(self.text_edit)

        buttons = QHBoxLayout()
        self.copy_btn = QPushButton("Copy to clipboard")
        self.copy_btn.clicked.connect(self._copy)
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._refresh)
        self.folder_btn = QPushButton("Open log folder")
        self.folder_btn.clicked.connect(self._open_folder)
        self.clear_btn = QPushButton("Clear logs")
        self.clear_btn.clicked.connect(self._clear)
        for b in (self.copy_btn, self.refresh_btn, self.folder_btn,
                  self.clear_btn):
            buttons.addWidget(b)
        buttons.addStretch()
        layout.addLayout(buttons)

        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.buttons.rejected.connect(self.reject)
        self.buttons.accepted.connect(self.accept)
        layout.addWidget(self.buttons)

    def report_text(self):
        return self.text_edit.toPlainText()

    def _refresh(self):
        self.text_edit.setPlainText(crash_report.build_report())

    def _copy(self):
        QGuiApplication.clipboard().setText(self.report_text())
        self.copy_btn.setText("Copied")
        self.copy_btn.setEnabled(False)

    def _open_folder(self):
        path = crash_report.open_log_folder()
        if path is None:
            QMessageBox.information(
                self, "Logs", f"Logs are in:\n{path or '?'}")

    def _clear(self):
        answer = QMessageBox.question(
            self, "Clear logs",
            "Delete the crash and state logs?\n"
            "They are only diagnostic; annotations are untouched.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return
        removed = crash_report.clear_logs()
        self._refresh()
        QMessageBox.information(
            self, "Logs cleared", f"Removed {len(removed)} file(s).")


def show(parent=None):
    dialog = CrashReportDialog(parent)
    QApplication.restoreOverrideCursor()
    dialog.exec()
    return dialog.report_text()