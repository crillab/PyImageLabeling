"""ML stays quiet by default; errors still print; verbose is reversible."""
import contextlib
import io
import os

import numpy as np
from PIL import Image as PILImage
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QColor

from tests.conftest import make_images
from PyImageLabeling.model.ML.MLPredictor import (
    ml_log, set_ml_verbose, ML_VERBOSE)
import PyImageLabeling.model.ML.MLPredictor as MLP


def _paint_some(model, paths):
    for p in paths[:3]:
        model.select_image(p)
        model.start_paint_brush(QPointF(10.0, 10.0))
        model.move_paint_brush(QPointF(40.0, 40.0))
        model.end_paint_brush()


def test_quiet_by_default():
    assert MLP.ML_VERBOSE is False


def test_training_prints_no_per_image_noise(project):
    _, _, model, paths = project
    _paint_some(model, paths)
    model.num_epochs = 1
    model.batch_size = 2
    model.image_size = 64
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        model.train_model_core()
    out = buf.getvalue()
    noisy = [ln for ln in out.splitlines()
             if "load_image_for_training" in ln
             or "painted pixels" in ln
             or "COLLECTING" in ln
             or "FINAL SEGMENTATION" in ln]
    assert noisy == []
    assert model.trained is True


def test_verbose_brings_it_back(project):
    _, _, model, paths = project
    for p in paths[:3]:
        model.image_items[p] = None
    set_ml_verbose(True)
    try:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            for p in paths[:3]:
                model.load_image_for_training(p)
        assert "load_image_for_training" in buf.getvalue()
    finally:
        set_ml_verbose(False)


def test_errors_always_print():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        ml_log("a failure that matters", force=True)
        ml_log("just chatter")
    out = buf.getvalue()
    assert "a failure that matters" in out
    assert "just chatter" not in out


def test_flag_roundtrip_in_parameters():
    from PyImageLabeling.model.Utils import Utils
    import shutil
    base = Utils.get_base_dir()
    pp = os.path.join(base, "parameters.json")
    backup = pp + ".testbak"
    shutil.copyfile(pp, backup)
    try:
        d = Utils.load_parameters()
        d["ml"]["verbose"] = True
        Utils.save_parameters(d)
        from PyImageLabeling.model.ML.MLPredictor import MLPredictor
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            MLPredictor()
        assert MLP.ML_VERBOSE is True
    finally:
        d = Utils.load_parameters()
        d["ml"]["verbose"] = False
        Utils.save_parameters(d)
        with contextlib.redirect_stdout(io.StringIO()):
            from PyImageLabeling.model.ML.MLPredictor import MLPredictor
            MLPredictor()
        assert MLP.ML_VERBOSE is False
        shutil.copyfile(backup, pp)
        os.remove(backup)
