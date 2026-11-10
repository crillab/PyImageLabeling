"""The label dialog must be safe to accept, import or not.

Regression: accept() called process_import_data() unconditionally, and that
method touched self.destination_directory — an attribute only created by the
import wizard. Closing the dialog with OK therefore printed

    Error importing labels: 'LabelSetting' object has no attribute
    'destination_directory'

for every user who simply opened the label settings and validated.
"""
import os

import pytest
from PyQt6.QtWidgets import QMessageBox

from PyImageLabeling.controller.settings.LabelSetting import LabelSetting
from tests.conftest import reset_app


def _label_dialog(app_stack, monkeypatch):
    """A LabelSetting built on the shared stack, with a safe parent()."""
    controller, view, model = app_stack
    reset_app(controller, view, model)
    d = LabelSetting(view.zoomable_graphics_view)
    return controller, view, model, d


def test_accept_without_import_is_silent(app_stack, monkeypatch, capsys):
    """The regression itself: no attribute error, no console noise."""
    controller, view, model, d = _label_dialog(app_stack, monkeypatch)

    errors = []
    monkeypatch.setattr(
        controller, "error_message",
        lambda title, msg: errors.append((title, msg)))

    d.process_import_data()

    out = capsys.readouterr().out
    assert "destination_directory" not in out
    assert "Error importing labels" not in out
    assert errors == []
    assert d.importdata is False


def test_accept_after_a_full_dry_run_does_not_raise(app_stack, monkeypatch,
                                                    tmp_path):
    """destination_directory set but nothing imported: still a no-op."""
    controller, view, model, d = _label_dialog(app_stack, monkeypatch)
    d.destination_directory = str(tmp_path)
    d.source_directory = str(tmp_path)

    d.process_import_data()          # importdata is False -> no write
    assert d.importdata is False


def test_missing_destination_is_reported(app_stack, monkeypatch, tmp_path):
    """An import that started without a destination must say so in the UI."""
    controller, view, model, d = _label_dialog(app_stack, monkeypatch)
    d.import_ready = True
    d.source_directory = str(tmp_path)
    d.destination_directory = ""
    model.save_directory = ""

    errors = []
    monkeypatch.setattr(
        controller, "error_message",
        lambda title, msg: errors.append((title, msg)))

    d.process_import_data()

    assert errors and errors[0][0] == "Import Error"
    assert d.importdata is False


def test_completed_wizard_imports_the_masks(app_stack, monkeypatch, tmp_path):
    """Regression: process_import_data() returned early on importdata, which
    is only set after a mask was written, so no import ever happened."""
    import numpy as np
    from PIL import Image
    from PyImageLabeling.controller.settings.LabelSetting import (
        ImportFormatDialog)

    controller, view, model, d = _label_dialog(app_stack, monkeypatch)
    source = tmp_path / "trimaps"
    destination = tmp_path / "save"
    source.mkdir()
    trimap = np.array([[0, 1], [2, 3]], dtype=np.uint8)
    for name in ("Abyssinian_1.png", "Bengal_1.png"):
        Image.fromarray(trimap).save(source / name)

    # state left by import_data() once the wizard went through
    d.source_directory = str(source)
    d.destination_directory = str(destination)
    d.import_format = ImportFormatDialog.FORMAT_INDEXED
    d.import_index_values = [1, 2, 3]
    d.import_filter = "Abyssinian*"
    d.import_ready = True

    d.process_import_data()

    label_id = model.get_static_label_id()
    written = destination / f"Abyssinian_1.label.{label_id}.png"
    assert d.importdata is True
    assert os.listdir(destination) == [written.name]
    assert np.array(Image.open(written)).tolist() == [[0, 255], [255, 255]]


# ----------------------------------------------------------------------
# importing a label keeps the open project as it is
# ----------------------------------------------------------------------
def test_import_adds_the_masks_to_the_open_project(app_stack, monkeypatch,
                                                   tmp_path):
    """The import used to reopen the whole project: with unsaved strokes it
    asked to save or discard them ("before opening the new folder"), and
    Cancel left the imported masks on disk but not shown."""
    import json
    import numpy as np
    from PIL import Image
    from PyQt6.QtCore import QPointF
    from PyQt6.QtGui import QColor
    import PyImageLabeling.controller.LabelEvents as label_events
    from PyImageLabeling.controller.settings.LabelSetting import (
        ImportFormatDialog)
    from tests.conftest import make_images, reset_app, write_labels_json

    controller, view, model = app_stack
    reset_app(controller, view, model)
    project = tmp_path / "project"
    project.mkdir()
    paths = make_images(project, 3, seed=5)
    write_labels_json(project)
    model.load(str(project))

    # img001 is loaded (and left), img000 holds an unsaved stroke, img002
    # has never been displayed
    model.select_image(paths[1])
    model.select_image(paths[0])
    model.start_paint_brush(QPointF(20.0, 20.0))
    model.move_paint_brush(QPointF(60.0, 50.0))
    model.end_paint_brush()
    assert model.get_edited()

    source = tmp_path / "external"
    source.mkdir()
    mask = np.zeros((128, 128), np.uint8)
    mask[90:120, 90:120] = 255
    for name in ("img001.png", "img002.png"):
        Image.fromarray(mask).save(source / name)

    class CompletedImport(label_events.LabelSetting):
        """The label dialog once the import wizard went through and OK."""
        def exec(self):
            self.name = "Imported"
            self.labeling_mode = "Pixel-by-pixel"
            self.color = QColor(255, 0, 0)
            self.source_directory = str(source)
            self.destination_directory = model.save_directory
            self.import_format = ImportFormatDialog.FORMAT_BINARY
            self.import_filter = "*"
            self.import_ready = True
            self.process_import_data()
            return True
    monkeypatch.setattr(label_events, "LabelSetting", CompletedImport)
    asked = []
    monkeypatch.setattr(
        QMessageBox, "question",
        staticmethod(lambda *a, **k: asked.append(a) or
                     QMessageBox.StandardButton.Cancel))

    controller.new_label()

    label_id = max(model.get_label_items())
    assert model.get_label_items()[label_id].name == "Imported"
    assert asked == []
    # the project stayed open, unsaved stroke included
    assert len(model.file_paths) == 3
    assert model.get_edited()
    assert model.get_current_image_item().path_image == paths[0]
    # the label is on disk next to its masks
    with open(project / "labels.json", encoding="utf-8") as f:
        assert str(label_id) in json.load(f)
    assert (project / f"img001.label.{label_id}.png").is_file()

    def imported_alpha(path):
        overlay = model.image_items[path].labeling_overlays[label_id]
        return overlay.labeling_overlay_pixmap.toImage().pixelColor(
            100, 100).alpha()

    # shown at once on the image already loaded...
    assert imported_alpha(paths[1]) > 0
    # ...and on the other one when it is displayed
    model.select_image(paths[2])
    assert imported_alpha(paths[2]) > 0
