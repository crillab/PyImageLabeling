"""SAM interactive assistants (multi-context).

Click / box prompts -> high-quality mask painted on the current label overlay.

Design notes:
- Lazy imports only (torch/transformers stay optional). The app must start
  even when SAM is not installed.
- Uses HuggingFace `transformers` (Sam2Model/SamModel) instead of the
  official `sam2` package to avoid compilation on Windows.
- Available assistants (general, medical, ...) are declared in
  `assistants.py`; the active one is selected in SAM settings (gear icon).
- ML-style workflow: clicks/boxes only produce a PREVIEW (in the selected
  label's color, like ML predictions). The user validates (Accept) or
  discards (Clear) it, e.g. via the floating bar or the ML panel buttons.
  Accept paints the mask into the current label overlay (undoable).
"""

import os

from PyImageLabeling.model.Core import Core
from PyImageLabeling.model.SAM.assistants import (
    get_assistant, detect_arch, DEFAULT_ASSISTANT, SAM_ASSISTANTS,
)


SAM_AVAILABLE_IMPORT_ERROR = None
try:
    import torch  # noqa: F401
    import transformers  # noqa: F401
    _SAM_DEPS_OK = True
except Exception as e:  # pragma: no cover - optional dependency
    _SAM_DEPS_OK = False
    SAM_AVAILABLE_IMPORT_ERROR = e


DEFAULT_SAM_MODEL_ID = SAM_ASSISTANTS[DEFAULT_ASSISTANT]["repo"]


def sam_dependencies_available():
    return _SAM_DEPS_OK


def _resolve_device(requested="auto"):
    if requested and requested != "auto":
        return requested
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
    except Exception:
        pass
    return "cpu"


class SAM2Assistant(Core):
    def __init__(self):
        super().__init__()
        # Session state (per image)
        self.sam_session_image_path = None
        self.sam_points_pos = []  # [(x, y)] in original image pixels
        self.sam_points_neg = []  # [(x, y)]
        self.sam_box = None  # [x1, y1, x2, y2] or None
        self.sam_preview_mask = None  # bool HxW array (preview, not painted)
        self.sam_preview_candidates = None  # bool [M, H, W] (multimask)
        self.sam_candidate_scores = []  # IoU per candidate
        self.sam_candidate_idx = 0  # currently displayed candidate
        self.sam_history = []  # prompt stack: ("pos"/"neg"/"box", payload)
        self.sam_preview_items = []  # QGraphicsItems of the preview
        self.sam_press_anchor = None  # for box drag detection
        self.sam_box_item = None  # transient QGraphicsRectItem rubber band
        self.sam_negative_next = False  # one-shot negative (toolbar toggle)
        # Cached backend
        self._sam_processor = None
        self._sam_model = None
        self._sam_device = None
        self._sam_model_id_loaded = None
        self._sam_arch_loaded = None
        self._sam_error = None
        self._sam_last_error = None

    # ------------------------------------------------------------------
    # Tool activation
    # ------------------------------------------------------------------
    def sam_assist(self):
        self.checked_button = "sam_assist"
        self.sam_negative_next = False
        print("sam_assist activated (SAM interactive)")

    def sam_toggle_negative(self):
        self.sam_negative_next = not self.sam_negative_next
        mode = "NEGATIVE (exclusion)" if self.sam_negative_next else "POSITIVE"
        print(f"sam next click mode: {mode}")
        try:
            self.view.statusBar().showMessage(
                f"SAM: next click = {mode} (right-click = negative)")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Backend loading (lazy)
    # ------------------------------------------------------------------
    def sam_backend_status(self):
        if not sam_dependencies_available():
            return (False,
                    "SAM backend not installed.\n\n"
                    "Run:\n  pip install transformers huggingface-hub pillow\n\n"
                    f"Details: {SAM_AVAILABLE_IMPORT_ERROR}")
        return (True, "ok")

    def _sam_params(self):
        try:
            from PyImageLabeling.model.Utils import Utils
            params = Utils.load_parameters().get("sam", {})
        except Exception:
            params = {}
        entry = get_assistant(params.get("assistant", DEFAULT_ASSISTANT))
        # The registry is the single source of truth: a leftover `model_id`
        # in parameters.json used to silently override the chosen assistant.
        repo = entry["repo"]
        # SamProcessor and Sam2Processor are not interchangeable (the former
        # reads size["longest_edge"], sam2 ships size:{height,width}), so
        # trust the checkpoint's own config over any stored arch.
        arch = detect_arch(repo, default=entry["arch"])
        return {
            "assistant": entry["key"],
            "repo": repo,
            "arch": arch,
            "device": params.get("device", "auto"),
            "multimask": bool(params.get("multimask", False)),
            "entry": entry,
        }

    # ------------------------------------------------------------------
    # Inference (with image-embedding cache)
    # ------------------------------------------------------------------
    _SAM_EMB_CACHE_SIZE = 3

    def _sam_oom_purge(self):
        """Free GPU/CPU caches after an out-of-memory (safe to call anytime)."""
        try:
            if hasattr(self, "_sam_emb_cache"):
                self._sam_emb_cache.clear()
            import gc
            gc.collect()
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass
        except Exception:
            pass
        print("[SAM] GPU caches purged after OOM")

    def _sam_emb_cache_key(self, image_path, rgb, repo):
        try:
            mtime = os.path.getmtime(image_path)
        except Exception:
            mtime = 0
        h, w = rgb.shape[:2]
        return (repo, str(image_path), mtime, h, w)

    def _sam_get_embeddings(self, rgb, image_path):
        """Image encoder output, cached per image (clicks reuse it).

        In batch mode (propagation) caching is skipped: each image is
        encoded once anyway, and holding N images of embeddings only
        raises the VRAM peak across runs.
        """
        import torch
        from PIL import Image
        cfg = self._sam_params()
        batch_mode = bool(getattr(self, "_sam_batch_mode", False))
        if not hasattr(self, "_sam_emb_cache"):
            self._sam_emb_cache = {}
        key = self._sam_emb_cache_key(image_path, rgb, cfg["repo"])
        if not batch_mode:
            hit = self._sam_emb_cache.get(key)
            if hit is not None:
                # refresh LRU order
                self._sam_emb_cache[key] = self._sam_emb_cache.pop(key)
                self._sam_last_emb_hit = True
                return hit
        self._sam_last_emb_hit = False
        pil_image = Image.fromarray(rgb)
        pv = self._sam_processor(images=pil_image,
                                 return_tensors="pt")["pixel_values"]
        pv = pv.to(self._sam_device)
        from PyImageLabeling.model.SAM.precision import cuda_autocast
        with torch.no_grad(), cuda_autocast(self._sam_device):
            emb = self._sam_model.get_image_embeddings(pv)
        del pv
        if batch_mode:
            return emb
        # keep VRAM bounded
        while len(self._sam_emb_cache) >= self._SAM_EMB_CACHE_SIZE:
            self._sam_emb_cache.pop(next(iter(self._sam_emb_cache)))
        self._sam_emb_cache[key] = emb
        return emb

    def sam_unload_backend(self):
        """Forget loaded weights (used when the assistant changes)."""
        self._sam_processor = None
        self._sam_model = None
        self._sam_device = None
        self._sam_model_id_loaded = None
        self._sam_arch_loaded = None
        if hasattr(self, "_sam_emb_cache"):
            self._sam_emb_cache.clear()

    def _ensure_sam_loaded(self):
        ok, msg = self.sam_backend_status()
        if not ok:
            return (False, msg)
        cfg = self._sam_params()
        if (self._sam_model is not None
                and self._sam_model_id_loaded == cfg["repo"]
                and self._sam_arch_loaded == cfg["arch"]):
            return (True, "cached")
        device = _resolve_device(cfg["device"])
        try:
            self.view.statusBar().showMessage(
                f"SAM ({cfg['entry']['name']}): loading on {device} "
                f"(first run downloads {cfg['entry']['size']})…")
        except Exception:
            pass
        try:
            from PyQt6.QtWidgets import QApplication
            QApplication.processEvents()
        except Exception:
            pass
        try:
            import warnings
            with warnings.catch_warnings():
                # HF checkpoint is tagged sam2_video; image inference is
                # validated — silence the warning.
                warnings.filterwarnings("ignore", message=".*sam2_video.*")
                if cfg["arch"] == "sam":
                    from transformers import SamModel, SamProcessor
                    processor = SamProcessor.from_pretrained(cfg["repo"])
                    model = SamModel.from_pretrained(cfg["repo"])
                else:
                    from transformers import Sam2Model, Sam2Processor
                    processor = Sam2Processor.from_pretrained(cfg["repo"])
                    model = Sam2Model.from_pretrained(cfg["repo"])
            model.to(device)
            model.eval()
            self._sam_processor = processor
            self._sam_model = model
            self._sam_device = device
            self._sam_model_id_loaded = cfg["repo"]
            self._sam_arch_loaded = cfg["arch"]
            self._sam_error = None
            print(f"[SAM] loaded {cfg['repo']} (arch={cfg['arch']}) on {device}")
            return (True, "loaded")
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._sam_error = str(e)
            return (False,
                    "Failed to load SAM weights:\n"
                    f"{e}\n\nCheck internet connection (first run downloads "
                    f"{cfg['entry']['size']}).")

    # ------------------------------------------------------------------
    # Session helpers
    # ------------------------------------------------------------------
    def _sam_current_image_rgb(self):
        item = self.get_current_image_item()
        if item is None:
            return None, None
        rgb = item.get_image_numpy_pixels_rgb()  # HxWx3 RGB uint8
        return rgb, item

    def _sam_reset_for_image(self, image_item):
        """Start a fresh prompt session when the image changed."""
        path = image_item.path_image
        if self.sam_session_image_path != path:
            self.sam_session_image_path = path
            self._sam_reset_prompts()

    def _sam_reset_prompts(self):
        self.sam_points_pos = []
        self.sam_points_neg = []
        self.sam_box = None
        self.sam_history = []
        self.sam_preview_mask = None
        self.sam_preview_candidates = None
        self.sam_candidate_scores = []
        self.sam_candidate_idx = 0
        self._sam_clear_preview_items()

    def _sam_clear_preview_items(self):
        """Remove preview graphics items (defensive: scene may be gone)."""
        for item in self.sam_preview_items[:]:
            try:
                if item.scene() is not None:
                    self.zoomable_graphics_view.scene.removeItem(item)
            except (RuntimeError, AttributeError):
                pass
        self.sam_preview_items.clear()
        if self.sam_box_item is not None:
            try:
                if self.sam_box_item.scene() is not None:
                    self.zoomable_graphics_view.scene.removeItem(
                        self.sam_box_item)
            except (RuntimeError, AttributeError):
                pass
            self.sam_box_item = None

    def _sam_preview_color(self):
        """Current label color (preview uses alpha like ML predictions)."""
        from PyQt6.QtGui import QColor
        label = self.get_current_label_item()
        if label is None:
            return QColor(0, 200, 255, 120)
        c = label.get_color()
        return QColor(c.red(), c.green(), c.blue(), 120)

    def _sam_show_preview(self, image_item, mask):
        """Display mask + prompts as preview (selected label color)."""
        import numpy as np
        from PyQt6.QtWidgets import (
            QGraphicsPixmapItem, QGraphicsEllipseItem, QGraphicsRectItem)
        from PyQt6.QtGui import QImage, QPixmap, QPen, QColor, QBrush
        from PyQt6.QtCore import Qt
        self._sam_clear_preview_items()
        self.sam_preview_mask = mask

        color = self._sam_preview_color()
        h, w = mask.shape[:2]
        rgba = np.zeros((h, w, 4), dtype=np.uint8)
        rgba[mask] = [color.red(), color.green(), color.blue(), 120]
        qimg = QImage(rgba.data, w, h, w * 4,
                      QImage.Format.Format_RGBA8888).copy()
        item = QGraphicsPixmapItem(QPixmap.fromImage(qimg))
        item.setZValue(9)
        self.zoomable_graphics_view.scene.addItem(item)
        self.sam_preview_items.append(item)

        # Point markers: green = include, red = exclude
        for (x, y) in self.sam_points_pos:
            m = QGraphicsEllipseItem(x - 5, y - 5, 10, 10)
            m.setPen(QPen(QColor(255, 255, 255, 220)))
            m.setBrush(QBrush(QColor(0, 200, 0, 220)))
            m.setZValue(20)
            self.zoomable_graphics_view.scene.addItem(m)
            self.sam_preview_items.append(m)
        for (x, y) in self.sam_points_neg:
            m = QGraphicsEllipseItem(x - 5, y - 5, 10, 10)
            m.setPen(QPen(QColor(255, 255, 255, 220)))
            m.setBrush(QBrush(QColor(220, 0, 0, 220)))
            m.setZValue(20)
            self.zoomable_graphics_view.scene.addItem(m)
            self.sam_preview_items.append(m)

        # Persistent box (dashed, label color)
        if self.sam_box is not None:
            x1, y1, x2, y2 = self.sam_box
            box = QGraphicsRectItem(x1, y1, x2 - x1, y2 - y1)
            pen = QPen(QColor(color.red(), color.green(), color.blue(), 220))
            pen.setWidth(2)
            pen.setStyle(Qt.PenStyle.DashLine)
            box.setPen(pen)
            box.setZValue(20)
            self.zoomable_graphics_view.scene.addItem(box)
            self.sam_preview_items.append(box)

        n_pos = len(self.sam_points_pos)
        n_neg = len(self.sam_points_neg)
        n_pix = int(np.count_nonzero(mask))
        label_name = self.get_current_label_item().get_name()
        n_cand = (len(self.sam_preview_candidates)
                  if self.sam_preview_candidates is not None else 1)
        cand_txt = (f"mask {self.sam_candidate_idx + 1}/{n_cand}, "
                    if n_cand > 1 else "")
        try:
            self.view.statusBar().showMessage(
                f"SAM preview → '{label_name}' ({n_pix} px, "
                f"{n_pos}+/{n_neg}-, {cand_txt}) — Apply to validate, "
                f"Cancel to discard, click to refine")
        except Exception:
            pass
        try:
            notify = getattr(self.controller, "sam_preview_changed", None)
            if callable(notify):
                notify(True)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Entry points called from Events.eventEater
    # ------------------------------------------------------------------
    def start_sam_assist(self, scene_pos, is_negative=False):
        """Click prompt: add a point and refresh the preview."""
        from PyQt6.QtWidgets import QApplication, QMessageBox
        if bool(getattr(self, "_sam_batch_mode", False)):
            try:
                self.view.statusBar().showMessage(
                    "Batch propagation running — wait for it to finish…")
            except Exception:
                pass
            return
        QApplication.setOverrideCursor(
            __import__("PyQt6.QtCore", fromlist=["Qt"]).Qt.CursorShape.WaitCursor)
        try:
            rgb, image_item = self._sam_current_image_rgb()
            if rgb is None:
                return
            if self.get_current_label_item() is None:
                QMessageBox.warning(None, "No label",
                                    "Select a label first, then use SAM Assist.")
                return
            self._sam_reset_for_image(image_item)
            x = max(0, min(int(scene_pos.x()), rgb.shape[1] - 1))
            y = max(0, min(int(scene_pos.y()), rgb.shape[0] - 1))
            neg = bool(is_negative or self.sam_negative_next)
            (self.sam_points_neg if neg else self.sam_points_pos).append((x, y))
            self.sam_history.append(("neg" if neg else "pos", (x, y)))
            self.sam_negative_next = False
            ok, msg = self._ensure_sam_loaded()
            if not ok:
                QMessageBox.critical(None, "SAM backend", msg)
                # rollback the point so next retry is clean
                (self.sam_points_neg if neg else self.sam_points_pos).pop()
                return
            mask = self._sam_predict_mask(rgb)
            if mask is None:
                if self._sam_consume_oom():
                    return
                QMessageBox.warning(None, "SAM", "No mask predicted, try other points.")
                return
            self._sam_show_preview(image_item, mask)
        finally:
            QApplication.restoreOverrideCursor()

    def sam_start_box(self, scene_pos):
        self.sam_press_anchor = (float(scene_pos.x()), float(scene_pos.y()))

    def sam_move_box(self, scene_pos):
        if self.sam_press_anchor is None:
            return
        try:
            from PyQt6.QtWidgets import QGraphicsRectItem
            from PyQt6.QtGui import QPen, QColor
            from PyQt6.QtCore import Qt
            x0, y0 = self.sam_press_anchor
            x1, y1 = float(scene_pos.x()), float(scene_pos.y())
            if self.sam_box_item is not None:
                try:
                    self.zoomable_graphics_view.scene.removeItem(self.sam_box_item)
                except Exception:
                    pass
                self.sam_box_item = None
            if abs(x1 - x0) < 5 or abs(y1 - y0) < 5:
                return
            rect_item = QGraphicsRectItem(min(x0, x1), min(y0, y1),
                                          abs(x1 - x0), abs(y1 - y0))
            pen = QPen(QColor(0, 200, 255, 220))
            pen.setWidth(2)
            pen.setStyle(Qt.PenStyle.DashLine)
            rect_item.setPen(pen)
            rect_item.setZValue(20)
            self.zoomable_graphics_view.scene.addItem(rect_item)
            self.sam_box_item = rect_item
        except Exception:
            pass

    def sam_end_box(self, scene_pos):
        anchor = self.sam_press_anchor
        self.sam_press_anchor = None
        if self.sam_box_item is not None:
            try:
                self.zoomable_graphics_view.scene.removeItem(self.sam_box_item)
            except Exception:
                pass
            self.sam_box_item = None
        if anchor is None:
            return False  # not a box, caller may treat as click
        x0, y0 = anchor
        x1, y1 = float(scene_pos.x()), float(scene_pos.y())
        if abs(x1 - x0) < 5 or abs(y1 - y0) < 5:
            return False
        if bool(getattr(self, "_sam_batch_mode", False)):
            try:
                self.view.statusBar().showMessage(
                    "Batch propagation running — wait for it to finish…")
            except Exception:
                pass
            return True
        from PyQt6.QtWidgets import QApplication, QMessageBox
        QApplication.setOverrideCursor(
            __import__("PyQt6.QtCore", fromlist=["Qt"]).Qt.CursorShape.WaitCursor)
        try:
            rgb, image_item = self._sam_current_image_rgb()
            if rgb is None:
                return True
            if self.get_current_label_item() is None:
                QMessageBox.warning(None, "No label", "Select a label first.")
                return True
            self._sam_reset_for_image(image_item)
            h, w = rgb.shape[:2]
            bx = [max(0, min(int(min(x0, x1)), w - 1)),
                  max(0, min(int(min(y0, y1)), h - 1)),
                  max(0, min(int(max(x0, x1)), w - 1)),
                  max(0, min(int(max(y0, y1)), h - 1))]
            self.sam_box = bx
            self.sam_history.append(("box", list(bx)))
            ok, msg = self._ensure_sam_loaded()
            if not ok:
                QMessageBox.critical(None, "SAM backend", msg)
                self.sam_box = None
                return True
            mask = self._sam_predict_mask(rgb)
            if mask is None:
                if self._sam_consume_oom():
                    return True
                QMessageBox.warning(None, "SAM", "No mask for this box.")
                return True
            self._sam_show_preview(image_item, mask)
            return True
        finally:
            QApplication.restoreOverrideCursor()

    def sam_clear_session(self):
        """Discard the SAM preview (nothing was painted)."""
        self._sam_reset_prompts()
        self.sam_negative_next = False
        try:
            notify = getattr(self.controller, "sam_preview_changed", None)
            if callable(notify):
                notify(False)
        except Exception:
            pass
        try:
            self.view.statusBar().showMessage("SAM preview discarded")
        except Exception:
            pass

    def sam_undo_last(self):
        """Remove the last prompt (point or box) and refresh the preview."""
        from PyQt6.QtWidgets import QApplication, QMessageBox
        if bool(getattr(self, "_sam_batch_mode", False)):
            try:
                self.view.statusBar().showMessage(
                    "Batch propagation running — wait for it to finish…")
            except Exception:
                pass
            return
        if not self.sam_history:
            try:
                self.view.statusBar().showMessage("SAM: nothing to undo")
            except Exception:
                pass
            return
        kind, payload = self.sam_history.pop()
        if kind == "pos" and payload in self.sam_points_pos:
            self.sam_points_pos.remove(payload)
        elif kind == "neg" and payload in self.sam_points_neg:
            self.sam_points_neg.remove(payload)
        elif kind == "box":
            self.sam_box = None
        points, labels = self._sam_session_prompts()
        if not points and self.sam_box is None:
            self._sam_reset_prompts()
            try:
                notify = getattr(self.controller, "sam_preview_changed", None)
                if callable(notify):
                    notify(False)
            except Exception:
                pass
            return
        QApplication.setOverrideCursor(
            __import__("PyQt6.QtCore", fromlist=["Qt"]).Qt.CursorShape.WaitCursor)
        try:
            rgb, image_item = self._sam_current_image_rgb()
            if rgb is None:
                return
            mask = self._sam_predict_mask(rgb)
            if mask is None:
                self._sam_consume_oom()
                self._sam_reset_prompts()
                return
            self._sam_show_preview(image_item, mask)
        finally:
            QApplication.restoreOverrideCursor()

    def sam_cycle_candidate(self):
        """Show the next multimask candidate (needs multimask enabled)."""
        if (self.sam_preview_candidates is None
                or len(self.sam_preview_candidates) <= 1):
            try:
                self.view.statusBar().showMessage(
                    "SAM: single mask (enable Multimask in SAM settings "
                    "for alternatives)")
            except Exception:
                pass
            return
        self.sam_candidate_idx = (
            (self.sam_candidate_idx + 1) % len(self.sam_preview_candidates))
        mask = self.sam_preview_candidates[self.sam_candidate_idx]
        image_item = self.get_current_image_item()
        if image_item is None:
            return
        self._sam_show_preview(image_item, mask)

    def sam_accept_session(self):
        """Validate the preview: paint it into the selected label overlay."""
        from PyQt6.QtWidgets import QMessageBox
        mask = self.sam_preview_mask
        if mask is None or (hasattr(mask, "sum") and mask.sum() == 0):
            QMessageBox.information(
                None, "No SAM preview",
                "Click on the image (or drag a box) to get a SAM preview first.")
            return
        image_item = self.get_current_image_item()
        label_item = self.get_current_label_item()
        if image_item is None or label_item is None:
            return
        label_id = label_item.get_label_id()
        if label_id not in image_item.labeling_overlays:
            QMessageBox.warning(
                None, "No overlay",
                f"Current image has no overlay for label "
                f"'{label_item.get_name()}'.")
            return
        self._sam_paint_mask(image_item, mask)
        n_pix = int(mask.sum())
        try:
            self.controller.ml_invalidate_stats_cache(image_item.path_image)
        except Exception:
            pass
        self._sam_reset_prompts()
        self.sam_negative_next = False
        try:
            notify = getattr(self.controller, "sam_preview_changed", None)
            if callable(notify):
                notify(False)
        except Exception:
            pass
        try:
            self.view.statusBar().showMessage(
                f"SAM mask accepted → '{label_item.get_name()}' ({n_pix} px)")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------
    def _sam_infer_candidates(self, rgb, image_path, points, labels, box):
        """Run SAM decoder on cached embeddings.

        Returns (masks, scores) with masks as bool numpy [M, H, W] and
        scores as list of floats, or (None, None) if nothing predicted.
        Prompt formatting follows each arch's processor convention, in
        original-image pixel coordinates:
        - sam2: points [[img][obj][pts][xy]], boxes [[img][box][xyxy]]
        - sam:  points [[img][pts][xy]],      boxes [[img][box][xyxy]]

        On CUDA out-of-memory the caches are purged and the call is
        retried once; persistent failure returns (None, None) with
        self._sam_last_error == "gpu-oom" (no exception escapes to Qt).
        """
        import torch
        import torch.nn.functional as F
        from PIL import Image
        cfg = self._sam_params()
        arch = cfg["arch"]
        h, w = rgb.shape[:2]
        if not points and box is None:
            return None, None
        self._sam_last_error = None
        for attempt in (1, 2):
            try:
                return self._sam_infer_once(
                    rgb, image_path, cfg, arch, h, w, points, labels, box, F)
            except Exception as e:
                if not self._sam_is_oom(e):
                    raise
                print(f"[SAM] OOM on attempt {attempt}, purging caches")
                self._sam_oom_purge()
                if attempt == 2:
                    self._sam_last_error = "gpu-oom"
                    return None, None
        self._sam_last_error = "gpu-oom"
        return None, None

    @staticmethod
    def _sam_is_oom(exc):
        import torch
        if isinstance(exc, torch.cuda.OutOfMemoryError):
            return True
        return ("out of memory" in str(exc).lower()
                and isinstance(exc, RuntimeError))

    def _sam_consume_oom(self):
        """Show OOM guidance if the last failure was OOM (then clear it)."""
        if getattr(self, "_sam_last_error", None) != "gpu-oom":
            return False
        self._sam_last_error = None
        try:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                None, "Out of memory",
                "SAM ran out of memory (GPU/CPU).\n\n"
                "Caches were purged — you can retry right away.\n"
                "If it persists: close images, use SAM2-Tiny, or switch "
                "the device to CPU in SAM settings (gear icon).")
        except Exception:
            pass
        return True

    def _sam_infer_once(self, rgb, image_path, cfg, arch, h, w, points,
                        labels, box, F):
        import torch
        from PIL import Image
        pil_image = Image.fromarray(rgb)
        proc_kwargs = {"images": pil_image, "return_tensors": "pt"}
        if points:
            if arch == "sam":
                proc_kwargs["input_points"] = [points]
                proc_kwargs["input_labels"] = [labels]
            else:
                proc_kwargs["input_points"] = [[points]]
                proc_kwargs["input_labels"] = [[labels]]
        if box is not None:
            proc_kwargs["input_boxes"] = [[box]]
        inputs = self._sam_processor(**proc_kwargs)
        fwd = {k: v.to(self._sam_device)
               for k, v in inputs.items()
               if k in ("input_points", "input_labels", "input_boxes")}
        emb = self._sam_get_embeddings(rgb, image_path)
        from PyImageLabeling.model.SAM.precision import cuda_autocast
        with torch.no_grad(), cuda_autocast(self._sam_device):
            outputs = self._sam_model(
                pixel_values=None,
                image_embeddings=emb,
                **fwd,
                multimask_output=cfg["multimask"],
            )
        # pred_masks is 5D [batch, X, Y, 256, 256] where {X, Y} are
        # {objects, masks} in arch-dependent order. We send a single
        # object, so merging the two middle dims yields [batch, M, 256, 256].
        pm = outputs.pred_masks
        masks = pm.reshape(pm.shape[0], -1, pm.shape[-2], pm.shape[-1])[0]
        iou = outputs.iou_scores.reshape(outputs.iou_scores.shape[0], -1)[0]
        if arch == "sam":
            # SAM-v1 pads its 1024 input -> crop the valid region first.
            L = max(h, w)
            vh = max(1, round(h * 256 / L))
            vw = max(1, round(w * 256 / L))
            masks = masks[:, :vh, :vw]
        prob = F.interpolate(masks.unsqueeze(1).to(torch.float32),
                             size=(h, w), mode="bilinear",
                             align_corners=False).squeeze(1)
        bool_masks = (prob.sigmoid().cpu().numpy() >= 0.5)
        scores = iou.detach().cpu().tolist()
        if not isinstance(scores, list):
            scores = [float(scores)]
        # drop empty masks (keep order for cycling)
        kept_m, kept_s = [], []
        for m, s in zip(bool_masks, scores):
            if m.sum() > 0:
                kept_m.append(m.astype(bool))
                kept_s.append(float(s))
        if not kept_m:
            return None, None
        import numpy as np
        return np.stack(kept_m), kept_s

    def _sam_session_prompts(self):
        points = [[x, y] for (x, y) in self.sam_points_pos]
        labels = [1] * len(points)
        for (x, y) in self.sam_points_neg:
            points.append([x, y])
            labels.append(0)
        return points, labels

    def _sam_predict_mask(self, rgb):
        """Session wrapper: infer all candidates, show the best one."""
        import numpy as np
        image_item = self.get_current_image_item()
        path = image_item.path_image if image_item is not None else ""
        points, labels = self._sam_session_prompts()
        masks, scores = self._sam_infer_candidates(
            rgb, path, points, labels, self.sam_box)
        if masks is None:
            self.sam_preview_candidates = None
            self.sam_candidate_idx = 0
            return None
        self.sam_preview_candidates = masks
        self.sam_candidate_scores = scores
        # default to highest-IoU candidate
        try:
            self.sam_candidate_idx = int(np.argmax(scores))
        except Exception:
            self.sam_candidate_idx = 0
        return masks[self.sam_candidate_idx]

    def _sam_collapse_undo(self, image_item, label_id):
        """Collapse a batch paint to ONE undo step (bounds RAM).

        Batch painting (propagation) appends one full-mask undo entry per
        image; without collapsing, N images x depth entries of mostly-opaque
        masks accumulate and can exhaust RAM on the second run.
        """
        try:
            from collections import deque
            overlay = image_item.labeling_overlays.get(label_id)
            if overlay is None:
                return
            dq = overlay.undo_deque
            if len(dq) <= 2:
                return
            overlay.undo_deque = deque([dq[0], dq[-1]], maxlen=dq.maxlen)
            overlay.previous_labeling_overlay_pixmap = \
                overlay.labeling_overlay_pixmap.copy()
        except Exception:
            pass

    def _sam_paint_mask(self, image_item, mask):
        """Paint bool mask onto current overlay (creates undo entry)."""
        import numpy as np
        from PyQt6.QtGui import QImage, QPixmap
        overlay = image_item.get_labeling_overlay()
        color = self.get_current_label_item().get_color()
        h, w = mask.shape[:2]
        r, g, b = color.red(), color.green(), color.blue()
        rgba = np.zeros((h, w, 4), dtype=np.uint8)
        rgba[mask] = (r, g, b, 255)
        qimg = QImage(rgba.data, w, h, w * 4, QImage.Format.Format_RGBA8888)
        qimg = qimg.copy()  # detach from numpy buffer
        pix = QPixmap.fromImage(qimg)
        painter = overlay.get_painter()
        painter.drawPixmap(0, 0, pix)
        try:
            self.controller.ml_invalidate_stats_cache(image_item.path_image)
        except Exception:
            pass
        image_item.update_labeling_overlay()
        try:
            self.controller.ml_update_stats()
        except Exception:
            pass
