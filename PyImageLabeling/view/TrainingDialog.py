"""Window shown while a model trains: settings, what the training images
hold, figures of each epoch, loss curve, and the full log on demand."""

from PyQt6.QtCore import Qt, QPointF, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QPixmap, QIcon, QPolygonF
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

MAX_LOG_LINES = 2000

LOSS_TOOLTIP = (
    "Cross-entropy, averaged over the pixels: it does not depend on the\n"
    "tile or image size.\n\n"
    "Reference: the loss of a model that answers the proportions of the\n"
    "labels for every pixel, without looking at the image. The percentage\n"
    "compares the loss to it: 100 % = nothing learnt from the image yet,\n"
    "0 % = no error.")

TRAIN_IOU_TOOLTIP = (
    "Intersection over union of each label on the training inputs of the\n"
    "last epoch (with their random flips and colour changes). Optimistic:\n"
    "the model is scored on what it learns from. The validation IoU, at\n"
    "the end, is measured on images it has not seen.")


def format_duration(seconds):
    seconds = int(round(seconds))
    if seconds < 60:
        return f"{seconds} s"
    minutes, seconds = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes} min {seconds:02d} s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours} h {minutes:02d} min"


def format_bytes(n):
    if n >= 1024 ** 3:
        return f"{n / 1024 ** 3:.1f} GB"
    return f"{n / 1024 ** 2:.0f} MB"


class LossCurve(QWidget):
    """Loss of each epoch (solid) and its reference (dashed)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.losses = []
        self.references = []
        self.setMinimumHeight(90)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Fixed)
        self.setToolTip("Loss of each epoch (solid) and reference loss "
                        "(dashed).\n\n" + LOSS_TOOLTIP)

    def add(self, loss, reference=None):
        self.losses.append(loss)
        self.references.append(reference)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        palette = self.palette()
        text = palette.color(palette.ColorRole.WindowText)
        grid = QColor(text)
        grid.setAlpha(50)
        rect = self.rect().adjusted(40, 8, -8, -8)
        painter.setPen(QPen(grid, 1))
        painter.drawRect(rect)
        values = [v for v in self.losses + self.references if v is not None]
        if not values:
            painter.setPen(text)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter,
                             "Loss curve: after the first epoch")
            return
        top = max(values) * 1.05 or 1.0
        n = max(len(self.losses), 2)

        def point(i, v):
            x = rect.left() + rect.width() * i / (n - 1)
            y = rect.bottom() - rect.height() * v / top
            return QPointF(x, y)

        painter.setPen(text)
        font = painter.font()
        font.setPointSizeF(max(6.0, font.pointSizeF() * 0.8))
        painter.setFont(font)
        painter.drawText(0, rect.top(), 36, 14,
                         Qt.AlignmentFlag.AlignRight, f"{top:.2f}")
        painter.drawText(0, rect.bottom() - 12, 36, 14,
                         Qt.AlignmentFlag.AlignRight, "0")

        refs = [(i, v) for i, v in enumerate(self.references) if v is not None]
        if refs:
            pen = QPen(QColor(text), 1, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.drawPolyline(QPolygonF([point(i, v) for i, v in refs]))
        accent = palette.color(palette.ColorRole.Highlight)
        painter.setPen(QPen(accent, 2))
        pts = [point(i, v) for i, v in enumerate(self.losses)]
        if len(pts) == 1:
            painter.drawEllipse(pts[0], 2, 2)
        else:
            painter.drawPolyline(QPolygonF(pts))


class TrainingDialog(QDialog):
    """Fed by the signals of the TrainingWorker: set_status(), add_log(),
    on_epoch(), on_stats(); then finish(), cancelled() or fail().

    Cancel (or Escape, or closing the window) asks for a confirmation, then
    emits cancel_requested; the window closes once the training has
    stopped (cancelled())."""

    cancel_requested = pyqtSignal()

    COLUMNS = ("Label", "Train images", "Pixels", "Tiles holding it",
               "IoU (train)", "IoU (val)")

    def __init__(self, n_images, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Training Model")
        self.running = True
        self.cancelling = False
        self.has_stats = False
        self.val_images = None
        self.classes = []
        self.rows = {}

        layout = QVBoxLayout(self)

        self.status_label = QLabel(
            f"Initializing training…\n{n_images} image(s) selected")
        font = self.status_label.font()
        font.setBold(True)
        self.status_label.setFont(font)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.settings_label = QLabel()
        self.settings_label.setWordWrap(True)
        self.settings_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.settings_label)

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.verticalHeader().setDefaultSectionSize(
            self.table.fontMetrics().height() + 8)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in range(1, len(self.COLUMNS)):
            header.setSectionResizeMode(
                col, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeaderItem(4).setToolTip(TRAIN_IOU_TOOLTIP)
        self.table.horizontalHeaderItem(2).setToolTip(
            "Share of the pixels of the training images.")
        self.table.horizontalHeaderItem(3).setToolTip(
            "Inputs of the last epoch holding at least one pixel of the\n"
            "label. With tiles, half of them are centred on an annotated\n"
            "pixel, so that small labels are seen.")
        self.table.setVisible(False)
        layout.addWidget(self.table)

        self.epoch_label = QLabel()
        self.epoch_label.setWordWrap(True)
        self.epoch_label.setToolTip(LOSS_TOOLTIP)
        layout.addWidget(self.epoch_label)

        self.curve = LossCurve()
        self.curve.setVisible(False)
        layout.addWidget(self.curve)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)          # busy until the first epoch
        layout.addWidget(self.progress)

        self.details_button = QToolButton()
        self.details_button.setText("Details (training log)")
        self.details_button.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.details_button.setArrowType(Qt.ArrowType.RightArrow)
        self.details_button.setCheckable(True)
        self.details_button.setAutoRaise(True)
        self.details_button.toggled.connect(self._toggle_details)
        layout.addWidget(self.details_button)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(MAX_LOG_LINES)
        self.log_view.setVisible(False)
        layout.addWidget(self.log_view, 1)

        # Cancel while it trains, Close once it is over
        self.buttons = QDialogButtonBox()
        self.cancel_button = self.buttons.addButton(
            QDialogButtonBox.StandardButton.Cancel)
        self.cancel_button.setToolTip(
            "Stop the training. Nothing of it is kept.")
        self.close_button = self.buttons.addButton(
            QDialogButtonBox.StandardButton.Close)
        self.close_button.setVisible(False)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.setMinimumWidth(560)
        self.resize(680, 520)

    # ---- worker signals -------------------------------------------------

    def set_status(self, text):
        self._status(text)

    def add_log(self, message):
        self.log_view.appendPlainText(message)

    def on_epoch(self, current, total, loss):
        """Every training path sends this one. A path that sends no stats
        (DINOv2 probe) gets the loss and its curve from here."""
        self.progress.setRange(0, total)
        self.progress.setValue(current)
        self._status(f"Epoch {current}/{total}")
        if not self.has_stats:
            self.epoch_label.setText(f"<b>Loss</b> {loss:.4f}")
            self.curve.setVisible(True)
            self.curve.add(loss)

    def on_stats(self, stats):
        kind = stats.get("kind")
        if kind == "setup":
            self._show_setup(stats)
        elif kind == "epoch":
            self._show_epoch(stats)

    # ---- end ------------------------------------------------------------

    def finish(self, val_metrics, mode, num_classes):
        self.running = False
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        self.status_label.setText("Training complete")
        vm = val_metrics or {}
        lines = [f"Mode: {mode} · {num_classes} classes"]
        bits = []
        if "seg_miou" in vm:
            bits.append(f"mIoU <b>{vm['seg_miou']:.3f}</b>")
        if "seg_loss" in vm:
            bits.append(f"segmentation loss {vm['seg_loss']:.4f}")
        if "det_loss" in vm:
            bits.append(f"detection loss {vm['det_loss']:.4f}")
        if bits:
            on = (f" on {self.val_images} image(s)" if self.val_images
                  else "")
            lines.append(f"Validation{on}: " + " · ".join(bits))
        else:
            lines.append("No validation: at least 5 annotated images are "
                         "needed to keep some aside.")
        self.epoch_label.setText(self.epoch_label.text() + "<br><br>"
                                 + "<br>".join(lines))
        for c, iou in (vm.get("seg_iou") or {}).items():
            self._set_cell(c, 5, f"{iou:.3f}")
        self._stopped()

    def cancelled(self):
        """The training has stopped after a cancel: nothing to show."""
        self._stopped()
        self.close()

    def fail(self):
        self._stopped()
        self.close()

    def closeEvent(self, event):
        if self.running:
            event.ignore()
            self.request_cancel()
            return
        super().closeEvent(event)

    def reject(self):
        if self.running:
            self.request_cancel()       # Cancel button, Escape
        else:
            super().reject()

    def request_cancel(self):
        """Ask whether to stop the training; if so, tell the worker."""
        if not self.running or self.cancelling:
            return
        if not self._confirm_cancel():
            return
        if not self.running:            # it ended while the question was up
            return
        self.cancelling = True
        self.cancel_button.setEnabled(False)
        self.status_label.setText(
            "Cancelling… (the current step ends first)")
        self.progress.setRange(0, 0)
        self.cancel_requested.emit()

    def _confirm_cancel(self):
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle("Cancel Training")
        box.setText("Stop the training?")
        box.setInformativeText("What has been trained so far is lost.")
        stop = box.addButton("Stop Training",
                             QMessageBox.ButtonRole.DestructiveRole)
        keep = box.addButton("Continue Training",
                             QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(keep)
        box.exec()
        return box.clickedButton() is stop

    # ---- internals ------------------------------------------------------

    def _stopped(self):
        self.running = False
        self.cancel_button.setVisible(False)
        self.close_button.setVisible(True)
        self.close_button.setDefault(True)

    def _status(self, text):
        # queued figures of the last steps must not hide "Cancelling…"
        if not self.cancelling:
            self.status_label.setText(text)

    def _toggle_details(self, shown):
        self.details_button.setArrowType(
            Qt.ArrowType.DownArrow if shown else Qt.ArrowType.RightArrow)
        self.log_view.setVisible(shown)
        if shown and self.height() < 700:
            self.resize(self.width(), self.height() + 220)

    def _uses_tiles(self):
        return getattr(self, "_unit", "tiles") == "tiles"

    def _show_setup(self, s):
        self.has_stats = True
        self._unit = s.get("unit", "tiles")
        self.val_images = s.get("val_images")
        pretrained = "pretrained" if s.get("pretrained") else "not pretrained"
        lines = [
            f"<b>Input:</b> {s.get('input', '?')}",
            f"<b>Backbone:</b> {s.get('backbone', '?')} ({pretrained}) · "
            f"{s.get('device', '?')}",
            f"<b>Epochs</b> {s.get('epochs', '?')} · <b>Batch</b> "
            f"{s.get('batch', '?')} · <b>Learning rate</b> {s.get('lr', 0):g}",
        ]
        images = (f"<b>Images:</b> {s.get('train_images', '?')} train / "
                  f"{s.get('val_images', '?')} validation")
        if s.get("tiles_per_epoch"):
            images += f" · {s['tiles_per_epoch']} {self._unit} per epoch"
        lines.append(images)
        self.settings_label.setText("<br>".join(lines))

        self.classes = s.get("classes") or []
        if not self.classes:
            return
        if not self._uses_tiles():
            self.table.horizontalHeaderItem(3).setText("Images holding it")
        self.table.setRowCount(len(self.classes))
        images = s.get("images_per_class") or {}
        pixels = s.get("pixels_per_class") or {}
        total = sum(pixels.values())
        for row, cls in enumerate(self.classes):
            c = cls["cls"]
            self.rows[c] = row
            item = QTableWidgetItem(cls["name"])
            if cls.get("color") is not None:
                swatch = QPixmap(12, 12)
                swatch.fill(QColor(*cls["color"]))
                item.setIcon(QIcon(swatch))
            self.table.setItem(row, 0, item)
            self._set_cell(c, 1, str(images.get(c, 0)) if images else "–")
            self._set_cell(c, 2, f"{100 * pixels.get(c, 0) / total:.1f} %"
                           if total else "–")
            for col in (3, 4, 5):
                self._set_cell(c, col, "–")
        self.table.setVisible(True)
        height = (self.table.horizontalHeader().height()
                  + sum(self.table.rowHeight(r)
                        for r in range(self.table.rowCount())) + 4)
        self.table.setFixedHeight(min(height, 260))

    def _set_cell(self, c, col, text):
        row = self.rows.get(c)
        if row is None:
            return
        item = QTableWidgetItem(text)
        if col:
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight
                                  | Qt.AlignmentFlag.AlignVCenter)
        self.table.setItem(row, col, item)

    def _show_epoch(self, s):
        epoch, total = s["epoch"], s["total"]
        self.progress.setRange(0, total)
        self.progress.setValue(epoch)
        self._status(f"Epoch {epoch}/{total}")

        lines = []
        loss = s.get("loss", 0.0)
        reference = s.get("reference")
        seg_loss = s.get("seg_loss")
        if s.get("det_loss") is not None and seg_loss is not None:
            lines.append(f"<b>Loss</b> {loss:.4f} (detection "
                         f"{s['det_loss']:.4f}, segmentation {seg_loss:.4f})")
            shown = seg_loss
        else:
            lines.append(f"<b>Loss</b> {loss:.4f}")
            shown = loss if seg_loss is not None else None
        if reference and shown is not None:
            lines[-1] += (f" — reference {reference:.4f}: "
                          f"<b>{100 * shown / reference:.0f} %</b> of it")
        if s.get("pixel_accuracy") is not None:
            lines.append(f"Pixel accuracy (training inputs) "
                         f"{100 * s['pixel_accuracy']:.1f} %")
        timing = [f"{format_duration(s.get('seconds', 0))} per epoch"]
        if epoch < total:
            timing.append(f"about {format_duration(s.get('seconds', 0) * (total - epoch))} left")
        if s.get("gpu_bytes"):
            timing.append(f"GPU {format_bytes(s['gpu_bytes'])}")
        if s.get("batch"):
            timing.append(f"batch {s['batch']}")
        lines.append(" · ".join(timing))
        self.epoch_label.setText("<br>".join(lines))

        present, inputs = s.get("present"), s.get("inputs")
        if present and inputs:
            for c, n in enumerate(present):
                self._set_cell(c, 3, f"{n} ({100 * n / inputs:.0f} %)")
        for c, iou in (s.get("train_iou") or {}).items():
            self._set_cell(c, 4, f"{iou:.3f}")

        self.curve.setVisible(True)
        self.curve.add(shown if shown is not None else loss, reference)
