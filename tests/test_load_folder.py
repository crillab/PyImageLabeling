"""Opening a folder: one project = one folder, and never a silent no-op.

Closing the window closes the project too: same save prompt.
"""
import os

import pytest

from PyQt6.QtWidgets import QMessageBox

from PyImageLabeling.model.File.Files import nothing_to_load_message
from tests.conftest import make_images, reset_app


def test_message_points_at_subfolders_with_images(tmp_path):
    (tmp_path / "patient_b").mkdir()
    make_images(tmp_path / "patient_b", 1)
    (tmp_path / "patient_a").mkdir()
    make_images(tmp_path / "patient_a", 2)
    (tmp_path / "empty").mkdir()
    (tmp_path / "notes.txt").write_text("x")

    msg = nothing_to_load_message(str(tmp_path))

    assert "No image found" in msg
    assert "patient_a" in msg and "patient_b" in msg
    assert "empty" not in msg
    assert msg.index("patient_a") < msg.index("patient_b")


def test_message_caps_the_subfolder_list(tmp_path):
    for i in range(13):
        sub = tmp_path / f"p{i:02d}"
        sub.mkdir()
        make_images(sub, 1)

    msg = nothing_to_load_message(str(tmp_path))

    assert "p09" in msg and "p10" not in msg
    assert "3 more" in msg


def test_message_ignores_mask_files(tmp_path):
    sub = tmp_path / "only_masks"
    sub.mkdir()
    (sub / "img.label.0.png").write_bytes(b"")

    msg = nothing_to_load_message(str(tmp_path))

    assert "only_masks" not in msg
    assert "Supported formats" in msg


def test_load_of_parent_folder_informs_and_keeps_project(
        app_stack, tmp_path, monkeypatch):
    controller, view, model = app_stack
    reset_app(controller, view, model)
    (tmp_path / "patient").mkdir()
    make_images(tmp_path / "patient", 2)

    shown = []
    monkeypatch.setattr(
        QMessageBox, "information",
        staticmethod(lambda parent, title, text, *a, **k: shown.append(text)))

    model.load(str(tmp_path))

    assert len(shown) == 1
    assert "patient" in shown[0]
    assert model.file_paths == []
    assert model.save_directory == ""


# ----------------------------------------------------------------------
# opening a second folder replaces the project
# ----------------------------------------------------------------------
from PyQt6.QtCore import QPointF

from tests.conftest import write_labels_json


def _folder(root, name, n, seed):
    folder = root / name
    folder.mkdir()
    paths = make_images(folder, n, seed=seed)
    write_labels_json(folder)
    return str(folder), paths


def _paint(model, path):
    model.select_image(path)
    model.start_paint_brush(QPointF(20.0, 20.0))
    model.move_paint_brush(QPointF(60.0, 50.0))
    model.end_paint_brush()


def _masks(folder):
    return [n for n in os.listdir(folder) if ".label." in n]


@pytest.fixture()
def two_folders(app_stack, tmp_path):
    controller, view, model = app_stack
    reset_app(controller, view, model)
    a, a_paths = _folder(tmp_path, "a", 3, seed=1)
    b, b_paths = _folder(tmp_path, "b", 2, seed=2)
    model.load(a)
    return controller, view, model, a, a_paths, b, b_paths


def _answer(monkeypatch, button):
    asked = []

    def question(*a, **k):
        asked.append(a)
        return button
    monkeypatch.setattr(QMessageBox, "question", staticmethod(question))
    return asked


def test_second_folder_replaces_the_first(two_folders):
    controller, view, model, a, a_paths, b, b_paths = two_folders
    assert len(model.file_paths) == 3

    model.load(b)

    assert sorted(os.path.normpath(p) for p in model.file_paths) == \
        sorted(os.path.normpath(p) for p in b_paths)
    assert view.file_bar_list.count() == 2
    assert set(model.icon_button_files) == set(model.file_paths)
    assert os.path.normpath(model.save_directory) == os.path.normpath(b)
    assert list(model.get_label_items()) == [0]
    assert list(view.container_label_bar_temporary) == [0]
    # the first image of the new folder is displayed
    assert model.get_current_image_item() is not None
    assert os.path.normpath(model.get_current_image_item().path_image) == \
        os.path.normpath(model.file_paths[0])


def test_unsaved_work_cancel_keeps_the_project(two_folders, monkeypatch):
    controller, view, model, a, a_paths, b, b_paths = two_folders
    _paint(model, model.file_paths[0])
    asked = _answer(monkeypatch, QMessageBox.StandardButton.Cancel)

    model.load(b)

    assert len(asked) == 1
    assert len(model.file_paths) == 3
    assert os.path.normpath(model.save_directory) == os.path.normpath(a)
    assert model.get_edited()
    assert _masks(a) == [] and _masks(b) == []


def test_unsaved_work_discard_opens_without_saving(two_folders, monkeypatch):
    controller, view, model, a, a_paths, b, b_paths = two_folders
    _paint(model, model.file_paths[0])
    _answer(monkeypatch, QMessageBox.StandardButton.Discard)

    model.load(b)

    assert view.file_bar_list.count() == 2
    assert not model.get_edited()
    assert _masks(a) == [] and _masks(b) == []


def test_unsaved_work_save_writes_into_the_first_folder(
        two_folders, monkeypatch):
    controller, view, model, a, a_paths, b, b_paths = two_folders
    _paint(model, model.file_paths[0])
    _answer(monkeypatch, QMessageBox.StandardButton.Save)

    model.load(b)

    assert len(_masks(a)) == 1
    assert _masks(b) == []
    assert view.file_bar_list.count() == 2

    # back to the first folder: the saved strokes are there
    model.load(a)
    assert model.get_current_image_item().get_edited() is False
    overlay = model.get_current_image_item().labeling_overlays[0]
    assert not overlay.labeling_overlay_pixmap.toImage().isNull()
    assert overlay.labeling_overlay_pixmap.toImage().pixelColor(
        40, 35).alpha() > 0


def test_folder_without_images_leaves_the_project_open(
        two_folders, tmp_path, monkeypatch):
    controller, view, model, a, a_paths, b, b_paths = two_folders
    parent = tmp_path / "parent"
    (parent / "sub").mkdir(parents=True)
    make_images(parent / "sub", 1)
    shown = []
    monkeypatch.setattr(
        QMessageBox, "information",
        staticmethod(lambda parent, title, text, *a, **k: shown.append(text)))

    model.load(str(parent))

    assert len(shown) == 1 and "sub" in shown[0]
    assert len(model.file_paths) == 3
    assert os.path.normpath(model.save_directory) == os.path.normpath(a)


# ----------------------------------------------------------------------
# closing the window offers to save, like opening another folder
# ----------------------------------------------------------------------
from PyQt6.QtGui import QCloseEvent


def _close(view):
    """Run the window's close handler (the shared window stays shown)."""
    event = QCloseEvent()
    view.closeEvent(event)
    return event.isAccepted()


def test_close_without_unsaved_work_asks_nothing(two_folders, monkeypatch):
    controller, view, model, a, a_paths, b, b_paths = two_folders
    asked = _answer(monkeypatch, QMessageBox.StandardButton.Cancel)

    assert _close(view) is True
    assert asked == []


def test_close_cancel_keeps_the_window_open(two_folders, monkeypatch):
    controller, view, model, a, a_paths, b, b_paths = two_folders
    _paint(model, model.file_paths[0])
    asked = _answer(monkeypatch, QMessageBox.StandardButton.Cancel)

    assert _close(view) is False
    assert len(asked) == 1
    assert "before quitting" in asked[0][2]
    assert model.get_edited()
    assert _masks(a) == []


def test_close_discard_closes_without_saving(two_folders, monkeypatch):
    controller, view, model, a, a_paths, b, b_paths = two_folders
    _paint(model, model.file_paths[0])
    _answer(monkeypatch, QMessageBox.StandardButton.Discard)

    assert _close(view) is True
    assert _masks(a) == []


def test_close_save_writes_the_masks(two_folders, monkeypatch):
    controller, view, model, a, a_paths, b, b_paths = two_folders
    _paint(model, model.file_paths[0])
    _answer(monkeypatch, QMessageBox.StandardButton.Save)

    assert _close(view) is True
    assert len(_masks(a)) == 1
    assert not model.get_edited()


def test_close_stays_open_when_the_save_does_not_go_through(
        two_folders, monkeypatch):
    controller, view, model, a, a_paths, b, b_paths = two_folders
    _paint(model, model.file_paths[0])
    _answer(monkeypatch, QMessageBox.StandardButton.Save)
    # what a cancelled save dialog or a failed mask write leaves behind
    monkeypatch.setattr(model, "save", lambda: None)

    assert _close(view) is False
    assert model.get_edited()
