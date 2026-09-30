from PyImageLabeling.controller.Events import Events
from PyImageLabeling.controller.settings.SAMSetting import SAMSetting
from PyQt6.QtCore import Qt, QPoint


class SAMEvents(Events):
    def __init__(self):
        super().__init__()
        self._sam_confirm_bar = None
        # True while the text-to-mask dialog owns its Apply/Cancel:
        # the floating bar must not pop up on top of it.
        self._sam_text_mode = False

    def sam_assist(self):
        self.model.remove_contour()
        self.desactivate_buttons_labeling_image_bar(self.sam_assist.__name__)
        self.all_events(self.sam_assist.__name__)
        try:
            self.view.zoomable_graphics_view.change_cursor("magic_ball")
        except Exception:
            self.view.zoomable_graphics_view.change_cursor("magic")
        self.model.sam_assist()
        self.view.statusBar().showMessage(
            "SAM Assist: left-click=+ point, shift/right-click=- point, drag=box")

    def sam_preview_changed(self, has_preview):
        """Called by the model when a SAM preview appears/disappears."""
        if getattr(self, "_sam_text_mode", False):
            return
        if has_preview:
            self._sam_show_confirm_bar()
        else:
            self._sam_hide_confirm_bar()

    def _sam_show_confirm_bar(self):
        from PyQt6.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QLabel, QDialogButtonBox,
            QPushButton)
        if self._sam_confirm_bar is None:
            bar = QDialog(self.view.zoomable_graphics_view)
            bar.setWindowFlag(Qt.WindowType.FramelessWindowHint)
            bar.setObjectName("apply_cancel_bar")
            layout = QVBoxLayout()
            layout.addWidget(QLabel(
                "SAM preview — Apply to validate into the selected label, "
                "Cancel to discard.\nClick the image to refine."))
            extra = QHBoxLayout()
            self._sam_undo_btn = QPushButton("Undo point")
            self._sam_undo_btn.setToolTip("Remove the last point/box prompt")
            self._sam_undo_btn.clicked.connect(self.sam_undo_point)
            extra.addWidget(self._sam_undo_btn)
            self._sam_prev_btn = QPushButton("Previous mask")
            self._sam_prev_btn.setToolTip("Show previous candidate")
            self._sam_prev_btn.clicked.connect(self.sam_prev_mask)
            extra.addWidget(self._sam_prev_btn)
            self._sam_next_btn = QPushButton("Next mask")
            self._sam_next_btn.setToolTip(
                "Cycle multimask candidates (needs Multimask in SAM settings)")
            self._sam_next_btn.clicked.connect(self.sam_next_mask)
            extra.addWidget(self._sam_next_btn)
            extra.addStretch()
            layout.addLayout(extra)
            buttons = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok
                | QDialogButtonBox.StandardButton.Cancel)
            for button in buttons.buttons():
                button.setObjectName("dialog")
            buttons.accepted.connect(self.sam_accept)
            buttons.rejected.connect(self.sam_clear)
            layout.addWidget(buttons)
            bar.setLayout(layout)
            self._sam_confirm_bar = bar
        try:
            self._sam_confirm_bar.move(
                self.view.zoomable_graphics_view.mapToGlobal(QPoint(10, 10)))
        except Exception:
            pass
        self._sam_confirm_bar.show()
        self._sam_confirm_bar.raise_()

    def _sam_hide_confirm_bar(self):
        if self._sam_confirm_bar is not None:
            try:
                self._sam_confirm_bar.hide()
            except Exception:
                pass

    def sam_prev_mask(self):
        """Show previous candidate."""
        if (self.model.sam_preview_candidates is None
                or len(self.model.sam_preview_candidates) <= 1):
            return
        n = len(self.model.sam_preview_candidates)
        self.model.sam_candidate_idx = (
            (self.model.sam_candidate_idx - 1) % n)
        mask = self.model.sam_preview_candidates[self.model.sam_candidate_idx]
        image_item = self.model.get_current_image_item()
        if image_item is not None:
            self.model._sam_show_preview(image_item, mask)

    def sam_assist_setting(self):
        self.all_events(self.sam_assist_setting.__name__)
        dialog = SAMSetting(self.view.zoomable_graphics_view, self.model)
        if dialog.exec():
            if getattr(dialog, "assistant_changed", False):
                self.model.sam_unload_backend()
                self.model.sam_clear_session()
            from PyImageLabeling.model.SAM.assistants import get_assistant
            from PyImageLabeling.model.Utils import Utils
            key = Utils.load_parameters().get("sam", {}).get(
                "assistant", "general-tiny")
            entry = get_assistant(key)
            self.view.statusBar().showMessage(
                f"SAM assistant: {entry['name']} ({entry['repo']})")
            # Reactivate the tool if it was active
            if self.model.checked_button == "sam_assist":
                self.sam_assist()

    def sam_negative(self):
        """Toggle next-click negative mode."""
        self.model.sam_toggle_negative()

    def sam_accept(self):
        self.model.sam_accept_session()

    def sam_clear(self):
        self.model.sam_clear_session()

    def sam_undo_point(self):
        self.model.sam_undo_last()

    def sam_next_mask(self):
        self.model.sam_cycle_candidate()

    def sam_text_mask(self):
        from PyImageLabeling.controller.settings.SAMTextDialog import (
            SAMTextDialog)
        self.all_events(self.sam_text_mask.__name__)
        dialog = SAMTextDialog(self.view.zoomable_graphics_view, self.model)
        self._sam_text_mode = True
        try:
            dialog.exec()
        finally:
            self._sam_text_mode = False
        # The dialog owns its whole lifecycle (Generate / threshold /
        # Previous-Next / OK / Cancel): nothing pending afterwards.

    def sam_propagate(self):
        """One-shot: current image+label mask -> all other images."""
        import os
        from PyQt6.QtWidgets import QProgressDialog, QMessageBox
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QImage
        import numpy as np
        from PyImageLabeling.model.SAM import oneshot
        from PyImageLabeling.model.Utils import Utils

        model = self.model
        ref_item = model.get_current_image_item()
        label_item = model.get_current_label_item()
        if ref_item is None or label_item is None:
            QMessageBox.information(
                self.view, "One-shot propagation",
                "Select an image and a label first.\n"
                "The current image + label is the reference.")
            return
        label_id = label_item.get_label_id()
        overlay = ref_item.labeling_overlays.get(label_id)
        if overlay is None:
            QMessageBox.information(
                self.view, "One-shot propagation",
                "No mask on the current image for this label.\n"
                "Validate a SAM preview (or paint) first: it becomes "
                "the reference.")
            return
        qimg = overlay.labeling_overlay_pixmap.toImage().convertToFormat(
            QImage.Format.Format_ARGB32)
        ptr = qimg.bits()
        ptr.setsize(qimg.sizeInBytes())
        arr = np.frombuffer(ptr, dtype=np.uint8).reshape(
            (qimg.height(), qimg.width(), 4))
        ref_mask = arr[:, :, 3] > 30
        if ref_mask.sum() == 0:
            QMessageBox.information(
                self.view, "One-shot propagation",
                "Reference mask is empty.")
            return
        # resize ref mask to image size if needed
        ref_rgb = ref_item.get_image_numpy_pixels_rgb()
        rh, rw = ref_rgb.shape[:2]
        if ref_mask.shape != (rh, rw):
            import cv2
            ref_mask = (cv2.resize(ref_mask.astype(np.uint8), (rw, rh),
                                   interpolation=cv2.INTER_NEAREST) > 0)

        targets = [p for p in model.file_paths
                   if p != ref_item.path_image]
        if not targets:
            QMessageBox.information(
                self.view, "One-shot propagation", "No other images.")
            return

        ok, msg = model._ensure_sam_loaded()
        if not ok:
            QMessageBox.critical(self.view, "SAM backend", msg)
            return

        sam_params = Utils.load_parameters().get("sam", {})
        threshold = float(sam_params.get("propagate_threshold", 0.25))
        device = model._sam_params()["device"]
        dino_key = sam_params.get("dino_model", "small")

        from PyImageLabeling.model.SAM import debug_log
        run_id = f"propagate[{label_item.get_name()}]"
        debug_log.log_event(
            f"{run_id} START n_targets={len(targets)} "
            f"thr={threshold} dino={dino_key} "
            f"totalRAM={debug_log.total_ram_mb()}MB "
            f"{debug_log.mem_stats()}")
        try:
            if debug_log.vram_pressure() > 0.85:
                debug_log.log_event(f"{run_id} high VRAM pressure: pre-purge")
                model._sam_oom_purge()
        except Exception:
            pass
        # suspend auto-save: its timer fires through processEvents and
        # would save hundreds of edited masks re-entrantly mid-batch
        # (UI freeze). Restored in the finally block below.
        autosave_was_on = bool(getattr(model, "autosave_enabled", False))
        try:
            model.set_autosave_enabled(False)
        except Exception:
            pass
        debug_log.arm_hang_dump(90)

        progress = QProgressDialog(
            "One-shot propagation…", "Cancel", 0, len(targets), self.view)
        progress.setWindowTitle("SAM Propagate")
        progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        progress.setMinimumDuration(0)
        progress.show()

        import time as _sam_time
        t0 = _sam_time.time()
        try:
            fg_proto, bg_proto, _dev = oneshot.reference_prototypes(
                ref_rgb, ref_mask, device=device, model_key=dino_key)
            debug_log.log_event(
                f"{run_id} reference_prototypes took "
                f"{_sam_time.time() - t0:.1f}s")
        except Exception as e:
            progress.close()
            try:
                oneshot.release_dinov2()
                model._sam_oom_purge()
            except Exception:
                pass
            try:
                debug_log.cancel_hang_dump()
                if autosave_was_on:
                    model.set_autosave_enabled(True)
            except Exception:
                pass
            debug_log.log_event(f"{run_id} DINOv2 backend failed: {e}")
            QMessageBox.critical(
                self.view, "One-shot propagation",
                f"DINOv2 backend failed:\n{e}")
            return

        # batch mode: no embedding cache (peak = 1 image, not N).
        # Heavy compute runs in a worker thread (GUI stays alive);
        # only Qt-safe preparation + painting happen here.
        model._sam_batch_mode = True
        try:
            model._last_batch = []
            model._last_batch_idx = -1
        except Exception:
            pass
        run = {"painted": 0, "skipped": 0, "errors": 0, "oom": 0,
               "touched": [], "done": 0, "total": len(targets),
               "autosave_was_on": autosave_was_on,
               "label_name": label_item.get_name(),
               "ref_base": os.path.basename(ref_item.path_image),
               "threshold": threshold}
        self._prop_run = run
        self._prop_label_id = label_id
        self._prop_run_id = run_id
        self._prop_progress = progress

        # GUI pre-pass: load + overlays (Qt objects, must be GUI thread).
        from PyQt6.QtWidgets import QApplication as _QAppPre
        try:
            n_pre = len(targets)
            for _j, _p in enumerate(targets):
                if model.image_items.get(_p) is None:
                    model.load_image_for_training(_p)
                _it = model.image_items.get(_p)
                if _it is not None:
                    try:
                        _it.update_labeling_overlays(
                            model.label_items, label_id)
                    except Exception as _e:
                        run["errors"] += 1
                        debug_log.log_event(
                            f"{run_id} ERROR prep {_p}: {_e}")
                if _j % 25 == 0:
                    progress.setLabelText(f"Preparing {_j + 1}/{n_pre}…")
                    progress.setValue(0)
                    _QAppPre.processEvents()
                    if progress.wasCanceled():
                        debug_log.log_event(f"{run_id} canceled in prep")
                        self._prop_cleanup()
                        self._prop_summary(canceled=True)
                        return
        except Exception as _e:
            debug_log.log_event(f"{run_id} FATAL prep: {_e}")

        from PyImageLabeling.model.SAM.propagate_worker import (
            PropagateWorker)
        worker = PropagateWorker(
            model, ref_rgb, ref_mask, targets, threshold, device, dino_key)
        self._prop_worker = worker
        try:
            self.view.buttons_ml_bar["sam_propagate_btn"].setEnabled(False)
        except Exception:
            pass
        worker.progress.connect(self._on_prop_progress)
        worker.image_done.connect(self._on_prop_image)
        worker.stage.connect(self._on_prop_stage)
        worker.done.connect(self._on_prop_done)
        worker.failed.connect(self._on_prop_failed)
        progress.canceled.connect(worker.request_cancel)
        worker.start()
        return

    # ------------------------------------------------------------------
    # Propagation handlers (GUI thread)
    # ------------------------------------------------------------------

    def _on_prop_stage(self, msg):
        try:
            if getattr(self, "_prop_progress", None) is not None:
                self._prop_progress.setLabelText(msg)
        except Exception:
            pass

    def _on_prop_progress(self, done, total, path):
        import os as _os
        try:
            if getattr(self, "_prop_progress", None) is not None:
                self._prop_progress.setLabelText(
                    f"Propagating {done}/{total}\n"
                    f"{_os.path.basename(path)}")
                self._prop_progress.setValue(done)
        except Exception:
            pass
        if done % 10 == 0:
            try:
                from PyImageLabeling.model.SAM import debug_log
                debug_log.log_event(
                    f"{self._prop_run_id} {done}/{total} "
                    f"{debug_log.mem_stats()}")
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                debug_log.cancel_hang_dump()
                debug_log.arm_hang_dump(120)
            except Exception:
                pass

    def _on_prop_image(self, path, mask, score, status):
        import os as _os
        from PyImageLabeling.model.SAM import debug_log
        model = self.model
        run = getattr(self, "_prop_run", None)
        if run is None:
            return
        label_id = self._prop_label_id
        run_id = self._prop_run_id
        run["done"] += 1
        bname = _os.path.basename(path)
        if status == "computed" and mask is not None:
            try:
                item = model.image_items.get(path)
                if item is None:
                    run["errors"] += 1
                else:
                    model._sam_paint_mask(item, mask)
                    run["touched"].append(item)
                    run["painted"] += 1
                    if run["done"] <= 3:
                        debug_log.log_event(
                            f"{run_id} {bname}: painted")
            except Exception as e:
                run["errors"] += 1
                debug_log.log_event(f"{run_id} ERROR paint {path}: {e}")
        elif status in ("skipped", "no-mask"):
            run["skipped"] += 1
        elif status == "oom":
            run["oom"] += 1
            debug_log.log_event(f"{run_id} {bname}: out-of-memory, skipped")
        else:
            run["errors"] += 1
            debug_log.log_event(f"{run_id} {status} {path}")
        if run["done"] % 5 == 0:
            try:
                model.controller.ml_invalidate_stats_cache(path)
                model.controller.ml_update_stats()
            except Exception:
                pass

    def _prop_cleanup(self):
        """Collapse undo, offload backends, purge, restore UI (GUI thread)."""
        model = self.model
        run = getattr(self, "_prop_run", None) or {}
        label_id = getattr(self, "_prop_label_id", None)
        try:
            model._sam_batch_mode = False
        except Exception:
            pass
        try:
            from PyImageLabeling.model.SAM import debug_log, oneshot
            debug_log.cancel_hang_dump()
            try:
                if run.get("autosave_was_on"):
                    model.set_autosave_enabled(True)
            except Exception:
                pass
            try:
                for item in run.get("touched", []):
                    model._sam_collapse_undo(item, label_id)
            except Exception:
                pass
            try:
                oneshot.release_dinov2()
            except Exception:
                pass
            try:
                model._sam_oom_purge()
            except Exception:
                pass
            try:
                if getattr(self, "_prop_progress", None) is not None:
                    self._prop_progress.close()
            except Exception:
                pass
            try:
                self.view.buttons_ml_bar["sam_propagate_btn"].setEnabled(
                    True)
            except Exception:
                pass
        except Exception:
            pass
        try:
            worker = getattr(self, "_prop_worker", None)
            if worker is not None:
                worker.deleteLater()
        except Exception:
            pass
        self._prop_worker = None

    def _prop_summary(self, canceled=False):
        from PyQt6.QtWidgets import QMessageBox
        from PyImageLabeling.model.SAM import debug_log
        model = self.model
        run = getattr(self, "_prop_run", None) or {}
        try:
            # painted masks are already on disk; release the ImageItems the
            # batch loaded so painting stays light afterwards
            dropped = model.controller.ml_unload_image_items()
            if dropped:
                debug_log.log_event(
                    f"{self._prop_run_id} released {dropped} image item(s)")
        except Exception:
            pass
        try:
            model.controller.ml_invalidate_stats_cache()
            model.controller.ml_update_stats(immediate=True)
        except Exception:
            pass
        try:
            debug_log.log_event(
                f"{self._prop_run_id} END painted={run.get('painted', 0)} "
                f"skipped={run.get('skipped', 0)} "
                f"errors={run.get('errors', 0)} oom={run.get('oom', 0)} "
                f"canceled={canceled} {debug_log.mem_stats()}")
        except Exception:
            pass
        extra = ""
        if run.get("oom", 0):
            extra += f"\nSkipped (out of memory): {run['oom']}"
        if canceled:
            extra += "\n\nCanceled by user — partial results kept."
        if (run.get("painted", 0) == 0 and run.get("errors", 0) > 0
                and run.get("total", 0)):
            extra += ("\n\nEvery image failed — details in:\n"
                      f"{debug_log.log_path()}")
        try:
            self.view.statusBar().showMessage(
                f"SAM propagated → {run.get('painted', 0)} painted, "
                f"{run.get('skipped', 0)} skipped, "
                f"{run.get('errors', 0)} errors")
            QMessageBox.information(
                self.view, "One-shot propagation",
                f"Reference: '{run.get('label_name', '')}' on\n"
                f"{run.get('ref_base', '')}\n\n"
                f"Painted: {run.get('painted', 0)}\n"
                f"Skipped (low confidence): {run.get('skipped', 0)}\n"
                f"Errors: {run.get('errors', 0)}{extra}")
        except Exception:
            pass
        self._prop_run = None

    def _on_prop_done(self, summary):
        from PyImageLabeling.model.SAM import debug_log
        try:
            if summary.get("canceled"):
                debug_log.log_event(
                    f"{self._prop_run_id} worker acknowledged cancel")
        except Exception:
            pass
        try:
            run = getattr(self, "_prop_run", None) or {}
            self.model._last_batch = [
                it.path_image for it in run.get("touched", [])
                if it is not None and hasattr(it, "path_image")]
            self.model._last_batch_idx = -1
        except Exception:
            pass
        self._prop_cleanup()
        self._prop_summary(canceled=bool(summary.get("canceled", False)))

    def ml_review_next(self):
        """Step through the last batch (Review): show next painted image.

        Validate with existing tools (undo / eraser / Clear All) per
        image; run again to loop. Status bar shows the position.
        """
        from PyQt6.QtWidgets import QMessageBox
        paths = list(getattr(self.model, "_last_batch", None) or [])
        if not paths:
            QMessageBox.information(
                self.view, "Review batch",
                "No batch to review — run Propagate first.")
            return
        try:
            cur = self.model.get_current_image_item()
            cur_path = cur.path_image if cur is not None else None
        except Exception:
            cur_path = None
        try:
            pos = paths.index(cur_path) if cur_path in paths else -1
        except Exception:
            pos = -1
        nxt = (pos + 1) % len(paths)
        self.model._last_batch_idx = nxt
        target = paths[nxt]
        found = False
        try:
            bar = self.view.file_bar_list
            for row in range(bar.count()):
                item = bar.item(row)
                if getattr(item, "file_path", None) == target:
                    # same no-op guard as _ml_goto_file: selecting the row
                    # that is already current emits nothing, so the model
                    # would silently stay behind
                    if bar.currentItem() is not item:
                        bar.setCurrentRow(row)
                    else:
                        try:
                            self.select_image(item)
                        except AttributeError:
                            pass
                    found = True
                    break
        except Exception:
            pass
        try:
            self.view.statusBar().showMessage(
                f"Review {nxt + 1}/{len(paths)}: "
                f"{__import__('os').path.basename(target)}"
                + ("" if found else " (not in file bar)"))
        except Exception:
            pass

    def _on_prop_failed(self, message):
        from PyQt6.QtWidgets import QMessageBox
        from PyImageLabeling.model.SAM import debug_log
        try:
            debug_log.log_event(f"{self._prop_run_id} FATAL: {message}")
        except Exception:
            pass
        self._prop_cleanup()
        run = getattr(self, "_prop_run", None) or {}
        try:
            QMessageBox.critical(
                self.view, "One-shot propagation",
                f"Propagation interrupted by an unexpected error:\n"
                f"{message}\n\n"
                f"Already painted: {run.get('painted', 0)} image(s) — "
                f"nothing was lost.\n"
                f"Details: {debug_log.log_path()}")
        except Exception:
            pass
        self._prop_run = None
