"""Labeling overlays are created lazily.

Each overlay holds a full-size ARGB pixmap. They used to be created for every
label on every loaded image (plus a second full-size "color" pixmap each),
which cost several GB on large slides. Now an image only gets the overlays of
the labels that have a mask on disk for it, plus the selected label; the
others are created on demand.
"""
import os

import numpy as np
from PIL import Image as PILImage
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QColor, QImage


def _paint(model, path):
    model.select_image(path)
    model.start_paint_brush(QPointF(20.0, 20.0))
    model.move_paint_brush(QPointF(60.0, 50.0))
    model.end_paint_brush()


def _alpha_rgb(pixmap):
    img = pixmap.toImage().convertToFormat(QImage.Format.Format_ARGB32)
    ptr = img.bits()
    ptr.setsize(img.sizeInBytes())
    arr = np.frombuffer(ptr, np.uint8).reshape(
        (img.height(), img.bytesPerLine() // 4, 4))[:, :img.width()]
    # ARGB32 is stored as B, G, R, A in memory (little endian)
    return arr[:, :, 3].copy(), arr[:, :, [2, 1, 0]].copy()


def _add_labels(model, n):
    return [model.new_label(f"L{i}", "Pixel-by-pixel", QColor(255, 0, 0))
            for i in range(n)]


def test_only_selected_label_gets_an_overlay(project):
    _, _, model, paths = project
    _add_labels(model, 3)  # 4 labels in total, label 0 selected
    model.select_image(paths[0])

    item = model.get_current_image_item()
    assert list(item.labeling_overlays) == [0]
    assert item.get_labeling_overlay() is item.labeling_overlays[0]


def test_label_with_mask_on_disk_is_loaded(project, workspace):
    _, _, model, paths = project
    _add_labels(model, 2)
    # a mask for label 2 on img000, as saved by an earlier session
    mask = np.zeros((128, 128), np.uint8)
    mask[10:30, 10:30] = 255
    key = "img000.label.2.png"
    mask_path = os.path.join(str(workspace), key)
    PILImage.fromarray(mask).save(mask_path)
    model.labeling_overview_was_loaded[key] = False
    model.labeling_overview_file_paths[key] = mask_path

    model.select_image(paths[0])
    item = model.get_current_image_item()
    assert sorted(item.labeling_overlays) == [0, 2]
    alpha, _ = _alpha_rgb(item.labeling_overlays[2].labeling_overlay_pixmap)
    assert alpha[20, 20] > 0 and alpha[60, 60] == 0


def test_switching_label_creates_its_overlay_and_paints(project):
    _, _, model, paths = project
    (label1,) = _add_labels(model, 1)
    model.select_image(paths[0])
    item = model.get_current_image_item()
    assert 1 not in item.labeling_overlays

    model.set_current_label_item(label1)
    model.update_labeling_overlays(label1.get_label_id())
    assert 1 in item.labeling_overlays
    assert item.labeling_overlays[1].is_displayed_in_scene

    _paint(model, paths[0])
    alpha, _ = _alpha_rgb(item.labeling_overlays[1].labeling_overlay_pixmap)
    assert (alpha > 0).any()
    # nothing was painted on label 0
    alpha0, _ = _alpha_rgb(item.labeling_overlays[0].labeling_overlay_pixmap)
    assert not (alpha0 > 0).any()


def test_ensure_labeling_overlay(project):
    _, _, model, paths = project
    _add_labels(model, 2)
    model.select_image(paths[0])
    model.update_labeling_overlays(0)  # puts the image in the scene
    item = model.get_current_image_item()

    overlay = item.ensure_labeling_overlay(2)
    assert overlay is item.labeling_overlays[2]
    assert overlay.is_displayed_in_scene
    assert overlay.zvalue == 2  # behind the selected label
    assert item.ensure_labeling_overlay(2) is overlay  # no re-creation
    assert item.ensure_labeling_overlay(99) is None  # unknown label
    assert 99 not in item.labeling_overlays


def test_update_color_without_overlay_is_a_noop(project):
    _, _, model, paths = project
    _add_labels(model, 1)
    model.select_image(paths[0])
    item = model.get_current_image_item()
    item.update_color(1)
    assert 1 not in item.labeling_overlays


def test_update_color_recolors_and_keeps_shape(project):
    _, _, model, paths = project
    _paint(model, paths[0])
    item = model.get_current_image_item()
    overlay = item.labeling_overlays[0]
    alpha_before, rgb_before = _alpha_rgb(overlay.labeling_overlay_pixmap)
    painted = alpha_before > 0
    assert painted.any()
    assert (rgb_before[painted] == [0, 255, 0]).all()

    model.label_items[0].set_color(QColor(10, 20, 200))
    item.update_color(0)

    alpha_after, rgb_after = _alpha_rgb(overlay.labeling_overlay_pixmap)
    np.testing.assert_array_equal(alpha_after, alpha_before)
    assert (rgb_after[painted] == [10, 20, 200]).all()
    # the undo history is recolored too
    for entry in overlay.undo_deque:
        a, rgb = _alpha_rgb(entry.to_pixmap())
        assert (rgb[a > 0] == [10, 20, 200]).all()
