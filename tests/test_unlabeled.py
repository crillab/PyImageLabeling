"""Painted images must never be reported as unlabeled.

Regression: ml_unload_image_items() releases the RAM ImageItems after a
propagation or a training run; ml_get_unlabeled_images() then saw every
released image as "not loaded" and offered it again in active learning.
"""
import os

import numpy as np
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QColor, QImage


def _save_label_file(folder, index):
    img = QImage(64, 64, QImage.Format.Format_ARGB32)
    from PyQt6.QtCore import Qt
    img.fill(Qt.GlobalColor.transparent)
    for y in range(10, 30):
        for x in range(10, 30):
            img.setPixelColor(x, y, QColor(255, 0, 0, 255))
    img.save(os.path.join(str(folder), f"img{index:03d}.label.0.png"), "PNG")


def test_painted_then_released_stays_annotated(project):
    controller, view, model, paths = project
    for p in paths[:6]:
        model.load_image_for_training(p)
        model.select_image(p)
        model.start_paint_brush(QPointF(20.0, 20.0))
        model.move_paint_brush(QPointF(60.0, 50.0))
        model.end_paint_brush()

    assert len(model.ml_get_unlabeled_images()) == 6

    dropped = controller.ml_unload_image_items()
    assert dropped > 0

    unlabeled = model.ml_get_unlabeled_images()
    assert len(unlabeled) == 6
    assert not [p for p in unlabeled if p in paths[:6]]


def test_previous_session_label_files_are_annotated(project, workspace):
    _, _, model, paths = project
    for i in range(4):
        _save_label_file(workspace, i)
    # cold caches: pure on-disk scan
    model._ml_annotated.clear()
    model.ml_invalidate_disk_cache()

    unlabeled = model.ml_get_unlabeled_images()
    assert len(unlabeled) == 12 - 4
    assert not [p for p in unlabeled if p in paths[:4]]


def test_rectangle_counts_as_annotated(project):
    _, _, model, paths = project
    model.select_image(paths[6])
    model.start_rectangle_tool(QPointF(10.0, 10.0))
    model.move_rectangle_tool(QPointF(60.0, 50.0))
    model.end_rectangle_tool()
    model.save_directory = str(paths[0].rsplit(os.sep, 1)[0])
    model.save()
    model.ml_invalidate_disk_cache()
    model._ml_annotated.clear()

    assert paths[6] not in model.ml_get_unlabeled_images()


def test_clearing_puts_the_image_back(project):
    from tests.conftest import reset_overlay
    _, _, model, paths = project
    model.select_image(paths[0])
    model.start_paint_brush(QPointF(20.0, 20.0))
    model.move_paint_brush(QPointF(60.0, 50.0))
    model.end_paint_brush()
    assert paths[0] not in model.ml_get_unlabeled_images()

    reset_overlay(model)
    assert paths[0] in model.ml_get_unlabeled_images()
