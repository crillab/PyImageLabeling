"""Undo restores exactly, on all three entry forms, without leaking."""
import numpy as np
from PyQt6.QtCore import QPointF

from tests.conftest import overlay_alpha, reset_overlay


def _stroke(model, x, y, n=20, step=4):
    model.start_paint_brush(QPointF(float(x), float(y)))
    for i in range(1, n):
        model.move_paint_brush(QPointF(x + i * step, y + i * step))
    model.end_paint_brush()


def _px(model):
    return int((overlay_alpha(model) > 0).sum())


def test_undo_pending_entries(project):
    _, _, model, paths = project
    model.select_image(paths[0])
    reset_overlay(model)
    n0 = _px(model)
    _stroke(model, 20, 20)
    n1 = _px(model)
    _stroke(model, 60, 20)
    n2 = _px(model)
    assert n1 > n0 and n2 > n1

    model.undo()
    assert _px(model) == n2 - (n2 - n1) or _px(model) == n1
    model.undo()
    model.undo()
    assert _px(model) == n0


def test_undo_after_idle_compaction(project):
    _, _, model, paths = project
    model.select_image(paths[0])
    reset_overlay(model)
    _stroke(model, 20, 80)
    n1 = _px(model)
    _stroke(model, 60, 80)
    n2 = _px(model)

    overlay = model.get_current_image_item().get_labeling_overlay()
    while overlay.pending_undo_entries() > 0:
        overlay.compact_undo(max_entries=8)

    model.undo()
    assert _px(model) == n1
    model.undo()
    assert _px(model) == 0


def test_undo_to_dense_entry(project):
    _, _, model, paths = project
    model.select_image(paths[0])
    reset_overlay(model)
    # paint most of the 128x128 image so entries take the dense form:
    # overlapping horizontal bands across the whole width
    for gy in range(8, 128, 16):
        model.start_paint_brush(QPointF(4.0, float(gy)))
        model.move_paint_brush(QPointF(60.0, float(gy)))
        model.move_paint_brush(QPointF(124.0, float(gy)))
        model.end_paint_brush()
    frac = _px(model) / (128 * 128)
    assert frac > 0.5

    overlay = model.get_current_image_item().get_labeling_overlay()
    while overlay.pending_undo_entries() > 0:
        overlay.compact_undo(max_entries=99)
    kinds = {"sparse" if e.sparse else "dense" if e._image is not None
             else "pending" for e in overlay.undo_deque}
    assert "dense" in kinds

    before = _px(model)
    model.undo()
    assert _px(model) < before


def test_undo_leaves_no_dangling_items(project):
    _, _, model, paths = project
    model.select_image(paths[0])
    reset_overlay(model)
    _stroke(model, 30, 30)
    model.undo()
    # the preview item is removed, only background + overlay remain
    assert len(model.zoomable_graphics_view.scene.items()) == 2
    # and the tool still paints afterwards
    _stroke(model, 60, 90)
    assert _px(model) > 0


def test_has_painted_pixels_forms():
    from PyQt6.QtGui import QPixmap
    from PyQt6.QtCore import Qt
    from PyImageLabeling.model.Core import CompactUndoEntry

    empty = QPixmap(8, 8)
    empty.fill(Qt.GlobalColor.transparent)
    assert CompactUndoEntry(empty, compact=False).has_painted_pixels() is False
    assert CompactUndoEntry(empty).has_painted_pixels() is False

    full = QPixmap(8, 8)
    full.fill(Qt.GlobalColor.red)
    assert CompactUndoEntry(full, compact=False).has_painted_pixels() is True
    assert CompactUndoEntry(full).has_painted_pixels() is True
