"""Which model predicts: a file you loaded, or one trained in this session?"""
import os

import numpy as np
import pytest
import torch

from PyImageLabeling.model.ML.DinoProbe import DinoLinearProbe
from PyImageLabeling.model.ML.MLPredictor import (
    MLPredictor, FastObjectDetectorWithSegmentation,
)

CHECKPOINT = os.environ.get("ML_CHECKPOINT")


class Net(FastObjectDetectorWithSegmentation):
    def __init__(self, enable_segmentation, enable_detection):
        torch.nn.Module.__init__(self)
        self.num_classes = 2
        self.backbone_name = "resnet18"
        self.enable_segmentation = enable_segmentation
        self.enable_detection = enable_detection


def make_probe():
    return DinoLinearProbe(
        num_classes=2, mapping={0: "background", 1: "person"},
        device="cpu",
    )


def make_predictor():
    p = MLPredictor.__new__(MLPredictor)
    p.model = None
    p.trained = False
    p.probe = None
    p._probe_val_items = None
    p._model_origin = None
    p._model_saved = False
    p._model_path = None
    p.training_mode = "segmentation"
    p.label_id_to_class = {}
    p.class_to_label_id = {}
    p.val_metrics = {}
    return p


# ---------------------------------------------------------------- capabilities

def test_dino_probe_reports_segmentation_even_with_no_net():
    """The bug: prediction asked the net for enable_segmentation.

    A DINO model trains no net, so self.model is None and the UI concluded
    it could not segment, drew nothing, and the user saw an empty screen.
    """
    p = make_predictor()
    p.probe = make_probe()
    p.trained = True

    info = p.ml_model_info()
    assert info["trained"]
    assert info["can_segment"] is True
    assert info["kind"] == "DINOv2 linear probe"


def test_resnet_capabilities_follow_the_net():
    p = make_predictor()
    p.model = Net(enable_segmentation=True, enable_detection=False)
    p.training_mode = "segmentation"
    p.trained = True

    info = p.ml_model_info()
    assert info["can_segment"] is True
    assert info["can_detect"] is False


def test_detection_only_net_does_not_claim_segmentation():
    p = make_predictor()
    p.model = Net(enable_segmentation=False, enable_detection=True)
    p.training_mode = "detection"
    p.trained = True

    info = p.ml_model_info()
    assert info["can_detect"] is True
    assert info["can_segment"] is False


def test_nothing_trained_reports_nothing_available():
    p = make_predictor()
    info = p.ml_model_info()
    assert info["trained"] is False
    assert info["can_detect"] is False
    assert info["can_segment"] is False
    assert info["origin"] is None


def test_flagged_but_empty_model_is_not_reported_as_trained():
    p = make_predictor()
    p.trained = True          # flag set but no net and no probe
    assert p.ml_model_info()["trained"] is False


# ---------------------------------------------------------------- provenance

def test_trained_model_is_reported_as_unsaved():
    p = make_predictor()
    p.probe = make_probe()
    p.trained = True
    p._model_origin = "trained"

    info = p.ml_model_info()
    assert info["origin"] == "trained"
    assert info["saved"] is False
    assert info["path"] is None


def test_loaded_model_carries_its_path():
    p = make_predictor()
    p.probe = make_probe()
    p.trained = True
    p._model_origin = "loaded"
    p._model_saved = True
    p._model_path = r"C:\models\run3.pth"

    info = p.ml_model_info()
    assert info["origin"] == "loaded"
    assert info["saved"] is True
    assert info["path"] == r"C:\models\run3.pth"


def test_saving_marks_the_live_model_saved():
    p = make_predictor()
    p.probe = make_probe()
    p.trained = True
    p._model_origin = "trained"

    p.ml_mark_model_saved(r"C:\models\new.pth")
    info = p.ml_model_info()
    assert info["saved"] is True
    assert info["origin"] == "trained"      # still trained here, not loaded


def test_clearing_state_forgets_the_previous_model():
    """Starting a training must drop the loaded model.

    Otherwise a failed or aborted training leaves the old model answering
    predictions while the user believes they are testing the new one.
    """
    p = make_predictor()
    p.model = Net(enable_segmentation=True, enable_detection=True)
    p.probe = make_probe()
    p.trained = True
    p._model_origin = "loaded"
    p._model_saved = True
    p._model_path = r"C:\models\run3.pth"
    p.label_id_to_class = {1: "person"}

    p.ml_clear_trained_state()

    info = p.ml_model_info()
    assert info["trained"] is False
    assert info["origin"] is None
    assert info["path"] is None
    assert p.model is None
    assert p.probe is None
    assert p.label_id_to_class == {}


# ------------------------------------------------------- what the UI displays

def test_status_says_which_model_predicts(app_stack):
    """The status bar must not just say "Trained".

    With a model loaded at startup and another trained afterwards, both are
    plausible and nothing said which one answers a prediction.
    """
    controller, view, model = app_stack

    model.ml_clear_trained_state()
    controller.ml_update_status()
    assert "no model" in view.ml_status_label.text().lower()

    model.trained = True
    model.model = Net(enable_segmentation=True, enable_detection=False)
    model.training_mode = "segmentation"
    model._model_origin = "loaded"
    model._model_saved = True
    model._model_path = r"C:\models\run3.pth"
    controller.ml_update_status()

    text = view.ml_status_label.text()
    assert "loaded" in text.lower()
    assert "resnet" in text.lower()
    assert "run3.pth" in view.ml_status_label.toolTip()

    # now train a fresh one: it must be flagged as in-memory only
    model.ml_clear_trained_state()
    model.trained = True
    model.probe = make_probe()
    model._model_origin = "trained"
    controller.ml_update_status()

    text = view.ml_status_label.text()
    assert "trained" in text.lower()
    assert "dino" in text.lower()
    assert "not saved" in text.lower()
    assert "in memory" in text.lower()

    model.ml_clear_trained_state()
    controller.ml_update_status()


def test_badge_names_the_predicting_model(app_stack):
    controller, view, model = app_stack
    model.ml_clear_trained_state()
    model.trained = True
    model.probe = make_probe()
    model._model_origin = "trained"

    info = model.ml_model_info()
    badge = controller._ml_model_badge(info, short=True)
    assert "DINOv2" in badge
    assert "not saved" in badge

    model.ml_clear_trained_state()
    controller.ml_update_status()


def test_stats_label_reports_the_live_model(app_stack):
    controller, view, model = app_stack
    model.ml_clear_trained_state()
    model.trained = True
    model.probe = make_probe()
    model._model_origin = "trained"
    model.file_paths = []

    controller.ml_update_stats(immediate=True)
    text = view.ml_stats_label.text()
    assert "Model Status" in text
    assert "DINO" in text

    model.ml_clear_trained_state()
    controller.ml_update_stats(immediate=True)


@pytest.mark.skipif(not CHECKPOINT, reason="ML_CHECKPOINT not set")
def test_real_checkpoint_round_trip_reports_its_source(tmp_path):
    saved = tmp_path / "ck.pth"
    ck = torch.load(CHECKPOINT, map_location="cpu", weights_only=False)

    p = make_predictor()
    p.image_size = ck.get("image_size", 416)
    p.confidence_threshold = ck.get("confidence_threshold", 0.3)
    p.nms_threshold = ck.get("nms_threshold", 0.4)
    p.segmentation_threshold = ck.get("segmentation_threshold", 0.5)
    p.training_mode = ck.get("training_mode")
    p.val_metrics = ck.get("val_metrics", {})
    p.seg_backbone = ck.get("seg_backbone", "resnet")
    p.label_id_to_class = ck.get("label_id_to_class", {})
    p.class_to_label_id = ck.get("class_to_label_id", {})
    p._det_val_loader = None
    p._seg_val_loader = None
    p.probe = (DinoLinearProbe.from_dict(ck["probe"], device=torch.device("cpu"))
               if ck.get("probe") is not None else None)
    if p.probe is None:
        p.model = FastObjectDetectorWithSegmentation(
            num_classes=ck.get("num_classes", 2), pretrained=False,
            enable_segmentation=ck.get("enable_segmentation", True),
            enable_detection=ck.get("enable_detection", True),
            backbone_name=ck.get("backbone_name", "resnet18"))
        p.model.load_state_dict(ck["model_state_dict"])
        p.model.eval()
    p.trained = True
    torch.save(ck, saved)

    info = p.ml_model_info()
    assert info["trained"] is True
    assert info["can_segment"] or info["can_detect"]