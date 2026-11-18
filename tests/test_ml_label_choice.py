"""Labels to Learn (ML settings): the training learns the chosen labels only.

One label chosen makes a binary model (that label against the background).
Images where none of the chosen labels is painted are left out; the pixels
of the other labels are background, or ignored by the loss.
"""
import os

import numpy as np
import pytest
from PIL import Image as PILImage
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QDialogButtonBox

from PyImageLabeling.model.ML import Tiling
from PyImageLabeling.model.ML.MLPredictor import (
    IGNORED_LABEL, TORCH_IGNORE, SegmentationDataset)
from tests.test_ml_tiles import _tiny_training

H, W = 96, 128


def _index_mask(model, workspace, image_path, label_id, painted):
    stem = os.path.splitext(os.path.basename(image_path))[0]
    key = f"{stem}.label.{label_id}.png"
    path = os.path.join(str(workspace), key)
    PILImage.fromarray(painted.astype(np.uint8) * 255).save(path)
    model.labeling_overview_was_loaded[key] = False
    model.labeling_overview_file_paths[key] = path


def _two_labels(model, workspace, paths):
    """Label 0 ("L") and label 1 ("M"):
    image 0: both (overlapping), image 1: label 1 only, image 2: label 0 only.
    """
    model.new_label("M", "Pixel-by-pixel", QColor(255, 0, 0))
    rng = np.random.RandomState(3)
    a = np.zeros((H, W), bool)
    a[10:40, 10:50] = True
    b = np.zeros((H, W), bool)
    b[30:70, 40:90] = True          # overlaps a on [30:40, 40:50]
    for path in paths[:3]:
        image = rng.randint(0, 60, (H, W, 3), np.uint8)
        image[a] = 220
        image[b] = 120
        PILImage.fromarray(image).save(path)
    _index_mask(model, workspace, paths[0], 0, a)
    _index_mask(model, workspace, paths[0], 1, b)
    _index_mask(model, workspace, paths[1], 1, b)
    _index_mask(model, workspace, paths[2], 0, a)
    return a, b


def test_all_labels_by_default(project, workspace):
    _, _, model, paths = project
    _two_labels(model, workspace, paths)
    data = dict(model.collect_segmentation_data(paths[:3]))
    assert set(data) == set(paths[:3])
    assert set(np.unique(data[paths[0]])) == {0, 1, 255}


def test_chosen_label_keeps_its_images_and_the_others_are_background(
        project, workspace):
    _, _, model, paths = project
    a, b = _two_labels(model, workspace, paths)
    data = dict(model.collect_segmentation_data(paths[:3], label_ids={0}))
    # image 1 holds label 1 only: left out
    assert set(data) == {paths[0], paths[2]}
    mask = data[paths[0]]
    assert (mask[a] == 0).all()
    assert (mask[~a] == 255).all()       # label 1 is background


def test_other_labels_can_be_ignored(project, workspace):
    _, _, model, paths = project
    a, b = _two_labels(model, workspace, paths)
    data = dict(model.collect_segmentation_data(
        paths[:3], label_ids={0}, ignored_ids={1}))
    assert set(data) == {paths[0], paths[2]}
    mask = data[paths[0]]
    assert (mask[a] == 0).all()           # the learnt label wins
    assert (mask[b & ~a] == IGNORED_LABEL).all()
    assert (mask[~a & ~b] == 255).all()


def test_dino_probe_gives_ignored_pixels_no_target():
    from PyImageLabeling.model.ML.DinoProbe import (
        GRID, IGNORE, DinoLinearProbe)
    mask = np.full((GRID * 4, GRID * 4), 255, np.uint8)
    mask[:GRID] = 3
    mask[GRID:2 * GRID] = IGNORED_LABEL
    probe = DinoLinearProbe(2, {3: 0, 255: 1}, device="cpu")
    t = probe.mask_to_target(mask)
    assert set(t.unique().tolist()) == {0, 1, IGNORE}


def test_segmentation_dataset_ignores_unmapped_values(tmp_path):
    path = str(tmp_path / "x.png")
    PILImage.fromarray(np.zeros((8, 8, 3), np.uint8)).save(path)
    mask = np.full((8, 8), 255, np.uint8)
    mask[:2] = 3
    mask[2:4] = IGNORED_LABEL
    ds = SegmentationDataset([path], [mask], {3: 0, 255: 1}, image_size=8,
                             augment=False)
    _, target = ds[0]
    assert (target[:2] == 0).all()
    assert (target[2:4] == TORCH_IGNORE).all()
    assert (target[4:] == 1).all()


def test_binary_training_learns_the_chosen_label_only(project, workspace):
    _, _, model, paths = project
    _two_labels(model, workspace, paths)
    _tiny_training(model)
    model.train_label_ids = [1]
    logs = []
    model.train_model_core(paths[:3], log_callback=logs.append)

    assert model.is_trained()
    assert model.model.num_classes == 2
    assert set(model.class_to_label_id.values()) == {1, 255}
    assert any("Labels learnt: M against the background (binary)" in m
               for m in logs)
    preds = model.predict_segmentation(paths[0], 0.0)
    assert set(preds) <= {1}


def test_ignored_pixels_reach_the_tiles_as_ignore_index(project, workspace,
                                                        monkeypatch):
    _, _, model, paths = project
    a, b = _two_labels(model, workspace, paths)
    _tiny_training(model)
    model.train_label_ids = [0]
    model.other_labels_as_background = False
    seen = {}

    def no_training(num_classes, has_seg, det_loader, seg_loader, *rest):
        seen["num_classes"] = num_classes
        seen["masks"] = {s.path: np.array(s.mask)
                         for s in seg_loader.dataset.sources}
    monkeypatch.setattr(model, "_train_network", no_training)
    model.train_model_core(paths[:3])

    assert seen["num_classes"] == 2
    mask = seen["masks"][paths[0]]
    label = model.label_id_to_class[0]
    assert (mask[a] == label).all()
    assert (mask[b & ~a] == Tiling.IGNORE_INDEX).all()
    assert (mask[~a & ~b] == model.label_id_to_class[255]).all()


def test_no_image_with_the_chosen_labels(project, workspace):
    _, _, model, paths = project
    _two_labels(model, workspace, paths)
    _tiny_training(model)
    model.train_label_ids = [1]
    with pytest.raises(RuntimeError, match="none of the labels chosen"):
        model.train_model_core([paths[2]])


def test_shapes_of_the_other_labels_are_left_out(project):
    _, _, model, paths = project
    base = os.path.basename(paths[0])
    model.left_rectangles[base] = [
        {"x": 1, "y": 1, "width": 5, "height": 5, "label_id": 0},
        {"x": 9, "y": 9, "width": 5, "height": 5, "label_id": 1}]
    model.left_rectangles[os.path.basename(paths[1])] = [
        {"x": 1, "y": 1, "width": 5, "height": 5, "label_id": 0}]
    data = dict(model.collect_training_data(paths[:2], label_ids={1}))
    assert list(data) == [paths[0]]
    assert [a[-1] for a in data[paths[0]]] == [1]


def test_image_counts_follow_the_chosen_labels(project, workspace):
    _, _, model, paths = project
    _two_labels(model, workspace, paths)
    assert model.ml_training_image_counts(paths[:3]) == (0, 3)
    model.train_label_ids = [1]
    assert model.ml_training_image_counts(paths[:3]) == (0, 2)
    model.train_label_ids = [0, 1]
    assert model.ml_training_image_counts(paths[:3]) == (0, 3)


def test_choice_is_forgotten_with_the_project(project):
    _, _, model, _ = project
    model.train_label_ids = [0]
    model.close_project()
    assert model.train_label_ids is None


def test_settings_dialog_chooses_the_labels(project, workspace, monkeypatch):
    _, view, model, paths = project
    _two_labels(model, workspace, paths)
    from PyImageLabeling.controller.settings.MLSetting import MLSetting
    from PyImageLabeling.model.Utils import Utils
    saved = {}
    monkeypatch.setattr(Utils, "save_parameters",
                        staticmethod(lambda data: saved.update(data)))

    dialog = MLSetting(view.zoomable_graphics_view, model)
    table = dialog.labels_table
    ok = dialog.buttons.button(QDialogButtonBox.StandardButton.Ok)
    assert table.rowCount() == 2
    assert dialog.chosen_label_ids() is None          # all of them
    assert not dialog.other_labels_checkbox.isEnabled()

    table.item(0, 0).setCheckState(Qt.CheckState.Unchecked)
    assert dialog.chosen_label_ids() == [1]
    assert "Binary model" in dialog.labels_summary.text()
    assert dialog.other_labels_checkbox.isEnabled()

    table.item(1, 0).setCheckState(Qt.CheckState.Unchecked)
    assert dialog.chosen_label_ids() == []
    assert not ok.isEnabled()

    table.item(1, 0).setCheckState(Qt.CheckState.Checked)
    dialog.other_labels_checkbox.setChecked(False)
    dialog.accept()
    assert saved["ml"]["other_labels_background"] is False

    # the dialog shows the model's choice when it opens again
    model.train_label_ids = [1]
    dialog = MLSetting(view.zoomable_graphics_view, model)
    try:
        assert dialog.labels_table.item(0, 0).checkState() \
            == Qt.CheckState.Unchecked
        assert dialog.chosen_label_ids() == [1]
    finally:
        dialog.reject()
