from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
    QGroupBox, QCheckBox, QFormLayout, QDialogButtonBox, QSpinBox, QFileDialog
)
from PyQt6.QtCore import Qt
import os

class GlobalOptionDialog(QDialog):
    def __init__(self, parent, model):
        super().__init__(parent)
        self.parent = parent
        self.model = model

        # Store original settings
        self.original_autosave_enabled = self.model.autosave_enabled
        self.original_autosave_interval = self.model.autosave_interval
        self.original_save_directory = self.model.save_directory

        # Current settings (will be modified by UI)
        self.autosave_enabled = self.model.autosave_enabled
        self.autosave_interval_minutes = self.model.autosave_interval // 60000  # Convert ms to minutes
        self.save_directory = self.model.save_directory

        self.setWindowTitle("Global Options")
        self.setModal(True)
        self.resize(600, 400)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Auto-save Group
        autosave_group = QGroupBox("Auto-save Settings")
        autosave_layout = QFormLayout()

        # Enable/Disable Auto-save
        self.autosave_checkbox = QCheckBox("Enable automatic saving")
        self.autosave_checkbox.setChecked(self.autosave_enabled)
        self.autosave_checkbox.stateChanged.connect(self.on_autosave_enabled_changed)
        autosave_layout.addRow("Auto-save:", self.autosave_checkbox)

        # Auto-save Interval (in minutes)
        interval_layout = QHBoxLayout()
        self.interval_spinbox = QSpinBox()
        self.interval_spinbox.setMinimum(1)
        self.interval_spinbox.setMaximum(60)
        self.interval_spinbox.setValue(self.autosave_interval_minutes)
        self.interval_spinbox.setSuffix(" minutes")
        self.interval_spinbox.setEnabled(self.autosave_enabled)
        self.interval_spinbox.valueChanged.connect(self.on_interval_changed)
        
        interval_layout.addWidget(self.interval_spinbox)
        interval_layout.addStretch()
        
        autosave_layout.addRow("Interval:", interval_layout)

        # Auto-save info label
        self.autosave_info_label = QLabel()
        self.update_autosave_info()
        autosave_layout.addRow("", self.autosave_info_label)

        autosave_group.setLayout(autosave_layout)
        layout.addWidget(autosave_group)

        # Save Directory Group
        save_dir_group = QGroupBox("Save Directories")
        save_dir_layout = QFormLayout()

        # Main Save Directory
        main_dir_layout = QHBoxLayout()
        self.save_dir_line = QLineEdit(self.save_directory)
        self.save_dir_line.setReadOnly(True)
        main_dir_layout.addWidget(self.save_dir_line)
        
        self.browse_save_btn = QPushButton("Browse...")
        self.browse_save_btn.clicked.connect(self.browse_save_directory)
        main_dir_layout.addWidget(self.browse_save_btn)
        
        save_dir_layout.addRow("Save Directory:", main_dir_layout)

        # Save Directory Info
        save_dir_info = QLabel("This is where your labels and annotations are saved.")
        save_dir_info.setWordWrap(True)
        save_dir_info.setStyleSheet("color: gray; font-size: 10px;")
        save_dir_layout.addRow("", save_dir_info)

        # Copy Save Directory (for Save Copy feature)
        copy_dir_layout = QHBoxLayout()
        self.copy_dir_line = QLineEdit()
        self.copy_dir_line.setPlaceholderText("Optional: Select directory for 'Save Copy'")
        self.copy_dir_line.setReadOnly(True)
        copy_dir_layout.addWidget(self.copy_dir_line)
        
        self.browse_copy_btn = QPushButton("Browse...")
        self.browse_copy_btn.clicked.connect(self.browse_copy_directory)
        copy_dir_layout.addWidget(self.browse_copy_btn)
        
        self.clear_copy_btn = QPushButton("Clear")
        self.clear_copy_btn.clicked.connect(self.clear_copy_directory)
        copy_dir_layout.addWidget(self.clear_copy_btn)
        
        save_dir_layout.addRow("Copy Directory:", copy_dir_layout)

        # Copy Directory Info
        copy_dir_info = QLabel("Optional: Pre-configure directory for 'Save Copy' operations.")
        copy_dir_info.setWordWrap(True)
        copy_dir_info.setStyleSheet("color: gray; font-size: 10px;")
        save_dir_layout.addRow("", copy_dir_info)

        # Quick Actions
        actions_layout = QHBoxLayout()
        
        self.open_save_dir_btn = QPushButton("Open Save Directory")
        self.open_save_dir_btn.clicked.connect(self.open_save_directory)
        self.open_save_dir_btn.setEnabled(bool(self.save_directory))
        actions_layout.addWidget(self.open_save_dir_btn)
        
        self.save_copy_now_btn = QPushButton("Save Copy Now")
        self.save_copy_now_btn.clicked.connect(self.save_copy_now)
        self.save_copy_now_btn.setEnabled(bool(self.copy_dir_line.text()))
        actions_layout.addWidget(self.save_copy_now_btn)
        
        actions_layout.addStretch()
        save_dir_layout.addRow("Actions:", actions_layout)

        save_dir_group.setLayout(save_dir_layout)
        layout.addWidget(save_dir_group)

        layout.addStretch()

        # Dialog Buttons
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.Apply
        )
        self.buttons.accepted.connect(self.apply_and_accept)
        self.buttons.rejected.connect(self.reject)
        self.buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.apply_changes)
        layout.addWidget(self.buttons)

        self.setLayout(layout)

    def on_autosave_enabled_changed(self, state):
        self.autosave_enabled = state == Qt.CheckState.Checked.value
        self.interval_spinbox.setEnabled(self.autosave_enabled)
        self.update_autosave_info()

    def on_interval_changed(self, value):
        self.autosave_interval_minutes = value
        self.update_autosave_info()

    def update_autosave_info(self):
        if self.autosave_enabled:
            info_text = f"Project will auto-save every {self.autosave_interval_minutes} minute(s)"
            self.autosave_info_label.setStyleSheet("color: green;")
        else:
            info_text = "Auto-save is disabled"
            self.autosave_info_label.setStyleSheet("color: gray;")
        self.autosave_info_label.setText(info_text)

    def browse_save_directory(self):
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Save Directory",
            self.save_directory if self.save_directory else ""
        )
        if directory:
            self.save_directory = directory
            self.save_dir_line.setText(directory)
            self.open_save_dir_btn.setEnabled(True)
            self.parent.statusBar().showMessage(f"Save directory set to: {directory}")

    def browse_copy_directory(self):
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Copy Directory",
            self.copy_dir_line.text() if self.copy_dir_line.text() else ""
        )
        if directory:
            self.copy_dir_line.setText(directory)
            self.save_copy_now_btn.setEnabled(True)
            self.parent.statusBar().showMessage(f"Copy directory set to: {directory}")

    def clear_copy_directory(self):
        self.copy_dir_line.clear()
        self.save_copy_now_btn.setEnabled(False)
        self.parent.statusBar().showMessage("Copy directory cleared")

    def open_save_directory(self):
        if self.save_directory and os.path.exists(self.save_directory):
            import platform
            import subprocess
            
            system = platform.system()
            try:
                if system == "Windows":
                    os.startfile(self.save_directory)
                elif system == "Darwin":  # macOS
                    subprocess.run(["open", self.save_directory])
                else:  # Linux and others
                    subprocess.run(["xdg-open", self.save_directory])
                self.parent.statusBar().showMessage(f"Opened: {self.save_directory}")
            except Exception as e:
                self.parent.statusBar().showMessage(f"Error opening directory: {str(e)}")
        else:
            self.parent.statusBar().showMessage("Save directory does not exist")

    def save_copy_now(self):
        copy_dir = self.copy_dir_line.text()
        if copy_dir and os.path.exists(copy_dir):
            try:
                self.model.save_copy(copy_dir)
                self.parent.statusBar().showMessage(f"Project saved to: {copy_dir}")
            except Exception as e:
                self.parent.statusBar().showMessage(f"Error saving copy: {str(e)}")
        else:
            self.parent.statusBar().showMessage("Invalid copy directory")

    def apply_changes(self):
        """Apply changes without closing dialog"""
        # Apply auto-save settings
        self.model.set_autosave_enabled(self.autosave_enabled)
        self.model.set_autosave_interval(self.autosave_interval_minutes * 60000)  # Convert minutes to ms
        
        # Apply save directory
        if self.save_directory != self.model.save_directory:
            self.model.save_directory = self.save_directory
            self.parent.statusBar().showMessage(f"Save directory updated to: {self.save_directory}")
        
        self.parent.statusBar().showMessage("Settings applied successfully")

    def apply_and_accept(self):
        """Apply changes and close dialog"""
        self.apply_changes()
        self.accept()

    def reject(self):
        """Restore original settings when canceling"""
        self.model.set_autosave_enabled(self.original_autosave_enabled)
        self.model.set_autosave_interval(self.original_autosave_interval)
        self.model.save_directory = self.original_save_directory
        super().reject()