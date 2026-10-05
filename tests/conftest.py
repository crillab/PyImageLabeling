"""Shared fixtures for the PyImageLabeling test suite.

Everything runs headless (QT_QPA_PLATFORM=offscreen). The app opens modal
dialogs in several flows (clear_all, Files.load, dynamic eraser, training
results), which would block a test forever: QMessageBox statics are stubbed
globally here, and tests avoid model.load() in favour of build_folder()
which reproduces the post-load state.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


import numpy as np
import pytest
from PIL import Image as PILImage
from PyQt6.QtWidgets import QApplication, QMessageBox

from PyImageLabeling.model.Utils import Utils
from PyImageLabeling.view.View import View
from PyImageLabeling.controller.Controller import Controller
from PyImageLabeling.model.Model import Model
import PyImageLabeling.model.Utils as _U


# ----------------------------------------------------------------------
# modal dialogs: never block a test
# ----------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _no_modals(monkeypatch):
    monkeypatch.setattr(
        QMessageBox, "information", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(
        QMessageBox, "warning", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(
        QMessageBox, "critical", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(
        QMessageBox, "question",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.No))


@pytest.fixture(autouse=True)
def _cuda_cache_guard():
    """Keep the shared GPU from fragmenting across the suite.

    Several tests train real models on cuda. The caching allocator keeps the
    freed blocks reserved for the *process*, so memory taken by an earlier
    test was still unavailable to a later training and the run died with a
    CUDA RuntimeError that had nothing to do with the test that reported it.
    """
    _empty_cuda_cache()
    yield
    _empty_cuda_cache()


def _empty_cuda_cache():
    try:
        import torch
    except Exception:
        return
    try:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        pass


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture()
def workspace(tmp_path):
    """A folder with N synthetic images, cleaned up afterwards."""
    folder = tmp_path / "ws"
    folder.mkdir()
    return folder


# Every stack is kept alive until the end of the session. Building a second
# View in the same process aborts natively inside setIcon() once a previous
# test has painted/selected/unloaded images (use-after-free somewhere in the
# Qt graphics stack): per-test View construction is simply not viable with
# this codebase, so the suite shares ONE stack and resets its state.
_live_stacks = []


@pytest.fixture(scope="session")
def app_stack(qapp):
    """(controller, view, model): a single shared app instance.

    One stack per session: constructing a second View after a test has
    painted/selected/unloaded aborts natively in setIcon(). State is reset
    by the project fixture instead.
    """
    config = Utils.get_config()
    controller = Controller(config)
    view = View(controller, config)
    model = Model(view, controller, config)
    controller.set_model(model)
    _live_stacks.append((controller, view, model))
    yield controller, view, model


def reset_app(controller, view, model):
    """Return the shared stack to a pristine state between tests."""
    from PyImageLabeling.model.Core import LabelItem

    model.file_paths = []
    model.image_items = {}
    model.icon_button_files = {}
    model.label_items = {}
    model.save_directory = ""
    model.current_image_item = None
    model.current_label_item = None
    LabelItem.static_label_id = 0
    LabelItem.used_ids = set()
    model.labeling_overview_was_loaded = {}
    model.labeling_overview_file_paths = {}
    model.left_rectangles = {}
    model.left_ellipses = {}
    model.left_polygons = {}
    model._ml_annotated = {}
    model._ml_disk_annotated = {}
    model._ml_painted_cache = {}
    model._last_batch = []
    model._last_batch_idx = -1
    # training state: a trained model must not leak into the next test
    # (Suggest next refuses to run "untrained", val loaders hold datasets)
    model.trained = False
    model.model = None
    model.probe = None
    model._probe_val_items = None
    # which model is live (loaded file vs trained-in-this-session)
    for attr, value in (("_model_origin", None),
                        ("_model_saved", False),
                        ("_model_path", None)):
        if hasattr(model, attr):
            setattr(model, attr, value)
    model.seg_backbone = "resnet"
    model.training_mode = None
    model.val_metrics = {}
    model._det_val_loader = None
    model._seg_val_loader = None
    model.label_id_to_class = {}
    model.class_to_label_id = {}
    controller._ml_paint_cache = {}
    controller._al_ranking = None
    controller._al_pos = -1
    try:
        view.file_bar_list.clear()
    except Exception:
        pass
    try:
        model.zoomable_graphics_view.scene.clear()
    except Exception:
        pass


def make_images(folder, n, size=128, seed=0):
    rng = np.random.RandomState(seed)
    paths = []
    for i in range(n):
        p = os.path.join(str(folder), f"img{i:03d}.png")
        PILImage.fromarray(
            rng.randint(0, 255, (size, size, 3), np.uint8)).save(p)
        paths.append(p)
    return paths


def write_labels_json(folder):
    with open(os.path.join(str(folder), "labels.json"), "w",
              encoding="utf-8") as f:
        f.write('{"0": {"name": "L", "labeling_mode": "Pixel-by-pixel", '
                '"color": [0, 255, 0]}}')


@pytest.fixture(scope="session")
def app_stack(qapp):
    """(controller, view, model): a single shared app instance.

    One stack per session: constructing a second View after a test has
    painted/selected/unloaded aborts natively in setIcon(). State is reset
    by the project fixture instead.
    """
    config = Utils.get_config()
    controller = Controller(config)
    view = View(controller, config)
    model = Model(view, controller, config)
    controller.set_model(model)
    _live_stacks.append((controller, view, model))
    yield controller, view, model


@pytest.fixture()
def project(app_stack, workspace):
    """App + 12 labelled images loaded without the modal progress dialog."""
    controller, view, model = app_stack
    reset_app(controller, view, model)
    paths = make_images(workspace, 12)
    write_labels_json(workspace)
    for p in paths:
        model.file_paths.append(p)
        model.image_items[p] = None
    view.file_bar_add(list(paths))
    from PyQt6.QtGui import QColor
    label = model.new_label("L", "Pixel-by-pixel", QColor(0, 255, 0))
    model.set_current_label_item(label)
    return controller, view, model, paths


@pytest.fixture()
def big_project(app_stack, workspace):
    """Same as project, but 512x512 images for stroke-geometry tests."""
    controller, view, model = app_stack
    reset_app(controller, view, model)
    paths = make_images(workspace, 4, size=512)
    write_labels_json(workspace)
    for p in paths:
        model.file_paths.append(p)
        model.image_items[p] = None
    view.file_bar_add(list(paths))
    from PyQt6.QtGui import QColor
    label = model.new_label("L", "Pixel-by-pixel", QColor(0, 255, 0))
    model.set_current_label_item(label)
    return controller, view, model, paths


def overlay_alpha(model):
    """Alpha channel of the current overlay as a bool array."""
    from PyQt6.QtGui import QImage
    o = model.get_current_image_item().get_labeling_overlay()
    img = o.labeling_overlay_pixmap.toImage()
    img = img.convertToFormat(QImage.Format.Format_ARGB32)
    ptr = img.bits()
    ptr.setsize(img.sizeInBytes())
    a = np.frombuffer(ptr, np.uint8).reshape(
        (img.height(), img.bytesPerLine()))
    a = a[:, :img.width() * 4].reshape(img.height(), img.width(), 4)
    return np.ascontiguousarray(a[:, :, 3])


def reset_overlay(model):
    """Back to a blank overlay (what clear_all/Yes does, minus the modal).

    Faithful to LabelingOverlay.reset(): the deque keeps one entry holding
    the pristine state, otherwise undo() can never walk back to empty.
    """
    from PyImageLabeling.model.Core import CompactUndoEntry
    o = model.get_current_image_item().get_labeling_overlay()
    o.labeling_overlay_pixmap.fill(__import__(
        "PyQt6.QtCore", fromlist=["Qt"]).Qt.GlobalColor.transparent)
    o.labeling_overlay_painter.begin(o.labeling_overlay_pixmap)
    o.reset_pen()
    o.set_is_edited(False)
    o.set_is_undo_none(True)
    o.undo_deque.clear()
    o.undo_deque.append(
        CompactUndoEntry(o.labeling_overlay_pixmap, compact=False))
    o.previous_labeling_overlay_pixmap = None


@pytest.fixture()
def fake_params(monkeypatch):
    """Temporarily override parameters without touching parameters.json."""
    real_load = _U.Utils.load_parameters

    def override(**sections):
        def fake():
            d = real_load()
            for key, values in sections.items():
                d.setdefault(key, {}).update(values)
            return d
        monkeypatch.setattr(_U.Utils, "load_parameters",
                            staticmethod(fake))
    return override
