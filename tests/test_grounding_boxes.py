"""Regression: the multi-scale dedup in text_to_boxes needs _box_iou.

_commit 10f7bfd_ ("purge dead code") deleted _box_iou() because the only call
site anyone looked at was inside text_to_boxes_multi(), which was deleted in
the same commit. The call that matters, in text_to_boxes(), survived:

    if any(_box_iou(b["box"], m["box"]) > 0.7 for m in merged):

so every text-to-mask run raised NameError on the first box, right after the
DINO forward pass had already run.
"""
import numpy as np
import pytest

from PyImageLabeling.model.SAM import grounding


def test_box_iou_is_importable():
    assert callable(grounding._box_iou)


def test_iou_of_a_box_with_itself_is_one():
    assert grounding._box_iou([0, 0, 10, 10], [0, 0, 10, 10]) == 1.0


def test_iou_of_disjoint_boxes_is_zero():
    assert grounding._box_iou([0, 0, 10, 10], [20, 20, 30, 30]) == 0.0


def test_iou_half_overlap():
    assert grounding._box_iou([0, 0, 10, 10], [0, 0, 10, 20]) == pytest.approx(0.5)


def test_iou_of_degenerate_box_is_zero_not_a_crash():
    # a zero-area box comes out of DINO on a hard image
    assert grounding._box_iou([5, 5, 5, 5], [0, 0, 10, 10]) == 0.0


def test_iou_is_symmetric():
    a, b = [3, 4, 30, 40], [10, 12, 25, 50]
    assert grounding._box_iou(a, b) == pytest.approx(grounding._box_iou(b, a))


def test_dedup_runs_and_keeps_the_best_scoring_duplicate(monkeypatch):
    """Same box at 1.0x and 1.5x must collapse to one, best score wins."""
    calls = {"n": 0}

    class FakeProcessor:
        def __call__(self, images, text, return_tensors):
            return {"input_ids": object()}

        def post_process_grounded_object_detection(self, outputs, ids,
                                                  threshold, text_threshold,
                                                  target_sizes):
            calls["n"] += 1
            sh, sw = target_sizes[0]
            # report in the coordinates of the scale we were handed, so the
            # inverse mapping lands on the same image box either way
            sx, sy = sw / 200.0, sh / 200.0
            score = 0.9 if calls["n"] == 1 else 0.4
            return [{
                "boxes": np.array([[10.0 * sx, 10.0 * sy,
                                    50.0 * sx, 50.0 * sy]]),
                "scores": np.array([score]),
            }]

    class FakeModel:
        def __call__(self, **kwargs):
            return object()

    monkeypatch.setattr(grounding, "ensure_grounding",
                        lambda device="cuda": (FakeModel(), FakeProcessor(),
                                               "cpu"))

    rgb = np.zeros((200, 200, 3), np.uint8)
    boxes = grounding.text_to_boxes(rgb, "cell", device="cpu",
                                    box_threshold=0.15)

    assert boxes, "dedup swallowed every box"
    assert len(boxes) == 1, f"duplicate across scales not merged: {boxes}"
    assert boxes[0]["score"] == pytest.approx(0.9)
    assert boxes[0]["box"] == [10, 10, 50, 50]


def test_nearby_boxes_are_not_merged(monkeypatch):
    """IoU > 0.7 keeps adjacent objects separate; a tight threshold would
    silently drop one of two neighbouring cells."""
    class FakeProcessor:
        def __call__(self, images, text, return_tensors):
            return {"input_ids": object()}

        def post_process_grounded_object_detection(self, outputs, ids,
                                                  threshold, text_threshold,
                                                  target_sizes):
            return [{
                "boxes": np.array([[0.0, 0.0, 10.0, 10.0],
                                   [10.0, 0.0, 20.0, 10.0]]),
                "scores": np.array([0.9, 0.8]),
            }]

    class FakeModel:
        def __call__(self, **kwargs):
            return object()

    monkeypatch.setattr(grounding, "ensure_grounding",
                        lambda device="cuda": (FakeModel(), FakeProcessor(),
                                               "cpu"))

    rgb = np.zeros((200, 200, 3), np.uint8)
    boxes = grounding.text_to_boxes(rgb, "cell", device="cpu",
                                    scales=(1.0,), box_threshold=0.15)

    assert len(boxes) == 2, f"adjacent boxes wrongly merged: {boxes}"


def test_threshold_still_filters_after_dedup(monkeypatch):
    """The dedup runs at a 0.01 floor, so the user's threshold has to keep
    filtering afterwards."""
    class FakeProcessor:
        def __call__(self, images, text, return_tensors):
            return {"input_ids": object()}

        def post_process_grounded_object_detection(self, outputs, ids,
                                                  threshold, text_threshold,
                                                  target_sizes):
            return [{
                "boxes": np.array([[0.0, 0.0, 10.0, 10.0],
                                   [50.0, 50.0, 60.0, 60.0]]),
                "scores": np.array([0.5, 0.05]),
            }]

    class FakeModel:
        def __call__(self, **kwargs):
            return object()

    monkeypatch.setattr(grounding, "ensure_grounding",
                        lambda device="cuda": (FakeModel(), FakeProcessor(),
                                               "cpu"))

    rgb = np.zeros((200, 200, 3), np.uint8)
    boxes = grounding.text_to_boxes(rgb, "cell", device="cpu",
                                    scales=(1.0,), box_threshold=0.3)

    assert [b["score"] for b in boxes] == [0.5]