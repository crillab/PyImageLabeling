"""Rectangles, ellipses and polygons: saved for every image, and offered to
be saved when they changed.

Only the loaded images used to be written to the shape files, so a save
erased the shapes of every image not open at that moment (an image freed
from memory did not even keep them). And the project never looked modified
after drawing a shape: no "save?" on closing.
"""
import json

from PyQt6.QtCore import QPointF

from tests.conftest import make_images, reset_app


def _draw_rectangle(model, x0=5.0, y0=5.0, x1=60.0, y1=45.0):
    model.start_rectangle_tool(QPointF(x0, y0))
    model.move_rectangle_tool(QPointF(x1, y1))
    model.end_rectangle_tool()


def _rectangles_on_disk(folder):
    path = folder / "Rectangles.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _two_images(project, workspace):
    controller, view, model, paths = project
    model.save_directory = str(workspace)
    return model, paths


def test_save_keeps_the_shapes_of_images_not_loaded(project, workspace):
    model, paths = _two_images(project, workspace)
    model.select_image(paths[0])
    _draw_rectangle(model)
    model.save()
    model.select_image(paths[1])
    model._unload_image(paths[0])          # freed from memory
    _draw_rectangle(model, 10, 10, 30, 30)
    model.save()
    on_disk = _rectangles_on_disk(workspace)
    assert set(on_disk) == {"img000.png", "img001.png"}


def test_shapes_read_from_disk_survive_a_save(project, workspace):
    model, paths = _two_images(project, workspace)
    (workspace / "Rectangles.json").write_text(json.dumps({
        "img005.png": [{"x": 1.0, "y": 2.0, "width": 20.0, "height": 10.0,
                        "label_id": 0}]}), encoding="utf-8")
    model.load_rectangles_json(str(workspace / "Rectangles.json"))
    model.select_image(paths[0])           # img005 never opened
    _draw_rectangle(model)
    model.save()
    assert set(_rectangles_on_disk(workspace)) == {"img000.png",
                                                    "img005.png"}


def test_unloading_an_image_keeps_its_unsaved_shapes(project, workspace):
    model, paths = _two_images(project, workspace)
    model.select_image(paths[0])
    _draw_rectangle(model)
    model.select_image(paths[1])
    model._unload_image(paths[0])
    assert len(model.left_rectangles["img000.png"]) == 1
    assert model.get_edited()              # still to be saved
    model.select_image(paths[0])
    assert len(model.get_current_image_item().image_rectangles) == 1


def test_images_freed_after_ml_keep_their_shapes(project, workspace):
    controller, _, model, paths = project
    model.save_directory = str(workspace)
    model.select_image(paths[0])
    _draw_rectangle(model)
    model.save()
    model.select_image(paths[1])
    controller.ml_unload_image_items()     # what training/propagation do
    assert model.image_items[paths[0]] is None
    _draw_rectangle(model, 10, 10, 30, 30)
    model.save()
    assert set(_rectangles_on_disk(workspace)) == {"img000.png",
                                                    "img001.png"}


def test_a_new_shape_marks_the_project_as_edited(project, workspace):
    model, paths = _two_images(project, workspace)
    model.select_image(paths[0])
    assert not model.get_edited()
    _draw_rectangle(model)
    assert model.get_edited()
    assert model.get_current_image_item().get_edited()   # red asterisk
    model.save()
    assert not model.get_edited()


def test_moving_or_deleting_a_shape_marks_the_project_as_edited(
        project, workspace):
    model, paths = _two_images(project, workspace)
    model.select_image(paths[0])
    _draw_rectangle(model)
    model.save()
    rect = model.get_current_image_item().image_rectangles[0]
    rect["x"] += 7                          # what RectangleItem.update_model does
    assert model.get_edited()
    model.save()
    assert not model.get_edited()
    model.clear_all_rectangles(0)
    assert model.get_edited()


def test_shapes_just_read_are_not_unsaved(project, workspace):
    model, paths = _two_images(project, workspace)
    (workspace / "Rectangles.json").write_text(json.dumps({
        "img000.png": [{"x": 1.0, "y": 2.0, "width": 20.0, "height": 10.0,
                        "label_id": 0}]}), encoding="utf-8")
    (workspace / "Polygons.json").write_text(json.dumps({
        "img000.png": [{"points": [[1.0, 1.0], [30.0, 1.0], [15.0, 20.0]],
                        "label": 0}]}), encoding="utf-8")
    model.load_rectangles_json(str(workspace / "Rectangles.json"))
    model.load_polygons_json(str(workspace / "Polygons.json"))
    model.select_image(paths[0])
    assert len(model.get_current_image_item().image_polygons) == 1
    assert not model.get_edited()


def test_autosave_does_not_count_as_saved(project, workspace):
    model, paths = _two_images(project, workspace)
    model.select_image(paths[0])
    _draw_rectangle(model)
    (workspace / "snapshot").mkdir()
    model._save_all(str(workspace / "snapshot"), reset_edited=False)
    assert model.get_edited()


def test_removing_a_label_removes_its_shapes_everywhere(project, workspace):
    model, paths = _two_images(project, workspace)
    model.select_image(paths[0])
    _draw_rectangle(model)
    model.select_image(paths[1])
    _draw_rectangle(model)
    model._unload_image(paths[0])
    model.remove_shapes_of_label(0)
    assert "img000.png" not in model.left_rectangles
    assert model.get_current_image_item().image_rectangles == []
    model.save()
    assert _rectangles_on_disk(workspace) == {}
