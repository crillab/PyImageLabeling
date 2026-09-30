"""The paint brush records the full passage, at any drag speed.

Regression: one dab per mouse event left beads on fast strokes (144 px of
holes on a 30 px brush). Dabs are interpolated along the segment, so the
line is solid; the release position is interpolated too.
"""
import time

import pytest
from PyQt6.QtCore import QPointF

from tests.conftest import overlay_alpha


def _drag(model, points, brush="circle"):
    model.start_paint_brush(QPointF(*points[0]))
    for pt in points[1:]:
        model.move_paint_brush(QPointF(*pt))
    model.end_paint_brush()


def _holes(mask, pts):
    """Unpainted samples walking the polyline (a bead gap would be long)."""
    holes = 0
    for i in range(len(pts) - 1):
        x0, y0 = pts[i]
        x1, y1 = pts[i + 1]
        n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for s in range(n + 1):
            t = s / n
            x = int(round(x0 + (x1 - x0) * t))
            y = int(round(y0 + (y1 - y0) * t))
            if mask[y, x] == 0:
                holes += 1
    return holes


@pytest.mark.parametrize("step", [3, 40, 120])
def test_no_gaps_at_any_speed(big_project, step):
    _, _, model, paths = big_project
    model.select_image(paths[0])
    # stay inside the 512x512 image whatever the step
    pts = [(40.0 + i * step, 60.0) for i in range(4)]
    _drag(model, pts)
    assert _holes(overlay_alpha(model) > 0, pts) == 0


def test_diagonal_fast_stroke_is_solid(big_project):
    _, _, model, paths = big_project
    model.select_image(paths[0])
    pts = [(60.0 + i * 30, 60.0 + i * 30) for i in range(6)]
    _drag(model, pts)
    assert _holes(overlay_alpha(model) > 0, pts) == 0


@pytest.mark.parametrize("brush", [
    "circle", "square", "diamond", "star", "triangle",
    "cross", "x", "hexagon", "spray", "soft",
])
def test_all_brushes_cover_the_path(project, fake_params, brush):
    fake_params(**{"paint_brush": {"brush_type": brush}})
    _, _, model, paths = project
    model.select_image(paths[0])
    pts = [(30.0, 90.0), (90.0, 90.0)]
    _drag(model, pts)
    mask = overlay_alpha(model) > 0
    # every brush paints its own centre line
    assert mask[90, 30:91].sum() > 0


def test_fast_move_stays_interactive(project):
    """Smoke perf: a 120 px jump must not stall a frame (16.7 ms)."""
    _, _, model, paths = project
    model.select_image(paths[0])
    model.start_paint_brush(QPointF(60.0, 60.0))
    t0 = time.perf_counter()
    model.move_paint_brush(QPointF(180.0, 180.0))
    dt = (time.perf_counter() - t0) * 1000
    model.end_paint_brush()
    assert dt < 16.7, f"{dt:.1f} ms for one fast jump"
