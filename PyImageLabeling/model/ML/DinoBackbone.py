"""DINOv2 as a backbone of the segmentation network (by tiles or not).

DINOv2 is a Vision Transformer trained without labels: it turns an image
into a grid of features, one per 14 x 14 px patch, that already tell apart
the kinds of texture and structure. It has no head of its own: the
decoder of the network (FPN or linear) is trained on top of it.

The encoder is frozen by default, so only the decoder learns, and the last
blocks can be fine-tuned (`set_trainable_blocks`).

What the decoders get:
- `last_layers(x)`: the last 4 layers (as in the linear evaluation of the
  DINOv2 paper), all at 1/14 of the input.
- `pyramid(x)`: 4 levels at 1/3.5, 1/7, 1/14 and 1/28 for the FPN decoder,
  made from layers at 1/4, 1/2, 3/4 and the end of the depth (shallower
  layers keep more of the fine detail), upsampled by transposed
  convolutions or pooled (as in ViTDet and DPT). These adapters are
  trained with the decoder.
"""

import math

import torch
import torch.nn as nn
import torch.nn.functional as F

PATCH = 14

# name in the settings -> (Hugging Face repository, architecture)
DINOV2_BACKBONES = {
    "DINOv2-S/14": ("facebook/dinov2-small",
                    dict(hidden_size=384, num_attention_heads=6)),
    "DINOv2-B/14": ("facebook/dinov2-base",
                    dict(hidden_size=768, num_attention_heads=12)),
}
DINOV2_NAMES = list(DINOV2_BACKBONES)
DEFAULT_DINOV2 = "DINOv2-S/14"

# learning rate of the fine-tuned blocks, relative to the decoder's: the
# full rate would wash out what the encoder learnt
FINETUNE_LR_FACTOR = 0.1


def is_dinov2(backbone_name):
    return backbone_name in DINOV2_BACKBONES


def _dinov2_model(backbone_name, pretrained):
    from transformers import Dinov2Config, Dinov2Model
    repo, arch = DINOV2_BACKBONES[backbone_name]
    if pretrained:
        return Dinov2Model.from_pretrained(repo)
    # the architecture alone (a model file brings the weights): no download
    return Dinov2Model(Dinov2Config(
        num_hidden_layers=12, patch_size=PATCH, image_size=518,
        mlp_ratio=4, layerscale_value=1.0, use_swiglu_ffn=False, **arch))


class DinoV2Extractor(nn.Module):
    """Backbone interface of MLPredictor (`forward`, `pyramid`,
    `last_layers`) around a Hugging Face Dinov2Model."""

    def __init__(self, backbone_name, pretrained):
        super().__init__()
        self.dino = _dinov2_model(backbone_name, pretrained)
        d = self.dino.config.hidden_size
        n = self.dino.config.num_hidden_layers
        self.hidden_dim = d
        self.pyramid_layers = [n // 4, n // 2, 3 * n // 4, n]
        self.linear_layers = [n - 3, n - 2, n - 1, n]
        self.up4 = nn.Sequential(
            nn.ConvTranspose2d(d, d // 2, 2, stride=2),
            nn.BatchNorm2d(d // 2), nn.GELU(),
            nn.ConvTranspose2d(d // 2, d // 4, 2, stride=2))
        self.up8 = nn.ConvTranspose2d(d, d // 2, 2, stride=2)
        self.down32 = nn.MaxPool2d(2)
        self.trainable_blocks = 0
        self.set_trainable_blocks(0)

    # -- training -------------------------------------------------------

    def set_trainable_blocks(self, n):
        """Freeze the encoder but its last `n` transformer blocks (and the
        final norm when n > 0). Returns the number of trainable blocks."""
        blocks = self.dino.encoder.layer
        n = max(0, min(int(n or 0), len(blocks)))
        for p in self.dino.parameters():
            p.requires_grad_(False)
        for block in list(blocks)[len(blocks) - n:]:
            for p in block.parameters():
                p.requires_grad_(True)
        if n:
            for p in self.dino.layernorm.parameters():
                p.requires_grad_(True)
        self.trainable_blocks = n
        return n

    def encoder_parameters(self):
        """Trainable parameters of the encoder (its own learning rate)."""
        return [p for p in self.dino.parameters() if p.requires_grad]

    # -- features -------------------------------------------------------

    def _maps(self, x, layers):
        """Patch features of the given layers, [B, D, H/14, W/14] each
        (the input is resized to a multiple of 14 first)."""
        b, _, h, w = x.shape
        gh, gw = max(1, math.ceil(h / PATCH)), max(1, math.ceil(w / PATCH))
        if (gh * PATCH, gw * PATCH) != (h, w):
            x = F.interpolate(x, size=(gh * PATCH, gw * PATCH),
                              mode="bilinear", align_corners=False)
        frozen = self.trainable_blocks == 0 or not torch.is_grad_enabled()
        with torch.set_grad_enabled(not frozen):
            hidden = self.dino(pixel_values=x,
                               output_hidden_states=True).hidden_states
            maps = []
            for i in layers:
                # hidden[0] = the patch embeddings, hidden[i] = block i
                tokens = self.dino.layernorm(hidden[i])[:, 1:]  # no CLS
                maps.append(tokens.transpose(1, 2)
                            .reshape(b, self.hidden_dim, gh, gw))
        return maps

    def forward(self, x):
        return self._maps(x, [self.dino.config.num_hidden_layers])[0]

    def last_layers(self, x):
        return self._maps(x, self.linear_layers)

    def pyramid(self, x):
        l1, l2, l3, l4 = self._maps(x, self.pyramid_layers)
        return [self.up4(l1), self.up8(l2), l3, self.down32(l4)]
