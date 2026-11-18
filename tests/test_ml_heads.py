"""The Enable Segmentation / Detection Head boxes of the ML settings."""
import pytest
from PyQt6.QtWidgets import QMessageBox

from tests.test_ml_tiles import _labelled_project, _tiny_training


def test_disabled_segmentation_head_ignores_painted_pixels(project, workspace,
                                                          monkeypatch):
    _, _, model, paths = project
    _labelled_project(model, workspace, paths[:5])
    _tiny_training(model)
    monkeypatch.setattr(model, "enable_segmentation", False)
    with pytest.raises(RuntimeError, match="No training data"):
        model.train_model_core()


def test_refused_training_keeps_the_model(project, monkeypatch):
    controller, _, model, _ = project
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(
        lambda parent, title, text: warnings.append((title, text))))
    monkeypatch.setattr(model, "_apply_ml_params", lambda: None)
    monkeypatch.setattr(model, "trained", True)
    monkeypatch.setattr(model, "enable_detection", False)
    monkeypatch.setattr(model, "enable_segmentation", False)
    controller.ml_train_model()
    assert warnings[-1][0] == "Nothing to Train"
    assert model.trained

    # only shapes, but the detection head is disabled
    model.enable_segmentation = True
    monkeypatch.setattr(model, "ml_training_image_counts",
                        lambda paths=None: (3, 0))
    controller.ml_train_model()
    title, text = warnings[-1]
    assert title == "Insufficient Data"
    assert "3 images with geometric shapes (head disabled" in text
    assert model.trained
