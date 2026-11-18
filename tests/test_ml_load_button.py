"""The "Load Existing Model" button names a model only when one is loaded.

parameters.json keeps the name of the last model file loaded, but no model is
loaded when the app starts: the button used to say "Loaded: <name>" anyway.
"""
import pytest


def _dialog(view, model, monkeypatch, info=None):
    from PyImageLabeling.controller.settings.MLSetting import MLSetting
    from PyImageLabeling.model.Utils import Utils
    params = Utils.load_parameters()
    params.setdefault("ml", {})["loaded_model_name"] = "an-old-model"
    monkeypatch.setattr(Utils, "load_parameters",
                        staticmethod(lambda: params))
    monkeypatch.setattr(Utils, "save_parameters",
                        staticmethod(lambda data: None))
    if info is not None:
        monkeypatch.setattr(model, "ml_model_info", lambda: info)
    return MLSetting(view.zoomable_graphics_view, model)


def _info(origin, path):
    return {"trained": True, "kind": "ResNet head (resnet18)",
            "origin": origin, "saved": origin == "loaded", "path": path,
            "can_detect": False, "can_segment": True}


@pytest.mark.parametrize("info, text", [
    (None, "Load Existing Model"),                       # nothing in memory
    (_info("trained", None), "Load Existing Model"),     # trained here
    (_info("loaded", "/models/my-model.pth"), "Loaded: my-model"),
])
def test_load_button_says_what_is_in_memory(project, monkeypatch, info, text):
    _, view, model, _ = project
    dialog = _dialog(view, model, monkeypatch, info)
    try:
        assert dialog.load_model_btn.text() == text
    finally:
        dialog.reject()
