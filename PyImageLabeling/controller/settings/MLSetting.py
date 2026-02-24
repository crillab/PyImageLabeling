from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QSpinBox, QDoubleSpinBox, QCheckBox,
    QListWidget, QListWidgetItem, QPushButton, QSlider,
    QComboBox, QScrollArea, QWidget, QSplitter, QAbstractItemView
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QColor

from PyImageLabeling.model.Utils import Utils
import os


class MLSetting(QDialog):
    def __init__(self, zoomable_graphic_view, model):
        super().__init__(zoomable_graphic_view)
        self.model = model
        self.setWindowTitle("ML Training Settings")
        self.resize(650, 600)

        # Load current params
        params = Utils.load_parameters()
        ml_params = params.get("ml", {})

        self.selected_image_paths = []  # Will hold final selection

        main_layout = QVBoxLayout()
        main_layout.setSpacing(8)

        img_group = QGroupBox("Training Images")
        img_group_layout = QVBoxLayout()

        # Legend
        legend_layout = QHBoxLayout()
        for color, text in [
            ("#2ecc71", "● Loaded in memory"),
            ("#f39c12", "● Has labels (not loaded)"),
            ("#bdc3c7", "● No labels"),
        ]:
            lbl = QLabel(text)
            lbl.setStyleSheet(f"color: {color}; font-size: 11px;")
            legend_layout.addWidget(lbl)
        legend_layout.addStretch()
        img_group_layout.addLayout(legend_layout)

        # Buttons row
        btn_row = QHBoxLayout()
        self.select_all_btn = QPushButton("Select All with Labels")
        self.select_all_btn.clicked.connect(self._select_all_with_labels)
        self.deselect_all_btn = QPushButton("Deselect All")
        self.deselect_all_btn.clicked.connect(self._deselect_all)
        btn_row.addWidget(self.select_all_btn)
        btn_row.addWidget(self.deselect_all_btn)
        btn_row.addStretch()
        img_group_layout.addLayout(btn_row)

        # List
        self.image_list = QListWidget()
        self.image_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.image_list.setMinimumHeight(200)
        self._populate_image_list()
        img_group_layout.addWidget(self.image_list)

        img_group.setLayout(img_group_layout)
        main_layout.addWidget(img_group)

        train_group = QGroupBox("Training Parameters")
        train_layout = QVBoxLayout()

        # Epochs
        epochs_row = QHBoxLayout()
        epochs_row.addWidget(QLabel("Epochs:"))
        self.epochs_spinbox = QSpinBox()
        self.epochs_spinbox.setRange(1, 500)
        self.epochs_spinbox.setValue(ml_params.get("num_epochs", 50))
        self.epochs_spinbox.setToolTip("Number of training epochs. More = better accuracy but slower.")
        epochs_row.addWidget(self.epochs_spinbox)
        epochs_row.addStretch()
        train_layout.addLayout(epochs_row)

        # Batch size
        batch_row = QHBoxLayout()
        batch_row.addWidget(QLabel("Batch Size:"))
        self.batch_spinbox = QSpinBox()
        self.batch_spinbox.setRange(1, 64)
        self.batch_spinbox.setValue(ml_params.get("batch_size", 8))
        self.batch_spinbox.setToolTip("Images per training step. Reduce if out of memory.")
        batch_row.addWidget(self.batch_spinbox)
        batch_row.addStretch()
        train_layout.addLayout(batch_row)

        # Learning rate
        lr_row = QHBoxLayout()
        lr_row.addWidget(QLabel("Learning Rate:"))
        self.lr_spinbox = QDoubleSpinBox()
        self.lr_spinbox.setRange(0.00001, 0.1)
        self.lr_spinbox.setSingleStep(0.0001)
        self.lr_spinbox.setDecimals(5)
        self.lr_spinbox.setValue(ml_params.get("learning_rate", 0.002))
        self.lr_spinbox.setToolTip("Step size for optimizer. Lower = more stable, slower.")
        lr_row.addWidget(self.lr_spinbox)
        lr_row.addStretch()
        train_layout.addLayout(lr_row)

        # Image size
        imgsize_row = QHBoxLayout()
        imgsize_row.addWidget(QLabel("Image Size (px):"))
        self.imgsize_combo = QComboBox()
        for s in [224, 320, 416, 512, 640]:
            self.imgsize_combo.addItem(str(s), s)
        current_size = ml_params.get("image_size", 416)
        idx = self.imgsize_combo.findData(current_size)
        if idx >= 0:
            self.imgsize_combo.setCurrentIndex(idx)
        self.imgsize_combo.setToolTip("Resolution images are resized to for training. Larger = slower but more detail.")
        imgsize_row.addWidget(self.imgsize_combo)
        imgsize_row.addStretch()
        train_layout.addLayout(imgsize_row)

        train_group.setLayout(train_layout)
        main_layout.addWidget(train_group)

        model_group = QGroupBox("Model Options")
        model_layout = QVBoxLayout()

        self.enable_seg_checkbox = QCheckBox("Enable Segmentation Head (paintbrush labels)")
        self.enable_seg_checkbox.setChecked(ml_params.get("enable_segmentation", True))
        self.enable_seg_checkbox.setToolTip(
            "Train a segmentation head using painted pixel annotations.\n"
            "Disable if you only have geometric shapes (rectangles, ellipses, polygons)."
        )
        model_layout.addWidget(self.enable_seg_checkbox)

        self.enable_det_checkbox = QCheckBox("Enable Detection Head (geometric shape labels)")
        self.enable_det_checkbox.setChecked(ml_params.get("enable_detection", True))
        self.enable_det_checkbox.setToolTip(
            "Train an object detection head using rectangle/ellipse/polygon annotations."
        )
        model_layout.addWidget(self.enable_det_checkbox)

        self.pretrained_checkbox = QCheckBox("Use Pretrained Backbone (ResNet18 ImageNet)")
        self.pretrained_checkbox.setChecked(ml_params.get("pretrained", True))
        self.pretrained_checkbox.setToolTip(
            "Start from ImageNet pretrained weights. Strongly recommended unless your images are very unusual."
        )
        model_layout.addWidget(self.pretrained_checkbox)

        model_group.setLayout(model_layout)
        main_layout.addWidget(model_group)

        infer_group = QGroupBox("Inference Parameters")
        infer_layout = QVBoxLayout()

        conf_row = QHBoxLayout()
        conf_row.addWidget(QLabel("Confidence Threshold:"))
        self.conf_spinbox = QDoubleSpinBox()
        self.conf_spinbox.setRange(0.01, 1.0)
        self.conf_spinbox.setSingleStep(0.05)
        self.conf_spinbox.setDecimals(2)
        self.conf_spinbox.setValue(ml_params.get("confidence_threshold", 0.3))
        conf_row.addWidget(self.conf_spinbox)
        conf_row.addStretch()
        infer_layout.addLayout(conf_row)

        nms_row = QHBoxLayout()
        nms_row.addWidget(QLabel("NMS Threshold:"))
        self.nms_spinbox = QDoubleSpinBox()
        self.nms_spinbox.setRange(0.01, 1.0)
        self.nms_spinbox.setSingleStep(0.05)
        self.nms_spinbox.setDecimals(2)
        self.nms_spinbox.setValue(ml_params.get("nms_threshold", 0.4))
        nms_row.addWidget(self.nms_spinbox)
        nms_row.addStretch()
        infer_layout.addLayout(nms_row)

        infer_group.setLayout(infer_layout)
        main_layout.addWidget(infer_group)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        main_layout.addWidget(self.buttons)

        self.setLayout(main_layout)

    def _populate_image_list(self):
        """
        Build list entries. Each item has a checkbox.
        Color coding:
          green  = ImageItem loaded in memory
          orange = has label data (label_tag) but not loaded
          gray   = no labels at all
        """
        self.image_list.clear()
        self._item_path_map = {}  # row -> file_path

        for file_path in self.model.file_paths:
            basename = os.path.basename(file_path)
            image_item = self.model.image_items.get(file_path)
            loaded = image_item is not None

            # Determine if this image has any label data
            has_label = self._image_has_labels(file_path, image_item, basename)

            # Display text
            status = ""
            if loaded:
                status = " [loaded]"
            elif has_label:
                status = " [has labels]"

            item = QListWidgetItem()
            item.setText(basename + status)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)

            # Default: check images that have labels
            item.setCheckState(
                Qt.CheckState.Checked if has_label else Qt.CheckState.Unchecked
            )

            # Color coding
            if loaded:
                item.setForeground(QColor("#27ae60"))
            elif has_label:
                item.setForeground(QColor("#e67e22"))
            else:
                item.setForeground(QColor("#7f8c8d"))

            self.image_list.addItem(item)
            self._item_path_map[self.image_list.count() - 1] = file_path

    def _image_has_labels(self, file_path, image_item, basename):
        """Return True if the image has any annotation data."""
        # Loaded image: check overlays and shapes
        if image_item is not None:
            if image_item.image_rectangles or image_item.image_ellipses or image_item.image_polygons:
                return True
            for ov in image_item.labeling_overlays.values():
                if not ov.get_is_undo_none():
                    return True
                if len(ov.undo_deque) == 1:
                    entry = ov.undo_deque[0]
                    if entry.y_coords is not None and len(entry.y_coords) > 0:
                        return True

        # Not loaded: check left_* dicts and labeling_overview_was_loaded
        name_no_ext = ".".join(basename.split(".")[:-1])
        if name_no_ext in self.model.left_rectangles:
            return True
        if basename in self.model.left_rectangles:
            return True
        if name_no_ext in self.model.left_ellipses:
            return True
        if basename in self.model.left_ellipses:
            return True
        if name_no_ext in self.model.left_polygons:
            return True
        if basename in self.model.left_polygons:
            return True

        # Check pixel overlays registered but not yet loaded
        for key in self.model.labeling_overview_was_loaded:
            from PyImageLabeling.model.Core import KEYWORD_SAVE_LABEL
            img_basename = key.split(KEYWORD_SAVE_LABEL)[0]
            if img_basename == name_no_ext:
                return True

        return False

    def _select_all_with_labels(self):
        for row in range(self.image_list.count()):
            item = self.image_list.item(row)
            file_path = self._item_path_map.get(row)
            if file_path is None:
                continue
            basename = os.path.basename(file_path)
            image_item = self.model.image_items.get(file_path)
            if self._image_has_labels(file_path, image_item, basename):
                item.setCheckState(Qt.CheckState.Checked)

    def _deselect_all(self):
        for row in range(self.image_list.count()):
            self.image_list.item(row).setCheckState(Qt.CheckState.Unchecked)

    def accept(self):
        # Collect checked image paths
        self.selected_image_paths = []
        for row in range(self.image_list.count()):
            item = self.image_list.item(row)
            if item.checkState() == Qt.CheckState.Checked:
                file_path = self._item_path_map.get(row)
                if file_path:
                    self.selected_image_paths.append(file_path)

        # Persist parameters
        data = Utils.load_parameters()
        if "ml" not in data:
            data["ml"] = {}

        data["ml"]["num_epochs"] = self.epochs_spinbox.value()
        data["ml"]["batch_size"] = self.batch_spinbox.value()
        data["ml"]["learning_rate"] = self.lr_spinbox.value()
        data["ml"]["image_size"] = self.imgsize_combo.currentData()
        data["ml"]["enable_segmentation"] = self.enable_seg_checkbox.isChecked()
        data["ml"]["enable_detection"] = self.enable_det_checkbox.isChecked()
        data["ml"]["pretrained"] = self.pretrained_checkbox.isChecked()
        data["ml"]["confidence_threshold"] = self.conf_spinbox.value()
        data["ml"]["nms_threshold"] = self.nms_spinbox.value()

        Utils.save_parameters(data)
        return super().accept()