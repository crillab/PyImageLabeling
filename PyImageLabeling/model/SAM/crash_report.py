"""Reads the SAM logs and turns them into a pasteable bug report.

A native crash (Windows fatal exception) leaves no Python frame, so the only
usable context is what was written just before it: the session header in the
fault log and the breadcrumb ring in the state log.
"""

import os
import platform
import re
import sys
from pathlib import Path

from PyImageLabeling.model.SAM.debug_log import (
    FAULT_NAME, STATE_NAME, log_dir, log_path,
)

FATAL_RE = re.compile(
    r"Windows fatal exception:\s*code\s*0x[^\"\s]*?([0-9a-fA-F]{8})(?=[\"\s]|$)")
THREAD_RE = re.compile(r"Thread (0x[0-9a-fA-F]{4,16})\b")
STAMP_RE = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]\s*(.*)$")
NO_FRAME_RE = re.compile(r"no Python frame")
TORN_RE = re.compile(r"Windows fatal exception:")
SEEN_NAME = ".fault_seen"


def _read(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def fault_signature():
    """Size, mtime and native-crash count of the fault log (or None)."""
    try:
        st = Path(log_path(FAULT_NAME)).stat()
        n = sum(1 for c in parse_fault_log() if c["kind"] == "native")
        return f"{st.st_size}:{int(st.st_mtime)}:{n}"
    except Exception:
        return None


def save_seen(sig=None):
    """Remember the fault log state so the next launch can spot new crashes."""
    try:
        if sig is None:
            sig = fault_signature()
        if sig is not None:
            (log_dir() / SEEN_NAME).write_text(sig, encoding="utf-8")
    except Exception:
        pass


def check_new_crashes():
    """(has_new, n_new): crashes recorded since the last acknowledged launch.

    First run with this feature baselines silently instead of nagging about
    years of history; a cleared/rotated log re-baselines too.
    """
    try:
        sig = fault_signature()
        if sig is None:
            return False, 0
        try:
            old = (log_dir() / SEEN_NAME).read_text(
                encoding="utf-8").strip()
        except Exception:
            old = None
        if not old:
            save_seen(sig)
            return False, 0
        try:
            old_size, _, old_n = old.split(":")
            size, _, n = sig.split(":")
            old_size, old_n, size, n = (
                int(old_size), int(old_n), int(size), int(n))
        except Exception:
            save_seen(sig)
            return False, 0
        if size < old_size:
            save_seen(sig)
            return False, 0
        new = n - old_n
        if size == old_size or new <= 0:
            return False, 0
        return True, new
    except Exception:
        return False, 0


def _unsplice(text):
    """faulthandler writes are not atomic: two crashes can land on one line.

    Re-split those lines so each fatal marker starts a fresh logical line and
    the following ``code 0x........`` fragment is recovered.
    """
    out = []
    for raw in text.splitlines():
        parts = raw.split("Windows fatal exception:")
        if len(parts) == 1:
            out.append(raw)
            continue
        out.append(parts[0])
        for p in parts[1:]:
            body = p.lstrip()
            m = re.match(r"code\s*0x", body)
            if m:
                out.append("Windows fatal exception: " + body)
                continue
            out.append("Windows fatal exception: code 0x" + body)
    return out


def parse_fault_log(text=None):
    """Split the fault log into crashes, each with the session that owns it."""
    text = _read(log_path(FAULT_NAME)) if text is None else text
    session = None
    crashes = []
    cur = None
    for raw in _unsplice(text):
        line = raw.strip()
        if not line:
            continue
        indented = raw[:1] in (" ", "\t")
        m = STAMP_RE.match(line)
        if m and m.group(2).startswith("session start"):
            session = m.group(2)
            continue
        if m and m.group(2).startswith("UNHANDLED"):
            if cur:
                crashes.append(cur)
            cur = {"kind": "python", "code": None, "thread": None,
                   "session": session, "ts": m.group(1),
                   "detail": m.group(2), "traceback": []}
            continue
        if cur and (line.startswith("File ") or indented
                    or NO_FRAME_RE.search(line)):
            cur["traceback"].append(line)
            if cur["kind"] == "python":
                cur["detail"] += "\n" + line
            continue
        f = FATAL_RE.search(line)
        t = THREAD_RE.match(line)
        if f or t or line.startswith("Current thread"):
            if cur:
                crashes.append(cur)
            cur = {"kind": "native", "code": None, "thread": None,
                   "session": session, "ts": None, "detail": line,
                   "traceback": []}
            if f:
                cur["code"] = f.group(1).lower()
            if t:
                cur["thread"] = t.group(1).lower()
            continue
        if cur:
            cur["traceback"].append(line)
    if cur:
        crashes.append(cur)
    return _merge_and_classify(crashes)


def _merge_and_classify(crashes):
    """Thread-only blocks belong to the crash above them; anything with neither
    code nor thread is a torn write, not an attributable crash."""
    out = []
    garbled = 0
    for c in crashes:
        if c["kind"] != "native":
            out.append(c)
            continue
        if c["code"] is None and c["thread"] is None:
            garbled += len(c["traceback"]) or 1
            continue
        if c["code"] is None and out and out[-1]["kind"] == "native":
            prev = out[-1]
            for frame in c["traceback"]:
                prev["traceback"].append(frame)
            if prev["thread"] is None:
                prev["thread"] = c["thread"]
            continue
        out.append(c)
    if garbled:
        out.append({"kind": "garbled", "code": None, "thread": None,
                    "session": None, "ts": None,
                    "detail": f"{garbled} torn lines", "traceback": []})
    return out


def parse_state_log(text=None, limit=25):
    """Last breadcrumbs, oldest first."""
    text = _read(log_path(STATE_NAME)) if text is None else text
    out = []
    for raw in text.splitlines():
        m = STAMP_RE.match(raw.strip())
        if m:
            out.append(f"{m.group(1)}  {m.group(2)}")
    return out[-limit:]


def environment():
    env = {
        "app": "?", "python": sys.version.split()[0],
        "platform": f"{platform.system()} {platform.release()}",
        "qt": "?", "device": "?", "torch": "?",
    }
    try:
        from PyImageLabeling.model.Utils import Utils
        env["app"] = "v" + Utils.get_version()
    except Exception:
        pass
    try:
        from PyQt6.QtCore import QT_VERSION_STR
        env["qt"] = QT_VERSION_STR
    except Exception:
        pass
    try:
        import torch
        env["torch"] = torch.__version__
        env["device"] = ("cuda" if torch.cuda.is_available() else "cpu")
        if torch.cuda.is_available():
            env["device"] += " " + torch.cuda.get_device_name(0)
    except Exception:
        pass
    return env


"""Text summary of the crash logs, ready to paste into a bug report."""

CODE_HINTS = {
    "80010012": "RPC_E_INVALID_REFN - COM marshalling rejected",
    "8001010e": "RPC_E_INVALID_REFN - COM call rejected on this thread",
}


def build_report():
    crashes = parse_fault_log()
    state = parse_state_log()
    env = environment()
    native = [c for c in crashes if c["kind"] == "native"]
    python = [c for c in crashes if c["kind"] == "python"]
    torn = [c for c in crashes if c["kind"] == "garbled"]
    codes = {}
    for c in native:
        codes[c["code"] or "?"] = codes.get(c["code"] or "?", 0) + 1
    code_hint = CODE_HINTS
    threads = sorted({c["thread"] for c in native if c["thread"]})
    sessions = []
    for c in crashes:
        if c["session"] and (not sessions or sessions[-1] != c["session"]):
            sessions.append(c["session"])

    lines = ["=== PyImageLabeling crash report ==="]
    for k in ("app", "python", "platform", "qt", "torch", "device"):
        lines.append(f"{k}: {env[k]}")
    lines.append(f"logs: {log_dir()}")
    lines.append("")
    lines.append(
        f"crashes: {len(native)} native, {len(python)} python "
        f"({len(state)} recent actions logged)")
    if codes:
        lines.append("native codes: " + ", ".join(
            f"0x{k} x{v}" for k, v in sorted(
                codes.items(), key=lambda kv: -kv[1])))
        for k in sorted(codes, key=lambda k: -codes[k]):
            if k in code_hint:
                lines.append(f"  0x{k}: {code_hint[k]}")
    if torn:
        lines.append(f"torn writes: {torn[0]['detail']} (crashes collided "
                     "in the log, codes may be undercounted)")
    if threads:
        lines.append("threads: " + ", ".join(threads))
    if crashes:
        lines.append("")
        lines.append("last crash:")
        last = crashes[-1]
        if last["ts"]:
            lines.append(f"  at {last['ts']}")
        lines.append(f"  kind: {last['kind']}")
        if last["code"]:
            lines.append(f"  code: 0x{last['code']}")
        if last["thread"]:
            lines.append(f"  thread: {last['thread']}")
        if last["session"]:
            lines.append(f"  session: {last['session']}")
        tb = [x for x in last["traceback"] if x.strip()][:6]
        if tb:
            lines.append("  frames:")
            lines.extend(f"    {x}" for x in tb)
        elif last["kind"] == "native":
            lines.append("  frames: none (crash below the Python layer)")
    if state:
        lines.append("")
        lines.append("recent actions before the crash:")
        lines.extend(f"  {x}" for x in state)
    else:
        lines.append("")
        lines.append("recent actions before the crash: none recorded "
                     "(state log empty)")
    if sessions:
        lines.append("")
        lines.append("sessions in fault log: " + str(len(sessions)))
    lines.append("")
    lines.append(f"fault log: {log_path(FAULT_NAME)}")
    lines.append(f"state log: {log_path(STATE_NAME)}")
    return "\n".join(lines)


def clear_logs():
    """Delete the crash logs after the user copied what they needed."""
    removed = []
    for name in (FAULT_NAME, STATE_NAME):
        try:
            p = Path(log_path(name))
            if p.is_file():
                p.unlink()
                removed.append(str(p))
        except Exception:
            pass
    return removed


def open_log_folder():
    d = log_dir()
    try:
        os.startfile(str(d)) if sys.platform == "win32" else None
    except Exception:
        return None
    return str(d)