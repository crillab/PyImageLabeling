"""Training reads the masks of images that are not loaded from their files.

Training used to load every selected image first (an ImageItem, with a
full-size ARGB overlay per painted label) only to read its masks back, which
cost GBs on large images. Now only the loaded images are read from their
overlays (they may hold unsaved strokes); the others from the mask files.
"""
import os

import numpy as np
from PIL import Image as PILImage
from PyQt6.QtCore import QPointF

from PyImageLabeling.model.Masks import read_painted_mask


def _paint(model, path):
    model.select_image(path)
    model.start_paint_brush(QPointF(20.0, 20.0))
    model.move_paint_brush(QPointF(60.0, 50.0))
    model.end_paint_brush()


def _index_mask(model, workspace, image_path, label_id, painted):
    """Write a mask file for (image, label) and index it, as a project
    opened from disk does."""
    stem = os.path.splitext(os.path.basename(image_path))[0]
    key = f"{stem}.label.{label_id}.png"
    path = os.path.join(str(workspace), key)
    PILImage.fromarray(painted.astype(np.uint8) * 255).save(path)
    model.labeling_overview_was_loaded[key] = False
    model.labeling_overview_file_paths[key] = path
    return path


def test_read_painted_mask_formats(tmp_path):
    painted = np.zeros((20, 30), bool)
    painted[5:10, 3:12] = True

    p_mode = tmp_path / "p.png"   # palette: index 0 white (painted), 1 black
    im = PILImage.fromarray((~painted).astype(np.uint8), mode="P")
    im.putpalette([255, 255, 255, 0, 0, 0])
    im.save(p_mode)
    one_bit = tmp_path / "one.png"
    PILImage.fromarray(painted).convert("1").save(one_bit)
    rgb = tmp_path / "rgb.png"
    arr = np.zeros((20, 30, 3), np.uint8)
    arr[painted] = (0, 200, 0)
    PILImage.fromarray(arr).save(rgb)

    for path in (p_mode, one_bit, rgb):
        np.testing.assert_array_equal(read_painted_mask(str(path)), painted)
    assert read_painted_mask(str(tmp_path / "missing.png")) is None


def test_saved_mask_reads_back_as_painted(project, workspace):
    """The format the app writes is read back with the same pixels."""
    _, _, model, paths = project
    _paint(model, paths[0])
    item = model.get_current_image_item()
    painted = model._overlay_painted(item.get_labeling_overlay())
    model.save_directory = str(workspace)
    model.save()

    saved = read_painted_mask(os.path.join(str(workspace),
                                           "img000.label.0.png"))
    assert painted.any()
    np.testing.assert_array_equal(saved, painted)


def test_unloaded_image_is_read_from_its_mask_file(project, workspace):
    _, _, model, paths = project
    painted = np.zeros((128, 128), bool)
    painted[10:40, 20:50] = True
    _index_mask(model, workspace, paths[3], 0, painted)

    data = dict(model.collect_segmentation_data())

    assert list(data) == [paths[3]]
    np.testing.assert_array_equal(data[paths[3]] == 0, painted)
    assert set(np.unique(data[paths[3]])) == {0, 255}
    # nothing was loaded to read it
    assert model.image_items[paths[3]] is None


def test_loaded_image_with_unsaved_strokes_is_read_from_memory(project):
    _, _, model, paths = project
    _paint(model, paths[1])   # not saved: no mask file

    data = dict(model.collect_segmentation_data())

    assert list(data) == [paths[1]]
    assert (data[paths[1]] == 0).sum() > 0


def test_training_counts_need_no_loading(project, workspace):
    _, _, model, paths = project
    painted = np.zeros((128, 128), bool)
    painted[:5, :5] = True
    _index_mask(model, workspace, paths[2], 0, painted)
    model.left_rectangles[os.path.basename(paths[4])] = [
        {"x": 1, "y": 2, "width": 30, "height": 40, "label_id": 0}]
    _paint(model, paths[5])

    assert model.ml_training_image_counts() == (1, 2)
    assert model.image_items[paths[2]] is None
    assert model.image_items[paths[4]] is None

    # shapes of an image that is not loaded are training data too
    det = dict(model.collect_training_data())
    assert det == {paths[4]: [(1, 2, 30, 40, 0)]}
