"""Cancelling a training."""
import os
import threading

import pytest
from PyQt6.QtGui import QCloseEvent

from PyImageLabeling.model.ML import Tiling
from PyImageLabeling.model.ML.MLPredictor import (
    TrainingCancelled, TrainingWorker)
from PyImageLabeling.view.TrainingDialog import TrainingDialog

from tests.test_ml_tiles import _labelled_project, _tiny_training


def test_cancel_stops_the_training_and_removes_the_tiles(project, workspace,
                                                        monkeypatch):
    _, _, model, paths = project
    _labelled_project(model, workspace, paths[:5])
    _tiny_training(model)
    caches = []
    real_cache = Tiling.TileCache

    def recording_cache(*a, **k):
        caches.append(real_cache(*a, **k))
        return caches[-1]
    monkeypatch.setattr(Tiling, "TileCache", recording_cache)

    event = threading.Event()
    epochs = []

    def on_epoch(current, total, loss):
        epochs.append(current)
        event.set()                       # cancelled during epoch 1

    with pytest.raises(TrainingCancelled):
        model.train_model_core(epoch_callback=on_epoch, cancel_event=event)
    assert epochs == [1]                  # stopped at the next batch
    assert not model.is_trained()
    assert caches and not os.path.exists(caches[0].directory)
    # what runs outside a training is not cancelled any more
    assert model._cancel_event is None
    assert model.collect_segmentation_data(paths[:5])


def test_cancel_during_the_validation_is_not_swallowed(project, workspace):
    """The validation is wrapped in `except Exception`: the cancel must
    still go through."""
    _, _, model, paths = project
    _labelled_project(model, workspace, paths[:5])
    _tiny_training(model)
    event = threading.Event()

    def on_status(message):
        if message.startswith("Evaluating"):
            event.set()

    with pytest.raises(TrainingCancelled):
        model.train_model_core(status_callback=on_status, cancel_event=event)


def test_worker_reports_the_cancel_and_nothing_is_kept(project, workspace):
    _, _, model, paths = project
    _labelled_project(model, workspace, paths[:5])
    _tiny_training(model)
    worker = TrainingWorker(model, list(paths[:5]))
    got = []
    worker.finished.connect(lambda: got.append("finished"))
    worker.error.connect(lambda message: got.append(message))
    worker.cancelled.connect(lambda: got.append("cancelled"))
    worker.status.connect(
        lambda m: worker.cancel() if m.startswith("Evaluating") else None)
    worker.run()                          # in this thread
    assert got == ["cancelled"]

    model._progress_dialog = TrainingDialog(5)
    model._on_training_cancelled()
    assert not model.is_trained()
    assert model.model is None and model.tiling is None
    assert not model._progress_dialog.running


def test_dialog_cancel_asks_then_waits_for_the_training(project, monkeypatch):
    dialog = TrainingDialog(3)
    asked, requested = [], []
    monkeypatch.setattr(dialog, "_confirm_cancel",
                        lambda: asked.append(1) or True)
    dialog.cancel_requested.connect(lambda: requested.append(1))
    try:
        dialog.reject()                   # Cancel button, Escape
        assert asked == [1] and requested == [1]
        assert dialog.running and dialog.cancelling
        assert not dialog.cancel_button.isEnabled()
        assert "Cancelling" in dialog.status_label.text()

        dialog.reject()                   # asked once only
        assert asked == [1] and requested == [1]
        dialog.on_epoch(2, 5, 0.3)        # queued figures do not hide it
        assert "Cancelling" in dialog.status_label.text()

        dialog.cancelled()
        assert not dialog.running
    finally:
        dialog.running = False
        dialog.close()


def test_closing_the_dialog_while_training_asks_to_cancel(project,
                                                         monkeypatch):
    dialog = TrainingDialog(3)
    asked = []
    monkeypatch.setattr(dialog, "_confirm_cancel",
                        lambda: asked.append(1) or False)
    try:
        event = QCloseEvent()
        dialog.closeEvent(event)
        assert not event.isAccepted()
        assert asked == [1] and dialog.running and not dialog.cancelling
    finally:
        dialog.running = False
        dialog.close()


def test_no_cancel_once_the_training_has_ended(project, monkeypatch):
    """The training may end while the question is up."""
    dialog = TrainingDialog(3)
    requested = []
    dialog.cancel_requested.connect(lambda: requested.append(1))

    def answer():
        dialog.finish({}, "segmentation", 2)
        return True
    monkeypatch.setattr(dialog, "_confirm_cancel", answer)
    try:
        dialog.request_cancel()
        assert requested == [] and not dialog.cancelling
        assert dialog.status_label.text() == "Training complete"
    finally:
        dialog.close()

