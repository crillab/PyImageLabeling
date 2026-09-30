"""File logging + memory telemetry for SAM runs.

Everything here is best-effort and never raises: logging must not break
the app. Logs go to ~/.pyimagelabeling/ (writable even for packaged exes).
"""

import os
import sys
import time
from pathlib import Path

LOG_NAME = "sam_debug.log"
STATE_NAME = "sam_state.log"
FAULT_NAME = "sam_fault.log"
STATE_KEEP = 400


def log_dir():
    d = Path.home() / ".pyimagelabeling"
    try:
        d.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return d


def log_path(name=LOG_NAME):
    return str(log_dir() / name)


def log_event(msg, name=LOG_NAME):
    try:
        _rotate(name)
        with open(log_path(name), "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception:
        pass


def _rotate(name=LOG_NAME, max_bytes=5 * 1024 * 1024):
    try:
        p = Path(log_path(name))
        if p.is_file() and p.stat().st_size > max_bytes:
            bak = p.with_suffix(p.suffix + ".prev")
            try:
                if bak.is_file():
                    bak.unlink()
            except Exception:
                pass
            p.rename(bak)
    except Exception:
        pass


def log_state(msg, name=STATE_NAME):
    """Breadcrumb of what the app was doing. Native crashes leave no Python
    frame, so this ring of recent actions is the only attribution signal."""
    try:
        _rotate(name, 512 * 1024)
        line = str(msg).replace("\n", " ")[:300]
        with open(log_path(name), "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {line}\n")
        _trim_state(name)
    except Exception:
        pass


def _trim_state(name=STATE_NAME, keep=None):
    keep = STATE_KEEP if keep is None else keep
    try:
        p = Path(log_path(name))
        if not p.is_file():
            return
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        if len(lines) <= keep:
            return
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text("\n".join(lines[-keep:]) + "\n", encoding="utf-8")
        tmp.replace(p)
    except Exception:
        pass


def session_header(name=FAULT_NAME):
    """Tag the fault log with the session environment, so each faulthandler
    dump can be attributed to a run (version, python, Qt, device)."""
    try:
        parts = [f"v{_app_version()}", f"py{sys.version.split()[0]}",
                 f"qt{_qt_version()}"]
        try:
            import torch
            parts.append("cuda" if torch.cuda.is_available() else "cpu")
        except Exception:
            parts.append("torch=n/a")
        with open(log_path(name), "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] session start "
                    f"| {' | '.join(parts)}\n")
    except Exception:
        pass


def _app_version():
    try:
        from PyImageLabeling.model.Utils import Utils
        return Utils.get_version()
    except Exception:
        return "?"


def _qt_version():
    try:
        from PyQt6.QtCore import QT_VERSION_STR
        return QT_VERSION_STR
    except Exception:
        return "?"


def total_ram_mb():
    try:
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes

            class MS(ctypes.Structure):
                _fields_ = [
                    ("dwLength", wintypes.DWORD),
                    ("dwMemoryLoad", wintypes.DWORD),
                    ("ullTotalPhys", ctypes.c_uint64),
                    ("ullAvailPhys", ctypes.c_uint64),
                    ("ullTotalPageFile", ctypes.c_uint64),
                    ("ullAvailPageFile", ctypes.c_uint64),
                    ("ullTotalVirtual", ctypes.c_uint64),
                    ("ullAvailVirtual", ctypes.c_uint64),
                    ("ullAvailExtendedVirtual", ctypes.c_uint64),
                ]

            k32 = ctypes.WinDLL("kernel32", use_last_error=True)
            st = MS()
            st.dwLength = ctypes.sizeof(MS)
            k32.GlobalMemoryStatusEx.restype = wintypes.BOOL
            k32.GlobalMemoryStatusEx.argtypes = [ctypes.POINTER(MS)]
            if k32.GlobalMemoryStatusEx(ctypes.byref(st)):
                return int(st.ullTotalPhys // (1024 * 1024))
    except Exception:
        pass
    return -1


def _rss_mb():
    try:
        if sys.platform != "win32":
            import resource
            return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024
        import ctypes
        from ctypes import wintypes

        class PMC(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE, ctypes.POINTER(PMC), wintypes.DWORD]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        pmc = PMC()
        pmc.cb = ctypes.sizeof(PMC)
        h = k32.GetCurrentProcess()
        if psapi.GetProcessMemoryInfo(h, ctypes.byref(pmc), pmc.cb):
            return int(pmc.WorkingSetSize // (1024 * 1024))
    except Exception:
        pass
    return -1


def mem_stats():
    """One-line summary: RAM + CUDA. Never raises."""
    try:
        rss = _rss_mb()
        try:
            import torch
            if torch.cuda.is_available():
                alloc = torch.cuda.memory_allocated() // (1024 * 1024)
                reserved = torch.cuda.memory_reserved() // (1024 * 1024)
                total = (torch.cuda.get_device_properties(0).total_memory
                         // (1024 * 1024))
                return (f"RSS={rss}MB "
                        f"VRAM alloc={alloc}MB reserved={reserved}MB "
                        f"total={total}MB")
        except Exception:
            pass
        return f"RSS={rss}MB VRAM=n/a"
    except Exception:
        return "mem_stats failed"


def install_excepthook():
    """Log unhandled Python exceptions (Qt slots print to stderr only).

    Also enables faulthandler so native crashes (segfaults) leave a
    C-level stack trace in the log file.
    """
    try:
        import faulthandler
        session_header()
        fh = open(log_path(FAULT_NAME), "a", encoding="utf-8")
        faulthandler.enable(file=fh)
    except Exception:
        pass
    prev = sys.excepthook

    def _hook(t, v, tb):
        try:
            import traceback
            log_event("UNHANDLED:\n"
                      + "".join(traceback.format_exception(t, v, tb)))
        except Exception:
            pass
        try:
            prev(t, v, tb)
        except Exception:
            pass

    sys.excepthook = _hook


def vram_pressure():
    """Fraction of total VRAM currently reserved (0.0 if unknown)."""
    try:
        import torch
        if not torch.cuda.is_available():
            return 0.0
        reserved = torch.cuda.memory_reserved()
        total = torch.cuda.get_device_properties(0).total_memory
        if total > 0:
            return float(reserved) / float(total)
    except Exception:
        pass
    return 0.0


_hang_file = None


def arm_hang_dump(timeout_sec=90, name=LOG_NAME):
    """If the process hangs longer than timeout, dump all thread stacks.

    Survives user-kill scenarios: the dump is written while still hung.
    Call cancel_hang_dump() on clean exit.
    """
    global _hang_file
    try:
        cancel_hang_dump()
        import faulthandler
        _hang_file = open(log_path(name), "a", encoding="utf-8")
        _hang_file.write(
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] hang-watch armed "
            f"({timeout_sec}s)\n")
        _hang_file.flush()
        faulthandler.dump_traceback_later(timeout_sec, file=_hang_file)
    except Exception:
        pass


def cancel_hang_dump():
    global _hang_file
    try:
        import faulthandler
        faulthandler.cancel_dump_traceback_later()
    except Exception:
        pass
    try:
        if _hang_file is not None:
            _hang_file.write(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] hang-watch off\n")
            _hang_file.flush()
            _hang_file.close()
    except Exception:
        pass
    _hang_file = None
