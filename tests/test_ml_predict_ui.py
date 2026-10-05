"""End-to-end: a DINO-trained model must actually draw masks.

Reproduces the reported failure: after training with the DINO head, nothing
was drawn and the status label stayed gray. Both came from ml_predict_current
and ml_update_status reading model.model, which is None for a DINO model.
"""
import numpy as np
import pytest
import torch

from PyImageLabeling.model.ML.DinoProbe import DinoLinearProbe
from PyImageLabeling.model.ML.MLPredictor import (
    MLPredictor, FastObjectDetectorWithSegmentation,
)


class Net(FastObjectDetectorWithSegmentation):
    def __init__(self, enable_segmentation, enable_detection):
        torch.nn.Module.__init__(self)
        self.num_classes = 2
        self.backbone_name = "resnet18"
        self.enable_segmentation = enable_segmentation
        self.enable_detection = enable_detection


def _probe():
    # mapping is {original_label_id: class_id}; identity here
    return DinoLinearProbe(
        num_classes=2, mapping={0: 0, 1: 1}, device="cpu")


def _install_probe(model, mask_value=255):
    """A DINO model whose probe returns a non-empty mask for every image."""
    probe = _probe()
    # bypass the frozen encoder: hand back a fixed all-ones feature grid so
    # the test exercises the UI path, not the 300M-param backbone
    probe.encoder = object()
    probe.processor = None
    probe.feat_dim = 8

    def _encode_path(_path):
        return torch.ones(8, 2, 2)

    probe.encode_path = _encode_path
    probe.encode = lambda _rgb: torch.ones(8, 2, 2)
    probe.head = torch.nn.Conv2d(8, 2, kernel_size=1)
    with torch.no_grad():
        probe.head.weight.zero_()
        probe.head.bias.copy_(torch.tensor(
            [float(mask_value), -float(mask_value)]))

    model.probe = probe
    model.model = None
    model.trained = True
    model._model_origin = "trained"
    return probe


def _install_net(model):
    model.model = Net(enable_segmentation=True, enable_detection=False)
    model.probe = None
    model.trained = True
    model.training_mode = "segmentation"
    model._model_origin = "trained"


def test_dino_prediction_reaches_the_view(project, monkeypatch):
    controller, view, model, paths = project
    model.select_image(paths[0])

    drawn = {}
    monkeypatch.setattr(
        model, "ml_visualize_segmentation",
        lambda seg: drawn.update(seg=seg))

    _install_probe(model)
    controller.ml_predict_current()

    assert "seg" in drawn, "DINO prediction never reached the view"
    assert drawn["seg"], "DINO returned no mask at all"
    assert any(np.any(m > 0) for m in drawn["seg"].values())

    model.ml_clear_trained_state()


def test_resnet_prediction_still_reaches_the_view(project, monkeypatch):
    controller, view, model, paths = project
    model.select_image(paths[0])

    drawn = {}
    monkeypatch.setattr(
        model, "ml_visualize_segmentation",
        lambda seg: drawn.update(seg=seg))
    monkeypatch.setattr(
        model, "predict_segmentation",
        lambda path, conf=None: {1: np.full((128, 128), 255, np.uint8)})

    _install_net(model)
    controller.ml_predict_current()

    assert "seg" in drawn, "ResNet regression: segmentation not displayed"

    model.ml_clear_trained_state()


def test_status_badge_turns_green_for_dino(project):
    """'ML trained' never turned green with DINO."""
    controller, view, model, _ = project

    model.ml_clear_trained_state()
    controller.ml_update_status()
    assert "gray" in view.ml_status_label.styleSheet()

    _install_probe(model)
    controller.ml_update_status()

    assert "green" in view.ml_status_label.styleSheet()
    assert "trained" in view.ml_status_label.text().lower()

    model.ml_clear_trained_state()
    controller.ml_update_status()


def test_starting_training_clears_the_previous_model(project):
    """A loaded model must not survive a new training and answer for it."""
    controller, view, model, _ = project

    model.ml_clear_trained_state()
    model.trained = True
    model.model = Net(True, True)
    model._model_origin = "loaded"
    model._model_saved = True
    model._model_path = r"C:\models\old.pth"

    # what ml_train_model does before launching the worker
    model.ml_clear_trained_state()
    controller.ml_update_status()

    assert model.model is None
    assert model.is_trained() is False
    assert "no model" in view.ml_status_label.text().lower()


def test_detection_gate_is_no_longer_always_false(project, monkeypatch):
    """The old gate read enable_detection off the predictor, where it never
    existed, so boxes were silently skipped for every model."""
    controller, view, model, paths = project
    model.select_image(paths[0])

    called = {}
    monkeypatch.setattr(
        controller, "ml_predictor_start",
        lambda path, conf=0.7: called.setdefault("boxes", [(1, 1, 2, 2, 0.9, "L")]))
    monkeypatch.setattr(
        model, "ml_visualize_predictions",
        lambda preds: called.setdefault("drawn", preds))
    monkeypatch.setattr(model, "predict_segmentation", lambda path, conf=None: None)

    _install_net(model)
    model.model.enable_detection = True
    model.training_mode = "both"
    model.model.__class__ = type("N", (Net,),
                                 {"enable_detection": True,
                                  "enable_segmentation": True})
    controller.ml_predict_current()

    assert "drawn" in called, "detection predictions still never requested"

    model.ml_clear_trained_state()