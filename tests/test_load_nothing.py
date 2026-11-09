"""Opening a folder with nothing to load must say so, not return silently."""
import os

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

    msg = nothing_to_load_message(str(tmp_path), [])

    assert "No image found" in msg
    assert "patient_a" in msg and "patient_b" in msg
    assert "empty" not in msg
    assert msg.index("patient_a") < msg.index("patient_b")


def test_message_caps_the_subfolder_list(tmp_path):
    for i in range(13):
        sub = tmp_path / f"p{i:02d}"
        sub.mkdir()
        make_images(sub, 1)

    msg = nothing_to_load_message(str(tmp_path), [])

    assert "p09" in msg and "p10" not in msg
    assert "3 more" in msg


def test_message_ignores_mask_files(tmp_path):
    sub = tmp_path / "only_masks"
    sub.mkdir()
    (sub / "img.label.0.png").write_bytes(b"")

    msg = nothing_to_load_message(str(tmp_path), [])

    assert "only_masks" not in msg
    assert "Supported formats" in msg


def test_message_when_everything_is_already_open(tmp_path):
    paths = make_images(tmp_path, 3)

    msg = nothing_to_load_message(str(tmp_path), paths)

    assert "already open" in msg and "3 image" in msg


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
