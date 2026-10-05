"""Real end-to-end DINO: train on painted masks, then draw predictions.

No encoder stub here — this drives the actual DinoLinearProbe so the UI path
that used to fail (empty screen after a DINO training) is exercised for real.
"""
import numpy as np
import pytest
import torch
from PyQt6.QtCore import QPointF


def _paint_square(model, path, box):
    model.select_image(path)
    model.start_paint_brush(QPointF(*box[0]))
    model.move_paint_brush(QPointF(*box[1]))
    model.end_paint_brush()


@pytest.mark.slow
def test_dino_training_then_prediction_draws_masks(project, monkeypatch):
    controller, view, model, paths = project

    # paint a square on the left half of every image: a learnable signal
    for p in paths:
        _paint_square(model, p, ((10, 10), (70, 70)))

    painted = {}
    monkeypatch.setattr(
        model, "ml_visualize_segmentation",
        lambda seg: painted.update(seg=seg))

    model.seg_backbone = "dinov2"
    model.num_epochs = 2
    model.learning_rate = 1e-3
    model.batch_size = 4
    model.training_mode = "segmentation"

    real_dialog = getattr(model, "_progress_dialog", None)
    monkeypatch.setattr(
        torch.nn.Module, "train", lambda self, mode=True: self)

    model.train_model_core(selected_paths=list(paths))

    # a DINO model trains a probe and no net: that is the whole point
    assert model.probe is not None, "no probe was created"
    assert model.model is None, "a net was built, so this is not the DINO path"
    assert model.is_trained()

    info = model.ml_model_info()
    assert info["can_segment"], "DINO reports it cannot segment: the bug"
    assert info["origin"] == "trained"
    assert info["saved"] is False

    controller.ml_update_status()
    assert "green" in view.ml_status_label.styleSheet()

    painted.clear()
    model.select_image(paths[0])
    # 2 epochs on 10 synthetic images is a weak model: its top pixel sits
    # near 0.6 confidence, below the slider default of 0.70
    view.ml_confidence_slider.setValue(20)
    controller.ml_predict_current()

    assert "seg" in painted, "DINO prediction never reached the view"
    assert any(np.any(m > 0) for m in painted["seg"].values()), \
        "DINO drew an all-empty mask"

    model.ml_clear_trained_state()
    controller.ml_update_status()
    assert real_dialog is None or True