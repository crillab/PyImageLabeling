"""File menu: grouped entries, shortcuts, and File > Import Labels."""
import collections
import os

import numpy as np
import pytest
from PIL import Image
from PyQt6.QtGui import QColor, QKeySequence
from PyQt6.QtWidgets import QMessageBox

import PyImageLabeling.controller.LabelEvents as label_events
from PyImageLabeling.controller.settings.LabelSetting import (
    ImportFormatDialog)
from tests.conftest import make_images, reset_app, write_labels_json


def _file_menu(view):
    return view.menuBar().actions()[0].menu()


def _action(view, text):
    for action in _file_menu(view).actions():
        if action.text() == text:
            return action
    raise AssertionError(f"File > {text} not found")


def test_entries_are_grouped(app_stack):
    controller, view, model = app_stack
    groups = [[]]
    for action in _file_menu(view).actions():
        if action.isSeparator():
            groups.append([])
        else:
            groups[-1].append(action.text())

    assert groups == [
        ["Open Project…", "Add Images…", "Import Labels…"],
        ["Save", "Save Copy…"],
        ["Next Image", "Previous Image"],
        ["Recover Unsaved Annotations…"],
    ]


def test_add_images_and_import_labels_have_a_shortcut(app_stack):
    controller, view, model = app_stack
    assert _action(view, "Add Images…").shortcut() == \
        QKeySequence("Ctrl+Shift+A")
    assert _action(view, "Import Labels…").shortcut() == \
        QKeySequence("Ctrl+Shift+L")


def test_no_shortcut_is_bound_twice(app_stack):
    controller, view, model = app_stack
    bound = collections.defaultdict(list)
    for menu_action in view.menuBar().actions():
        for action in menu_action.menu().actions():
            if not action.shortcut().isEmpty():
                bound[action.shortcut().toString()].append(action.text())
    assert {k: v for k, v in bound.items() if len(v) > 1} == {}


def test_bar_tooltips_show_their_shortcut(app_stack):
    controller, view, model = app_stack
    tooltip = view.buttons_file_bar["load"].toolTip()
    assert tooltip.startswith("Open a project folder")
    assert tooltip.endswith(f"({QKeySequence('Ctrl+O').toString()})")
    # no shortcut, no suffix
    assert not view.buttons_file_bar["save_copy"].toolTip().endswith(")")


# ----------------------------------------------------------------------
# File > Import Labels: the import wizard first, then the label dialog
# ----------------------------------------------------------------------
@pytest.fixture()
def open_project(app_stack, tmp_path, monkeypatch):
    controller, view, model = app_stack
    reset_app(controller, view, model)
    project = tmp_path / "project"
    project.mkdir()
    paths = make_images(project, 2, seed=3)
    write_labels_json(project)
    model.load(str(project))

    source = tmp_path / "external"
    source.mkdir()
    mask = np.zeros((128, 128), np.uint8)
    mask[90:120, 90:120] = 255
    Image.fromarray(mask).save(source / "img001.png")
    return controller, view, model, paths, str(source)


def _dialog(source, wizard_completed, events):
    class Dialog(label_events.LabelSetting):
        def import_data(self):
            events.append("wizard")
            if wizard_completed:       # the state import_data() leaves
                self.source_directory = source
                self.destination_directory = \
                    self.parent().view.controller.model.save_directory
                self.import_format = ImportFormatDialog.FORMAT_BINARY
                self.import_filter = "*"
                self.import_ready = True

        def exec(self):
            events.append("dialog")
            self.name = "Imported"
            self.labeling_mode = "Pixel-by-pixel"
            self.color = QColor(255, 0, 0)
            self.process_import_data()
            return True
    return Dialog


def test_import_labels_runs_the_wizard_then_creates_the_label(
        open_project, monkeypatch):
    controller, view, model, paths, source = open_project
    events = []
    monkeypatch.setattr(label_events, "LabelSetting",
                        _dialog(source, True, events))

    _action(view, "Import Labels…").trigger()

    assert events == ["wizard", "dialog"]
    label_id = max(model.get_label_items())
    assert model.get_label_items()[label_id].name == "Imported"
    model.select_image(paths[1])
    overlay = model.get_current_image_item().labeling_overlays[label_id]
    assert overlay.labeling_overlay_pixmap.toImage().pixelColor(
        100, 100).alpha() > 0


def test_cancelling_the_wizard_creates_nothing(open_project, monkeypatch):
    controller, view, model, paths, source = open_project
    events = []
    monkeypatch.setattr(label_events, "LabelSetting",
                        _dialog(source, False, events))
    labels_before = list(model.get_label_items())

    controller.import_labels()

    assert events == ["wizard"]
    assert list(model.get_label_items()) == labels_before


def test_import_labels_needs_an_open_project(app_stack, monkeypatch):
    controller, view, model = app_stack
    reset_app(controller, view, model)
    events, shown = [], []
    monkeypatch.setattr(label_events, "LabelSetting",
                        _dialog("", True, events))
    monkeypatch.setattr(
        QMessageBox, "information",
        staticmethod(lambda parent, title, *a, **k: shown.append(title)))

    controller.import_labels()

    assert shown == ["No project open"]
    assert events == []
