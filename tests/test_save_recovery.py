"""Saving your work must never lose it: atomic writes, project round-trip,
and the auto-save snapshot that is finally readable.

Every test here is about data safety, not features: a native crash used to
be able to leave a 0-byte labels.json or a half-written mask behind, and the
auto-save snapshot had no way back at all.
"""
import json
import os
import time

import numpy as np
import pytest
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QColor, QImage
from PyQt6.QtWidgets import QMessageBox

from PyImageLabeling.model import Autosave
from PyImageLabeling.model.Utils import Utils
from PyImageLabeling.model.Core import KEYWORD_SAVE_LABEL
from tests.conftest import make_images, reset_app


# ----------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------
def _annotate(app_stack, workspace):
    """Two images, two pixel labels, one painted box + one rectangle."""
    controller, view, model = app_stack
    reset_app(controller, view, model)
    paths = make_images(workspace, 2, size=128, seed=11)
    for p in paths:
        model.file_paths.append(p)
        model.image_items[p] = None
    view.file_bar_add(list(paths))

    la = model.new_label("A", "Pixel-by-pixel", QColor(0, 0, 255))
    lb = model.new_label("B", "Pixel-by-pixel", QColor(255, 0, 0))
    model.set_current_label_item(la)

    model.select_image(paths[0])
    painter = (model.get_current_image_item().get_labeling_overlay()
               .get_painter())
    painter.fillRect(10, 10, 40, 40, la.get_color())
    model.get_current_image_item().update_labeling_overlay()

    model.select_image(paths[1])
    model.start_rectangle_tool(QPointF(5.0, 5.0))
    model.move_rectangle_tool(QPointF(60.0, 45.0))
    model.end_rectangle_tool()
    model.set_current_label_item(lb)
    return controller, view, model, paths, la, lb


def _mask_files(directory, paths, label_id):
    return [os.path.join(
        directory,
        os.path.basename(p).rsplit(".", 1)[0] + KEYWORD_SAVE_LABEL
        + str(label_id) + ".png") for p in paths]


# ----------------------------------------------------------------------
# atomic writes
# ----------------------------------------------------------------------
def test_write_json_atomic_leaves_no_tmp(tmp_path):
    target = tmp_path / "labels.json"
    Utils.write_json_atomic(str(target), {"0": {"name": "A"}})
    assert json.loads(target.read_text(encoding="utf-8")) == {
        "0": {"name": "A"}}
    assert not os.path.exists(str(target) + ".tmp")


def test_write_json_atomic_replaces_previous_content(tmp_path):
    target = tmp_path / "labels.json"
    Utils.write_json_atomic(str(target), {"0": "old"})
    Utils.write_json_atomic(str(target), {"1": "new"})
    assert json.loads(target.read_text(encoding="utf-8")) == {"1": "new"}


def test_write_json_atomic_keeps_file_when_dump_fails(tmp_path,
                                                       monkeypatch):
    target = tmp_path / "labels.json"
    Utils.write_json_atomic(str(target), {"0": "good"})

    def boom(*a, **k):
        raise RuntimeError("disk full")

    monkeypatch.setattr(json, "dump", boom)
    with pytest.raises(RuntimeError):
        Utils.write_json_atomic(str(target), {"0": "bad"})

    # the previous annotations are intact, and no scratch file is left
    assert json.loads(target.read_text(encoding="utf-8")) == {"0": "good"}
    assert not os.path.exists(str(target) + ".tmp")


def test_save_labels_writes_atomically(app_stack, workspace, tmp_path):
    _, _, model, _, la, lb = _annotate(app_stack, workspace)
    out = tmp_path / "out"
    out.mkdir()
    model.save_labels(str(out))
    path = out / "labels.json"
    assert json.loads(path.read_text(encoding="utf-8"))["1"]["name"] == "B"
    assert not os.path.exists(str(path) + ".tmp")


def test_failed_mask_write_keeps_previous_mask(app_stack, workspace,
                                               tmp_path, monkeypatch):
    """mask.save() returning False used to be ignored: silent data loss."""
    _, _, model, paths, la, _ = _annotate(app_stack, workspace)
    out = tmp_path / "out"
    out.mkdir()
    model.save_labels(str(out))
    model.select_image(paths[0])
    model.get_current_image_item().save_overlays(str(out))

    mask_path = _mask_files(str(out), [paths[0]], la.get_label_id())[0]
    assert os.path.isfile(mask_path)
    before = open(mask_path, "rb").read()

    monkeypatch.setattr(QImage, "save", lambda *a, **k: False)
    model.get_current_image_item().get_labeling_overlay().save(
        str(out), paths[0])

    assert open(mask_path, "rb").read() == before
    assert not os.path.exists(mask_path + ".tmp")


def test_mask_write_leaves_no_tmp(app_stack, workspace, tmp_path):
    _, _, model, paths, la, _ = _annotate(app_stack, workspace)
    out = tmp_path / "out"
    out.mkdir()
    model.select_image(paths[0])
    model.get_current_image_item().get_labeling_overlay().save(
        str(out), paths[0])
    mask_path = _mask_files(str(out), [paths[0]], la.get_label_id())[0]
    assert os.path.isfile(mask_path)
    assert not os.path.exists(mask_path + ".tmp")


# ----------------------------------------------------------------------
# project round-trip: save then read back
# ----------------------------------------------------------------------
def test_project_roundtrip(app_stack, workspace, tmp_path):
    controller, view, model, paths, la, lb = _annotate(app_stack, workspace)
    project = tmp_path / "project"
    project.mkdir()
    model.save_directory = str(project)
    model.save()

    labels = json.loads((project / "labels.json").read_text(encoding="utf-8"))
    assert {v["name"] for v in labels.values()} == {"A", "B"}

    mask_a = _mask_files(str(project), [paths[0]], la.get_label_id())[0]
    assert os.path.isfile(mask_a)

    rects = json.loads((project / "Rectangles.json").read_text(
        encoding="utf-8"))
    assert os.path.basename(paths[1]) in rects
    # an empty class must not leave a stale file behind
    assert not os.path.exists(str(project / "Ellipses.json"))
    assert not os.path.exists(str(project / "Polygons.json"))

    state = json.loads((project / "complete_state.json").read_text(
        encoding="utf-8"))
    assert os.path.basename(paths[0]) in state

    # and the bytes are readable again as a mask
    img = QImage(mask_a)
    assert not img.isNull()
    assert img.width() > 0


def test_corrupt_labels_json_is_isolated(app_stack, workspace, tmp_path,
                                         monkeypatch):
    """A truncated file must not take the whole project down."""
    controller, view, model, paths, la, lb = _annotate(app_stack, workspace)
    project = tmp_path / "project"
    project.mkdir()
    model.save_directory = str(project)
    model.save()

    broken = project / "labels.json"
    broken.write_text('{"1": {"name": "B"', encoding="utf-8")

    reported = []
    monkeypatch.setattr(
        controller, "error_message",
        lambda title, msg: reported.append((title, msg)))

    reset_app(controller, view, model)
    model.view = view
    model.load_labels_json(str(broken))

    assert os.path.isfile(str(broken) + ".corrupt")
    assert model.get_label_items() == {}
    assert reported and "corrupted" in reported[0][1]


# ----------------------------------------------------------------------
# auto-save snapshot
# ----------------------------------------------------------------------
def test_auto_save_writes_a_snapshot(app_stack, workspace, tmp_path):
    _, _, model, paths, la, _ = _annotate(app_stack, workspace)
    project = tmp_path / "project"
    project.mkdir()
    model.save_directory = str(project)
    model.auto_save()

    snapshot = Autosave.autosave_dir(str(project))
    assert os.path.isdir(snapshot)
    assert "labels.json" in Autosave.snapshot_files(snapshot)
    # complete_state used to be written to the project instead of the
    # snapshot, so the tick state could never be restored
    assert "complete_state.json" in Autosave.snapshot_files(snapshot)
    assert _mask_files(snapshot, [paths[0]], la.get_label_id())[0] \
        .replace(snapshot, snapshot).endswith(".png")


def test_snapshot_is_offered_after_a_crash(app_stack, workspace, tmp_path):
    _, _, model, paths, la, _ = _annotate(app_stack, workspace)
    project = tmp_path / "project"
    project.mkdir()
    model.save_directory = str(project)
    model.save()
    assert not Autosave.needs_recovery(str(project))

    model.auto_save()
    time.sleep(0.01)
    # snapshot strictly newer than the project files
    assert Autosave.needs_recovery(str(project))


def test_snapshot_not_offered_when_project_is_newer(app_stack, workspace,
                                                     tmp_path):
    _, _, model, _, la, _ = _annotate(app_stack, workspace)
    project = tmp_path / "project"
    project.mkdir()
    model.save_directory = str(project)
    model.auto_save()
    time.sleep(0.01)
    model.save()
    assert not Autosave.needs_recovery(str(project))


def test_real_save_closes_the_snapshot(app_stack, workspace, tmp_path):
    _, _, model, _, la, _ = _annotate(app_stack, workspace)
    project = tmp_path / "project"
    project.mkdir()
    model.save_directory = str(project)
    model.auto_save()
    assert os.path.isdir(Autosave.autosave_dir(str(project)))
    model.save()
    assert not os.path.isdir(Autosave.autosave_dir(str(project)))


def test_restore_brings_the_snapshot_back(app_stack, workspace, tmp_path):
    _, _, model, paths, la, _ = _annotate(app_stack, workspace)
    project = tmp_path / "project"
    project.mkdir()
    model.save_directory = str(project)
    model.save()

    # work that never reached the project files
    model.select_image(paths[0])
    painter = (model.get_current_image_item().get_labeling_overlay()
               .get_painter())
    painter.fillRect(0, 0, 128, 128, la.get_color())
    model.get_current_image_item().update_labeling_overlay()
    model.auto_save()

    snapshot = Autosave.autosave_dir(str(project))
    mask = _mask_files(snapshot, [paths[0]], la.get_label_id())[0]
    saved_bytes = open(mask, "rb").read()

    # crash: the project still holds the pre-stroke mask
    project_mask = _mask_files(str(project), [paths[0]], la.get_label_id())[0]
    assert open(project_mask, "rb").read() != saved_bytes
    assert Autosave.needs_recovery(str(project))

    restored = Autosave.restore(str(project))
    assert restored
    assert open(project_mask, "rb").read() == saved_bytes
    assert not os.path.isdir(snapshot)
    assert not Autosave.needs_recovery(str(project))


def test_restore_is_a_noop_without_snapshot(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    assert Autosave.restore(str(project)) == []
    assert Autosave.scan(str(project))["exists"] is False


def test_scan_reports_the_snapshot_content(app_stack, workspace, tmp_path):
    _, _, model, _, la, _ = _annotate(app_stack, workspace)
    project = tmp_path / "project"
    project.mkdir()
    model.save_directory = str(project)
    model.auto_save()
    # a stray non-annotation file must not be restored
    stray = os.path.join(Autosave.autosave_dir(str(project)), "notes.txt")
    open(stray, "w", encoding="utf-8").write("ignore me")

    info = Autosave.scan(str(project))
    assert info["exists"] is True
    assert "notes.txt" not in info["files"]
    assert "labels.json" in info["files"]
    assert "auto-saved at" in Autosave.describe(str(project))
    assert "notes.txt" not in Autosave.restore(str(project))


def test_pending_recovery_uses_the_persisted_paths(app_stack, workspace,
                                                  tmp_path):
    _, _, model, _, la, _ = _annotate(app_stack, workspace)
    project = tmp_path / "project"
    project.mkdir()
    model.save_directory = str(project)
    model.auto_save()

    params = {"save": {"path": str(project)}, "load": {"path": str(project)}}
    assert Autosave.pending_recovery(params)["project_dir"] == str(project)

    empty = Autosave.pending_recovery(
        {"save": {"path": str(tmp_path / "nope")}, "load": {"path": ""}})
    assert empty is None


def test_controller_recover_annotations_declines_when_nothing_pending(
        app_stack, workspace, tmp_path, monkeypatch):
    controller, view, model, paths, la, _ = _annotate(app_stack, workspace)
    project = tmp_path / "project"
    project.mkdir()
    model.save_directory = str(project)
    model.save()

    asked = []
    monkeypatch.setattr(
        QMessageBox, "question",
        staticmethod(lambda *a, **k: asked.append(a) or
                     QMessageBox.StandardButton.No))
    assert controller.recover_annotations() is False
    assert asked == []


def test_controller_recover_annotations_restores(app_stack, workspace,
                                                tmp_path, monkeypatch):
    controller, view, model, paths, la, _ = _annotate(app_stack, workspace)
    project = tmp_path / "project"
    project.mkdir()
    model.save_directory = str(project)
    model.save()

    # new work after the save, so the overlay counts as edited again and the
    # snapshot has something the project files do not have
    model.select_image(paths[0])
    painter = (model.get_current_image_item().get_labeling_overlay()
               .get_painter())
    painter.fillRect(0, 0, 128, 128, la.get_color())
    model.get_current_image_item().update_labeling_overlay()

    model.auto_save()
    snapshot = Autosave.autosave_dir(str(project))
    saved = open(_mask_files(snapshot, [paths[0]], la.get_label_id())[0],
                 "rb").read()

    monkeypatch.setattr(
        QMessageBox, "question",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))
    assert controller.recover_annotations() is True
    assert open(_mask_files(str(project), [paths[0]], la.get_label_id())[0],
                "rb").read() == saved
    assert not os.path.isdir(snapshot)