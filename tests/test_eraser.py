"""Intelligent eraser: colour criterion, shape erase, dialog, masks hiding."""
import numpy as np
import pytest
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QColor, QPixmap

from tests.conftest import write_labels_json, overlay_alpha, reset_overlay


@pytest.fixture()
def two_color(app_stack, workspace):
    """256x256, left half blue, right half red."""
    from tests.conftest import reset_app
    from PIL import Image as PILImage
    controller, view, model = app_stack
    reset_app(controller, view, model)
    p = str(workspace / "two.png")
    arr = np.full((256, 256, 3), 128, np.uint8)
    arr[:, :128] = (30, 30, 220)
    arr[:, 128:] = (220, 30, 30)
    PILImage.fromarray(arr).save(p)
    write_labels_json(workspace)
    model.file_paths.append(p)
    model.image_items[p] = None
    view.file_bar_add([p])
    label = model.new_label("L", "Pixel-by-pixel", QColor(0, 255, 0))
    model.set_current_label_item(label)
    model.select_image(p)
    model.update_labeling_overlays(label.get_label_id())
    return controller, view, model, p


def _blob(model):
    reset_overlay(model)
    model.start_paint_brush(QPointF(20.0, 128.0))
    model.move_paint_brush(QPointF(226.0, 128.0))
    model.move_paint_brush(QPointF(226.0, 200.0))
    model.end_paint_brush()
    return overlay_alpha(model) > 0


def test_colour_off_erases_the_whole_shape(two_color, fake_params):
    _, _, model, _ = two_color
    _blob(model)
    fake_params(**{"eraser": {"mode": "intelligent", "tolerance": 10,
                              "dynamic_adjust": False, "use_color": False}})
    model.intelligent_erase(40, 128)
    assert int((overlay_alpha(model) > 0).sum()) == 0


def test_colour_on_keeps_the_matching_part(two_color, fake_params):
    _, _, model, _ = two_color
    blob = _blob(model)
    n0 = int(blob.sum())
    assert n0 > 0
    fake_params(**{"eraser": {"mode": "intelligent", "tolerance": 10,
                              "dynamic_adjust": False, "use_color": True,
                              "keep_color": "#ff1e1edc"}})
    model.intelligent_erase(40, 128)
    left = overlay_alpha(model) > 0
    assert 0 < int(left.sum()) < n0
    # the blue (kept) half survives
    assert int(left[:, :128].sum()) > 1000


def test_click_outside_any_shape_is_safe(two_color, fake_params):
    _, _, model, _ = two_color
    reset_overlay(model)
    fake_params(**{"eraser": {"mode": "intelligent", "use_color": False}})
    model.intelligent_erase(10, 10)  # bare image
    assert int((overlay_alpha(model) > 0).sum()) == 0


def test_masks_hidden_while_native_picker_open(two_color, monkeypatch):
    from PyQt6.QtWidgets import QColorDialog
    from PyImageLabeling.controller.settings.EraserSetting import (
        EraserSetting)
    _, view, model, _ = two_color
    _blob(model)
    from PyImageLabeling.model.Utils import Utils
    dlg = EraserSetting(view, model)

    seen = {}

    def _fake(initial, parent=None):
        seen["during"] = [i.isVisible() for i in
                          (o.labeling_overlay_item for o in
                           model.get_current_image_item()
                           .get_labeling_overlays())
                          if i is not None]
        return QColor(7, 7, 7)

    monkeypatch.setattr(QColorDialog, "getColor", staticmethod(_fake))
    dlg.pick_color()
    assert seen.get("during") == [False]
    assert [i.isVisible() for i in
            (o.labeling_overlay_item for o in
             model.get_current_image_item().get_labeling_overlays())
            if i is not None] == [True]
    # the same label is still current
    assert model.get_current_label_item().get_label_id() == 0
    assert dlg.selected_color.name() == "#070707"


def test_dynamic_dialog_counts_and_reset(two_color):
    from PyImageLabeling.controller.settings.EraserSetting import (
        DynamicEraserDialog)
    _, view, model, _ = two_color
    shape = np.zeros((64, 64), bool)
    shape[10:50, 10:50] = True
    img = np.zeros((64, 64, 4), np.uint8)
    img[..., 0] = 30
    img[..., 2] = 220
    dlg = DynamicEraserDialog(
        view, img, shape, np.array([30, 30, 220, 255]), 10,
        QPixmap(64, 64), QPixmap(64, 64), model=model)
    assert "px will be erased" in dlg.info_label.text()
    dlg.reset_preview()  # used to raise AttributeError (dead code)
    dlg._on_use_color(False)
    assert not dlg.tolerance_slider.isEnabled()
    assert int(dlg.get_final_erase_mask().sum()) == int(shape.sum())
    dlg._on_use_color(True)
    dlg._on_tolerance(200)
    assert dlg.tolerance_slider.value() == dlg.tolerance_spinbox.value()


def test_eraser_end_to_end_perf(two_color, fake_params):
    import time
    _, _, model, _ = two_color
    _blob(model)
    fake_params(**{"eraser": {"mode": "intelligent", "tolerance": 10,
                              "dynamic_adjust": False, "use_color": False}})
    t0 = time.perf_counter()
    model.intelligent_erase(40, 128)
    dt = (time.perf_counter() - t0) * 1000
    # smoke ratio, not an absolute budget: CI machines vary
    assert dt < 400, f"{dt:.0f} ms"
