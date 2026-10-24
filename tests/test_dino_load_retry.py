"""A failed DINOv2 load must not poison the next attempt.

_ensure_dinov2() used to `del` its globals before reloading: when the
download then failed (no network), the names stayed unbound and every later
DINO action raised NameError until the app was restarted.
"""
import pytest
import transformers

from PyImageLabeling.model.SAM import oneshot


def test_failed_load_is_retried_not_nameerror(monkeypatch):
    calls = []

    def offline(*args, **kwargs):
        calls.append(args)
        raise OSError("offline")

    # start from "nothing loaded"; monkeypatch puts back whatever an earlier
    # test cached, so the rest of the suite keeps its backbone
    monkeypatch.setattr(oneshot, "_dino_model", None)
    monkeypatch.setattr(oneshot, "_dino_processor", None)
    monkeypatch.setattr(oneshot, "_dino_key", None)
    monkeypatch.setattr(transformers.AutoImageProcessor, "from_pretrained",
                        offline)

    for _ in range(2):
        with pytest.raises(OSError):
            oneshot._ensure_dinov2(device="cpu")

    assert len(calls) == 2
    assert oneshot._dino_model is None
