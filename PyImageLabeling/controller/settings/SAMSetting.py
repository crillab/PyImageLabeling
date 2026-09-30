from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QGroupBox, QCheckBox, QPushButton, QApplication,
    QDoubleSpinBox,
)
from PyQt6.QtCore import Qt

from PyImageLabeling.model.Utils import Utils
from PyImageLabeling.model.SAM.assistants import (
    list_assistants, get_assistant, assistant_cache_status,
    DEFAULT_ASSISTANT,
)


class SAMSetting(QDialog):
    """Settings dialog for the SAM Assist tool (gear icon).

    Lets the user pick one assistant per context (general, medical, ...),
    the device, and multimask output. Persists to parameters.json ["sam"].
    """

    def __init__(self, parent, model):
        super().__init__(parent)
        self.model = model
        self.setWindowTitle("SAM Assist Settings")
        self.resize(520, 420)

        params = Utils.load_parameters().get("sam", {})
        self._initial_assistant = params.get("assistant", DEFAULT_ASSISTANT)

        layout = QVBoxLayout()

        # ---- Assistant group ----
        assist_group = QGroupBox("Assistant (one per context)")
        assist_layout = QVBoxLayout()

        self.assistant_combo = QComboBox()
        for entry in list_assistants():
            self.assistant_combo.addItem(
                f"{entry['context']} — {entry['name']} ({entry['size']})",
                entry["key"])
        idx = self.assistant_combo.findData(
            params.get("assistant", DEFAULT_ASSISTANT))
        if idx >= 0:
            self.assistant_combo.setCurrentIndex(idx)
        self.assistant_combo.currentIndexChanged.connect(
            self._refresh_description)
        assist_layout.addWidget(self.assistant_combo)

        self.desc_label = QLabel()
        self.desc_label.setWordWrap(True)
        self.desc_label.setTextFormat(Qt.TextFormat.RichText)
        assist_layout.addWidget(self.desc_label)

        self.cache_label = QLabel()
        assist_layout.addWidget(self.cache_label)

        pred_row = QHBoxLayout()
        self.predownload_btn = QPushButton("Pre-download weights")
        self.predownload_btn.setToolTip(
            "Download this assistant's weights now instead of on first use.")
        self.predownload_btn.clicked.connect(self._predownload)
        pred_row.addWidget(self.predownload_btn)
        pred_row.addStretch()
        assist_layout.addLayout(pred_row)

        assist_group.setLayout(assist_layout)
        layout.addWidget(assist_group)

        # ---- Inference group ----
        infer_group = QGroupBox("Inference")
        infer_layout = QVBoxLayout()

        dev_row = QHBoxLayout()
        dev_row.addWidget(QLabel("Device:"))
        self.device_combo = QComboBox()
        self.device_combo.addItems(["auto", "cuda", "cpu"])
        dev_idx = self.device_combo.findText(params.get("device", "auto"))
        if dev_idx >= 0:
            self.device_combo.setCurrentIndex(dev_idx)
        self.device_combo.setToolTip(
            "auto = GPU if available, else CPU.")
        dev_row.addWidget(self.device_combo)
        dev_row.addStretch()
        infer_layout.addLayout(dev_row)

        self.multimask_checkbox = QCheckBox(
            "Multimask output (pick best of 3 candidates)")
        self.multimask_checkbox.setChecked(bool(params.get("multimask", False)))
        self.multimask_checkbox.setToolTip(
            "Slower but better on ambiguous prompts. "
            "Single mask is fine for most cases.")
        infer_layout.addWidget(self.multimask_checkbox)

        infer_group.setLayout(infer_layout)
        layout.addWidget(infer_group)

        # ---- Propagation group ----
        prop_group = QGroupBox("One-shot propagation")
        prop_layout = QVBoxLayout()
        dino_row = QHBoxLayout()
        dino_row.addWidget(QLabel("Matching backbone:"))
        self.dino_combo = QComboBox()
        self.dino_combo.addItem("DINOv2-small · fast (~90MB)", "small")
        self.dino_combo.addItem("DINOv2-base · stronger (~350MB)", "base")
        dino_idx = self.dino_combo.findData(params.get("dino_model",
                                                        "small"))
        if dino_idx >= 0:
            self.dino_combo.setCurrentIndex(dino_idx)
        self.dino_combo.setToolTip(
            "Base matches objects across scales/poses better; "
            "downloaded once on first use.")
        dino_row.addWidget(self.dino_combo)
        dino_row.addStretch()
        prop_layout.addLayout(dino_row)
        thr_row = QHBoxLayout()
        thr_row.addWidget(QLabel("Confidence threshold:"))
        self.thr_spinbox = QDoubleSpinBox()
        self.thr_spinbox.setRange(0.0, 1.0)
        self.thr_spinbox.setSingleStep(0.05)
        self.thr_spinbox.setDecimals(2)
        self.thr_spinbox.setValue(float(params.get("propagate_threshold",
                                                   0.25)))
        self.thr_spinbox.setToolTip(
            "Reference-to-query similarity below this skips the image.")
        thr_row.addWidget(self.thr_spinbox)
        thr_row.addStretch()
        prop_layout.addLayout(thr_row)
        prop_group.setLayout(prop_layout)
        layout.addWidget(prop_group)

        # ---- Buttons ----
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.setLayout(layout)
        self._refresh_description()

    # ------------------------------------------------------------------
    def _selected_entry(self):
        return get_assistant(self.assistant_combo.currentData())

    def _refresh_description(self):
        entry = self._selected_entry()
        self.desc_label.setText(
            f"<b>{entry['name']}</b> · {entry['context']}<br>"
            f"Model: <i>{entry['repo']}</i> · {entry['size']} · "
            f"{entry['device_hint']}<br><br>{entry['description']}")
        downloaded, size_mb = assistant_cache_status(entry["repo"])
        if downloaded:
            self.cache_label.setText(
                f"Weights: downloaded ✓ ({size_mb} MB in local cache)")
            self.cache_label.setStyleSheet("color: green;")
        else:
            self.cache_label.setText(
                f"Weights: not downloaded "
                f"(~{entry['size']} on first use or via Pre-download)")
            self.cache_label.setStyleSheet("color: gray;")

    def _predownload(self):
        from huggingface_hub import snapshot_download
        entry = self._selected_entry()
        self.predownload_btn.setEnabled(False)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            QApplication.processEvents()
            snapshot_download(repo_id=entry["repo"])
            self.cache_label.setText("Weights: downloaded ✓")
            self.cache_label.setStyleSheet("color: green;")
        except Exception as e:
            self.cache_label.setText(f"Download failed: {e}")
            self.cache_label.setStyleSheet("color: red;")
        finally:
            QApplication.restoreOverrideCursor()
            self.predownload_btn.setEnabled(True)

    # ------------------------------------------------------------------
    def accept(self):
        data = Utils.load_parameters()
        if "sam" not in data:
            data["sam"] = {}
        data["sam"]["assistant"] = self.assistant_combo.currentData()
        # The repo/arch come from the registry: drop any stale override so the
        # assistant choice is the single source of truth.
        data["sam"].pop("model_id", None)
        data["sam"].pop("arch", None)
        data["sam"]["device"] = self.device_combo.currentText()
        data["sam"]["multimask"] = self.multimask_checkbox.isChecked()
        data["sam"]["propagate_threshold"] = self.thr_spinbox.value()
        data["sam"]["dino_model"] = self.dino_combo.currentData()
        Utils.save_parameters(data)
        self.assistant_changed = (
            self.assistant_combo.currentData() != self._initial_assistant)
        return super().accept()
