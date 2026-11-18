"""The former DINOv2-linear segmentation head: its setting now trains the
network with a frozen DINOv2 backbone and the linear decoder, and its model
files still load and predict."""
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


def _train_old_setting(model, epochs=3):
    model.seg_backbone = "dinov2"
    model.num_epochs = epochs
    model.batch_size = 2
    model.image_size = 64
    model.learning_rate = 0.001
    model.train_model_core()


def test_old_setting_trains_the_dinov2_network(app_stack, workspace):
    _, _, model, paths = _probe_project(app_stack, workspace)
    _train_old_setting(model)
    assert model.trained is True
    assert model.training_mode == "segmentation"
    assert model.probe is None
    assert model.model.backbone_name == "DINOv2-S/14"
    assert model.model.seg_decoder == "linear"
    assert model.model.backbone.trainable_blocks == 0
    assert model.seg_backbone == "resnet"          # setting converted
    assert "seg_miou" in model.val_metrics
    assert isinstance(model.predict_segmentation(paths[0], 0.0), dict)


def test_old_setting_with_detection_shapes(app_stack, workspace):
    # the probe could not detect (it fell back to the ResNet head): the
    # network does both, on its DINOv2 backbone
    controller, view, model, paths = _probe_project(app_stack, workspace)
    model.select_image(paths[0])
    model.start_rectangle_tool(QPointF(10.0, 10.0))
    model.move_rectangle_tool(QPointF(50.0, 50.0))
    model.end_rectangle_tool()
    _train_old_setting(model, epochs=2)
    assert model.training_mode == "both"
    assert model.model.backbone_name == "DINOv2-S/14"
    assert model.probe is None


def _old_probe_file(model, paths, folder):
    """A model file of the former DINOv2-linear head (no longer trained)."""
    from PyImageLabeling.model.ML.DinoProbe import DinoLinearProbe
    model.label_id_to_class = {0: 0, 1: 1, 255: 2}
    model.class_to_label_id = {0: 0, 1: 1, 2: 255}
    items = []
    for p in paths:
        mask = np.full((128, 128), 255, np.uint8)
        mask[20:60, 20:60] = 0
        mask[70:110, 70:110] = 1
        items.append((p, mask))
    probe = DinoLinearProbe(3, model.label_id_to_class, device=model.device)
    probe.fit(items, epochs=3, lr=0.01)
    model.probe, model.model = probe, None
    model.trained = True
    model.training_mode = "segmentation"
    model.save_model_file(str(folder), "probe_test")
    return str(folder / "probe_test.pth")


def test_old_probe_file_still_loads_and_predicts(app_stack, workspace,
                                                 tmp_path):
    _, _, model, paths = _probe_project(app_stack, workspace)
    path = _old_probe_file(model, paths[:3], tmp_path)
    before = model.predict_segmentation(paths[0], 0.0)
    assert before
    model.ml_clear_trained_state()
    assert model.load_model_file(path) is True
    assert model.trained is True
    assert model.probe is not None and model.model is None
    assert model.ml_model_info()["can_segment"]
    h, w = np.array(PILImage.open(paths[0])).shape[:2]
    after = model.predict_segmentation(paths[0], 0.0)
    assert set(after) == set(before)
    for lid in before:
        assert after[lid].shape == (h, w)
        assert np.array_equal(before[lid], after[lid])


def test_resnet_default_unchanged(app_stack, workspace):
    _, _, model, _ = _probe_project(app_stack, workspace)
    assert model.seg_backbone == "resnet"
    model.num_epochs = 2
    model.batch_size = 2
    model.image_size = 64
    model.train_model_core()
    assert model.model is not None
    assert model.probe is None
