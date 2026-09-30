"""parameters.json: atomic writes, user values win, corrupt fallback."""
import json
import os

from PyImageLabeling.model.Utils import Utils


def _paths():
    base = Utils.get_base_dir()
    return (os.path.join(base, "parameters.json"),
            os.path.join(base, "default_parameters.json"))


def test_user_values_win_over_defaults():
    pp, _ = _paths()
    backup = pp + ".testbak"
    import shutil
    shutil.copyfile(pp, backup)
    try:
        d = Utils.load_parameters()
        d["sam"]["device"] = "cpu"
        d["zoom"]["max_zoom"] = 42
        Utils.save_parameters(d)
        d2 = Utils.load_parameters()
        assert d2["sam"]["device"] == "cpu"
        assert d2["zoom"]["max_zoom"] == 42
        assert "min_zoom" in d2["zoom"]
    finally:
        shutil.copyfile(backup, pp)
        os.remove(backup)


def test_load_does_not_rewrite():
    pp, _ = _paths()
    before = os.path.getmtime(pp)
    size_before = os.path.getsize(pp)
    for _ in range(20):
        Utils.load_parameters()
    assert os.path.getmtime(pp) == before
    assert os.path.getsize(pp) == size_before


def test_empty_file_recovers():
    pp, _ = _paths()
    backup = pp + ".testbak"
    import shutil
    shutil.copyfile(pp, backup)
    try:
        with open(pp, "w", encoding="utf-8"):
            pass
        assert os.path.getsize(pp) == 0
        d = Utils.load_parameters()
        assert isinstance(d, dict)
        assert os.path.exists(pp + ".corrupt")
    finally:
        for extra in (".corrupt", ".tmp"):
            p = pp + extra
            if os.path.exists(p):
                os.remove(p)
        shutil.copyfile(backup, pp)
        os.remove(backup)


def test_truncated_json_recovers():
    pp, _ = _paths()
    backup = pp + ".testbak"
    import shutil
    shutil.copyfile(pp, backup)
    try:
        with open(pp, "w", encoding="utf-8") as f:
            f.write('{"sam": {"device": "cud')
        d = Utils.load_parameters()
        assert isinstance(d, dict)
    finally:
        for extra in (".corrupt", ".tmp"):
            p = pp + extra
            if os.path.exists(p):
                os.remove(p)
        shutil.copyfile(backup, pp)
        os.remove(backup)


def test_no_tmp_left_behind():
    pp, _ = _paths()
    d = Utils.load_parameters()
    Utils.save_parameters(d)
    assert not os.path.exists(pp + ".tmp")
    assert isinstance(json.load(open(pp, encoding="utf-8")), dict)


def test_ml_verbose_flag_exists_and_defaults_off():
    d = Utils.load_parameters()
    assert d.get("ml", {}).get("verbose") is False
