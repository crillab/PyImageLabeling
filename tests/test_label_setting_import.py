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
    d.importdata = True
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