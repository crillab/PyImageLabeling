"""Data-loss regressions (audit P0): basename collisions, saves that
survive a broken image, concurrent complete_state, LRU unloading and
degraded first-run parameters.

Each test reproduces a bug that used to destroy annotations silently.
"""
import json
import os

import numpy as np
import PIL.Image as PILImage
import pytest
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QColor, QImage

from PyImageLabeling.model import Autosave
from PyImageLabeling.model.Base import (KEYWORD_SAVE_LABEL,
                                        image_base_from_mask_name,
                                        mask_file_name, path_hash)
from PyImageLabeling.model.Labeling.PaintBrush import PaintBrush
from tests.conftest import make_images, reset_app


# ----------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------
def _register(controller, view, model, paths):
    reset_app(controller, view, model)
    for p in paths:
        model.file_paths.append(p)
        model.image_items[p] = None
    view.file_bar_add(list(paths))


def _make_img(folder, name, seed, size=128):
    os.makedirs(folder, exist_ok=True)
    p = os.path.join(folder, name)
    rng = np.random.RandomState(seed)
    PILImage.fromarray(
        rng.randint(0, 255, (size, size, 3)).astype(np.uint8)).save(p)
    return p


def _paint_box(model, path, label_item, x, y, w=20, h=20):
    model.select_image(path)
    painter = (model.get_current_image_item().get_labeling_overlay()
               .get_painter())
    painter.fillRect(x, y, w, h, label_item.get_color())
    model.get_current_image_item().update_labeling_overlay()


def _setup_two_labels(model):
    la = model.new_label("A", "Pixel-by-pixel", QColor(0, 0, 255))
    lb = model.new_label("B", "Pixel-by-pixel", QColor(255, 0, 0))
    model.set_current_label_item(la)
    return la, lb


def _assert_per_image_masks(project, painted, paths, label_id):
    """painted: {path: (x, y)} pixel inside path's painted box. For every
    pixel, exactly the images that stroked it hold an ANNOTATION pixel in
    their own mask file, and no other mask does.

    On-disk mask semantics (validated against the app's own load path,
    which renders opaque where the file is non-black): the annotation
    region is stored WHITE (gray 255) and the background BLACK (0) -- NOT
    the naive "annotation is black on disk".
    """
    from PyQt6.QtGui import QImage

    images = {p: QImage(mask_file_name(str(project), p, label_id))
              for p in paths}
    for p in paths:
        assert not images[p].isNull(), f"missing mask for {p}"

    pixels = {(120, 120)}   # known annotation-free spot in every 128 img
    for x, y in painted.values():
        if x is not None:
            pixels |= {(i, j)
                       for i, j in ((x, y), (x + 10, y + 10))}
    for pixel in sorted(pixels):
        annotated_in = set()
        for p in paths:
            if _mask_annotated(images[p], pixel[0], pixel[1]):
                annotated_in.add(p)
        owners = set()
        x_, y_ = pixel
        for p, (bx, by) in painted.items():
            if bx is not None:
                if bx <= x_ < bx + 20 and by <= y_ < by + 20:
                    owners.add(p)
        assert annotated_in == owners, (
            f"pixel {pixel}: annotations found in "
            f"{sorted(os.path.basename(os.path.dirname(p)) for p in annotated_in)}, expected "
            f"{sorted(os.path.basename(os.path.dirname(p)) for p in owners)}")


def _mask_annotated(image, x, y):
    """True where the mask file's pixel marks an annotation: on-disk the
    annotation region is non-black (white), the background black."""
    return image.pixelColor(x, y).red() > 0


# ----------------------------------------------------------------------
# basename collisions
# ----------------------------------------------------------------------
def test_collision_same_basename_two_folders(app_stack, workspace, tmp_path):
    """dirA/IMG_001.png and dirB/IMG_001.png used to overwrite each
    other's single mask: both annotations must survive save + reload."""
    controller, view, model = app_stack
    pA = _make_img(os.path.join(str(workspace), "dirA"), "IMG_001.png", 1)
    pB = _make_img(os.path.join(str(workspace), "dirB"), "IMG_001.png", 2)
    _register(controller, view, model, [pA, pB])
    la, _ = _setup_two_labels(model)

    _paint_box(model, pA, la, 5, 5)
    _paint_box(model, pB, la, 90, 90)
    project = str(tmp_path / "project")
    os.makedirs(project)
    model.save_directory = project
    model.save()

    maskA = mask_file_name(project, pA, la.get_label_id())
    maskB = mask_file_name(project, pB, la.get_label_id())
    assert maskA != maskB                    # no silent overwrite
    _assert_per_image_masks(
        project, {pA: (5, 5), pB: (90, 90)}, [pA, pB], la.get_label_id())


def test_collision_same_basename_different_extensions(app_stack, workspace,
                                                      tmp_path):
    """dup.png and dup.jpg: same mask name except for the path digest."""
    controller, view, model = app_stack
    pPng = _make_img(str(workspace), "dup.png", 3)
    pJpg = _make_img(str(workspace), "dup.jpg", 4)
    _register(controller, view, model, [pPng, pJpg])
    la, _ = _setup_two_labels(model)

    _paint_box(model, pPng, la, 5, 5)
    _paint_box(model, pJpg, la, 90, 90)
    project = str(tmp_path / "project")
    os.makedirs(project)
    model.save_directory = project
    model.save()

    maskPng = mask_file_name(project, pPng, la.get_label_id())
    maskJpg = mask_file_name(project, pJpg, la.get_label_id())
    assert maskPng != maskJpg
    _assert_per_image_masks(
        project, {pPng: (5, 5), pJpg: (90, 90)}, [pPng, pJpg],
        la.get_label_id())


def test_mask_name_collision_images_have_valid_tag(app_stack, workspace,
                                                   tmp_path):
    """'has annotations' tag must resolve hashed mask names back to the
    plain image basename (cosmetic but user-facing)."""
    controller, view, model = app_stack
    pA = _make_img(os.path.join(str(workspace), "dA"), "IMG_001.png", 5)
    pB = _make_img(os.path.join(str(workspace), "dB"), "IMG_001.png", 6)
    _register(controller, view, model, [pA, pB])
    la, _ = _setup_two_labels(model)
    _paint_box(model, pA, la, 5, 5)
    _paint_box(model, pB, la, 90, 90)
    project = str(tmp_path / "project")
    os.makedirs(project)
    model.save_directory = project
    model.save()

    assert image_base_from_mask_name(
        os.path.basename(mask_file_name(project, pA, la.get_label_id()))
    ) == "IMG_001"


def test_legacy_mask_names_still_load(app_stack, workspace, tmp_path):
    """Projects saved before the collision fix keep loading: the plain
    'stem.label.<id>.png' files remain valid mask sources."""
    controller, view, model = app_stack
    p = _make_img(str(workspace), "old.png", 7)
    _register(controller, view, model, [p])
    la, _ = _setup_two_labels(model)

    project = str(tmp_path / "project")
    os.makedirs(project)
    model.save_directory = project
    # legacy-format mask on disk, as an older project would hold
    legacy = os.path.join(project, f"old{KEYWORD_SAVE_LABEL}"
                                 f"{la.get_label_id()}.png")
    PILImage.fromarray(np.zeros((128, 128), np.uint8)).convert(
        "L").point(lambda v: 255).save(legacy, "PNG")

    # post-load index state, built by the same function Files.load() calls
    # for every mask file (model.load() itself opens a modal progress
    # dialog that would hang a test)
    model.save_labels(project)          # the project's labels.json
    model.load_labels_images(legacy)
    model.select_image(p)
    item = model.image_items.get(p)
    assert item is not None
    assert item.labeling_overlays, "legacy mask was not bound to the image"
    overlay = item.labeling_overlays[la.get_label_id()]
    img = overlay.labeling_overlay_pixmap.toImage()
    # legacy file = fully annotated (all white on disk)
    assert img.pixelColor(60, 60).alpha() == 255


# ----------------------------------------------------------------------
# saving a broken image must not take the whole project down
# ----------------------------------------------------------------------
def test_save_survives_corrupt_image(app_stack, workspace, tmp_path):
    """A corrupted image used to crash save() with
    'NoneType' has no attribute asstring', losing every OTHER image's
    annotations in the same save."""
    controller, view, model = app_stack
    good = _make_img(str(workspace), "good.png", 8)
    bad = os.path.join(str(workspace), "garbage.png")
    with open(bad, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\nGARBAGE" * 20)
    empty = os.path.join(str(workspace), "zero.png")
    open(empty, "wb").close()

    _register(controller, view, model, [good, bad, empty])
    la, _ = _setup_two_labels(model)
    _paint_box(model, good, la, 5, 5)

    project = str(tmp_path / "project")
    os.makedirs(project)
    model.save_directory = project
    model.save()   # must not raise

    assert os.path.isfile(mask_file_name(project, good,
                                         la.get_label_id()))
    assert os.path.isfile(os.path.join(project, "labels.json"))


def test_broken_overlay_does_not_kill_other_labels(app_stack, workspace,
                                                   tmp_path, monkeypatch):
    """If one label's mask write blows up, the other labels/images must
    still be written, and the image stays flagged as unsaved."""
    controller, view, model = app_stack
    good = _make_img(str(workspace), "keep.png", 9)
    doomed = _make_img(str(workspace), "doom.png", 10)
    _register(controller, view, model, [good, doomed])
    la, _ = _setup_two_labels(model)
    _paint_box(model, good, la, 5, 5)
    _paint_box(model, doomed, la, 40, 40)

    real_save = None
    from PyImageLabeling.model.LabelingOverlay import LabelingOverlay
    real_save = LabelingOverlay.save

    def exploding_save(self, directory, path_image):
        if os.path.basename(path_image) == "doom.png":
            raise RuntimeError("simulated IO failure")
        return real_save(self, directory, path_image)

    monkeypatch.setattr(LabelingOverlay, "save", exploding_save)
    errors = []
    monkeypatch.setattr(
        controller, "error_message",
        staticmethod(lambda title, msg: errors.append((title, msg))))

    project = str(tmp_path / "project")
    os.makedirs(project)
    model.save_directory = project
    model.save()   # must not raise

    assert os.path.isfile(mask_file_name(project, good, la.get_label_id()))
    doomed_item = model.image_items[doomed]
    assert doomed_item.get_edited()   # retryable: still marked unsaved
    assert errors and "Save Error" == errors[0][0]


# ----------------------------------------------------------------------
# concurrent instances / complete_state.json
# ----------------------------------------------------------------------
def test_complete_state_merge_keeps_foreign_images(app_stack, workspace,
                                                   tmp_path):
    """Instance B saving its ticks must not wipe instance A's ticks."""
    controller, view, model = app_stack
    p = _make_img(str(workspace), "B.png", 11)
    _register(controller, view, model, [p])
    project = str(tmp_path / "project")
    os.makedirs(project)
    model.save_directory = project

    # what the other instance wrote moments before
    foreign = os.path.join(project, "complete_state.json")
    with open(foreign, "w", encoding="utf-8") as f:
        json.dump({"A.png": True}, f)

    model.save_complete_state(project)
    new_state = json.loads(open(foreign, encoding="utf-8").read())
    assert new_state.get("A.png") is True, "other instance's state was lost"
    assert "B.png" in new_state


# ----------------------------------------------------------------------
# memory: LRU unloading
# ----------------------------------------------------------------------
def test_lru_unloads_old_images_but_keeps_recent(app_stack, workspace,
                                                 tmp_path, monkeypatch):
    controller, view, model = app_stack
    paths = make_images(workspace, 6, size=64, seed=12)
    _register(controller, view, model, paths)
    _setup_two_labels(model)
    monkeypatch.setattr(model, "_keep_loaded_images", lambda: 2)

    for p in paths:
        model.select_image(p)

    assert model.image_items[paths[5]] is not None     # current
    assert model.image_items[paths[4]] is not None     # kept (2 slots)
    assert all(model.image_items[p] is None for p in paths[:4])


def test_lru_never_unloads_unsaved_work(app_stack, workspace, tmp_path,
                                        monkeypatch):
    controller, view, model = app_stack
    paths = make_images(workspace, 5, size=64, seed=13)
    _register(controller, view, model, paths)
    la, _ = _setup_two_labels(model)
    monkeypatch.setattr(model, "_keep_loaded_images", lambda: 1)

    _paint_box(model, paths[0], la, 5, 5)      # unsaved strokes
    for p in paths[1:]:
        model.select_image(p)

    assert model.image_items[paths[0]] is not None, \
        "unsaved annotations were evicted: they would be lost"


def test_lru_reload_rebinds_disk_masks(app_stack, workspace, tmp_path,
                                       monkeypatch):
    """Unloaded then re-selected: the disk mask must come back, not a
    blank overlay (the pre-fix behaviour reset the index flag wrongly
    or pointed at a stale key)."""
    controller, view, model = app_stack
    paths = make_images(workspace, 4, size=64, seed=14)
    _register(controller, view, model, paths)
    la, _ = _setup_two_labels(model)
    monkeypatch.setattr(model, "_keep_loaded_images", lambda: 1)

    _paint_box(model, paths[0], la, 20, 20)
    project = str(tmp_path / "project")
    os.makedirs(project)
    model.save_directory = project
    model.save()
    for p in paths[1:]:
        model.select_image(p)
    assert model.image_items[paths[0]] is None   # was evicted

    model.select_image(paths[0])   # rebuilds from the disk mask
    image = model.get_current_image_item() \
        .labeling_overlays[la.get_label_id()].labeling_overlay_pixmap \
        .toImage()
    assert not image.isNull()
    assert image.pixelColor(30, 30).alpha() == 255    # back from disk
    assert image.pixelColor(5, 5).alpha() == 0


# ----------------------------------------------------------------------
# first launch on a read-only installation
# ----------------------------------------------------------------------
def test_parameters_fallback_to_user_home(monkeypatch, tmp_path):
    """Read-only install dir (sudo pip, system python): settings move to
    ~/.pyimagelabeling instead of PermissionError-crashing at startup."""
    from PyImageLabeling.model.Utils import Utils

    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    ro = tmp_path / "readonly"
    ro.mkdir()
    monkeypatch.setattr(Utils, "get_base_dir", staticmethod(lambda: str(ro)))
    # first candidate (the read-only base dir) refuses, the user-home
    # fallback accepts: exercises order + fallback selection
    refuses = [False]   # flip to True only for the base-dir candidate

    real_ensure = Utils._ensure_writable

    def selective(directory):
        if directory == str(ro):
            return False
        return real_ensure(directory)

    monkeypatch.setattr(Utils, "_ensure_writable",
                        staticmethod(selective))
    monkeypatch.setattr(Utils, "_params_path_cache", None)

    path = Utils.get_parameters_path()
    assert path == os.path.join(str(home), ".pyimagelabeling",
                                "parameters.json")
    assert os.path.isdir(os.path.dirname(path))


def test_parameters_all_unwritable_degrades(monkeypatch, tmp_path):
    """Even with no writable location at all, the app must boot on
    in-memory defaults (no exception, save is a no-op)."""
    from PyImageLabeling.model.Utils import Utils

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setattr(Utils, "_params_path_cache", None)
    monkeypatch.setattr(
        Utils, "_ensure_writable", staticmethod(lambda directory: False))

    assert Utils.get_parameters_path() == ""
    params = Utils.load_parameters()   # no raise
    assert isinstance(params, dict) and "zoom" in params
    Utils.save_parameters(dict(params))   # no raise
