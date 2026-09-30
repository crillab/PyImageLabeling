"""Unload releases background ImageItems without losing track of them."""

from PyQt6.QtCore import QPointF



def _paint(model, path):
    model.select_image(path)
    model.start_paint_brush(QPointF(20.0, 20.0))
    model.move_paint_brush(QPointF(60.0, 50.0))
    model.end_paint_brush()


def test_unload_keeps_current_and_reloads(project):
    controller, _, model, paths = project
    for p in paths:
        model.load_image_for_training(p)
    model.select_image(paths[0])
    assert sum(1 for v in model.image_items.values()
               if v is not None) == len(paths)

    dropped = controller.ml_unload_image_items()
    assert dropped == len(paths) - 1
    assert sum(1 for v in model.image_items.values()
               if v is not None) == 1

    # re-selecting a released image reloads it and still paints
    _paint(model, paths[5])
    assert sum(1 for v in model.image_items.values()
               if v is not None) == 2
    assert model.get_current_image_item() is not None


def test_unload_after_painting_keeps_annotations(project):
    controller, _, model, paths = project
    for p in paths[:4]:
        model.load_image_for_training(p)
        _paint(model, p)
    model.select_image(paths[0])

    controller.ml_unload_image_items()
    # the painted ones are remembered, not re-listed as unlabeled
    unlabeled = model.ml_get_unlabeled_images()
    assert not [p for p in unlabeled if p in paths[:4]]
    assert len(unlabeled) == len(paths) - 4


def test_switching_label_after_unload(project):
    controller, _, model, paths = project
    for p in paths:
        model.load_image_for_training(p)
    model.select_image(paths[0])
    controller.ml_unload_image_items()

    from PyQt6.QtGui import QColor
    label2 = model.new_label("L2", "Pixel-by-pixel", QColor(255, 0, 0))
    model.set_current_label_item(label2)
    model.update_labeling_overlays(label2.get_label_id())
    assert label2.get_label_id() in \
        model.get_current_image_item().labeling_overlays
