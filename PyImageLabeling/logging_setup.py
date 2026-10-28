"""Central logging for PyImageLabeling.

Replaces the raw print() conversation: same console visibility by
default, but with levels, module attribution and timestamps. Handlers
write to stderr (stdout stays reserved for real program output, and
tests that assert console silence on stdout keep working).

The level can be raised/lowered with the PYIMAGELABELING_LOG_LEVEL
environment variable (DEBUG, INFO, WARNING, ERROR — default INFO).
All application modules get their logger through get_logger("slug");
they must never call logging.getLogger() directly, so reconfiguration
of the attached handler stays in one place.

import-only-stdlib on purpose: it must be importable from anywhere in
the package, including from partially-initialized package state.
"""
import logging
import os
import sys

ROOT_NAME = "pyimagelabeling"
_configured = False


def _level_from_env():
    raw = os.environ.get("PYIMAGELABELING_LOG_LEVEL", "INFO").upper()
    return getattr(logging, raw, logging.INFO)


def _configure():
    """Attach one stderr handler to the package root logger (one-shot)."""
    global _configured
    if _configured:
        return
    root = logging.getLogger(ROOT_NAME)
    root.setLevel(_level_from_env())
    if sys.stderr is not None:          # None in frozen windowed apps
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(
            "[%(asctime)s] %(levelname)s %(name)s: %(message)s",
            datefmt="%H:%M:%S"))
        root.addHandler(handler)
    else:
        root.addHandler(logging.NullHandler())
    _configured = True


def get_logger(slug: str) -> logging.Logger:
    """Logger namespaced under 'pyimagelabeling.<slug>'.

    Configures the package root logger on first use, so calling this at
    import time from any module is safe and cheap.
    """
    _configure()
    return logging.getLogger(f"{ROOT_NAME}.{slug}")
