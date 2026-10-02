"""Crash-report parsing: torn writes, code hints, breadcrumbs."""


from PyImageLabeling.model.SAM import crash_report as cr
from PyImageLabeling.model.SAM import debug_log


FAULT_LOG = (
    "[2026-01-02 10:00:00] session start | v1.0.13 | py3.13 | qt6.9 | cuda\n"
    "Windows fatal exception: code 0x80010012\n"
    "\n"
    "Thread 0x000062b4 (most recent call first):\n"
    "  <no Python frame>\n"
    "Windows fatal exception: code 0x80010012\n"
    "\n"
    "Thread 0x00005f54 (most recent call first):\n"
    "  <no Python frame>\n"
    "[2026-01-02 11:00:00] session start | v1.0.13 | py3.13 | qt6.9 | cpu\n"
    "[2026-01-02 11:00:01] UNHANDLED:\n"
    '  File "x.py", line 3, in f\n'
    "    boom()\n"
)


def test_parses_each_native_crash():
    crashes = cr.parse_fault_log(FAULT_LOG)
    native = [c for c in crashes if c["kind"] == "native"]
    assert len(native) == 2
    assert all(c["code"] == "80010012" for c in native)
    assert {c["thread"] for c in native} == {"0x000062b4", "0x00005f54"}


def test_python_traceback_is_separate():
    crashes = cr.parse_fault_log(FAULT_LOG)
    py = [c for c in crashes if c["kind"] == "python"]
    assert len(py) == 1
    assert py[0]["session"].startswith("session start")
    assert "boom()" in py[0]["detail"]


def test_sessions_attributed():
    crashes = cr.parse_fault_log(FAULT_LOG)
    first, last = crashes[0], crashes[-1]
    assert "cuda" in first["session"]
    assert "cpu" in last["session"]


def test_torn_lines_are_recovered():
    # faulthandler writes are not atomic: two crashes share one line
    torn = (
        '  File "Windows fatal exception: code 0xC:\\PyImageLabeling\\'
        'controller\\settings\\MLSetting.py8001010e", line \n'
    )
    crashes = cr.parse_fault_log(torn)
    native = [c for c in crashes if c["kind"] == "native"]
    assert len(native) == 1
    assert native[0]["code"] == "8001010e"


def test_no_python_frame_is_reported():
    crashes = cr.parse_fault_log(FAULT_LOG)
    assert "no Python frame" in crashes[0]["traceback"][0]


def test_thread_only_block_merges_into_previous_crash():
    text = ("Windows fatal exception: code 0x8001010e\n"
            "\n"
            "Thread 0x0000127c (most recent call first):\n"
            "  <no Python frame>\n"
            "Thread 0x0000999c (most recent call first):\n"
            "  File \"a.py\", line 2, in g\n")
    crashes = cr.parse_fault_log(text)
    native = [c for c in crashes if c["kind"] == "native"]
    assert len(native) == 1
    assert native[0]["code"] == "8001010e"
    assert any("a.py" in f for f in native[0]["traceback"])


def test_state_breadcrumbs_oldest_first():
    text = ("[2026-01-02 10:00:00] start_paint_brush: size=8\n"
            "[2026-01-02 10:00:01] select_image: a.png\n"
            "[2026-01-02 10:00:02] end_paint_brush: 42 points\n")
    crumbs = cr.parse_state_log(text)
    assert len(crumbs) == 3
    assert "start_paint_brush" in crumbs[0]
    assert "end_paint_brush" in crumbs[-1]


def test_state_log_is_trimmed(tmp_path, monkeypatch):
    monkeypatch.setattr(debug_log, "log_dir", lambda: tmp_path)
    monkeypatch.setattr(debug_log, "STATE_KEEP", 10)
    for i in range(30):
        debug_log.log_state(f"action {i}")
    lines = (tmp_path / "sam_state.log").read_text(
        encoding="utf-8").splitlines()
    assert len(lines) == 10
    assert "action 29" in lines[-1]
    assert "action 20" in lines[0]
    assert "action 19" not in "\n".join(lines)


def test_log_state_never_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(debug_log, "log_dir",
                        lambda: tmp_path / "missing" / "\0bad")
    debug_log.log_state("should not raise")


def test_environment_has_no_question_marks():
    env = cr.environment()
    assert env["app"] != "?"
    assert env["qt"] != "?"
    assert env["python"].startswith("3.")


def test_clear_logs_only_touches_logs(tmp_path, monkeypatch):
    monkeypatch.setattr(debug_log, "log_dir", lambda: tmp_path)
    (tmp_path / "sam_fault.log").write_text("x", encoding="utf-8")
    (tmp_path / "sam_state.log").write_text("y", encoding="utf-8")
    (tmp_path / "sam_debug.log").write_text("keep", encoding="utf-8")
    removed = cr.clear_logs()
    assert len(removed) == 2
    assert (tmp_path / "sam_debug.log").exists()
    assert not (tmp_path / "sam_fault.log").exists()


def test_dialog_renders_report(qapp, app_stack, tmp_path, monkeypatch):
    monkeypatch.setattr(debug_log, "log_dir", lambda: tmp_path)
    monkeypatch.setattr(cr, "log_dir", lambda: tmp_path)
    (tmp_path / "sam_fault.log").write_text(FAULT_LOG, encoding="utf-8")
    (tmp_path / "sam_state.log").write_text(
        "[2026-01-02 10:00:02] end_paint_brush: 42 points\n", encoding="utf-8")
    from PyImageLabeling.controller.settings.CrashReportDialog import (
        CrashReportDialog)
    controller, view, model = app_stack
    dlg = CrashReportDialog(view)
    text = dlg.report_text()
    assert "crash report" in text.lower()
    assert "0x80010012" in text
    assert "RPC_E_INVALID_REFN" in text
    assert "end_paint_brush" in text
    dlg._refresh()
    assert "0x80010012" in dlg.report_text()
    dlg._copy()
    from PyQt6.QtGui import QGuiApplication
    assert "0x80010012" in QGuiApplication.clipboard().text()
    dlg.close()


def test_help_menu_exposes_crash_report(app_stack):
    controller, view, model = app_stack
    labels = []
    for action in view.menuBar().actions():
        if action.menu() is not None:
            labels.append(action.menu().title())
            labels.extend(sub.text() for sub in action.menu().actions())
    assert any("Crash Report" in x for x in labels)


def _use_tmp_logs(tmp_path, monkeypatch):
    monkeypatch.setattr(debug_log, "log_dir", lambda: tmp_path)
    monkeypatch.setattr(cr, "log_dir", lambda: tmp_path)


def test_first_run_baselines_silently(tmp_path, monkeypatch):
    _use_tmp_logs(tmp_path, monkeypatch)
    (tmp_path / "sam_fault.log").write_text(FAULT_LOG, encoding="utf-8")
    has_new, n_new = cr.check_new_crashes()
    assert (has_new, n_new) == (False, 0)
    assert (tmp_path / ".fault_seen").is_file()


def test_appended_crash_is_detected_then_acknowledged(
        tmp_path, monkeypatch):
    _use_tmp_logs(tmp_path, monkeypatch)
    (tmp_path / "sam_fault.log").write_text(FAULT_LOG, encoding="utf-8")
    assert cr.check_new_crashes() == (False, 0)
    with open(tmp_path / "sam_fault.log", "a", encoding="utf-8") as f:
        f.write("Windows fatal exception: code 0x8001010e\n"
                "\n"
                "Thread 0x0000127c (most recent call first):\n"
                "  <no Python frame>\n")
    assert cr.check_new_crashes() == (True, 1)
    cr.save_seen()
    assert cr.check_new_crashes() == (False, 0)


def test_cleared_log_rebaselines_without_nagging(tmp_path, monkeypatch):
    _use_tmp_logs(tmp_path, monkeypatch)
    (tmp_path / "sam_fault.log").write_text(FAULT_LOG, encoding="utf-8")
    assert cr.check_new_crashes() == (False, 0)
    (tmp_path / "sam_fault.log").write_text("", encoding="utf-8")
    assert cr.check_new_crashes() == (False, 0)


def test_missing_fault_log_is_quiet(tmp_path, monkeypatch):
    _use_tmp_logs(tmp_path, monkeypatch)
    assert cr.check_new_crashes() == (False, 0)


def test_all_events_writes_breadcrumb(tmp_path, monkeypatch, app_stack):
    _use_tmp_logs(tmp_path, monkeypatch)
    controller, view, model = app_stack
    controller.all_events("zoom_plus")
    crumbs = cr.parse_state_log()
    assert any("zoom_plus" in c for c in crumbs)