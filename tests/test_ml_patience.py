"""Patience: stop the training when the validation no longer improves, and
keep the weights of the best epoch."""
import torch

from PyImageLabeling.model.ML.MLPredictor import _EarlyStopping
from PyImageLabeling.view.TrainingDialog import TrainingDialog
from tests.test_ml_tiles import _labelled_project, _tiny_training


def test_stopper_waits_patience_epochs_after_the_best():
    net = torch.nn.Linear(2, 1)
    stopper = _EarlyStopping(2)
    scores = [0.3, 0.5, 0.5, 0.49, 0.6]
    stopped = None
    for epoch, score in enumerate(scores, 1):
        with torch.no_grad():
            net.weight.fill_(epoch)
        stopper.update(epoch, {"seg_miou": score}, net)
        if stopper.should_stop():
            stopped = epoch
            break
    # 0.5 at epoch 2, no progress at 3 and 4 (a tie is no progress)
    assert stopped == 4 and stopper.best_epoch == 2
    assert stopper.restore(net)
    assert (net.weight == 2).all()


def test_stopper_detection_loss_and_off():
    stopper = _EarlyStopping(1)
    net = torch.nn.Linear(1, 1)
    stopper.update(1, {"det_loss": 1.0}, net)
    stopper.update(2, {"det_loss": 0.8}, net)       # lower loss = better
    assert stopper.best_epoch == 2 and not stopper.should_stop()
    assert not stopper.restore(net)                 # best = last epoch
    assert not _EarlyStopping(0).should_stop()
    assert _EarlyStopping(0).stats() == {}


def test_training_stops_and_keeps_the_best_weights(project, workspace,
                                                   monkeypatch):
    _, _, model, paths = project
    _labelled_project(model, workspace, paths[:5])
    _tiny_training(model)
    model.num_epochs = 10
    monkeypatch.setattr(model, "patience", 2)
    scores = iter([0.2, 0.4, 0.3, 0.35, 0.9, 0.9])
    snapshots = {}

    def evaluate():
        epoch = len(snapshots) + 1
        snapshots[epoch] = {k: v.detach().cpu().clone()
                            for k, v in model.model.state_dict().items()}
        score = next(scores)
        return {"seg_miou": score, "seg_iou": {0: score}}
    monkeypatch.setattr(model, "evaluate_model", evaluate)
    stats, logs = [], []
    model.train_model_core(stats_callback=stats.append,
                           log_callback=logs.append)

    epochs = [s for s in stats if s["kind"] == "epoch"]
    assert [s["epoch"] for s in epochs] == [1, 2, 3, 4]
    assert len(snapshots) == 4          # no evaluation after the stop
    assert epochs[-1]["best_epoch"] == 2 and epochs[-1]["waited"] == 2
    assert epochs[-1]["val_iou"] == {0: 0.35}
    stopped = next(s for s in stats if s["kind"] == "stopped")
    assert (stopped["epoch"], stopped["best_epoch"]) == (4, 2)
    assert stats[0]["patience"] == 2
    state = model.model.state_dict()
    assert all(torch.equal(state[k].cpu(), v)
               for k, v in snapshots[2].items())
    assert model.val_metrics["seg_miou"] == 0.4
    assert any("Early stop at epoch 4" in line for line in logs)


def test_patience_needs_validation_images(project, workspace, monkeypatch):
    _, _, model, paths = project
    _labelled_project(model, workspace, paths[:3])   # < 5: no val split
    _tiny_training(model)
    monkeypatch.setattr(model, "patience", 1)
    logs, stats = [], []
    model.train_model_core(log_callback=logs.append,
                           stats_callback=stats.append)
    assert any("Patience ignored" in line for line in logs)
    assert len([s for s in stats if s["kind"] == "epoch"]) == 2
    assert not stats[0].get("patience")


def test_settings_dialog_saves_the_patience(project, monkeypatch):
    _, view, model, _ = project
    from PyImageLabeling.controller.settings.MLSetting import MLSetting
    from PyImageLabeling.model.Utils import Utils
    saved = {}
    monkeypatch.setattr(Utils, "save_parameters",
                        staticmethod(lambda data: saved.update(data)))
    dialog = MLSetting(view.zoomable_graphics_view, model)
    dialog.patience_spinbox.setValue(7)
    dialog.accept()
    assert saved["ml"]["patience"] == 7


def test_dialog_shows_the_validation_of_each_epoch(project, monkeypatch):
    dialog = TrainingDialog(5)
    monkeypatch.setattr(dialog, "_confirm_cancel", lambda: False)
    try:
        dialog.on_stats({"kind": "setup", "unit": "tiles", "epochs": 20,
                         "patience": 3, "train_images": 4, "val_images": 1,
                         "classes": [{"cls": 0, "name": "A"},
                                     {"cls": 1, "name": "Background"}]})
        assert "patience 3" in dialog.settings_label.text()
        dialog.on_stats({"kind": "epoch", "epoch": 6, "total": 20,
                         "loss": 0.5, "seconds": 3, "val_score": 0.41,
                         "best_score": 0.45, "best_epoch": 4, "waited": 2,
                         "patience": 3, "val_metric": "miou",
                         "val_iou": {0: 0.41, 1: 0.97}})
        text = dialog.epoch_label.text()
        assert "mIoU of the labels 0.410" in text
        assert "best 0.450 at epoch 4" in text and "2/3" in text
        assert dialog.table.item(0, dialog.IOU_VAL).text() == "0.410"
        assert "left" in text
        dialog.on_stats({"kind": "stopped", "epoch": 7, "best_epoch": 4,
                         "total": 20, "patience": 3})
        dialog.finish({"seg_miou": 0.45}, "segmentation", 2)
        text = dialog.epoch_label.text()
        assert "Stopped at epoch 7/20" in text
        assert "weights of epoch <b>4</b> kept" in text
        # stopped early: no time is left any more
        assert "left" not in text and "3 s per epoch" in text
    finally:
        dialog.close()
