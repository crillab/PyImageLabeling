"""Accept paints the prediction shown on the current image, and nothing
else: changing image or Clear used to leave the prediction in memory, and
Accept painted it afterwards (on the other image too)."""
import numpy as np

from tests.test_ml_predict_ui import _install_net


def _predict(controller, model, monkeypatch, value=1):
    monkeypatch.setattr(
        model, "predict_segmentation",
        lambda path, conf=None: {0: np.full((128, 128), value, np.uint8)})
    _install_net(model)
    controller.ml_predict_current()


def _painted(model, path):
    item = model.image_items[path]
    return any(o.get_is_edited() for o in item.labeling_overlays.values())


def test_accept_paints_the_prediction(project, monkeypatch):
    controller, _, model, paths = project
    model.select_image(paths[0])
    _predict(controller, model, monkeypatch)
    controller.ml_accept_predictions()
    assert _painted(model, paths[0])
    model.ml_clear_trained_state()


def test_accept_after_clear_paints_nothing(project, monkeypatch):
    controller, _, model, paths = project
    model.select_image(paths[0])
    _predict(controller, model, monkeypatch)
    controller.ml_clear_predictions()
    controller.ml_accept_predictions()
    assert not _painted(model, paths[0])
    model.ml_clear_trained_state()


def test_accept_on_another_image_paints_nothing(project, monkeypatch):
    controller, _, model, paths = project
    model.select_image(paths[0])
    _predict(controller, model, monkeypatch)
    model.select_image(paths[1])
    controller.ml_accept_predictions()
    assert not _painted(model, paths[1])
    assert not _painted(model, paths[0])
    assert model.ml_segmentation_predictions is None
    model.ml_clear_trained_state()


def test_an_empty_prediction_drops_the_previous_one(project, monkeypatch):
    controller, _, model, paths = project
    model.select_image(paths[0])
    _predict(controller, model, monkeypatch)
    _predict(controller, model, monkeypatch, value=0)   # finds nothing
    controller.ml_accept_predictions()
    assert not _painted(model, paths[0])
    model.ml_clear_trained_state()
