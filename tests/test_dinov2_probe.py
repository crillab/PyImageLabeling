"""DINOv2-linear segmentation head: train, predict, save/load, fallback."""
import os

import numpy as np
from PIL import Image as PILImage
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QColor

from tests.conftest import make_images


def _paint_boxes(model, paths, specs, la, lb):
    for i, p in enumerate(paths):
        model.load_image_for_training(p)
        model.select_image(p)
        kind, x0, y0, x1, y1 = specs[i]
        item = model.get_current_image_item()
        target = la if kind == 0 else lb
        model.set_current_label_item(target)
        model.update_labeling_overlays(target.get_label_id())
        painter = item.get_labeling_overlay().get_painter()
        painter.fillRect(x0, y0, x1 - x0, y1 - y0, target.get_color())
        item.update_labeling_overlay()


def _probe_project(app_stack, workspace):
    controller, view, model = app_stack
    from tests.conftest import reset_app
    reset_app(controller, view, model)
    paths = make_images(workspace, 6, size=128, seed=3)
    for p in paths:
        model.file_paths.append(p)
        model.image_items[p] = None
    view.file_bar_add(list(paths))
    la = model.new_label("A", "Pixel-by-pixel", QColor(0, 0, 255))
    lb = model.new_label("B", "Pixel-by-pixel", QColor(255, 0, 0))
    rng = np.random.RandomState(5)
    specs = []
    for i in range(6):
        x0, y0 = rng.randint(5, 50, 2)
        w, h = rng.randint(30, 60, 2)
        specs.append((i % 2, int(x0), int(y0),
                      min(int(x0 + w), 127), min(int(y0 + h), 127)))
    _paint_boxes(model, paths, specs, la, lb)
    return controller, view, model, paths


def _train_probe(model, epochs=5):
    model.seg_backbone = "dinov2"
    model.num_epochs = epochs
    model.batch_size = 2
    model.image_size = 64
    model.learning_rate = 0.001
    model.train_model_core()


def test_probe_trains_and_validates(app_stack, workspace):
    _, _, model, _ = _probe_project(app_stack, workspace)
    _train_probe(model)
    assert model.trained is True
    assert model.training_mode == "segmentation"
    assert model.probe is not None
    assert model.model is None
    assert model.label_id_to_class == {255: 1, 0: 0, 1: 2} or \
        set(model.label_id_to_class) == {255, 0, 1}
    assert model.val_metrics.get("seg_miou", 0) > 0.3


def test_probe_predicts_label_masks(app_stack, workspace):
    _, _, model, paths = _probe_project(app_stack, workspace)
    _train_probe(model)
    out = model.predict_segmentation(paths[0])
    assert isinstance(out, dict) and len(out) > 0
    h, w = np.array(PILImage.open(paths[0])).shape[:2]
    for lid, mask in out.items():
        assert lid in (0, 1, 255)
        assert mask.shape == (h, w)
        assert mask.dtype == np.uint8
        assert set(np.unique(mask).tolist()) <= {0, 255}


def test_probe_save_load_roundtrip(app_stack, workspace, tmp_path):
    _, _, model, paths = _probe_project(app_stack, workspace)
    _train_probe(model)
    before = model.predict_segmentation(paths[0])
    model.save_model_file(str(tmp_path), "probe_test")
    assert os.path.isfile(str(tmp_path / "probe_test.pth"))
    model.probe = None
    model.model = None
    model.trained = False
    assert model.load_model_file(str(tmp_path / "probe_test.pth")) is True
    assert model.trained is True
    assert model.probe is not None
    assert model.model is None
    after = model.predict_segmentation(paths[0])
    assert set(after) == set(before)
    for lid in before:
        assert np.array_equal(before[lid], after[lid])


def test_probe_falls_back_with_detection_shapes(app_stack, workspace):
    controller, view, model, paths = _probe_project(app_stack, workspace)
    model.select_image(paths[0])
    model.start_rectangle_tool(QPointF(10.0, 10.0))
    model.move_rectangle_tool(QPointF(50.0, 50.0))
    model.end_rectangle_tool()
    _train_probe(model)
    assert model.training_mode == "both"
    assert model.model is not None
    assert model.probe is None


def test_resnet_default_unchanged(app_stack, workspace):
    _, _, model, _ = _probe_project(app_stack, workspace)
    assert model.seg_backbone == "resnet"
    model.num_epochs = 2
    model.batch_size = 2
    model.image_size = 64
    model.train_model_core()
    assert model.model is not None
    assert model.probe is None