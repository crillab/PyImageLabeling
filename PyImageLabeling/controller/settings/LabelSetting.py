from PyQt6.QtWidgets import (
    QComboBox, QPushButton, QHBoxLayout, QColorDialog, QDialog, QSlider,
    QFormLayout, QDialogButtonBox, QSpinBox, QFileDialog,
    QRadioButton, QLabel, QVBoxLayout, QButtonGroup, QLineEdit, QFrame,
    QProgressDialog,
)

from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt, QFileInfo
import random

from PyImageLabeling.model.Utils import Utils

import os
import shutil
import fnmatch

from PIL import Image
import numpy as np


# ---------------------------------------------------------------------------
# Dialog: choose the source annotation format before importing
# ---------------------------------------------------------------------------

class ImportFormatDialog(QDialog):
    """
    Small dialog shown when the user clicks "Import existing Label".
    Lets them pick one of three annotation formats:
      - Binary mask  (default PyImageLabeling format): 0 / 255 per file
      - Indexed / grayscale PNG  (e.g. Trimaps): integer values 0 … N
      - RGB colour mask: each class = a distinct colour
    """

    FORMAT_BINARY  = "binary"
    FORMAT_INDEXED = "indexed"
    FORMAT_RGB     = "rgb"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Annotation import format")
        self.selected_format = self.FORMAT_BINARY
        self.index_values    = [1]               # list[int] for indexed masks
        self.rgb_color       = QColor(255, 255, 255)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("<b>Select the format of the annotations to import:</b>"))
        layout.addSpacing(8)

        self._btn_group = QButtonGroup(self)

        # ── Option 1: Binary mask (default) ───────────────────────────────
        self.radio_binary = QRadioButton(
            "Binary mask  (PyImageLabeling default)\n"
            "One file per object / class — exactly 2 values: 0 and 255"
        )
        self.radio_binary.setChecked(True)
        self._btn_group.addButton(self.radio_binary)
        layout.addWidget(self.radio_binary)
        layout.addSpacing(8)
        layout.addWidget(self._make_separator())

        # ── Option 2: Indexed / grayscale ─────────────────────────────────
        self.radio_indexed = QRadioButton(
            "Indexed PNG / grayscale\n"
            "Single channel, integer values (0 … N) — e.g. Trimaps"
        )
        self._btn_group.addButton(self.radio_indexed)
        layout.addWidget(self.radio_indexed)

        #   sub-row: foreground value(s) — transparent background, no box
        self._lbl_index = QLabel("    Foreground values (e.g. 1, 2, 3):")
        self._lbl_index.setEnabled(False)
        self.index_edit = QLineEdit("1")
        self.index_edit.setPlaceholderText("e.g. 1, 2, 3")
        self.index_edit.setFixedWidth(130)
        self.index_edit.setEnabled(False)
        sub_idx = QHBoxLayout()
        sub_idx.setContentsMargins(0, 2, 0, 4)
        sub_idx.addWidget(self._lbl_index)
        sub_idx.addWidget(self.index_edit)
        sub_idx.addStretch()
        layout.addLayout(sub_idx)
        layout.addSpacing(4)
        layout.addWidget(self._make_separator())

        # ── Option 3: RGB colour mask ──────────────────────────────────────
        self.radio_rgb = QRadioButton(
            "RGB colour mask\n"
            "Each class = a distinct colour in the mask"
        )
        self._btn_group.addButton(self.radio_rgb)
        layout.addWidget(self.radio_rgb)

        #   sub-row: colour picker — transparent, no box
        self._lbl_rgb = QLabel("    Colour of this class in the mask:")
        self._lbl_rgb.setEnabled(False)
        self._rgb_btn = QPushButton()
        self._rgb_btn.setFixedWidth(80)
        self._rgb_btn.setEnabled(False)
        self._rgb_btn.clicked.connect(self._pick_rgb_color)
        self._rgb_edit = QLineEdit()
        self._rgb_edit.setFixedWidth(100)
        self._rgb_edit.setPlaceholderText("#rrggbb or r,g,b")
        self._rgb_edit.setEnabled(False)
        self._rgb_edit.editingFinished.connect(self._on_rgb_text_edited)
        self._refresh_rgb_button()
        sub_rgb = QHBoxLayout()
        sub_rgb.setContentsMargins(0, 2, 0, 4)
        sub_rgb.addWidget(self._lbl_rgb)
        sub_rgb.addWidget(self._rgb_btn)
        sub_rgb.addWidget(self._rgb_edit)
        sub_rgb.addStretch()
        layout.addLayout(sub_rgb)

        # wire toggle signals
        self.radio_binary.toggled.connect(self._on_format_changed)
        self.radio_indexed.toggled.connect(self._on_format_changed)
        self.radio_rgb.toggled.connect(self._on_format_changed)

        # ── Filename filter ───────────────────────────────────────────────
        layout.addSpacing(8)
        layout.addWidget(self._make_separator())
        layout.addSpacing(4)
        layout.addWidget(QLabel("<b>Filename filter:</b>"))
        filter_hint = QLabel("Wildcards: * (any chars), ? (one char) — e.g. Bombay*, [A-Z]*, pom_?")
        filter_hint.setStyleSheet("font-size: 9pt; font-weight: normal;")
        layout.addWidget(filter_hint)
        self.filter_edit = QLineEdit("*")
        self.filter_edit.setPlaceholderText("* = all files")
        layout.addWidget(self.filter_edit)

        layout.addSpacing(10)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self.setLayout(layout)


    # ------------------------------------------------------------------
    @staticmethod
    def _make_separator():
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: #808080; max-height: 1px;")
        return line

    def _on_format_changed(self):
        indexed = self.radio_indexed.isChecked()
        self._lbl_index.setEnabled(indexed)
        self.index_edit.setEnabled(indexed)

        rgb = self.radio_rgb.isChecked()
        self._lbl_rgb.setEnabled(rgb)
        self._rgb_btn.setEnabled(rgb)
        self._rgb_edit.setEnabled(rgb)

    def _pick_rgb_color(self):
        color = QColorDialog.getColor(self.rgb_color, self)
        if color.isValid():
            self.rgb_color = color
            self._refresh_rgb_button()

    def _refresh_rgb_button(self):
        c = self.rgb_color
        txt = "white" if c.lightness() < 128 else "black"
        self._rgb_btn.setStyleSheet(
            f"background-color: rgb({c.red()},{c.green()},{c.blue()}); color: {txt};"
        )
        self._rgb_btn.setText(c.name())
        self._rgb_edit.setText(f"{c.red()}, {c.green()}, {c.blue()}")

    def _on_rgb_text_edited(self):
        text = self._rgb_edit.text().strip()
        color = QColor(text)  # handles #rrggbb
        if not color.isValid():
            # try "r, g, b" format
            try:
                parts = [int(v.strip()) for v in text.split(",")]
                if len(parts) == 3:
                    color = QColor(*parts)
            except ValueError:
                pass
        if color.isValid():
            self.rgb_color = color
            self._refresh_rgb_button()

    def accept(self):
        if self.radio_indexed.isChecked():
            self.selected_format = self.FORMAT_INDEXED
            raw = self.index_edit.text()
            try:
                parsed = [int(v.strip()) for v in raw.split(",") if v.strip()]
                self.index_values = parsed if parsed else [1]
            except ValueError:
                self.index_values = [1]
        elif self.radio_rgb.isChecked():
            self.selected_format = self.FORMAT_RGB
        else:
            self.selected_format = self.FORMAT_BINARY
        super().accept()


# ---------------------------------------------------------------------------

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

        # Step 2: Ask the user for the annotation format
        fmt_dialog = ImportFormatDialog(self)
        if fmt_dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.import_format        = fmt_dialog.selected_format
        self.import_index_values  = fmt_dialog.index_values
        self.import_rgb_color     = fmt_dialog.rgb_color
        self.import_filter        = fmt_dialog.filter_edit.text().strip() or "*"

        if self.import_format == ImportFormatDialog.FORMAT_RGB:
            self.color_update(self.import_rgb_color)

        # Step 3: Select save/destination folder
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


    # ------------------------------------------------------------------
    # Conversion helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _indexed_to_binary(file_path, index_values: list):
        """
        Indexed / grayscale mask → binary mask.
        Pixels whose value is in *index_values* become white (255); all others black (0).
        Handles trimaps (e.g. [1]) and multi-value selections (e.g. [1, 2]).
        """
        arr = np.array(Image.open(file_path).convert("L"))
        mask = np.isin(arr, index_values).astype(np.uint8) * 255
        return Image.fromarray(mask, mode="L")

    @staticmethod
    def _rgb_to_binary(file_path, color):
        """
        RGB colour mask → binary mask.
        Pixels whose colour matches *color* (a QColor) become white (255); rest black (0).
        """
        arr  = np.array(Image.open(file_path).convert("RGB"))
        target = np.array([color.red(), color.green(), color.blue()], dtype=np.uint8)
        mask = (np.all(arr == target, axis=2).astype(np.uint8)) * 255
        return Image.fromarray(mask, mode="L")

    # ------------------------------------------------------------------

    def process_import_data(self):
        try:
            # Get label ID for renaming
            label_id = self.parent().view.controller.model.get_static_label_id()

            # Ensure destination directory exists
            os.makedirs(self.destination_directory, exist_ok=True)

            # Retrieve the format chosen in the dialog (default: binary)
            fmt         = getattr(self, "import_format",       ImportFormatDialog.FORMAT_BINARY)
            idx_values  = getattr(self, "import_index_values", [1])
            rgb_color   = getattr(self, "import_rgb_color",    None)

            IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif")
            pattern = getattr(self, "import_filter", "*")
            files_to_import = [
                f for f in os.listdir(self.source_directory)
                if not f.startswith(".")
                and not os.path.isdir(os.path.join(self.source_directory, f))
                and f.lower().endswith(IMAGE_EXTS)
                and fnmatch.fnmatch(f, pattern)
            ]

            n = len(files_to_import)
            progress = QProgressDialog("Importing annotations…", "Cancel", 0, n, self)
            progress.setWindowTitle("Importing Annotations")
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setMinimumDuration(0)
            progress.setValue(0)
            _upd = max(1, n // 100)

            for i, filename in enumerate(files_to_import):
                if progress.wasCanceled():
                    break

                source_file_path = os.path.join(self.source_directory, filename)
                name, _ = os.path.splitext(filename)

                # Match the label file to a loaded image by finding the image whose
                # basename is a prefix of the label filename (e.g. "img" in "img_L").
                loaded_paths = self.parent().view.controller.model.file_paths
                matched_base = None
                for fp in loaded_paths:
                    img_base = os.path.splitext(os.path.basename(fp))[0]
                    remainder = name[len(img_base):]
                    if name == img_base or (name.startswith(img_base) and len(remainder) > 0 and remainder[0] in ("_", "-", " ", ".")):
                        matched_base = img_base
                        break
                output_name = matched_base if matched_base else name

                new_filename   = f"{output_name}.label.{label_id}.png"
                dest_file_path = os.path.join(self.destination_directory, new_filename)

                if fmt == ImportFormatDialog.FORMAT_INDEXED:
                    mask = self._indexed_to_binary(source_file_path, idx_values)
                    if not np.any(np.array(mask)):
                        continue
                    print(f"[import] Indexed mask '{filename}': values={idx_values} → white binary")
                    mask.save(dest_file_path)

                elif fmt == ImportFormatDialog.FORMAT_RGB and rgb_color is not None:
                    mask = self._rgb_to_binary(source_file_path, rgb_color)
                    if not np.any(np.array(mask)):
                        continue
                    print(f"[import] RGB mask '{filename}': colour={rgb_color.name()} → white binary")
                    mask.save(dest_file_path)

                else:
                    print(f"[import] Binary mask '{filename}': copied as-is")
                    shutil.copy2(source_file_path, dest_file_path)

                self.importdata = True

                if i % _upd == 0 or i == n - 1:
                    progress.setLabelText(f"Importing '{filename}'…  ({i + 1} / {n})")
                    progress.setValue(i + 1)
                    if progress.wasCanceled():
                        break

            progress.setValue(n)

        except Exception as e:
            print(f"Error importing labels: {str(e)}")

   