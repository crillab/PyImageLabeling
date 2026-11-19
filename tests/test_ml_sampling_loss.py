"""Small labels on large images: how the training tiles are drawn (Tile
Sampling), the Dice loss, and a validation score that leaves the
background out."""
import numpy as np
import pytest
import torch

from PyImageLabeling.model.ML import LabelStats, Tiling
from PyImageLabeling.model.ML.MLPredictor import (
    SEG_LOSS_CE_DICE, TileDataset, dice_loss)
from tests.test_ml_tiles import _labelled_project, _tiny_training


def _source(name, boxes, shape=(400, 400)):
    mask = np.zeros(shape, np.uint8)
    for cls, (y0, y1, x0, x1) in boxes:
        mask[y0:y1, x0:x1] = cls
    image = np.zeros(shape + (3,), np.uint8)
    classes = sorted({cls for cls, _ in boxes})
    return Tiling.TileSource(name, image, mask,
                             Tiling.class_points(mask, classes))


def _share_holding(ds, cls, draws=400):
    ds.rng = np.random.default_rng(0)
    return np.mean([(ds[i % len(ds)][1] == cls).any()
                    for i in range(draws)])


def test_random_tiles_ignore_the_share():
    small = _source("a", [(1, (300, 304, 300, 304))])
    ds = TileDataset([small], 64, augment=False,
                     sampling=Tiling.SAMPLING_RANDOM, labelled_share=1.0)
    assert ds.labelled_share == 0.0
    assert _share_holding(ds, 1) < 0.2
    ds = TileDataset([small], 64, augment=False,
                     sampling=Tiling.SAMPLING_LABELS, labelled_share=1.0)
    assert _share_holding(ds, 1) == 1.0


def test_balanced_tiles_see_a_rare_label_more():
    """Class 2 is tiny, on one image of two: centred on the labels of each
    image, a quarter of the tiles hold it; balanced, half of them."""
    a = _source("a", [(1, (0, 200, 0, 400))])
    b = _source("b", [(1, (0, 200, 0, 400)), (2, (300, 306, 300, 306))])
    labels = TileDataset([a, b], 64, augment=False,
                         sampling=Tiling.SAMPLING_LABELS, labelled_share=1.0)
    balanced = TileDataset([a, b], 64, augment=False,
                           sampling=Tiling.SAMPLING_BALANCED,
                           labelled_share=1.0)
    assert len(labels) == len(balanced)        # same epoch length
    assert _share_holding(labels, 2) == pytest.approx(0.25, abs=0.07)
    assert _share_holding(balanced, 2) == pytest.approx(0.5, abs=0.07)


def test_balanced_tiles_keep_some_random_ones():
    b = _source("b", [(2, (300, 306, 300, 306))])
    ds = TileDataset([b], 64, augment=False,
                     sampling=Tiling.SAMPLING_BALANCED, labelled_share=0.0)
    assert _share_holding(ds, 2) < 0.2


def test_settings_are_normalized():
    assert Tiling.normalize_sampling("BALANCED") == "balanced"
    assert Tiling.normalize_sampling("whatever") == Tiling.DEFAULT_SAMPLING
    assert Tiling.normalize_share(1.5) == 1.0
    assert Tiling.normalize_share(-1) == 0.0
    assert Tiling.normalize_share("x") == Tiling.LABELLED_SHARE


def _logits(classes, c):
    """Confident logits predicting `classes` (B, H, W)."""
    return torch.nn.functional.one_hot(classes, c).permute(0, 3, 1, 2) \
        .float() * 20


def test_dice_loss():
    target = torch.zeros(1, 8, 8, dtype=torch.long)
    target[0, :2, :2] = 1                     # a small label
    assert dice_loss(_logits(target, 2), target, 255, background=0) \
        == pytest.approx(0, abs=1e-3)
    nothing = torch.zeros_like(target)        # the label is missed
    assert dice_loss(_logits(nothing, 2), target, 255, background=0) \
        > 0.7
    # the background is not scored: getting it wrong costs nothing here
    wrong_bg = target.clone()
    wrong_bg[0, 4:, 4:] = 1
    assert dice_loss(_logits(target, 2), target, 255, background=0) \
        < dice_loss(_logits(wrong_bg, 2), target, 255, background=0)
    # ignored pixels are left out
    ignored = target.clone()
    ignored[0, 4:, 4:] = 255
    assert dice_loss(_logits(wrong_bg, 2), ignored, 255, background=0) \
        == pytest.approx(0, abs=1e-3)
    # gradients flow
    logits = torch.zeros(1, 2, 8, 8, requires_grad=True)
    dice_loss(logits, target, 255, background=0).backward()
    assert logits.grad.abs().sum() > 0


def test_iou_scores_leave_the_background_out():
    s = LabelStats.iou_scores([10, 0, 90], [20, 0, 100], background=2)
    assert s["seg_iou"] == {0: 0.5, 2: 0.9}
    assert s["seg_miou"] == 0.5
    assert s["seg_miou_all"] == pytest.approx(0.7)
    only_bg = LabelStats.iou_scores([0, 90], [0, 100], background=1)
    assert only_bg["seg_miou"] == only_bg["seg_miou_all"] == 0.9
    assert LabelStats.iou_scores([0], [0]) == {}


def test_training_with_dice_and_balanced_tiles(project, workspace):
    _, _, model, paths = project
    _labelled_project(model, workspace, paths[:5])
    _tiny_training(model)
    model.seg_loss = SEG_LOSS_CE_DICE
    model.tile_sampling = Tiling.SAMPLING_BALANCED
    model.labelled_share = 0.33
    stats, logs = [], []
    model.train_model_core(log_callback=logs.append,
                           stats_callback=stats.append)

    assert model.is_trained()
    setup = next(s for s in stats if s["kind"] == "setup")
    assert setup["loss"] == "cross-entropy + Dice"
    assert "33 % of them centred on a label, labels balanced" \
        in setup["input"]
    epoch = [s for s in stats if s["kind"] == "epoch"][-1]
    assert epoch["dice"] is not None and epoch["ce"] is not None
    assert epoch["loss"] == pytest.approx(epoch["ce"] + epoch["dice"],
                                          rel=1e-4)
    assert sum(epoch["seen"].values()) == pytest.approx(1.0)
    assert {"seg_miou", "seg_miou_all"} <= set(model.val_metrics)
    assert any("mIoU (labels)=" in m for m in logs)


def test_settings_dialog_saves_sampling_and_loss(project, monkeypatch):
    _, view, model, _ = project
    from PyImageLabeling.controller.settings.MLSetting import MLSetting
    from PyImageLabeling.model.Utils import Utils
    saved = {}
    monkeypatch.setattr(Utils, "save_parameters",
                        staticmethod(lambda data: saved.update(data)))
    dialog = MLSetting(view.zoomable_graphics_view, model)
    dialog.tiles_radio.setChecked(True)
    dialog.sampling_combo.setCurrentIndex(
        dialog.sampling_combo.findData(Tiling.SAMPLING_RANDOM))
    assert dialog.share_row.isHidden()
    dialog.sampling_combo.setCurrentIndex(
        dialog.sampling_combo.findData(Tiling.SAMPLING_BALANCED))
    assert not dialog.share_row.isHidden()
    dialog.share_spinbox.setValue(33)
    dialog.loss_combo.setCurrentIndex(
        dialog.loss_combo.findData(SEG_LOSS_CE_DICE))
    dialog.accept()
    ml = saved["ml"]
    assert (ml["tile_sampling"], ml["labelled_share"], ml["seg_loss"]) == \
        ("balanced", 0.33, "ce_dice")

    real = Utils.load_parameters
    monkeypatch.setattr(Utils, "load_parameters",
                        staticmethod(lambda: {**real(), "ml": ml}))
    model._apply_ml_params()
    assert (model.tile_sampling, model.labelled_share, model.seg_loss) == \
        ("balanced", 0.33, "ce_dice")
    ml.update(tile_sampling="nope", seg_loss="nope", labelled_share=7)
    model._apply_ml_params()
    assert (model.tile_sampling, model.labelled_share, model.seg_loss) == \
        (Tiling.DEFAULT_SAMPLING, 1.0, "ce")
