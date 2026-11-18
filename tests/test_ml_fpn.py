"""Multi-scale (FPN) decoder of the segmentation head.

The last layer of a backbone is at 1/32 of the resolution: the head that
only upsamples it blurs the edges. The FPN decoder also uses the 1/4, 1/8
and 1/16 layers.
"""
import pytest
import torch

from PyImageLabeling.model.ML.MLPredictor import (
    FastObjectDetectorWithSegmentation, FPNSegmentationHead,
    SEG_DECODER_FPN, SEG_DECODER_SIMPLE, SegmentationHead, _build_backbone,
    backbone_pyramid)
from tests.test_ml_tiles import _labelled_project, _tiny_training


@pytest.mark.parametrize("name", ["ResNet18", "MobileNetV3-Small",
                                  "ConvNeXt-Tiny", "Swin-Tiny"])
def test_pyramid_goes_from_a_quarter_to_the_last_layer(name):
    ext, _ = _build_backbone(name, False)
    ext.eval()
    x = torch.randn(1, 3, 128, 128)
    with torch.no_grad():
        feats = backbone_pyramid(ext, x)
        last = ext(x)
    assert [128 // f.shape[-2] for f in feats] == [4, 8, 16, 32]
    assert [f.shape[1] for f in feats] == ext.pyramid_channels
    # the coarsest level is what the detection head gets
    assert torch.allclose(feats[-1], last, atol=1e-5)


def test_vit_has_a_single_level():
    ext, _ = _build_backbone("ViT-B/16", False)
    with torch.no_grad():
        feats = backbone_pyramid(ext.eval(), torch.randn(1, 3, 224, 224))
    assert len(feats) == 1 and feats[0].shape[-1] == 14


@pytest.mark.parametrize("decoder, head", [
    (SEG_DECODER_FPN, FPNSegmentationHead),
    (SEG_DECODER_SIMPLE, SegmentationHead),
])
def test_both_decoders_give_a_mask_of_the_input_size(decoder, head):
    net = FastObjectDetectorWithSegmentation(
        num_classes=3, pretrained=False, seg_decoder=decoder).eval()
    assert isinstance(net.segmentation_head, head)
    with torch.no_grad():
        obj, _, _, seg = net(torch.randn(2, 3, 96, 160))
    assert seg.shape == (2, 3, 96, 160)
    assert obj.shape[1:3] == (3, 5)          # detection: last layer, 1/32


def test_fpn_mask_follows_a_fine_detail():
    # the layer at 1/4 reaches the output: a change of one 4 x 4 block
    # changes the mask there (with the last layer only, a whole 32 x 32
    # block moves together)
    torch.manual_seed(0)
    net = FastObjectDetectorWithSegmentation(
        num_classes=2, pretrained=False, enable_detection=False,
        seg_decoder=SEG_DECODER_FPN).eval()
    x = torch.zeros(1, 3, 64, 64)
    y = x.clone()
    y[:, :, 40:44, 40:44] = 3.0
    with torch.no_grad():
        diff = (net(y)[3] - net(x)[3]).abs().sum(1)[0]
    near, far = diff[36:48, 36:48].mean(), diff[:8, :8].mean()
    assert near > 5 * far


def test_training_saves_and_reloads_the_decoder(project, workspace, tmp_path):
    _, _, model, paths = project
    _labelled_project(model, workspace, paths[:3])
    _tiny_training(model)
    stats = []
    model.train_model_core(stats_callback=stats.append)
    assert model.model.seg_decoder == SEG_DECODER_FPN     # the default
    setup = next(s for s in stats if s["kind"] == "setup")
    assert "multi-scale (FPN) decoder" in setup["backbone"]
    assert "FPN" in model.ml_model_info()["kind"]
    preds = model.predict_segmentation(paths[0], 0.0)
    assert preds is not None
    model.save_model_file(str(tmp_path), "fpn")

    model.seg_decoder = SEG_DECODER_SIMPLE    # settings changed since
    assert model.load_model_file(str(tmp_path / "fpn.pth"))
    assert isinstance(model.model.segmentation_head, FPNSegmentationHead)

    # a model saved before the FPN decoder has the last-layer head
    model.seg_decoder = SEG_DECODER_SIMPLE
    _tiny_training(model)
    model.train_model_core()
    model.save_model_file(str(tmp_path), "simple")
    ck = torch.load(str(tmp_path / "simple.pth"), weights_only=True)
    del ck["seg_decoder"]
    torch.save(ck, str(tmp_path / "old.pth"))
    model.seg_decoder = SEG_DECODER_FPN
    assert model.load_model_file(str(tmp_path / "old.pth"))
    assert isinstance(model.model.segmentation_head, SegmentationHead)


def test_settings_dialog_chooses_the_decoder(project, monkeypatch):
    _, view, model, _ = project
    from PyImageLabeling.controller.settings.MLSetting import MLSetting
    from PyImageLabeling.model.Utils import Utils
    saved = {}
    monkeypatch.setattr(Utils, "save_parameters",
                        staticmethod(lambda data: saved.update(data)))
    dialog = MLSetting(view.zoomable_graphics_view, model)
    assert dialog.decoder_combo.currentData() == SEG_DECODER_FPN
    assert not dialog.decoder_row.isHidden()
    dialog.decoder_combo.setCurrentIndex(
        dialog.decoder_combo.findData(SEG_DECODER_SIMPLE))
    dialog.accept()
    assert saved["ml"]["seg_decoder"] == SEG_DECODER_SIMPLE
