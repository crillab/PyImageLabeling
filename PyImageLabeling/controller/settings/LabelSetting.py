from PyQt6.QtWidgets import QComboBox, QPushButton, QHBoxLayout, QColorDialog, QDialog, QSlider, QFormLayout, QDialogButtonBox, QSpinBox, QFileDialog

from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt, QFileInfo
import random

from PyImageLabeling.model.Utils import Utils

import os
import shutil

class LabelSetting(QDialog):

    def __init__(self, parent, name=None, labeling_mode=None, color=None):
        super().__init__(parent)

        labeling_mode_pixel = parent.view.config["labeling_bar"]["pixel"]["name_view"]
        labeling_mode_geometric = parent.view.config["labeling_bar"]["geometric"]["name_view"]
        automatic_name = "label "+str(parent.view.controller.model.get_static_label_id()+1)

        self.name = automatic_name if name is None else name
        self.color = QColor(random.choice(QColor.colorNames())) if color is None else color
        self.labeling_mode = labeling_mode_pixel if labeling_mode is None else labeling_mode
        self.importdata = False
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
        self.mode_combo.addItems([labeling_mode_pixel,labeling_mode_geometric]) #add later:  labeling_mode_geometric
        self.mode_combo.setCurrentText(self.labeling_mode)
        self.mode_combo.currentTextChanged.connect(self.mode_update)
        layout.addRow("Labeling Mode:", self.mode_combo)

        #import label image button
        self.import_button = QPushButton("Import existing Label")
        self.import_button.clicked.connect(self.import_data)
        self.import_button.setVisible(True)  # Initially hidden
        layout.addRow("", self.import_button) 

        # Color selection
        self.color_button = QPushButton("Choose Color")
        self.color_button.clicked.connect(self.select_color)
        self.color_update(self.color)  
        layout.addRow("Color:", self.color_button)

        # Thickness selection (only for geometric mode)
        self.thickness_spin = QSpinBox()
        self.thickness_spin.setRange(1, 100)
        self.thickness_spin.setValue(Utils.load_parameters()["geometric_shape"]["thickness"])
        self.thickness_spin.setVisible(self.labeling_mode == labeling_mode_geometric)
        layout.addRow("Thickness:", self.thickness_spin)
        self.thickness_label = layout.labelForField(self.thickness_spin)
        
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept) 
        self.buttons.rejected.connect(self.reject)
        layout.addRow(self.buttons)
        
        self.setLayout(layout)
        self.mode_update(self.labeling_mode)

    def name_update(self, name):
        self.name = name

    def mode_update(self, labeling_mode):
        self.labeling_mode = labeling_mode
        if labeling_mode == self.parent().view.config["labeling_bar"]["pixel"]["name_view"]:
            self.import_button.setVisible(True)
            self.thickness_spin.setVisible(False)
            self.thickness_label.setVisible(False)
        else:
            self.import_button.setVisible(False)
            self.thickness_spin.setVisible(True)
            self.thickness_label.setVisible(True)

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
        self.process_import_data()
        if self.labeling_mode == self.parent().view.config["labeling_bar"]["geometric"]["name_view"]:
            data = Utils.load_parameters()
            data["geometric_shape"]["thickness"] = self.thickness_spin.value()
            Utils.save_parameters(data)
        return super().accept()
    
    def import_data(self):
        """Import label data from a folder and copy to save directory with renamed files"""
        
        # Step 1: Select source folder with label data
        source_dialog = QFileDialog()
        source_dialog.setFileMode(QFileDialog.FileMode.Directory)
        source_dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)  
        source_dialog.setOption(QFileDialog.Option.ShowDirsOnly, False)  
        source_dialog.setOption(QFileDialog.Option.ReadOnly, False)  
        source_dialog.setWindowTitle("Select folder containing label data to import")

        def check_selection(path):
                info = QFileInfo(path)
                if info.isFile():
                    self.default_path = info.absolutePath()
                    data = Utils.load_parameters()
                    data["save"]["path"] = self.default_path
                    Utils.save_parameters(data)
                    source_dialog.done(0)  
                    self.parent().view.controller.error_message("Load Error", "You can not select a file, chose a folder !")
                    self.import_data()
                    
        source_dialog.currentChanged.connect(check_selection)
        
        if source_dialog.exec() != QFileDialog.DialogCode.Accepted:
            return
            
        self.source_directory = source_dialog.selectedFiles()[0]
        if not self.source_directory:
            return
        
        # Step 2: Select save/destination folder
        if self.parent().view.controller.model.save_directory == "":
            save_dialog = QFileDialog()
            save_dialog.setFileMode(QFileDialog.FileMode.Directory)
            save_dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
            save_dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
            save_dialog.setWindowTitle("Select destination folder to save imported labels")
            
            if save_dialog.exec() != QFileDialog.DialogCode.Accepted:
                return
                
            self.destination_directory = save_dialog.selectedFiles()[0]
            if not self.destination_directory:
                return
            self.parent().view.controller.model.save_directory = self.destination_directory
        else :
            self.destination_directory = self.parent().view.controller.model.save_directory

        self.import_button.setText("Import Ready")


    def process_import_data(self):
        try:
            # Get label ID for renaming
            label_id = self.parent().view.controller.model.get_static_label_id()
            
            # Ensure destination directory exists
            os.makedirs(self.destination_directory, exist_ok=True)
            
            # Copy and rename all files directly to destination
            for filename in os.listdir(self.source_directory):
                source_file_path = os.path.join(self.source_directory, filename)
                
                # Skip directories
                if os.path.isdir(source_file_path):
                    continue
                
                # Create new filename with label extension
                name, ext = os.path.splitext(filename)
                new_filename = f"{name}.label.{label_id}.png"
                dest_file_path = os.path.join(self.destination_directory, new_filename)
                
                # Copy file with new name directly to destination
                shutil.copy2(source_file_path, dest_file_path)
                self.importdata = True

        except Exception as e:
            print(f"Error importing labels: {str(e)}")

   