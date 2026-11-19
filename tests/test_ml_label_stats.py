"""Figures of the labels in the ML settings (model/ML/LabelStats.py): how
many images hold each label, its share of their pixels, and what a
training on the checked labels would see."""
import numpy as np
import pytest
from PyQt6.QtCore import QPointF, Qt

from PyImageLabeling.model.ML import LabelStats
from PyImageLabeling.model.ML.LabelStats import BACKGROUND, IGNORED
from tests.test_ml_label_choice import _two_labels


def test_painted_stats_and_tiles():
    painted = np.zeros((70, 100), bool)
    painted[0, 0] = True
    painted[69, 99] = True
    st = LabelStats.painted_stats(painted)
    assert st.pixels == 2 and st.shape == (70, 100)
    assert st.blocks.shape == (3, 4)              # 32 px blocks, rounded up
    assert st.blocks[0, 0] and st.blocks[2, 3] and st.blocks.sum() == 2
    assert LabelStats.tiles_holding(st.blocks, 1) == (12, 2)
    assert LabelStats.tiles_holding(st.blocks, 2) == (4, 2)
    assert LabelStats.tiles_holding(st.blocks, 4) == (1, 1)


def _image(shape, *boxes):
    painted = np.zeros(shape, bool)
    for y0, y1, x0, x1 in boxes:
        painted[y0:y1, x0:x1] = True
    return LabelStats.painted_stats(painted)


def test_summarize():
    images = {
        "a": {1: _image((64, 64), (0, 10, 0, 10))},
        "b": {1: _image((64, 64), (63, 64, 63, 64)),
              2: _image((64, 64), (0, 64, 0, 64))},
        "c": {},                                   # nothing painted
    }
    s = LabelStats.summarize(images)
    assert s["labels"][1] == {"images": 2, "density": 101 / 8192}
    assert s["labels"][2] == {"images": 1, "density": 1.0}
    assert s["training_images"] == 2
    assert s["tiles"] is None and s["empty_tiles"] is None

    s = LabelStats.summarize(images, chosen={1}, tile_px=32)
    assert s["training_images"] == 2
    assert s["share"][1] == pytest.approx(101 / 8192)
    assert s["share"][BACKGROUND] == pytest.approx(1 - 101 / 8192)
    assert IGNORED not in s["share"]
    assert s["tiles"] == {1: 2 / 8}
    assert s["empty_tiles"] == 6 / 8

    s = LabelStats.summarize(images, chosen={1}, ignore_others=True)
    assert s["share"][IGNORED] == 0.5
    assert s["share"][BACKGROUND] == pytest.approx((4096 - 101) / 8192)

    s = LabelStats.summarize(images, chosen={2}, tile_px=64)
    assert s["training_images"] == 1
    assert s["share"] == {2: 1.0, BACKGROUND: 0.0}
    assert s["tiles"] == {2: 1.0} and s["empty_tiles"] == 0.0


def test_file_stats_are_cached(tmp_path):
    from PIL import Image as PILImage
    path = tmp_path / "m.png"
    painted = np.zeros((40, 40), np.uint8)
    painted[:4, :5] = 255
    PILImage.fromarray(painted).save(path)
    cache = {}
    reads = []

    def reader(p):
        reads.append(p)
        return np.asarray(PILImage.open(p)) > 0
    assert LabelStats.file_stats(str(path), cache, reader).pixels == 20
    assert LabelStats.file_stats(str(path), cache, reader).pixels == 20
    assert len(reads) == 1
    assert LabelStats.file_stats(str(tmp_path / "missing.png"), cache) \
        is None


def _dialog(view, model):
    from PyImageLabeling.controller.settings.MLSetting import MLSetting
    dialog = MLSetting(view.zoomable_graphics_view, model)
    dialog.wait_for_label_stats()
    return dialog


def _cell(dialog, row, col):
    return dialog.labels_table.item(row, col).text()


def test_settings_dialog_shows_the_figures(project, workspace):
    """Image 0: labels 0 and 1, image 1: label 1, image 2: label 0, on
    96 x 128 px images; label 0 covers 1200 px, label 1 2000 px."""
    _, view, model, paths = project
    _two_labels(model, workspace, paths)
    dialog = _dialog(view, model)
    bg, ignored = dialog._background_row, dialog._ignored_row
    try:
        # all labels: 3 training images of 12288 px
        assert _cell(dialog, 0, 1) == "2"
        assert _cell(dialog, 0, 2) == "9.8 %"      # 2400 / 24576
        assert _cell(dialog, 1, 2) == "16.3 %"     # 4000 / 24576
        assert _cell(dialog, 0, 3) == "6.5 %"      # 2400 / 36864
        assert _cell(dialog, 1, 3) == "10.9 %"
        assert _cell(dialog, bg, 3) == "82.6 %"
        assert dialog.labels_table.isRowHidden(ignored)
        assert "Training images: 3 of the 3 checked" in \
            dialog.labels_summary.text()

        # binary, label 1: images 0 and 1
        dialog.labels_table.item(0, 0).setCheckState(Qt.CheckState.Unchecked)
        assert _cell(dialog, 0, 3) == "–"
        assert _cell(dialog, 0, 2) == "9.8 %"      # still shown
        assert _cell(dialog, 1, 3) == "16.3 %"
        assert _cell(dialog, bg, 3) == "83.7 %"

        # label 0 ignored: 1200 px of image 0
        dialog.other_labels_checkbox.setChecked(False)
        dialog.wait_for_label_stats()
        assert not dialog.labels_table.isRowHidden(ignored)
        assert _cell(dialog, ignored, 3) == "4.9 %"
        assert _cell(dialog, bg, 3) == "78.8 %"

        # tiles: their column and the empty tiles
        dialog.whole_radio.setChecked(True)
        dialog.wait_for_label_stats()
        assert dialog.labels_table.isColumnHidden(4)
        dialog.tiles_radio.setChecked(True)
        dialog.tile_spinbox.setValue(64)
        dialog.wait_for_label_stats()
        assert not dialog.labels_table.isColumnHidden(4)
        assert _cell(dialog, 1, 4).endswith("%")
        assert "of their tiles hold none" in dialog.labels_summary.text()

        # the figures follow the images checked
        dialog.image_list.item(1).setCheckState(Qt.CheckState.Unchecked)
        dialog.wait_for_label_stats()
        assert "Training images: 1 of the 2 checked" in \
            dialog.labels_summary.text()
    finally:
        dialog.reject()


def test_figures_come_from_the_cache_the_second_time(project, workspace,
                                                     monkeypatch):
    _, view, model, paths = project
    _two_labels(model, workspace, paths)
    _dialog(view, model).reject()

    import PyImageLabeling.model.Masks as Masks

    def broken(path):
        raise AssertionError("read again")
    monkeypatch.setattr(Masks, "read_painted_mask", broken)
    dialog = _dialog(view, model)
    try:
        assert _cell(dialog, 0, 1) == "2"
        assert _cell(dialog, 1, 1) == "2"
    finally:
        dialog.reject()


def test_unsaved_strokes_count(project, workspace):
    """A loaded image with strokes that are not saved is read from its
    overlay, not from the (missing) file."""
    _, view, model, paths = project
    _two_labels(model, workspace, paths)
    model.select_image(paths[5])
    model.start_paint_brush(QPointF(20.0, 20.0))
    model.move_paint_brush(QPointF(60.0, 50.0))
    model.end_paint_brush()

    files, overlays = model.ml_label_stat_sources([paths[5]])
    assert not files and list(overlays) == [paths[5]]
    label_id = model.get_current_label_item().get_label_id()

    dialog = _dialog(view, model)
    try:
        row = dialog._label_row_ids.index(label_id)
        assert _cell(dialog, row, 1) == "3"
    finally:
        dialog.reject()
