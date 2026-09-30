"""Undo restores exactly, on all three entry forms, without leaking."""
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


def _loaded_mask_setup(model, paths):
    """Simulate a mask from a previous session: deque[0] holds content,
    like an overlay constructed with from_file does."""
    from PyImageLabeling.model.Core import CompactUndoEntry
    from PyQt6.QtCore import QPointF
    model.select_image(paths[0])
    reset_overlay(model)
    _stroke(model, 20, 20)
    overlay = model.get_current_image_item().get_labeling_overlay()
    overlay.undo_deque.clear()
    overlay.undo_deque.append(
        CompactUndoEntry(overlay.labeling_overlay_pixmap, compact=False))
    overlay.previous_labeling_overlay_pixmap = None
    overlay.set_is_undo_none(True)


def test_clear_all_then_undo_restores_exactly(project):
    """Undo right after Clear All brings back what was just cleared,
    not the oldest history entry."""
    _, _, model, paths = project
    _loaded_mask_setup(model, paths)
    _stroke(model, 60, 20)
    n_before_clear = _px(model)
    assert n_before_clear > 0

    model.get_current_image_item().get_labeling_overlay().reset()
    assert _px(model) == 0

    model.undo()
    assert _px(model) == n_before_clear


def test_undo_never_walks_past_clear_all(project):
    """After clear + new painting, undos stop at the empty mask: the
    pre-clear content is unreachable."""
    from PyQt6.QtCore import QPointF
    _, _, model, paths = project
    _loaded_mask_setup(model, paths)
    overlay = model.get_current_image_item().get_labeling_overlay()
    overlay.reset()

    # paint somewhere else (bottom half) so content is distinguishable
    model.start_paint_brush(QPointF(20.0, 90.0))
    model.move_paint_brush(QPointF(60.0, 110.0))
    model.end_paint_brush()
    model.start_paint_brush(QPointF(70.0, 90.0))
    model.move_paint_brush(QPointF(100.0, 110.0))
    model.end_paint_brush()
    assert _px(model) > 0

    for _ in range(12):
        model.undo()
        top = overlay_alpha(model)[:50, :]
        assert int((top > 0).sum()) == 0
    assert _px(model) == 0


def test_undo_depth_reaches_every_overlay(project):
    """The depth setting resizes all overlays, trims, and stays enforced."""
    from PyQt6.QtCore import QPointF
    from PyQt6.QtGui import QColor
    _, _, model, paths = project
    label2 = model.new_label("L2", "Pixel-by-pixel", QColor(255, 0, 0))
    for p in paths[:2]:
        model.load_image_for_training(p)
        model.select_image(p)
        for lab in (model.label_items[0], label2):
            model.set_current_label_item(lab)
            model.update_labeling_overlays(lab.get_label_id())
            _stroke(model, 20, 20)

    n = model.resize_all_undo_deques(4)
    assert n > 0
    for p in paths[:2]:
        item = model.image_items.get(p)
        for overlay in item.labeling_overlays.values():
            assert overlay.undo_deque.maxlen == 4
            assert overlay.memory_depth == 4
            assert len(overlay.undo_deque) <= 4

    # and it really caps new history
    model.select_image(paths[0])
    model.set_current_label_item(model.label_items[0])
    for i in range(8):
        _stroke(model, 10 + i * 5, 10)
    overlay = model.get_current_image_item().get_labeling_overlay()
    assert len(overlay.undo_deque) <= 4

    # garbage input must not raise
    assert model.resize_all_undo_deques("nope") == 0
