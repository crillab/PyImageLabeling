"""Background worker for one-shot propagation.

Heavy compute (DINOv2 + SAM, torch/CUDA, PIL, numpy) runs here, off the
GUI thread, so the interface never freezes. Only plain data crosses the
thread boundary (paths, numpy masks, scores); every Qt object
(QPixmap, QPainter, scene items, widgets) stays on the GUI thread.
"""

import threading
import traceback

import numpy as np
from PIL import Image
from PyQt6.QtCore import QThread, pyqtSignal


class PropagateWorker(QThread):
    progress = pyqtSignal(int, int, str)              # done, total, label
    image_done = pyqtSignal(str, object, float, str)  # path, mask|None, score, status
    stage = pyqtSignal(str)                           # e.g. "reference…"
    done = pyqtSignal(dict)                           # summary counts
    failed = pyqtSignal(str)                          # fatal message

    def __init__(self, model, ref_rgb, ref_mask, targets, threshold,
                 device, dino_key, parent=None):
        super().__init__(parent)
        self.model = model
        self.ref_rgb = ref_rgb
        self.ref_mask = ref_mask
        self.targets = list(targets)
        self.threshold = threshold
        self.device = device
        self.dino_key = dino_key
        self._cancel = threading.Event()

    def request_cancel(self):
        self._cancel.set()

    def run(self):
        import time
        from PyImageLabeling.model.SAM import oneshot, debug_log
        model = self.model
        summary = {"computed": 0, "skipped": 0, "errors": 0,
                   "oom": 0, "canceled": False}
        try:
            self.stage.emit("Computing reference prototypes…")
            t0 = time.time()
            fg_proto, bg_proto, _dev = oneshot.reference_prototypes(
                self.ref_rgb, self.ref_mask, device=self.device,
                model_key=self.dino_key)
            debug_log.log_event(
                f"reference_prototypes took {time.time() - t0:.1f}s")
            total = len(self.targets)
            for i, path in enumerate(self.targets):
                if self._cancel.is_set():
                    summary["canceled"] = True
                    debug_log.log_event(f"canceled at {i}")
                    break
                try:
                    import os as _os
                    bname = _os.path.basename(path)
                    t_img = time.time()
                    rgb = np.array(Image.open(path).convert("RGB"))
                    t_dino = time.time()
                    prompts = oneshot.propose_prompts(
                        rgb, fg_proto, bg_proto, device=self.device,
                        model_key=self.dino_key)
                    t_dino = time.time() - t_dino
                    if prompts is None or prompts["score"] < self.threshold:
                        summary["skipped"] += 1
                        self.image_done.emit(path, None, 0.0, "skipped")
                    else:
                        t_sam = time.time()
                        masks, scores = model._sam_infer_candidates(
                            rgb, path, prompts["points"], prompts["labels"],
                            prompts["box"])
                        t_sam = time.time() - t_sam
                        if masks is None:
                            if (getattr(model, "_sam_last_error", None)
                                    == "gpu-oom"):
                                model._sam_last_error = None
                                summary["oom"] += 1
                                self.image_done.emit(path, None, 0.0, "oom")
                            else:
                                summary["skipped"] += 1
                                self.image_done.emit(path, None, 0.0,
                                                     "no-mask")
                        else:
                            best = (int(np.argmax(scores))
                                    if len(scores) > 1 else 0)
                            summary["computed"] += 1
                            self.image_done.emit(path, masks[best],
                                                 float(scores[best]),
                                                 "computed")
                    if i < 3:
                        debug_log.log_event(
                            f"{bname}: t={time.time() - t_img:.1f}s "
                            f"(dino {t_dino:.1f}s)")
                except Exception as e:
                    summary["errors"] += 1
                    self.image_done.emit(path, None, 0.0,
                                         f"error: {e}")
                self.progress.emit(i + 1, total, path)
            self.done.emit(summary)
        except Exception as e:
            self.failed.emit(f"{e}\n{traceback.format_exc()}")
