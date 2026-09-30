"""Review batch walks the propagated images; Suggest next ranks by doubt.

Suggest next needs a genuinely trained model so al_uncertainty really runs
the network: a 1-epoch training on the fixture set provides it.
"""
import os

from PyQt6.QtCore import QPointF


def _paint(model, path):
    model.select_image(path)
    model.start_paint_brush(QPointF(20.0, 20.0))
    model.move_paint_brush(QPointF(60.0, 50.0))
    model.end_paint_brush()


def _row_of(view, path):
    for r in range(view.file_bar_list.count()):
        if getattr(view.file_bar_list.item(r), "file_path", None) == path:
            return r
    raise AssertionError(path)


def test_review_no_batch_is_safe(project):
    controller, _, model, _ = project
    model._last_batch = []
    controller.ml_review_next()  # shows a (stubbed) message, no crash


def test_review_walks_and_loops(project):
    controller, view, model, paths = project
    batch = paths[4:9]
    for p in batch:
        _paint(model, p)
    model._last_batch = list(batch)
    model._last_batch_idx = -1

    # enter from outside the batch: starts at item 0
    view.file_bar_list.setCurrentRow(_row_of(view, paths[9]))
    seen = []
    for _ in range(len(batch)):
        controller.ml_review_next()
        seen.append(os.path.basename(
            model.get_current_image_item().path_image))
    assert seen == [os.path.basename(p) for p in batch]

    # and it loops
    controller.ml_review_next()
    assert os.path.basename(
        model.get_current_image_item().path_image) == os.path.basename(
            batch[0])


def test_review_missing_path_is_safe(project):
    controller, view, model, paths = project
    batch = paths[4:6]
    model._last_batch = list(batch) + [os.path.join("nowhere", "ghost.png")]
    view.file_bar_list.setCurrentRow(_row_of(view, paths[0]))
    for _ in range(4):
        controller.ml_review_next()  # must not raise


def test_suggest_next_ranks_and_cycles(project):
    controller, view, model, paths = project
    for p in paths[:4]:
        _paint(model, p)
    model.num_epochs = 1
    model.batch_size = 2
    model.image_size = 64
    model.train_model_core()
    assert model.is_trained()

    controller._al_ranking = None
    controller._al_pos = -1
    controller.ml_suggest_next()
    ranking = controller._al_ranking
    assert ranking, "a ranking was produced"
    scores = [s for _, s in ranking]
    assert all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1))
    assert all(0.0 <= s <= 1.0 for s in scores)
    # no annotated image may be suggested
    assert not {p for p, _ in ranking} & set(paths[:4])

    first = os.path.basename(model.get_current_image_item().path_image)
    assert first == os.path.basename(ranking[0][0])
    if len(ranking) > 1:
        order = [first]
        for _ in range(min(3, len(ranking))):
            controller.ml_suggest_next()
            order.append(os.path.basename(
                model.get_current_image_item().path_image))
        assert len(set(order)) == len(order)


def test_suggest_next_untrained_is_safe(project):
    controller, _, model, _ = project
    assert not model.is_trained()
    controller.ml_suggest_next()  # stubbed message, no crash
