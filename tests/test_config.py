"""ML bar has no dangling slots; the SAM floating bar drives accept/clear."""
import os

import numpy as np
from PIL import Image as PILImage
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QDialogButtonBox


def test_no_dangling_slots(project):
    controller, _, model, _ = project
    cfg = model.config if hasattr(model, "config") else None
    from PyImageLabeling.model.Utils import Utils
    cfg = Utils.get_config()
    slots = {b.get("slot") for b in cfg["ml_buttons_config"]}
    slots |= {b.get("slot") for b in cfg["labeling_bar_setting"]}
    missing = [s for s in slots
               if s and not hasattr(controller, s) and not hasattr(model, s)]
    assert missing == []
    assert "sam_accept_btn" not in [b.get("name")
                                    for b in cfg["ml_buttons_config"]]
    assert "sam_clear_btn" not in [b.get("name")
                                   for b in cfg["ml_buttons_config"]]


def test_floating_bar_opens_and_hides(project, tmp_path):
    controller, view, model, paths = project
    model.select_image(paths[0])

    controller._sam_show_confirm_bar()
    bar = controller._sam_confirm_bar
    assert bar is not None and bar.isVisible()
    boxes = bar.findChildren(QDialogButtonBox)
    assert boxes and len(boxes[0].buttons()) >= 2

    controller.sam_clear()  # must not raise with no preview
    controller._sam_hide_confirm_bar()
    assert not bar.isVisible()


def test_brush_end_to_end_smoke(project):
    """Paint, undo, stats, unload: the everyday loop stays consistent."""
    controller, _, model, paths = project
    model.select_image(paths[0])
    model.start_paint_brush(QPointF(20.0, 20.0))
    model.move_paint_brush(QPointF(80.0, 70.0))
    model.end_paint_brush()
    from tests.conftest import overlay_alpha
    assert int((overlay_alpha(model) > 0).sum()) > 0

    model.undo()
    assert int((overlay_alpha(model) > 0).sum()) == 0

    controller.ml_update_stats(immediate=True)
    assert "Annotated Images" in view_text(controller)

    dropped = controller.ml_unload_image_items()
    assert dropped >= 0


def view_text(controller):
    return controller.view.ml_stats_label.text()
