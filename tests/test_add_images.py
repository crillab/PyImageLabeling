"""File > Add Images: images from another folder join the open project.

One project = one folder, so an image joins the project by being copied
into its folder (reopening the folder finds it again). The project stays
open: no save prompt, unsaved strokes kept.
"""
import os

import pytest
from PyQt6.QtCore import QPointF
from PyQt6.QtWidgets import QMessageBox

from tests.conftest import make_images, reset_app, write_labels_json


def _paint(model, path):
    model.select_image(path)
    model.start_paint_brush(QPointF(20.0, 20.0))
    model.move_paint_brush(QPointF(60.0, 50.0))
    model.end_paint_brush()


@pytest.fixture()
def open_project(app_stack, tmp_path, monkeypatch):
    controller, view, model = app_stack
    reset_app(controller, view, model)
    project = tmp_path / "project"
    project.mkdir()
    paths = make_images(project, 3, seed=1)
    write_labels_json(project)
    model.load(str(project))

    external = tmp_path / "external"
    external.mkdir()
    # make_images names files img000.png, img001.png, ...: rename the
    # external ones so they do not clash with the project's
    outside = []
    for i, p in enumerate(make_images(external, 2, seed=2)):
        q = os.path.join(str(external), f"other{i}.png")
        os.rename(p, q)
        outside.append(q)

    shown, asked = [], []
    monkeypatch.setattr(
        QMessageBox, "information",
        staticmethod(lambda parent, title, text, *a, **k:
                     shown.append(text)))
    monkeypatch.setattr(
        QMessageBox, "question",
        staticmethod(lambda *a, **k: asked.append(a) or
                     QMessageBox.StandardButton.Cancel))
    return model, view, str(project), paths, outside, shown, asked


def test_images_are_copied_into_the_project(open_project):
    model, view, project, paths, outside, shown, asked = open_project
    _paint(model, model.file_paths[0])

    added = model.add_images(outside)

    assert [os.path.basename(p) for p in added] == ["other0.png",
                                                    "other1.png"]
    for p in added:
        assert os.path.dirname(p) == os.path.normpath(project)
        assert os.path.isfile(p)
    assert all(os.path.isfile(p) for p in outside)   # copied, not moved
    assert len(model.file_paths) == 5
    assert view.file_bar_list.count() == 5
    assert os.path.normpath(model.save_directory) == \
        os.path.normpath(project)
    # the project stayed open: no prompt, the stroke is still unsaved
    assert asked == [] and shown == []
    assert model.get_edited()
    # the first added image is displayed
    assert model.get_current_image_item().path_image == added[0]


def test_added_images_are_back_when_the_project_is_reopened(open_project):
    model, view, project, paths, outside, shown, asked = open_project
    model.add_images(outside)
    _paint(model, model.file_paths[3])     # other0.png
    model.save()

    model.load(project)

    names = sorted(os.path.basename(p) for p in model.file_paths)
    assert names == ["img000.png", "img001.png", "img002.png",
                     "other0.png", "other1.png"]
    other0 = [p for p in model.file_paths if p.endswith("other0.png")][0]
    model.select_image(other0)
    overlay = model.get_current_image_item().labeling_overlays[0]
    assert overlay.labeling_overlay_pixmap.toImage().pixelColor(
        40, 35).alpha() > 0


def test_a_project_file_is_never_overwritten(open_project, tmp_path):
    model, view, project, paths, outside, shown, asked = open_project
    clash_dir = tmp_path / "clash"
    clash_dir.mkdir()
    clash = make_images(clash_dir, 1, seed=9)[0]        # img000.png
    before = open(paths[0], "rb").read()

    added = model.add_images([clash])

    assert added == []
    assert open(paths[0], "rb").read() == before
    assert len(model.file_paths) == 3
    assert len(shown) == 1 and "img000.png" in shown[0]


def test_an_image_already_in_the_project_is_not_added_twice(open_project):
    model, view, project, paths, outside, shown, asked = open_project

    assert model.add_images([paths[1]]) == []
    assert len(model.file_paths) == 3
    assert "already in the project" in shown[0]


def test_mask_files_are_not_added_as_images(open_project, tmp_path):
    model, view, project, paths, outside, shown, asked = open_project
    mask = tmp_path / "external" / "other0.label.0.png"
    os.rename(outside[0], mask)

    assert model.add_images([str(mask)]) == []
    assert not os.path.exists(os.path.join(project, mask.name))
    assert "Import data" in shown[0]


def test_without_a_project_nothing_is_copied(app_stack, tmp_path,
                                             monkeypatch):
    controller, view, model = app_stack
    reset_app(controller, view, model)
    image = make_images(tmp_path, 1)[0]
    shown = []
    monkeypatch.setattr(
        QMessageBox, "information",
        staticmethod(lambda parent, title, text, *a, **k:
                     shown.append(title)))

    assert model.add_images([image]) == []
    assert shown == ["No project open"]
    assert model.file_paths == []


def test_the_file_menu_offers_it(app_stack):
    controller, view, model = app_stack
    file_menu = view.menuBar().actions()[0].menu()
    assert "Add Images…" in [a.text() for a in file_menu.actions()]
