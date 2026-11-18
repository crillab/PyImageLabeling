"""Figures sent to the training dialog, and the dialog itself."""
import math

from PyImageLabeling.view.TrainingDialog import TrainingDialog, format_duration

from tests.test_ml_tiles import _labelled_project, _tiny_training


def _train_with_stats(model, workspace, paths, **tiles):
    _labelled_project(model, workspace, paths)
    _tiny_training(model, **tiles)
    stats = []
    model.train_model_core(stats_callback=stats.append)
    return stats


def test_stats_of_a_training_by_tiles(project, workspace):
    _, _, model, paths = project
    stats = _train_with_stats(model, workspace, paths[:5])

    setup = stats[0]
    assert setup["kind"] == "setup"
    assert setup["unit"] == "tiles"
    assert setup["input"].startswith("tiles of 64 px, overlap 16 px")
    assert (setup["train_images"], setup["val_images"]) == (4, 1)
    names = [c["name"] for c in setup["classes"]]
    assert "Background" in names and len(names) == model.model.num_classes
    # every train image holds the painted label and the background
    assert all(n == 4 for n in setup["images_per_class"].values())
    assert sum(setup["pixels_per_class"].values()) == 4 * 192 * 256

    epochs = [s for s in stats if s["kind"] == "epoch"]
    assert [s["epoch"] for s in epochs] == [1, 2]
    for s in epochs:
        assert s["inputs"] == setup["tiles_per_epoch"]
        assert all(0 <= n <= s["inputs"] for n in s["present"])
        # entropy of the class proportions: between 0 and ln(classes)
        assert 0 < s["reference"] <= math.log(len(names)) + 1e-9
        assert 0 <= s["pixel_accuracy"] <= 1
        assert all(0 <= v <= 1 for v in s["train_iou"].values())
        assert s["seg_loss"] == s["loss"] and s["det_loss"] is None
    assert "seg_iou" in model.val_metrics


def test_stats_of_a_training_on_whole_images(project, workspace):
    _, _, model, paths = project
    stats = _train_with_stats(model, workspace, paths[:5], mode="off")
    assert stats[0]["unit"] == "images"
    assert stats[0]["input"] == "whole images resized to 64 px"
    epochs = [s for s in stats if s["kind"] == "epoch"]
    assert epochs and all(s["inputs"] == 4 for s in epochs)


def test_dialog_shows_the_figures_and_stays_open_at_the_end(project):
    dialog = TrainingDialog(3)
    try:
        dialog.on_stats({
            "kind": "setup", "unit": "tiles", "input": "tiles of 512 px",
            "backbone": "ResNet18", "pretrained": True, "device": "cpu",
            "epochs": 2, "batch": 8, "lr": 0.002, "train_images": 2,
            "val_images": 1, "tiles_per_epoch": 10,
            "classes": [{"cls": 0, "name": "A", "color": (255, 0, 0)},
                        {"cls": 1, "name": "Background", "color": None}],
            "images_per_class": {0: 2, 1: 2},
            "pixels_per_class": {0: 25, 1: 75}})
        assert dialog.table.rowCount() == 2
        assert dialog.table.item(0, 2).text() == "25.0 %"

        dialog.on_epoch(1, 2, 0.5)
        dialog.on_stats({
            "kind": "epoch", "epoch": 1, "total": 2, "loss": 0.5,
            "seg_loss": 0.5, "det_loss": None, "reference": 0.5623,
            "pixel_accuracy": 0.9, "train_iou": {0: 0.4, 1: 0.8},
            "present": [6, 10], "inputs": 10, "seconds": 70, "batch": 8})
        text = dialog.epoch_label.text()
        assert "0.5000" in text and "0.5623" in text and "89 %" in text
        assert "1 min 10 s left" in text
        assert dialog.table.item(0, 3).text() == "6 (60 %)"
        assert dialog.table.item(1, 4).text() == "0.800"
        assert len(dialog.curve.losses) == 1

        dialog.add_log("hello")
        assert "hello" in dialog.log_view.toPlainText()

        # cannot be closed while training
        assert not dialog.buttons.isEnabled()
        dialog.reject()
        assert dialog.running

        dialog.finish({"seg_miou": 0.6, "seg_loss": 0.3,
                       "seg_iou": {0: 0.45, 1: 0.75}}, "segmentation", 2)
        assert dialog.buttons.isEnabled()
        assert dialog.table.item(0, 5).text() == "0.450"
        assert "mIoU <b>0.600</b>" in dialog.epoch_label.text()
        assert "on 1 image(s)" in dialog.epoch_label.text()
    finally:
        dialog.running = False
        dialog.close()


def test_dialog_without_stats_shows_the_loss(project):
    """The DINOv2 probe only reports the loss of each epoch."""
    dialog = TrainingDialog(3)
    try:
        dialog.on_epoch(1, 3, 0.75)
        assert "0.7500" in dialog.epoch_label.text()
        assert dialog.curve.losses == [0.75]
        dialog.finish({}, "segmentation", 2)
        assert "No validation" in dialog.epoch_label.text()
    finally:
        dialog.close()


def test_format_duration():
    assert format_duration(42) == "42 s"
    assert format_duration(130) == "2 min 10 s"
    assert format_duration(3900) == "1 h 05 min"
