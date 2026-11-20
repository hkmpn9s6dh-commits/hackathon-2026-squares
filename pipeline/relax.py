"""Soft relaxation: the only search in this project.

A packing is legal when no two unit squares overlap; the score only cares about
the container side L. So the search is a pressure cooker: shrink the box by a
hair, let the squares repel each other through a soft penalty (overlaps are
allowed *during* the search, never in the result), and keep the state only if it
settles legally. One non-local move — tilt a single square by 45 degrees — is
what lets a mostly-full row fold into the space above it.

Everything is numpy and deterministic given the seed: no gradients from a
framework, no external solver, no random thread scheduling.
"""
from __future__ import annotations

import math
import time

import numpy as np

from . import geometry as g


def half_extent(th: np.ndarray) -> np.ndarray:
    return 0.5 * (np.abs(np.cos(th)) + np.abs(np.sin(th)))


def _pair_terms(cx, cy, th, pairs):
    """Per-pair: signed gap, chosen axis direction, and angle sensitivities."""
    i, j = pairs[:, 0], pairs[:, 1]
    dx, dy = cx[j] - cx[i], cy[j] - cy[i]
    ci, si = np.cos(th[i]), np.sin(th[i])
    cj, sj = np.cos(th[j]), np.sin(th[j])
    axes = (
        (ci, si, 0), (-si, ci, 0),
        (cj, sj, 1), (-sj, cj, 1),
    )
    best_gap = None
    best = None
    for ax, ay, owner in axes:
        proj = np.abs(dx * ax + dy * ay)
        # half extents of both squares along (ax, ay)
        hi = 0.5 * (np.abs(ax * ci + ay * si) + np.abs(-ax * si + ay * ci))
        hj = 0.5 * (np.abs(ax * cj + ay * sj) + np.abs(-ax * sj + ay * cj))
        gap = proj - hi - hj
        if best_gap is None:
            best_gap, best = gap, (ax, ay, owner, proj)
        else:
            better = gap > best_gap
            best_gap = np.where(better, gap, best_gap)
            best = tuple(np.where(better, new, old) for new, old in zip((ax, ay, owner, proj), best))
    return best_gap, best


def relax(cx, cy, th, box=None, iters=200, lr=0.25, margin=0.0, damp=0.6, w_wall=1.0,
          w_angle=1.0, rebuild_every=8, tol_ang=0.35, w_center=0.0):
    """Damped gradient flow on the soft overlap + wall energy. Mutates copies."""
    cx, cy, th = cx.copy(), cy.copy(), th.copy()
    n = len(cx)
    if n == 0:
        return cx, cy, th
    vx = np.zeros(n)
    vy = np.zeros(n)
    vth = np.zeros(n)
    pairs = g.neighbour_pairs(cx, cy, reach=2.4)
    for it in range(iters):
        if len(pairs) and it % rebuild_every == 0:
            pairs = g.neighbour_pairs(cx, cy, reach=2.4)
        fx = np.zeros(n)
        fy = np.zeros(n)
        fth = np.zeros(n)
        if len(pairs):
            gap, (ax, ay, owner, proj) = _pair_terms(cx, cy, th, pairs)
            pen = np.maximum(margin - gap, 0.0)
            if pen.any():
                i, j = pairs[:, 0], pairs[:, 1]
                sgn = np.sign(np.abs(proj) + 1e-300) * np.sign(
                    (cx[j] - cx[i]) * ax + (cy[j] - cy[i]) * ay + 1e-300)
                ux, uy = sgn * ax, sgn * ay
                fx_i = -pen * ux
                fy_i = -pen * uy
                np.add.at(fx, i, fx_i)
                np.add.at(fy, i, fy_i)
                np.add.at(fx, j, -fx_i)
                np.add.at(fy, j, -fy_i)
                # d(gap)/d(theta_i)
                ci, si = np.cos(th[i]), np.sin(th[i])
                cj, sj = np.cos(th[j]), np.sin(th[j])
                # owner == 0 -> axis belongs to square i
                own_i = owner < 0.5
                # derivative of |d.a| wrt theta_i (only when a belongs to i)
                dproj_i = np.where(own_i, sgn * ((cx[j] - cx[i]) * (-si) + (cy[j] - cy[i]) * ci), 0.0)
                dproj_j = np.where(~own_i, sgn * ((cx[j] - cx[i]) * (-sj) + (cy[j] - cy[i]) * cj), 0.0)
                # derivative of -h_i wrt theta_i (only when a belongs to j)
                dhi = 0.5 * (np.sign(ax * ci + ay * si) * (ax * (-si) + ay * ci)
                             + np.sign(-ax * si + ay * ci) * (-ax * ci - ay * si))
                dhj = 0.5 * (np.sign(ax * cj + ay * sj) * (ax * (-sj) + ay * cj)
                             + np.sign(-ax * sj + ay * cj) * (-ax * cj - ay * sj))
                gthi = np.where(own_i, dproj_i, -dhi)
                gthj = np.where(own_i, -dhj, dproj_j)
                np.add.at(fth, i, pen * gthi)
                np.add.at(fth, j, pen * gthj)
        # optional hard walls, or a weak spring towards the centroid so that a
        # wall-free relaxation does not diffuse
        if box is not None:
            half = half_extent(th)
            bx, by = box if isinstance(box, tuple) else (box, box)
            if w_wall < 0:      # hard projection: the box wins, overlaps must move
                cx = np.clip(cx, half, bx - half)
                cy = np.clip(cy, half, by - half)
            else:
                fx += w_wall * (np.maximum(half - cx, 0.0) - np.maximum(cx + half - bx, 0.0))
                fy += w_wall * (np.maximum(half - cy, 0.0) - np.maximum(cy + half - by, 0.0))
        if w_center:
            fx += w_center * (cx.mean() - cx)
            fy += w_center * (cy.mean() - cy)
        vx = damp * vx + lr * fx
        vy = damp * vy + lr * fy
        vth = damp * vth + lr * w_angle * fth
        vth = np.clip(vth, -tol_ang, tol_ang)
        cx = cx + vx
        cy = cy + vy
        th = th + vth
    return cx, cy, th


def _rescale(cx, cy, factor):
    mx = 0.5 * (cx.min() + cx.max())
    my = 0.5 * (cy.min() + cy.max())
    return mx + (cx - mx) * factor, my + (cy - my) * factor


def _is_legal(cx, cy, th, tol=1e-9) -> bool:
    n = len(cx)
    if n < 2:
        return True
    pairs = g.neighbour_pairs(cx, cy, reach=2.4)
    if len(pairs) == 0:
        pairs = g.all_pairs(n) if n <= 128 else pairs
        if len(pairs) == 0:
            return True
    return g.min_gap(cx, cy, th, pairs) >= -tol


def project(cx, cy, th, box=None, sweeps=60, tol=1e-12):
    """Hard SAT projection: push every overlapping pair apart by its exact depth.

    The soft relaxation converges linearly and stalls at ~1e-3; this finishes the
    job in a handful of sweeps so that a candidate can be tested at 1e-9.
    """
    n = len(cx)
    if n < 2:
        return cx, cy
    cx, cy = cx.copy(), cy.copy()
    for _ in range(sweeps):
        pairs = g.neighbour_pairs(cx, cy, reach=2.4)
        if len(pairs) == 0:
            break
        i, j = pairs[:, 0], pairs[:, 1]
        dx, dy = cx[j] - cx[i], cy[j] - cy[i]
        best_gap, bx, by = None, None, None
        for t in (th[i], th[j]):
            c, s = np.cos(t), np.sin(t)
            for ax, ay in ((c, s), (-s, c)):
                proj_ = np.abs(dx * ax + dy * ay)
                hi = 0.5 * (np.abs(ax * np.cos(th[i]) + ay * np.sin(th[i]))
                            + np.abs(-ax * np.sin(th[i]) + ay * np.cos(th[i])))
                hj = 0.5 * (np.abs(ax * np.cos(th[j]) + ay * np.sin(th[j]))
                            + np.abs(-ax * np.sin(th[j]) + ay * np.cos(th[j])))
                gap = proj_ - hi - hj
                if best_gap is None:
                    best_gap, bx, by = gap, ax, ay
                else:
                    better = gap > best_gap
                    best_gap = np.where(better, gap, best_gap)
                    bx = np.where(better, ax, bx)
                    by = np.where(better, ay, by)
        sgn = np.sign(dx * bx + dy * by + 1e-300)
        pen = np.maximum(-best_gap, 0.0)
        if not pen.any():
            break
        ux, uy = sgn * bx, sgn * by
        np.add.at(cx, i, -pen * ux * 0.5)
        np.add.at(cy, i, -pen * uy * 0.5)
        np.add.at(cx, j, +pen * ux * 0.5)
        np.add.at(cy, j, +pen * uy * 0.5)
        if box is not None:
            half = half_extent(th)
            bxx, byy = box if isinstance(box, tuple) else (box, box)
            cx = np.clip(cx, half, bxx - half)
            cy = np.clip(cy, half, byy - half)
    return cx, cy


def _shake(cx, cy, th, rng, strength=1.0):
    """Basin hop: tilt a few squares and nudge the rest, then let the cook settle."""
    n = len(cx)
    cx = cx + 0.03 * strength * rng.standard_normal(n)
    cy = cy + 0.03 * strength * rng.standard_normal(n)
    k = max(1, int(round(0.08 * n)))
    idx = rng.choice(n, size=min(k, n), replace=False)
    th = th.copy()
    th[idx] = th[idx] + rng.choice([-1.0, 1.0], size=len(idx)) * (math.pi / 4)
    return cx, cy, th


def pack(n: int, budget_s: float, seed: int, restarts: int | None = None,
         verbose: bool = False):
    """Best legal packing found for n unit squares within the time budget.

    The container is a box and only the binding axis is squeezed: L is the
    larger of width and height, so shrinking the shorter axis buys nothing, and
    the free axis is left at the full side length so that squeezed rows have
    somewhere to spread. Walls are hard projections, overlaps are resolved by
    soft repulsion followed by an exact projection pass, and the only non-local
    move is a 45 degree tilt of a random square.

    restarts=-2 mixes random starts with grid starts; anything else starts from
    the grid. `best` is only ever replaced by a *legal* packing.
    """
    if n <= 1:
        cx, cy, th = g.grid_packing(max(n, 1))
        return cx, cy, th, float(n)
    rng = np.random.default_rng(seed)
    grid = g.grid_packing(n)
    best = grid
    best_side = float(g.side_length(*best))
    mixed = restarts == -2
    t_end = time.perf_counter() + budget_s
    while time.perf_counter() < t_end:
        if mixed and rng.random() < 0.5:
            s0 = g.grid_side(n) * 1.02
            cur = (rng.uniform(0.5, s0 - 0.5, n), rng.uniform(0.5, s0 - 0.5, n),
                   rng.choice([-math.pi / 4, 0.0, math.pi / 4], n))
        else:
            cur = (best[0].copy(), best[1].copy(), best[2].copy())
        delta = 0.01
        guard = 0
        while time.perf_counter() < t_end and delta > 3e-4 and guard < 400:
            guard += 1
            w, h = g.extents(*cur)
            if h >= w:
                bx, by = best_side, h * (1.0 - delta)
                y = cur[1] - cur[1].mean() + by * 0.5
                x = cur[0] - cur[0].mean() + bx * 0.5
            else:
                bx, by = w * (1.0 - delta), best_side
                x = cur[0] - cur[0].mean() + bx * 0.5
                y = cur[1] - cur[1].mean() + by * 0.5
            t = cur[2]
            x, y, t = relax(x, y, t, (bx, by), iters=240, lr=0.3, damp=0.5, w_wall=-1.0,
                            w_angle=0.8, rebuild_every=10)
            x, y = project(x, y, t, (bx, by))
            if _is_legal(x, y, t):
                side = float(g.side_length(x, y, t))
                if side < best_side - 1e-12:
                    best, best_side = (x, y, t), side
                    cur = (x, y, t)
                    delta = min(delta * 1.2, 0.012)
                    if verbose:
                        print(f"  n={n}: L={best_side:.6f}")
                    continue
            delta *= 0.6
            cur = _shake(best[0], best[1], best[2], rng, strength=0.5 + 0.5 * (guard % 3))
    return best[0], best[1], best[2], float(best_side)
