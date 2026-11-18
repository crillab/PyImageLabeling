from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QMessageBox,
    QFileDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QComboBox,
    QScrollArea,
    QWidget,
    QAbstractItemView,
    QInputDialog,
    QLineEdit,
    QRadioButton,
    QButtonGroup,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)
from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon, QImageReader, QPixmap, QScreen


from PyImageLabeling.model.Utils import Utils
from PyImageLabeling.model.ML.MLPredictor import (
    BACKBONE_NAMES,
    DEFAULT_BACKBONE,
)
from PyImageLabeling.model.ML import LabelStats, Tiling
import os


class LabelStatsWorker(QThread):
    """Reads mask files for the label statistics, off the GUI thread:
    a large mask takes a fraction of a second to decode."""

    mask_done = pyqtSignal(str, int, object)   # image, label id, MaskStats

    def __init__(self, jobs, cache, parent=None):
        super().__init__(parent)
        self.jobs = list(jobs)       # [(image path, label id, mask file)]
        self.cache = cache
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        for path, label_id, mask_path in self.jobs:
            if self._stop:
                return
            try:
                stats = LabelStats.file_stats(mask_path, self.cache)
            except Exception:
                stats = None
            self.mask_done.emit(path, label_id, stats)


class MLSetting(QDialog):
    def __init__(self, zoomable_graphic_view, model):
        super().__init__(zoomable_graphic_view)
        self.model = model
        self.setWindowTitle("ML Training Settings")
        
        # Adapter la taille à l'écran
        self._setup_window_size()

        # Load current params
        params = Utils.load_parameters()
        ml_params = params.get("ml", {})

        self.loaded_model_name = ml_params.get("loaded_model_name", None)

        self.selected_image_paths = []

        # Créer un QScrollArea pour rendre le contenu scrollable
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Widget conteneur pour le contenu
        content_widget = QWidget()
        main_layout = QVBoxLayout(content_widget)
        main_layout.setSpacing(8)

        # [Tout le contenu existant reste identique]
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
        self.image_list.setMinimumHeight(150)  # Réduire la hauteur minimale
        self._populate_image_list()
        img_group_layout.addWidget(self.image_list)

        img_group.setLayout(img_group_layout)
        main_layout.addWidget(img_group)

        self._build_labels_group(main_layout, ml_params)

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
        self.imgsize_combo.setToolTip(
            "Square size the whole image is resized to: segmentation with\n"
            "the Whole image input, and detection. Larger = slower but more\n"
            "detail.")
        imgsize_row.addWidget(self.imgsize_combo)
        imgsize_row.addStretch()
        train_layout.addLayout(imgsize_row)

        train_group.setLayout(train_layout)
        main_layout.addWidget(train_group)

        model_group = QGroupBox("Model Options")
        model_layout = QVBoxLayout()

        self.pretrained_checkbox = QCheckBox("Use Pretrained Backbone (ImageNet weights)")
        self.pretrained_checkbox.setChecked(ml_params.get("pretrained", True))
        self.pretrained_checkbox.setToolTip(
            "Start from ImageNet pretrained weights. Strongly recommended unless your images are very unusual."
        )
        model_layout.addWidget(self.pretrained_checkbox)

        # Backbone selector
        backbone_row = QHBoxLayout()
        backbone_lbl = QLabel("Backbone Architecture:")
        backbone_lbl.setToolTip(
        "Feature extractor used for detection and segmentation.\n\n"

        "=== Classic CNNs (Stable & Proven) ===\n"
        "• ResNet18 / 34 — fast, reliable defaults.\n"
        "• ResNet50 — strong baseline.\n"
        "• ResNet101 / 152 — higher accuracy, slower.\n\n"

        "=== Mobile / Edge (Very Fast) ===\n"
        "• MobileNetV3-Small — fastest, lowest accuracy.\n"
        "• MobileNetV3-Large — better accuracy, still lightweight.\n"
        "• MobileNetV2 — balanced lightweight model.\n\n"

        "=== EfficientNet (Best trade-off) ===\n"
        "• B0 → B4 — increasing accuracy & compute cost.\n"
        "• B0 = best default balance.\n\n"

        "=== Vision Transformers (High Accuracy) ===\n"
        "• ViT-B/16, B/32 — strong but need more data.\n"
        "• ViT-L/16 — very large, GPU recommended.\n\n"

        "=== Swin Transformers (Detection/Segmentation) ===\n"
        "• Tiny / Small / Base — excellent for dense tasks.\n\n"

        "=== ConvNeXt (Modern CNNs) ===\n"
        "• Tiny / Small / Base — competitive with transformers.\n\n"

        "=== RegNet (Efficient scaling) ===\n"
        "• 400MF → 3.2GF — scalable performance.\n\n"

        "=== DenseNet (Feature reuse) ===\n"
        "• Dense connections, good efficiency.\n\n"

        "=== Wide / ResNeXt ===\n"
        "• Better feature representation than standard ResNet.\n\n"

        "=== Hybrid ===\n"
        "• MaxViT — CNN + Transformer, very powerful.\n\n"

        "⚠ Changing backbone invalidates any previously saved model.\n"
        "⚠ Large models require GPU and more memory."
    )
        self.backbone_combo = QComboBox()
        for name in BACKBONE_NAMES:
            self.backbone_combo.addItem(name)
        current_backbone = ml_params.get("backbone_name", DEFAULT_BACKBONE)
        idx = self.backbone_combo.findText(current_backbone)
        if idx >= 0:
            self.backbone_combo.setCurrentIndex(idx)
        backbone_row.addWidget(backbone_lbl)
        backbone_row.addWidget(self.backbone_combo)
        backbone_row.addStretch()
        model_layout.addLayout(backbone_row)

        self.enable_det_checkbox = QCheckBox("Enable Detection Head (geometric shape labels)")
        self.enable_det_checkbox.setChecked(ml_params.get("enable_detection", True))
        self.enable_det_checkbox.setToolTip(
            "Train an object detection head using rectangle/ellipse/polygon annotations.\n"
            "Unchecked: the shapes are ignored by the training."
        )
        model_layout.addWidget(self.enable_det_checkbox)

        self.enable_seg_checkbox = QCheckBox("Enable Segmentation Head (paintbrush labels)")
        self.enable_seg_checkbox.setChecked(ml_params.get("enable_segmentation", True))
        self.enable_seg_checkbox.setToolTip(
            "Train a segmentation head using painted pixel annotations.\n"
            "Unchecked: the painted pixels are ignored by the training.\n"
            "Its settings are shown below it when it is checked."
        )
        model_layout.addWidget(self.enable_seg_checkbox)

        # the settings of the segmentation, under its box, only when checked
        self.seg_options = QWidget()
        self.seg_options.setObjectName("ml_seg_options")
        # plain containers: the group's colour, not the dark one style.css
        # gives every QWidget
        self.seg_options.setStyleSheet(
            "#ml_seg_options, #ml_tiles_box "
            "{ background-color: transparent; }")
        seg_layout = QVBoxLayout(self.seg_options)
        seg_layout.setContentsMargins(24, 0, 0, 0)

        # Segmentation head: ResNet (default) or frozen DINOv2 + linear probe
        seg_row = QHBoxLayout()
        seg_lbl = QLabel("Segmentation Head:")
        seg_lbl.setToolTip(
            "Head used for painted pixel annotations.\n\n"
            "• ResNet head — the default, trains detection + "
            "segmentation jointly.\n"
            "• DINOv2-linear — frozen DINOv2 features + a 1x1 head: "
            "much faster to train and stronger on photos, "
            "but segmentation-only (falls back to ResNet when "
            "geometric shapes are present)."
        )
        self.seg_combo = QComboBox()
        self.seg_combo.addItem("ResNet head", "resnet")
        self.seg_combo.addItem("DINOv2-linear (fast, seg-only)", "dinov2")
        current_seg = ml_params.get("seg_backbone", "resnet")
        idx = self.seg_combo.findData(current_seg)
        if idx >= 0:
            self.seg_combo.setCurrentIndex(idx)
        seg_row.addWidget(seg_lbl)
        seg_row.addWidget(self.seg_combo)
        seg_row.addStretch()
        seg_layout.addLayout(seg_row)

        self._build_tiles_options(seg_layout, ml_params)
        model_layout.addWidget(self.seg_options)
        self.enable_seg_checkbox.toggled.connect(self._update_seg_options)

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

        btn_model_row = QHBoxLayout()
        self.save_model_btn = QPushButton("Save Trained Model")
        self.load_model_btn = QPushButton("Load Existing Model")

        if self.loaded_model_name:
            self.load_model_btn.setText(f"Loaded: {self.loaded_model_name}")

        self.save_model_btn.clicked.connect(self._save_model)
        self.load_model_btn.clicked.connect(self._load_model)

        btn_model_row.addWidget(self.save_model_btn)
        btn_model_row.addWidget(self.load_model_btn)
        btn_model_row.addStretch()
        main_layout.addLayout(btn_model_row)

        # Which model is actually going to predict. Both a loaded file and a
        # model trained in this session can be alive at once, so say it here
        # instead of letting the user guess from the history.
        self.active_model_label = QLabel()
        self.active_model_label.setWordWrap(True)
        self.active_model_label.setStyleSheet("padding: 4px;")
        main_layout.addWidget(self.active_model_label)
        self._refresh_active_model_label()

        # Buttons OK/Cancel
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        main_layout.addWidget(self.buttons)

        # Appliquer le layout au widget de contenu
        content_widget.setLayout(main_layout)
        
        # Mettre le widget dans le scroll area
        scroll_area.setWidget(content_widget)
        
        # Layout principal de la fenêtre
        dialog_layout = QVBoxLayout()
        dialog_layout.setContentsMargins(0, 0, 0, 0)
        dialog_layout.addWidget(scroll_area)
        self.setLayout(dialog_layout)

        # only now that every widget has a parent: showing one without
        # would open it as a window of its own
        self._update_seg_options()
        self._update_tiles_box()
        self._update_label_choice()
        # the figures follow the images, the labels and the tiles chosen
        self.image_list.itemChanged.connect(self._schedule_stats_refresh)
        self.other_labels_checkbox.toggled.connect(
            self._schedule_stats_refresh)
        self.tiles_radio.toggled.connect(self._schedule_stats_refresh)
        self.tile_spinbox.valueChanged.connect(self._schedule_stats_refresh)
        self.scale_combo.currentIndexChanged.connect(
            self._schedule_stats_refresh)
        self._start_label_stats()

    # ------------------------------------------------------------------
    # Labels to learn
    # ------------------------------------------------------------------

    def _build_labels_group(self, main_layout, ml_params):
        """The labels the next training learns. One label = a binary model
        (the label against the background)."""
        group = QGroupBox("Labels to Learn")
        layout = QVBoxLayout(group)

        self.labels_table = QTableWidget(0, len(self.LABEL_COLUMNS))
        self.labels_table.setHorizontalHeaderLabels(self.LABEL_COLUMNS)
        self.labels_table.verticalHeader().setVisible(False)
        self.labels_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers)
        self.labels_table.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection)
        self.labels_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.labels_table.verticalHeader().setDefaultSectionSize(
            self.labels_table.fontMetrics().height() + 8)
        header = self.labels_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in range(1, len(self.LABEL_COLUMNS)):
            header.setSectionResizeMode(
                col, QHeaderView.ResizeMode.ResizeToContents)
        for col, tip in enumerate(self.LABEL_TOOLTIPS):
            self.labels_table.horizontalHeaderItem(col).setToolTip(tip)

        chosen = (self.model.ml_chosen_label_ids()
                  if hasattr(self.model, "ml_chosen_label_ids") else None)
        self._label_row_ids = []
        for label_id in sorted(self.model.label_items):
            label = self.model.label_items[label_id]
            cell = QTableWidgetItem(label.get_name())
            cell.setFlags(Qt.ItemFlag.ItemIsEnabled
                          | Qt.ItemFlag.ItemIsUserCheckable)
            cell.setCheckState(
                Qt.CheckState.Checked if chosen is None or label_id in chosen
                else Qt.CheckState.Unchecked)
            swatch = QPixmap(12, 12)
            swatch.fill(label.get_color())
            cell.setIcon(QIcon(swatch))
            row = self.labels_table.rowCount()
            self.labels_table.insertRow(row)
            self.labels_table.setItem(row, 0, cell)
            self._label_row_ids.append(label_id)
        # the classes that are not labels: background, ignored pixels
        italic = QFont(self.labels_table.font())
        italic.setItalic(True)
        for key, text, tip in (
                (LabelStats.BACKGROUND, "Background",
                 "Pixels of no checked label: those painted with nothing,\n"
                 "and those of the other labels when they count as\n"
                 "background."),
                (LabelStats.IGNORED, "Other labels (ignored)",
                 "Pixels of the unchecked labels on the training images,\n"
                 "left out of the training.")):
            cell = QTableWidgetItem(text)
            cell.setFlags(Qt.ItemFlag.ItemIsEnabled)
            cell.setFont(italic)
            cell.setToolTip(tip)
            row = self.labels_table.rowCount()
            self.labels_table.insertRow(row)
            self.labels_table.setItem(row, 0, cell)
            self._label_row_ids.append(None)
            setattr(self, f"_{key}_row", row)
        self._label_names = {
            label_id: self.model.label_items[label_id].get_name()
            for label_id in self._label_row_ids if label_id is not None}
        self._label_stats = {}       # image path -> {label id: MaskStats}
        self._stats_pending = 0
        self._stats_worker = None
        self._closed = False
        # one refresh for a burst of changes (Select All, masks read); a
        # child of the dialog, so that it never fires once it is gone
        self._stats_timer = QTimer(self)
        self._stats_timer.setSingleShot(True)
        self._stats_timer.setInterval(0)
        self._stats_timer.timeout.connect(self._refresh_label_stats)
        self._fit_labels_table()
        self.labels_table.itemChanged.connect(self._update_label_choice)
        layout.addWidget(self.labels_table)

        self.labels_summary = QLabel()
        self.labels_summary.setWordWrap(True)
        layout.addWidget(self.labels_summary)

        self.other_labels_checkbox = QCheckBox(
            "Count the pixels of the other labels as background")
        self.other_labels_checkbox.setChecked(
            bool(ml_params.get("other_labels_background", True)))
        self.other_labels_checkbox.setToolTip(
            "On the training images, the pixels painted with a label that\n"
            "is not checked:\n"
            "• checked: are background — examples of what the model must\n"
            "  not mark;\n"
            "• unchecked: are left out of the training (neither the label\n"
            "  nor the background).")
        layout.addWidget(self.other_labels_checkbox)
        main_layout.addWidget(group)

    LABEL_COLUMNS = ("Label", "Images", "Where painted", "Share", "Tiles")
    LABEL_TOOLTIPS = (
        "Check the labels the model learns; every other pixel is the\n"
        "background. One label checked: a binary model (that label against\n"
        "the background).",
        "Checked training images where the label is painted.",
        "Share of the pixels of those images painted with the label: how\n"
        "small the label is where it is annotated.",
        "Share of the pixels of the training images (those holding a\n"
        "checked label, validation included) of each class the model\n"
        "learns. A class of a few percent is easily drowned by the\n"
        "background: see the Tile Sampling and the Loss settings.",
        "Share of the tiles of the training images (Tile Size, at the\n"
        "Resolution chosen, on a grid) holding at least one pixel of the\n"
        "label.")

    def _fit_labels_table(self):
        """As high as its rows (up to 8 of them), no inner scroll bar
        before that."""
        table = self.labels_table
        rows = min(sum(not table.isRowHidden(r)
                       for r in range(table.rowCount())), 8)
        height = (table.horizontalHeader().sizeHint().height()
                  + rows * table.verticalHeader().defaultSectionSize()
                  + 2 * table.frameWidth() + 2)
        table.setFixedHeight(max(height, 40))

    def chosen_label_ids(self):
        """Label ids checked in Labels to Learn, or None when all of them
        are (a label created later is then learnt too)."""
        rows = [(row, label_id)
                for row, label_id in enumerate(self._label_row_ids)
                if label_id is not None]
        ids = [label_id for row, label_id in rows
               if self.labels_table.item(row, 0).checkState()
               == Qt.CheckState.Checked]
        if len(ids) == len(rows):
            return None
        return ids

    def _choice_text(self):
        """What the checked labels make, in words."""
        names = self._label_names
        chosen = self.chosen_label_ids()
        n_all = len(names)
        ids = list(names) if chosen is None else chosen
        if not n_all:
            text = "The project has no label yet."
        elif not ids:
            text = ("<span style='color:#e74c3c'>Check at least one "
                    "label.</span>")
        elif len(ids) == 1:
            text = (f"Binary model: <b>{names[ids[0]]}</b> against the "
                    f"background.")
        elif chosen is None:
            text = f"{n_all} labels + the background."
        else:
            text = f"{len(ids)} of the {n_all} labels + the background."
        if chosen is not None and ids:
            text += (" Images where it is not painted are left out of the "
                     "training." if len(ids) == 1 else
                     " Images where none of them is painted are left out "
                     "of the training.")
        return text

    def _update_label_choice(self, item=None):
        """Say what the checked labels make, and refuse none."""
        if item is not None and item.column() != 0:
            return                   # a figure, not a check box
        chosen = self.chosen_label_ids()
        n_all = sum(i is not None for i in self._label_row_ids)
        self.other_labels_checkbox.setEnabled(
            chosen is not None and bool(chosen))
        if hasattr(self, "buttons"):
            self.buttons.button(
                QDialogButtonBox.StandardButton.Ok).setEnabled(
                    not n_all or chosen is None or bool(chosen))
        self._refresh_label_stats()

    # ---- figures of the labels -------------------------------------------

    def _checked_image_paths(self):
        return [self._item_path_map[row]
                for row in range(self.image_list.count())
                if self.image_list.item(row).checkState()
                == Qt.CheckState.Checked and row in self._item_path_map]

    def _start_label_stats(self):
        """Read what each mask holds: loaded images with unsaved strokes
        here (their overlays live on the GUI thread), mask files in a
        thread (cached by file and date, so mostly instant the next
        time)."""
        if not self.model.label_items or not hasattr(
                self.model, "ml_label_stat_sources"):
            self._refresh_label_stats()
            return
        files, overlays = self.model.ml_label_stat_sources(
            list(self.model.file_paths))
        for path, per_label in overlays.items():
            for label_id, overlay in per_label.items():
                try:
                    stats = self.model.ml_overlay_stats(overlay)
                except Exception:
                    stats = None
                self._label_stats.setdefault(path, {})[label_id] = stats
        jobs = [(path, label_id, mask_path)
                for path, per_label in files.items()
                for label_id, mask_path in per_label.items()
                if label_id not in overlays.get(path, {})]
        self._stats_pending = len(jobs)
        if jobs:
            cache = self.model.__dict__.setdefault(
                "_ml_label_stats_cache", {})
            self._stats_worker = LabelStatsWorker(jobs, cache, self)
            self._stats_worker.mask_done.connect(self._on_mask_stats)
            self._stats_worker.start()
        self._refresh_label_stats()

    def _on_mask_stats(self, path, label_id, stats):
        if self._closed:
            return
        self._label_stats.setdefault(path, {})[label_id] = stats
        self._stats_pending = max(0, self._stats_pending - 1)
        self._schedule_stats_refresh()

    def wait_for_label_stats(self):
        """Block until every mask is read and shown (tests)."""
        from PyQt6.QtWidgets import QApplication
        if self._stats_worker is not None:
            self._stats_worker.wait()
        QApplication.processEvents()
        self._refresh_label_stats()

    def _stop_label_stats(self):
        worker = self._stats_worker
        if worker is not None:
            worker.stop()
            worker.wait()
            self._stats_worker = None

    def _schedule_stats_refresh(self, *_):
        """One refresh for a burst of changes (Select All, masks read)."""
        if not self._closed:
            self._stats_timer.start()

    def _tile_px(self):
        """Side of a tile in image pixels, or None for whole images."""
        if not hasattr(self, "tiles_radio") or not self.tiles_radio.isChecked():
            return None
        return self.tile_spinbox.value() / (self.scale_combo.currentData()
                                            or 1.0)

    def _refresh_label_stats(self):
        self._stats_timer.stop()
        if self._closed or not hasattr(self, "labels_table"):
            return
        chosen = self.chosen_label_ids()
        chosen = None if chosen is None else set(chosen)
        others = chosen is not None and any(
            i is not None and i not in chosen for i in self._label_row_ids)
        ignore = others and not self.other_labels_checkbox.isChecked()
        tile_px = self._tile_px()
        checked = set(self._checked_image_paths())
        images = {path: per_label for path, per_label
                  in self._label_stats.items() if path in checked}
        summary = LabelStats.summarize(images, chosen, ignore, tile_px)

        table = self.labels_table
        was_blocked = table.blockSignals(True)
        try:
            for row, label_id in enumerate(self._label_row_ids):
                if label_id is None:
                    continue
                learnt = chosen is None or label_id in chosen
                figures = summary["labels"].get(label_id)
                share = summary["share"].get(label_id)
                tiles = (summary["tiles"] or {}).get(label_id)
                self._set_stat(row, 1, str(figures["images"])
                               if figures else "0", not learnt)
                self._set_stat(row, 2, self._percent(figures["density"])
                               if figures else "–", not learnt)
                self._set_stat(row, 3, self._percent(share)
                               if learnt and share is not None else "–",
                               not learnt)
                self._set_stat(row, 4, self._percent(tiles)
                               if learnt and tiles is not None else "–",
                               not learnt)
            for key in (LabelStats.BACKGROUND, LabelStats.IGNORED):
                row = getattr(self, f"_{key}_row")
                share = summary["share"].get(key)
                for col in (1, 2, 4):
                    self._set_stat(row, col, "")
                self._set_stat(row, 3, self._percent(share)
                               if share is not None else "–")
            table.setRowHidden(self._ignored_row, not ignore)
            table.setColumnHidden(4, tile_px is None)
        finally:
            table.blockSignals(was_blocked)
        self._fit_labels_table()

        lines = [self._choice_text()]
        if self._label_names:
            if self._stats_pending:
                lines.append(f"<i>Reading the masks… "
                             f"{self._stats_pending} left</i>")
            training = (f"Training images: {summary['training_images']} of "
                        f"the {len(checked)} checked (validation included)")
            if summary["empty_tiles"] is not None:
                training += (f" · {self._percent(summary['empty_tiles'])} "
                             f"of their tiles hold none of the checked "
                             f"labels")
            lines.append(training + ".")
        self.labels_summary.setText("<br>".join(lines))

    @staticmethod
    def _percent(value):
        if value is None:
            return "–"
        if 0 < value < 0.001:
            return "< 0.1 %"
        return f"{100 * value:.1f} %"

    def _set_stat(self, row, col, text, dim=False):
        item = QTableWidgetItem(text)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled)
        item.setTextAlignment(Qt.AlignmentFlag.AlignRight
                              | Qt.AlignmentFlag.AlignVCenter)
        if dim:
            item.setForeground(QColor("#7f8c8d"))
        self.labels_table.setItem(row, col, item)

    def _setup_window_size(self):
        """Configure la taille de la fenêtre en fonction de l'écran"""
        # Obtenir la géométrie de l'écran
        screen = self.screen()
        if screen is None:
            screen = QScreen.primaryScreen()
        
        screen_geometry = screen.availableGeometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()
        
        # Définir la taille à 80% de l'écran (max)
        max_width = int(screen_width * 0.8)
        max_height = int(screen_height * 0.8)
        
        # Taille minimale
        min_width = 600
        min_height = 400
        
        # Taille préférée
        preferred_width = min(650, max_width)
        preferred_height = min(900, max_height)
        
        self.setMinimumSize(min_width, min_height)
        self.resize(preferred_width, preferred_height)
        
        # Centrer la fenêtre
        self.move(
            screen_geometry.center().x() - self.width() // 2,
            screen_geometry.center().y() - self.height() // 2
        )

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
        from PyImageLabeling.model.Masks import (
            KEYWORD_SAVE_LABEL,
            image_base_from_mask_name)
        for key in self.model.labeling_overview_was_loaded:
            img_basename = image_base_from_mask_name(key)
            if img_basename == name_no_ext:
                return True

        return False
    
    def _refresh_active_model_label(self):
        """Describe the model that would predict right now."""
        if not hasattr(self, "active_model_label"):
            return
        info = (self.model.ml_model_info()
                if hasattr(self.model, "ml_model_info") else None)
        if not info or not info["trained"]:
            self.active_model_label.setText(
                "<b>Active model:</b> none — train or load one first.")
            self.active_model_label.setToolTip("")
            return

        if info["origin"] == "loaded":
            state = "loaded from file"
            detail = info["path"] or ""
        elif info["saved"]:
            state = "trained, then saved"
            detail = info["path"] or ""
        else:
            state = ("<b>trained in this session, not saved — in memory "
                     "only</b>")
            detail = "Close the app or start another training and it is lost."

        can = []
        if info["can_detect"]:
            can.append("boxes")
        if info["can_segment"]:
            can.append("segmentation")

        self.active_model_label.setText(
            f"<b>Active model:</b> {info['kind']}<br>"
            f"Source: {state}<br>"
            f"Predicts: {', '.join(can) if can else 'nothing'}"
            + (f"<br>{detail}" if detail else "")
        )
        self.active_model_label.setToolTip(detail)

    def _save_model(self):
        if not self.model.trained:
            QMessageBox.warning(self, "No Model", "Train a model first.")
            return

        model_name, ok = QInputDialog.getText(
            self,
            "Model Name",
            "Enter a name for your model:",
            QLineEdit.EchoMode.Normal,
            "my_model"
        )
        
        if not ok or not model_name.strip():
            return
        
        # Clean the model name (remove invalid characters)
        model_name = model_name.strip()
        
        directory = QFileDialog.getExistingDirectory(
            self, "Select Folder to Save Model"
        )
        if directory:
            # Pass the model name to the save function
            # You may need to modify save_model_file to accept the name parameter
            self.model.save_model_file(directory, model_name)
            # the active model now has a file behind it: refresh both the
            # dialog and the status bar so it stops saying "not saved"
            self._refresh_active_model_label()
            try:
                self.model.controller.ml_update_status()
            except Exception:
                pass
            QMessageBox.information(self, "Saved", f"Model '{model_name}' saved successfully.")


    def _load_model(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Model",
            "",
            "PyTorch Model (*.pth);;All Files (*)"
        )

        if file_path:
            success = self.model.load_model_file(file_path)
            if success:
                self.loaded_model_name = os.path.splitext(os.path.basename(file_path))[0]
                self.load_model_btn.setText(f"Loaded: {self.loaded_model_name}")
                # loading replaces whatever was live, and predictions now come
                # from this file: say so on screen right away
                self._refresh_active_model_label()
                try:
                    self.model.controller.ml_update_status()
                except Exception:
                    pass
                
                # Save to parameters
                data = Utils.load_parameters()
                if "ml" not in data:
                    data["ml"] = {}
                data["ml"]["loaded_model_name"] = self.loaded_model_name
                Utils.save_parameters(data)
                QMessageBox.information(self, "Loaded", "Model loaded successfully.")
            else:
                QMessageBox.critical(self, "Error", "Failed to load model.")
    
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

    def _build_tiles_options(self, seg_layout, ml_params):
        """How a segmentation model sees the images: the whole image resized
        to the Image Size, or tiles of it. The user chooses. Added to
        `seg_layout`, under the segmentation box."""
        tiles = str(ml_params.get("tiling", "off")).lower() == "on"
        self.whole_radio = QRadioButton(
            "Whole image, resized to the Image Size")
        self.whole_radio.setToolTip(
            "The whole image is resized to the Image Size (a square) for\n"
            "training and prediction. Fast, and fine for small images; a\n"
            "large image loses its fine details and its aspect ratio.")
        self.tiles_radio = QRadioButton("Tiles")
        self.tiles_radio.setToolTip(
            "Training and prediction work on square crops of the image at\n"
            "(or near) its own resolution, put back together. For large\n"
            "images: slower, but the details are kept.")
        (self.tiles_radio if tiles else self.whole_radio).setChecked(True)
        self.tiling_group = QButtonGroup(self)
        self.tiling_group.addButton(self.whole_radio)
        self.tiling_group.addButton(self.tiles_radio)

        # the settings of the tiles, under their button, only for tiles
        self.tiles_box = QWidget()
        self.tiles_box.setObjectName("ml_tiles_box")
        layout = QVBoxLayout(self.tiles_box)
        layout.setContentsMargins(24, 0, 0, 0)

        tile_row = QHBoxLayout()
        tile_row.addWidget(QLabel("Tile Size:"))
        self.tile_spinbox = QSpinBox()
        self.tile_spinbox.setRange(Tiling.MIN_TILE_SIZE, 2048)
        self.tile_spinbox.setSingleStep(Tiling.TILE_MULTIPLE)
        self.tile_spinbox.setSuffix(" px")
        self.tile_spinbox.setValue(Tiling.normalize_tile_size(
            ml_params.get("tile_size", Tiling.DEFAULT_TILE_SIZE)))
        self.tile_spinbox.setToolTip(
            f"Side of the square tiles (a multiple of {Tiling.TILE_MULTIPLE}).\n"
            "Larger tiles give more context around each pixel, but need more\n"
            "GPU memory (if it runs out, the batches are made smaller).\n"
            "Each epoch sees about a third of every image, whatever the size.")
        self.tile_spinbox.editingFinished.connect(self._snap_tile_size)
        self.tile_spinbox.valueChanged.connect(self._update_overlap_range)
        tile_row.addWidget(self.tile_spinbox)
        tile_row.addStretch()
        layout.addLayout(tile_row)

        overlap_row = QHBoxLayout()
        overlap_row.addWidget(QLabel("Overlap:"))
        self.overlap_spinbox = QSpinBox()
        self.overlap_spinbox.setSingleStep(16)
        self.overlap_spinbox.setSuffix(" px")
        self._update_overlap_range()
        self.overlap_spinbox.setValue(Tiling.normalize_overlap(
            ml_params.get("tile_overlap", Tiling.DEFAULT_OVERLAP),
            self.tile_spinbox.value()))
        self.overlap_spinbox.setToolTip(
            "Overlap between neighbouring tiles when predicting (at most half\n"
            "a tile). The network sees less around the pixels near the edge of\n"
            "a tile; with an overlap each pixel is taken from the tile where it\n"
            "is the farthest from the edge, so the seams between tiles do not\n"
            "show. More overlap = more tiles to predict.")
        overlap_row.addWidget(self.overlap_spinbox)
        overlap_row.addStretch()
        layout.addLayout(overlap_row)

        scale_row = QHBoxLayout()
        scale_row.addWidget(QLabel("Resolution:"))
        self.scale_combo = QComboBox()
        for text, value in (("Full (1:1)", 1.0), ("Half (1:2)", 0.5),
                            ("Quarter (1:4)", 0.25)):
            self.scale_combo.addItem(text, value)
        idx = self.scale_combo.findData(
            Tiling.normalize_scale(ml_params.get("tile_scale", 1.0)))
        self.scale_combo.setCurrentIndex(max(0, idx))
        self.scale_combo.setToolTip(
            "Images are downscaled by this factor before being cut into tiles.\n"
            "Half: each tile covers 4 times more of the image (more context,\n"
            "4 times fewer tiles), with less detail.")
        scale_row.addWidget(self.scale_combo)
        scale_row.addStretch()
        layout.addLayout(scale_row)

        input_lbl = QLabel("Segmentation Input:")
        input_lbl.setToolTip(
            "How the segmentation model sees the images, for training and\n"
            "prediction: the whole image resized, or tiles of it.")
        seg_layout.addWidget(input_lbl)
        inputs = QVBoxLayout()
        inputs.setContentsMargins(16, 0, 0, 0)
        inputs.addWidget(self.whole_radio)
        inputs.addWidget(self.tiles_radio)
        inputs.addWidget(self.tiles_box)
        self.image_size_hint = QLabel()
        self.image_size_hint.setWordWrap(True)
        inputs.addWidget(self.image_size_hint)
        seg_layout.addLayout(inputs)

        self.tiles_radio.toggled.connect(self._update_tiles_box)
        self.tile_spinbox.valueChanged.connect(self._update_image_size_hint)
        self.scale_combo.currentIndexChanged.connect(
            self._update_image_size_hint)
        self._largest_image = self._largest_image_size()

    def tiling_mode(self):
        """"on" (tiles) or "off" (whole image), as saved in the parameters."""
        return "on" if self.tiles_radio.isChecked() else "off"

    def _largest_image_size(self):
        """(width, height) of the largest image of the project, read from
        the file headers (no decode), or None."""
        largest = None
        for path in getattr(self.model, "file_paths", None) or []:
            size = QImageReader(path).size()
            if size.isValid() and (largest is None or
                                   size.width() * size.height()
                                   > largest[0] * largest[1]):
                largest = (size.width(), size.height())
        return largest

    def _update_image_size_hint(self):
        """Information only: the mode is never changed for the user."""
        if self._largest_image is None:
            self.image_size_hint.setText("")
            return
        w, h = self._largest_image
        text = f"Largest image of the project: {w} × {h} px."
        tile = self.tile_spinbox.value() / (self.scale_combo.currentData()
                                            or 1.0)
        if max(w, h) > 2 * tile:
            text += (f" Tiles are recommended for images larger than twice "
                     f"the tile size ({int(2 * tile)} px at this resolution).")
        self.image_size_hint.setText(text)

    def _snap_tile_size(self):
        value = Tiling.normalize_tile_size(self.tile_spinbox.value())
        if value != self.tile_spinbox.value():
            self.tile_spinbox.setValue(value)

    def _update_overlap_range(self):
        self.overlap_spinbox.setRange(0, self.tile_spinbox.value() // 2)

    def _update_seg_options(self):
        """The segmentation settings show only when it is enabled."""
        self.seg_options.setVisible(self.enable_seg_checkbox.isChecked())

    def _update_tiles_box(self):
        """The tile settings show only when tiles are chosen."""
        self.tiles_box.setVisible(self.tiles_radio.isChecked())
        self._update_image_size_hint()

    def _deselect_all(self):
        for row in range(self.image_list.count()):
            self.image_list.item(row).setCheckState(Qt.CheckState.Unchecked)

    def done(self, result):
        self._closed = True
        self._stats_timer.stop()
        self._stop_label_stats()
        super().done(result)

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
        data["ml"]["backbone_name"] = self.backbone_combo.currentText()
        data["ml"]["seg_backbone"] = self.seg_combo.currentData()
        data["ml"]["other_labels_background"] = \
            self.other_labels_checkbox.isChecked()
        data["ml"]["confidence_threshold"] = self.conf_spinbox.value()
        data["ml"]["nms_threshold"] = self.nms_spinbox.value()
        tile = Tiling.normalize_tile_size(self.tile_spinbox.value())
        data["ml"]["tiling"] = self.tiling_mode()
        data["ml"]["tile_size"] = tile
        data["ml"]["tile_overlap"] = Tiling.normalize_overlap(
            self.overlap_spinbox.value(), tile)
        data["ml"]["tile_scale"] = self.scale_combo.currentData()

        Utils.save_parameters(data)
        return super().accept()
