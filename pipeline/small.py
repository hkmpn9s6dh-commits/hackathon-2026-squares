"""Brute-force search for small n: random starts, a ladder of box sizes.

For n <= 24 the configuration space is small enough that plain random restarts
beat the continuation heuristic: drop n squares at random inside a box, relax,
project, and keep whatever is legal. The box is swept from the grid side down to
0.85 of it, so a lucky legal state at a smaller radius is found even when the
path there is not continuous.
"""
from __future__ import annotations

import math
import time

import numpy as np

from . import geometry as g
from . import relax as R


def brute(n: int, budget_s: float, seed: int):
    rng = np.random.default_rng(seed)
    grid = g.grid_packing(n)
    best = grid
    best_side = float(g.side_length(*best))
    l0 = float(g.grid_side(n))
    t_end = time.perf_counter() + budget_s
    step = 0
    while time.perf_counter() < t_end:
        step += 1
        frac = 1.0 - 0.15 * ((step % 11) / 10.0)
        radius = l0 * frac
        cx = rng.uniform(0.5, radius - 0.5, n)
        cy = rng.uniform(0.5, radius - 0.5, n)
        th = rng.choice([-math.pi / 4, 0.0, math.pi / 4], n)
        cx, cy, th = R.relax(cx, cy, th, (radius, radius), iters=500, lr=0.3,
                             damp=0.5, w_wall=-1.0, w_angle=0.8)
        cx, cy = R.project(cx, cy, th, (radius, radius))
        if R._is_legal(cx, cy, th):
            side = float(g.side_length(cx, cy, th))
            if side < best_side - 1e-12:
                best, best_side = (cx, cy, th), side
    return best[0], best[1], best[2], float(best_side)
