"""DINOv2 as a backbone of the segmentation network (model/ML/DinoBackbone.py).

The DINOv2-linear probe saw the whole image squeezed to 448 px. As a
backbone, DINOv2 takes the tiles like the other backbones, frozen by
default, with the FPN or the linear decoder.
"""
import pytest
import torch

from PyImageLabeling.model.ML import DinoBackbone
from PyImageLabeling.model.ML.MLPredictor import (
    FastObjectDetectorWithSegmentation, FPNSegmentationHead,
    LinearSegmentationHead, SEG_DECODER_FPN, SEG_DECODER_LINEAR,
    SEG_DECODER_SIMPLE, _build_backbone, backbone_linear_inputs,
    backbone_pyramid)
from tests.test_ml_tiles import _labelled_project, _tiny_training

DINO = "DINOv2-S/14"


@pytest.fixture
def no_download(monkeypatch):
    """The "pretrained" encoder is a random one: no download in the tests
    (and the training takes the path of a pretrained encoder: frozen)."""
    real = DinoBackbone._dinov2_model
    monkeypatch.setattr(DinoBackbone, "_dinov2_model",
                        lambda name, pretrained: real(name, False))


def test_levels_of_the_decoders():
    ext, feat_ch = _build_backbone(DINO, False)
    ext.eval()
    x = torch.randn(1, 3, 518, 518)            # 37 x 37 patches
    with torch.no_grad():
        pyramid = backbone_pyramid(ext, x)
        linear = backbone_linear_inputs(ext, x)
        last = ext(x)
    assert [f.shape[-1] for f in pyramid] == [148, 74, 37, 18]
    assert [f.shape[1] for f in pyramid] == ext.pyramid_channels
    assert [f.shape[-1] for f in linear] == [37] * 4
    assert [f.shape[1] for f in linear] == ext.linear_channels == [384] * 4
    # the last of the linear inputs is the last layer (detection head)
    assert feat_ch == 384 and torch.allclose(linear[-1], last, atol=1e-5)
    # the levels come from different depths
    assert not torch.allclose(linear[0], linear[-1])


@pytest.mark.parametrize("decoder, head", [
    (SEG_DECODER_FPN, FPNSegmentationHead),
    (SEG_DECODER_LINEAR, LinearSegmentationHead),
    (SEG_DECODER_SIMPLE, None),
])
def test_every_decoder_gives_a_mask_of_the_input_size(decoder, head):
    # 100 x 150 is no multiple of the 14 px patches
    net = FastObjectDetectorWithSegmentation(
        num_classes=3, pretrained=False, backbone_name=DINO,
        seg_decoder=decoder).eval()
    if head is not None:
        assert isinstance(net.segmentation_head, head)
    with torch.no_grad():
        obj, _, _, seg = net(torch.randn(2, 3, 100, 150))
    assert seg.shape == (2, 3, 100, 150)
    assert obj.shape[0] == 2


def test_linear_decoder_on_a_convolutional_backbone():
    net = FastObjectDetectorWithSegmentation(
        num_classes=2, pretrained=False, backbone_name="ResNet18",
        seg_decoder=SEG_DECODER_LINEAR).eval()
    with torch.no_grad():
        obj, _, _, seg = net(torch.randn(1, 3, 128, 96))
    assert seg.shape == (1, 2, 128, 96)
    assert obj.shape[1:3] == (4, 3)          # detection: last layer, 1/32


def test_encoder_frozen_but_its_last_blocks():
    ext, _ = _build_backbone(DINO, False)
    assert ext.trainable_blocks == 0
    assert not any(p.requires_grad for p in ext.dino.parameters())
    assert all(p.requires_grad for p in ext.up4.parameters())

    assert ext.set_trainable_blocks(2) == 2
    blocks = ext.dino.encoder.layer
    trainable = [any(p.requires_grad for p in b.parameters())
                 for b in blocks]
    assert trainable == [False] * 10 + [True] * 2
    assert all(p.requires_grad for p in ext.dino.layernorm.parameters())
    assert not any(p.requires_grad
                   for p in ext.dino.embeddings.parameters())
    assert ext.set_trainable_blocks(99) == 12
    assert ext.set_trainable_blocks(0) == 0
    assert ext.encoder_parameters() == []


def test_frozen_encoder_gets_no_gradient():
    net = FastObjectDetectorWithSegmentation(
        num_classes=2, pretrained=False, enable_detection=False,
        backbone_name=DINO, seg_decoder=SEG_DECODER_FPN).train()
    _, _, _, seg = net(torch.randn(2, 3, 56, 56))
    seg.sum().backward()
    assert all(p.grad is None for p in net.backbone.dino.parameters())
    assert net.backbone.up4[0].weight.grad is not None
    assert net.segmentation_head.final[-1].weight.grad is not None


def test_training_by_tiles_keeps_the_encoder(project, workspace, tmp_path,
                                             monkeypatch, no_download):
    _, _, model, paths = project
    _labelled_project(model, workspace, paths[:5])
    _tiny_training(model)
    monkeypatch.setattr(model, "use_pretrained", True)
    monkeypatch.setattr(model, "backbone_name", DINO)
    monkeypatch.setattr(model, "seg_decoder", SEG_DECODER_FPN)
    monkeypatch.setattr(model, "finetune_blocks", 0)

    torch.manual_seed(0)
    before = {}
    real_build = DinoBackbone.DinoV2Extractor.__init__

    def recording_init(ext, *a, **k):
        real_build(ext, *a, **k)
        before.update({n: p.detach().clone()
                       for n, p in ext.dino.named_parameters()})
    monkeypatch.setattr(DinoBackbone.DinoV2Extractor, "__init__",
                        recording_init)
    stats, logs = [], []
    model.train_model_core(stats_callback=stats.append,
                           log_callback=logs.append)

    assert model.model.backbone_name == DINO
    assert model.tiling is not None
    after = dict(model.model.backbone.dino.named_parameters())
    assert all(torch.equal(before[n], after[n].cpu()) for n in before)
    setup = next(s for s in stats if s["kind"] == "setup")
    assert setup["backbone"] == (
        "DINOv2-S/14, frozen, multi-scale (FPN) decoder")
    assert any("DINOv2 encoder: frozen" in line for line in logs)
    assert model.ml_model_info()["kind"].startswith("Network (DINOv2-S/14")

    import cv2
    import numpy as np
    image = cv2.cvtColor(cv2.imread(paths[0]), cv2.COLOR_BGR2RGB)
    model.model.eval()
    expected = model._predict_seg_tiled(image)
    model.save_model_file(str(tmp_path), "dino")
    model.seg_decoder = SEG_DECODER_LINEAR             # settings changed
    assert model.load_model_file(str(tmp_path / "dino.pth"))
    assert model.model.backbone_name == DINO
    assert isinstance(model.model.segmentation_head, FPNSegmentationHead)
    got = model._predict_seg_tiled(image)
    assert (expected[0] == got[0]).all()
    assert np.allclose(expected[1], got[1], atol=1e-5)


def test_fine_tuned_blocks_learn_at_a_lower_rate(project, workspace,
                                                 monkeypatch, no_download):
    _, _, model, paths = project
    _labelled_project(model, workspace, paths[:5])
    _tiny_training(model)
    monkeypatch.setattr(model, "use_pretrained", True)
    monkeypatch.setattr(model, "backbone_name", DINO)
    monkeypatch.setattr(model, "seg_decoder", SEG_DECODER_LINEAR)
    monkeypatch.setattr(model, "finetune_blocks", 2)
    monkeypatch.setattr(model, "learning_rate", 0.01)
    groups = []
    real_adamw = torch.optim.AdamW

    def recording_adamw(params, **k):
        opt = real_adamw(params, **k)
        groups.extend(opt.param_groups)
        return opt
    monkeypatch.setattr(torch.optim, "AdamW", recording_adamw)
    stats = []
    model.train_model_core(stats_callback=stats.append)

    ext = model.model.backbone
    assert ext.trainable_blocks == 2
    encoder = {id(p) for p in ext.encoder_parameters()}
    assert len(groups) == 2
    assert groups[0]["initial_lr"] == 0.01
    assert not any(id(p) in encoder for p in groups[0]["params"])
    assert groups[1]["initial_lr"] == pytest.approx(
        0.01 * DinoBackbone.FINETUNE_LR_FACTOR)
    assert {id(p) for p in groups[1]["params"]} == encoder
    setup = next(s for s in stats if s["kind"] == "setup")
    assert "last 2 block(s) fine-tuned, linear decoder" in setup["backbone"]


def test_old_dinov2_linear_setting_by_tiles(project, workspace, monkeypatch,
                                            no_download):
    _, _, model, paths = project
    _labelled_project(model, workspace, paths[:5])
    _tiny_training(model)
    monkeypatch.setattr(model, "use_pretrained", True)
    monkeypatch.setattr(model, "seg_backbone", "dinov2")
    monkeypatch.setattr(model, "backbone_name", "DINOv2-B/14")
    monkeypatch.setattr(model, "finetune_blocks", 3)
    model.train_model_core()
    assert model.probe is None
    assert model.tiling is not None
    # a DINOv2 backbone already chosen is kept
    assert model.model.backbone_name == "DINOv2-B/14"
    assert model.model.seg_decoder == SEG_DECODER_LINEAR
    assert model.model.backbone.trainable_blocks == 0


def test_settings_dialog_reads_the_old_dinov2_linear_setting(project,
                                                             monkeypatch):
    _, view, model, _ = project
    from PyImageLabeling.controller.settings.MLSetting import MLSetting
    from PyImageLabeling.model.Utils import Utils
    real = Utils.load_parameters

    def params():
        data = real()
        data.setdefault("ml", {}).update(seg_backbone="dinov2",
                                         backbone_name="ResNet34",
                                         seg_decoder=SEG_DECODER_FPN,
                                         finetune_blocks=2)
        return data
    monkeypatch.setattr(Utils, "load_parameters", staticmethod(params))
    saved = {}
    monkeypatch.setattr(Utils, "save_parameters",
                        staticmethod(lambda data: saved.update(data)))
    dialog = MLSetting(view.zoomable_graphics_view, model)
    assert dialog.backbone_combo.currentText() == DINO
    assert dialog.decoder_combo.currentData() == SEG_DECODER_LINEAR
    assert dialog.finetune_spinbox.value() == 0
    dialog.accept()
    assert "seg_backbone" not in saved["ml"]
    assert saved["ml"]["backbone_name"] == DINO
    assert saved["ml"]["seg_decoder"] == SEG_DECODER_LINEAR


def test_settings_dialog_dinov2_options(project, monkeypatch):
    _, view, model, _ = project
    from PyImageLabeling.controller.settings.MLSetting import MLSetting
    from PyImageLabeling.model.Utils import Utils
    saved = {}
    monkeypatch.setattr(Utils, "save_parameters",
                        staticmethod(lambda data: saved.update(data)))
    dialog = MLSetting(view.zoomable_graphics_view, model)
    assert dialog.backbone_combo.findText(DINO) >= 0
    dialog.backbone_combo.setCurrentIndex(
        dialog.backbone_combo.findText("ResNet18"))
    assert dialog.finetune_row.isHidden()
    dialog.backbone_combo.setCurrentIndex(dialog.backbone_combo.findText(DINO))
    assert not dialog.finetune_row.isHidden()
    dialog.finetune_spinbox.setValue(3)
    dialog.decoder_combo.setCurrentIndex(
        dialog.decoder_combo.findData(SEG_DECODER_LINEAR))
    dialog.accept()
    assert saved["ml"]["backbone_name"] == DINO
    assert saved["ml"]["finetune_blocks"] == 3
    assert saved["ml"]["seg_decoder"] == SEG_DECODER_LINEAR
