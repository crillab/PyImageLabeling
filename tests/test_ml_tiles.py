"""Segmentation models on large images, by tiles (model/ML/Tiling.py).

Whole images used to be resized to the network input (416 px): a large image
lost most of its resolution. With tiles, training draws random crops of the
image and prediction slides a window of overlapping tiles over it.
"""
import os

import numpy as np
import pytest
import torch
from PIL import Image as PILImage

from PyImageLabeling.model.ML import Tiling
from PyImageLabeling.model.ML.MLPredictor import TileDataset


# ----------------------------------------------------------------------
# Sliding window
# ----------------------------------------------------------------------

@pytest.mark.parametrize("h, w, tile, overlap", [
    (1000, 1000, 512, 128),
    (6000, 8192, 512, 128),
    (300, 700, 256, 0),
    (100, 50, 128, 32),       # image smaller than a tile
    (513, 512, 512, 256),
])
def test_grid_predicts_every_pixel_exactly_once(h, w, tile, overlap):
    count = np.zeros((h, w), np.int32)
    for y0, x0, (ky0, ky1), (kx0, kx1) in Tiling.tile_grid(h, w, tile,
                                                          overlap):
        # what a tile predicts is inside the tile
        assert y0 <= ky0 < ky1 <= y0 + tile
        assert x0 <= kx0 < kx1 <= x0 + tile
        count[ky0:ky1, kx0:kx1] += 1
    assert (count == 1).all()


def test_pixels_are_taken_away_from_the_tile_edges():
    h = w = 2000
    tile, overlap = 512, 128
    for y0, x0, (ky0, ky1), (kx0, kx1) in Tiling.tile_grid(h, w, tile,
                                                          overlap):
        # at least overlap / 2 from an edge, except on the image border
        if ky0 > 0:
            assert ky0 - y0 >= overlap // 2
        if ky1 < h:
            assert y0 + tile - ky1 >= overlap // 2
        if kx0 > 0:
            assert kx0 - x0 >= overlap // 2
        if kx1 < w:
            assert x0 + tile - kx1 >= overlap // 2


def test_tile_starts():
    assert Tiling.tile_starts(1280, 512, 128) == [0, 384, 768]
    assert Tiling.tile_starts(1000, 512, 128) == [0, 384, 488]
    assert Tiling.tile_starts(400, 512, 128) == [0]


def test_crop_pads_small_images():
    image = np.ones((10, 20, 3), np.uint8)
    tile = Tiling.crop(image, 0, 0, 32, fill=7)
    assert tile.shape == (32, 32, 3)
    assert (tile[:10, :20] == 1).all() and (tile[10:] == 7).all()


def test_settings_are_normalized():
    assert Tiling.normalize_tile_size(500) == 512
    assert Tiling.normalize_tile_size(10) == Tiling.MIN_TILE_SIZE
    assert Tiling.normalize_overlap(400, 512) == 256
    assert Tiling.normalize_overlap(-3, 512) == 0
    assert Tiling.normalize_scale(0.4) == 0.5


# ----------------------------------------------------------------------
# Training tiles
# ----------------------------------------------------------------------

def test_epoch_covers_a_third_of_each_image_whatever_the_tile_size():
    assert Tiling.tiles_per_image(6000, 8192, 512) == 62
    assert Tiling.tiles_per_image(6000, 8192, 1024) == 16
    assert Tiling.tiles_per_image(100, 100, 512) == Tiling.MIN_TILES_PER_IMAGE


def test_class_points_finds_classes_smaller_than_the_grid():
    mask = np.full((200, 300), 5, np.uint8)
    mask[101, 33] = 1                  # one pixel, off the 8 px grid
    mask[40:80, 100:200] = 2
    points = Tiling.class_points(mask, [1, 2, 3])
    assert set(points) == {1, 2}
    assert list(zip(*points[1])) == [(101, 33)]
    ys, xs = points[2]
    assert (mask[ys, xs] == 2).all()


def test_labelled_tiles_contain_the_label():
    rng = np.random.default_rng(0)
    mask = np.zeros((1000, 1500), np.uint8)
    mask[700:720, 1300:1330] = 1      # 0.04% of the image
    image = np.zeros((1000, 1500, 3), np.uint8)
    source = Tiling.TileSource("x", image, mask,
                               Tiling.class_points(mask, [1]))
    for _ in range(50):
        _, tile_mask = source.sample(128, rng, labelled_share=1.0)
        assert (tile_mask == 1).any()


def test_tile_cache_files_are_removed(tmp_path):
    path = str(tmp_path / "img.png")
    PILImage.fromarray(np.zeros((40, 60, 3), np.uint8)).save(path)
    mask = np.zeros((40, 60), np.uint8)
    mask[:10, :10] = 1
    cache = Tiling.TileCache(scale=0.5)
    source = cache.add(path, mask, [1])
    assert source.shape == (20, 30)
    assert source.image.shape == (20, 30, 3)
    assert (source.mask[:5, :5] == 1).all()
    assert cache.add(str(tmp_path / "missing.png"), mask, [1]) is None
    folder = cache.directory
    assert os.listdir(folder)
    cache.close()
    assert not os.path.exists(folder)


def test_tile_dataset_draws_padded_tiles_with_ignored_borders():
    image = np.zeros((40, 50, 3), np.uint8)
    mask = np.zeros((40, 50), np.uint8)
    source = Tiling.TileSource("x", image, mask, {})
    ds = TileDataset([source], 64, augment=False)   # no random flip
    assert len(ds) == Tiling.MIN_TILES_PER_IMAGE
    x, y = ds[0]
    assert x.shape == (3, 64, 64) and x.dtype == torch.float32
    assert y.shape == (64, 64)
    assert (y[40:] == Tiling.IGNORE_INDEX).all()
    assert (y[:40, :50] == 0).all()


# ----------------------------------------------------------------------
# In the app
# ----------------------------------------------------------------------

def _labelled_project(model, workspace, paths, size=(192, 256)):
    """Images with a bright square, painted as label 0 (saved masks)."""
    h, w = size
    rng = np.random.RandomState(1)
    for i, path in enumerate(paths):
        image = rng.randint(0, 60, (h, w, 3), np.uint8)
        y, x = 20 + 7 * i, 30 + 11 * i
        image[y:y + 40, x:x + 40] = 230
        PILImage.fromarray(image).save(path)
        painted = np.zeros((h, w), np.uint8)
        painted[y:y + 40, x:x + 40] = 255
        key = os.path.basename(path).rsplit(".", 1)[0] + ".label.0.png"
        mask_path = os.path.join(str(workspace), key)
        PILImage.fromarray(painted).save(mask_path)
        model.labeling_overview_was_loaded[key] = False
        model.labeling_overview_file_paths[key] = mask_path


def _tiny_training(model, **tiles):
    model.num_epochs = 2
    model.batch_size = 4
    model.image_size = 64
    model.use_pretrained = False
    model.tiling_mode = tiles.get("mode", "on")
    model.tile_size = tiles.get("tile", 64)
    model.tile_overlap = tiles.get("overlap", 16)
    model.tile_scale = tiles.get("scale", 1.0)


def test_training_and_prediction_by_tiles(project, workspace, monkeypatch):
    _, _, model, paths = project
    _labelled_project(model, workspace, paths[:5])
    _tiny_training(model)

    caches = []
    real_cache = Tiling.TileCache

    def recording_cache(*a, **k):
        caches.append(real_cache(*a, **k))
        return caches[-1]
    monkeypatch.setattr(Tiling, "TileCache", recording_cache)
    logs = []
    model.train_model_core(log_callback=logs.append)

    assert model.is_trained()
    assert model.tiling == {"tile_size": 64, "overlap": 16, "scale": 1.0}
    assert any("Tiles: 64 px, overlap 16 px" in m for m in logs)
    # validation went through the sliding window
    assert "seg_miou" in model.val_metrics
    # the decoded images are gone
    assert caches and not os.path.exists(caches[0].directory)

    preds = model.predict_segmentation(paths[0], 0.0)
    assert preds is not None and set(preds) <= {0}
    for mask in preds.values():
        assert mask.shape == (192, 256)
    assert 0.0 <= model.al_uncertainty(paths[6]) <= 1.0


def test_small_images_stay_whole_in_auto_mode(project, workspace):
    _, _, model, paths = project
    _labelled_project(model, workspace, paths[:2])
    _tiny_training(model, mode="auto", tile=512)
    model.train_model_core()
    assert model.is_trained()
    assert model.tiling is None


def test_vit_backbones_get_224_px_tiles(project):
    _, _, model, _ = project
    model.tiling_mode, model.tile_size = "on", 512
    model.tile_overlap, model.tile_scale = 128, 1.0
    model.backbone_name = "ViT-B/16"
    try:
        logs = []
        tiling = model._resolve_tiling(
            [("x", np.zeros((10, 10), np.uint8))], logs.append)
    finally:
        model.backbone_name = "ResNet18"
    assert tiling == {"tile_size": 224, "overlap": 112, "scale": 1.0}
    assert logs


def test_stitched_prediction_matches_the_whole_image(project, monkeypatch):
    """Whatever the tiling, each pixel gets the prediction made at its own
    place: a fake network marks the bright pixels of its tile."""
    _, _, model, _ = project
    rng = np.random.RandomState(0)
    image = (rng.rand(300, 410, 3) > 0.5).astype(np.uint8) * 255

    def fake_logits(tiles):
        bright = torch.from_numpy(tiles[..., 0] > 128).float()
        return torch.stack([torch.zeros_like(bright), 10 * bright], dim=1)
    monkeypatch.setattr(model, "_seg_logits", fake_logits)
    model.batch_size = 3
    for tile, overlap in ((64, 16), (128, 0), (512, 128)):
        model.tiling = {"tile_size": tile, "overlap": overlap, "scale": 1.0}
        cls, conf = model._predict_seg_tiled(image)
        np.testing.assert_array_equal(cls, image[..., 0] > 128)
        assert cls.shape == conf.shape == (300, 410)


def test_scaled_prediction_comes_back_at_the_image_size(project, monkeypatch):
    _, _, model, _ = project
    monkeypatch.setattr(
        model, "_seg_logits",
        lambda tiles: torch.zeros((len(tiles), 2) + tiles.shape[1:3]))
    model.batch_size = 8
    model.tiling = {"tile_size": 64, "overlap": 16, "scale": 0.5}
    cls, conf = model._predict_seg_tiled(np.zeros((301, 205, 3), np.uint8))
    assert cls.shape == conf.shape == (301, 205)


def test_out_of_gpu_memory_halves_the_batches(project, workspace,
                                              monkeypatch):
    _, _, model, paths = project
    _labelled_project(model, workspace, paths[:2])
    _tiny_training(model)
    model.batch_size = 8
    real_step = model._seg_train_step
    sizes = []

    def small_gpu(images, *a):
        sizes.append(images.size(0))
        if images.size(0) > 2:
            raise torch.cuda.OutOfMemoryError("fake")
        return real_step(images, *a)
    monkeypatch.setattr(model, "_seg_train_step", small_gpu)
    logs = []
    model.train_model_core(log_callback=logs.append)

    assert model.is_trained()
    assert any("going on with batches of 2" in m for m in logs)
    # no tile was dropped: the failed batches were trained in halves
    per_epoch = 2 * Tiling.tiles_per_image(192, 256, 64)
    assert sum(s for s in sizes if s <= 2) == 2 * per_epoch
    # and the next epoch went straight to batches of 2
    assert sizes[-(per_epoch // 2):] == [2] * (per_epoch // 2)


def test_saved_model_keeps_its_tiling(project, workspace, tmp_path):
    _, _, model, paths = project
    _labelled_project(model, workspace, paths[:2])
    _tiny_training(model, scale=0.5)
    model.train_model_core()
    tiling = dict(model.tiling)
    model.save_model_file(str(tmp_path), "tiles")

    model.tiling = None
    assert model.load_model_file(str(tmp_path / "tiles.pth"))
    assert model.tiling == tiling == {"tile_size": 64, "overlap": 16,
                                      "scale": 0.5}

    # a model saved before tiles existed predicts on the whole image
    ck = torch.load(str(tmp_path / "tiles.pth"), weights_only=True)
    del ck["tiling"]
    torch.save(ck, str(tmp_path / "old.pth"))
    assert model.load_model_file(str(tmp_path / "old.pth"))
    assert model.tiling is None


def test_settings_dialog_saves_the_tiles(project, monkeypatch):
    _, view, model, _ = project
    from PyImageLabeling.controller.settings.MLSetting import MLSetting
    from PyImageLabeling.model.Utils import Utils

    saved = {}
    monkeypatch.setattr(Utils, "save_parameters",
                        staticmethod(lambda data: saved.update(data)))
    dialog = MLSetting(view.zoomable_graphics_view, model)
    dialog.tiling_combo.setCurrentIndex(dialog.tiling_combo.findData("on"))
    dialog.tile_spinbox.setValue(768)
    dialog.overlap_spinbox.setValue(600)          # more than half a tile
    dialog.scale_combo.setCurrentIndex(dialog.scale_combo.findData(0.5))
    dialog.accept()

    ml = saved["ml"]
    assert (ml["tiling"], ml["tile_size"], ml["tile_overlap"],
            ml["tile_scale"]) == ("on", 768, 384, 0.5)

    dialog = MLSetting(view.zoomable_graphics_view, model)
    dialog.tiling_combo.setCurrentIndex(dialog.tiling_combo.findData("off"))
    assert not dialog.tile_spinbox.isEnabled()
    dialog.reject()
