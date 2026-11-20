"""Grow-then-squeeze: build a packing for every n by adding one square at a time.

The score is a sum over n, and the packings for n and n+1 are nearly the same
object. So instead of solving 1000 independent problems, we walk up: take the
best packing for n-1, drop a new square into the emptiest corner, let the soft
relaxation settle it, then squeeze. This is the classic repeated-insertion
heuristic; it is cheap because every step starts from a legal state.

Deterministic: the only randomness is the RNG seeded per n, and the insertion
point is chosen by a rule (farthest empty corner), not by sampling.
"""
from __future__ import annotations

import math
import time

import numpy as np

from . import geometry as g
from . import relax as R


def _insertion_point(cx, cy, th):
    """The corner of the current bounding box that is farthest from any square."""
    half = R.half_extent(th)
    x0, x1 = float(np.min(cx - half)), float(np.max(cx + half))
    y0, y1 = float(np.min(cy - half)), float(np.max(cy + half))
    corners = [(x0, y0), (x1, y0), (x0, y1), (x1, y1)]
    best, best_d = corners[0], -1.0
    for px, py in corners:
        d = float(np.min((cx - px) ** 2 + (cy - py) ** 2)) if len(cx) else 1e9
        if d > best_d:
            best, best_d = (px, py), d
    return best


def _squeeze(cx, cy, th, budget_s, rng, delta0=0.004, legal_tol=1e-9):
    """Compress a legal packing as far as the time budget allows."""
    t_end = time.perf_counter() + budget_s
    cur = (cx.copy(), cy.copy(), th.copy(), float(g.side_length(cx, cy, th)))
    delta = delta0
    fails = 0
    while time.perf_counter() < t_end and fails < 10:
        tx, ty = R._rescale(cur[0], cur[1], 1.0 - delta)
        nx, ny, nth = R.relax(tx, ty, cur[2], None, iters=80, lr=0.35, damp=0.6, w_angle=0.6)
        if R._is_legal(nx, ny, nth, legal_tol):
            side = float(g.side_length(nx, ny, nth))
            if side < cur[3] - 1e-12:
                cur = (nx, ny, nth, side)
                fails = 0
                continue
        fails += 1
        delta = max(delta * 0.5, 1e-5)
        if fails in (3, 6):
            sx, sy, sth = R._shake(cur[0], cur[1], cur[2], rng, strength=0.6)
            bx, by = R._rescale(sx, sy, 1.0)
            rx, ry, rth = R.relax(bx, by, sth, None, iters=90, lr=0.3, damp=0.5, w_angle=0.6)
            if R._is_legal(rx, ry, rth, legal_tol) and float(g.side_length(rx, ry, rth)) < cur[3] - 1e-12:
                cur = (rx, ry, rth, float(g.side_length(rx, ry, rth)))
                fails = 0
    return cur


def grow(n_max: int, per_n_budget=0.06, seed=20260131, start=None, log=None):
    """Return {n: (cx, cy, th, side)} for n = 1..n_max, grown one square at a time."""
    rng = np.random.default_rng(seed)
    out: dict[int, tuple] = {}
    if start is None:
        cx = np.array([0.5])
        cy = np.array([0.5])
        th = np.array([0.0])
    else:
        cx, cy, th = start[0].copy(), start[1].copy(), start[2].copy()
    n0 = len(cx)
    out[n0] = (cx.copy(), cy.copy(), th.copy(), float(g.side_length(cx, cy, th)))
    for n in range(n0 + 1, n_max + 1):
        px, py = _insertion_point(cx, cy, th)
        # push the new square just outside the corner so that it lands *in* the
        # notch rather than on top of an existing square
        half = R.half_extent(th)
        x0, x1 = float(np.min(cx - half)), float(np.max(cx + half))
        y0, y1 = float(np.min(cy - half)), float(np.max(cy + half))
        # grow the box by 0.5 in the direction of the chosen corner, then place
        dx = 0.5 if abs(px - x1) < 1e-9 else -0.5
        dy = 0.5 if abs(py - y1) < 1e-9 else -0.5
        if dx < 0:
            cx = cx - dx
            px = px + dx
        if dy < 0:
            cy = cy - dy
            py = py + dy
        cx = np.append(cx, px + dx * 0.5)
        cy = np.append(cy, py + dy * 0.5)
        th = np.append(th, 0.0)
        cur = _squeeze(cx, cy, th, per_n_budget, rng)
        cx, cy, th = cur[0], cur[1], cur[2]
        out[n] = cur
        if log is not None and (n % 50 == 0 or n < 12):
            log(f"  n={n}: L={cur[3]:.6f} (grid {g.grid_side(n)})")
    return out
