"""Geometry for packing unit squares in an axis-aligned square.

Everything here is exact up to float64 rounding: a packing is legal when the
interiors of no two squares intersect, tested with the separating axis theorem
on the four edge normals of each pair. The container side L is the larger of the
bounding-box width and height of the 4n corners.
"""
from __future__ import annotations

import math

import numpy as np

EDGES = np.array([(0.5, 0.5), (-0.5, 0.5), (-0.5, -0.5), (0.5, -0.5)], dtype=np.float64)


def corners(cx: np.ndarray, cy: np.ndarray, th: np.ndarray) -> np.ndarray:
    """(n,4,2) corners of each unit square, rotated by th about its centre."""
    c, s = np.cos(th), np.sin(th)
    # local corner (a,b) -> (a*c - b*s, a*s + b*c)
    x = cx[:, None] + EDGES[None, :, 0] * c[:, None] - EDGES[None, :, 1] * s[:, None]
    y = cy[:, None] + EDGES[None, :, 0] * s[:, None] + EDGES[None, :, 1] * c[:, None]
    return np.stack([x, y], axis=-1)


def side_length(cx: np.ndarray, cy: np.ndarray, th: np.ndarray) -> float:
    """Container side L of the tightest axis-aligned square holding the packing."""
    if len(cx) == 0:
        return 0.0
    half = 0.5 * (np.abs(np.cos(th)) + np.abs(np.sin(th)))
    w = float(np.max(cx + half) - np.min(cx - half))
    h = float(np.max(cy + half) - np.min(cy - half))
    return max(w, h)


def extents(cx: np.ndarray, cy: np.ndarray, th: np.ndarray) -> tuple[float, float]:
    """Bounding-box width and height of the packing."""
    if len(cx) == 0:
        return 0.0, 0.0
    half = 0.5 * (np.abs(np.cos(th)) + np.abs(np.sin(th)))
    return (float(np.max(cx + half) - np.min(cx - half)),
            float(np.max(cy + half) - np.min(cy - half)))


def pair_gap(cx, cy, th, i, j) -> np.ndarray:
    """Signed separation for each pair: >0 legal gap, <0 penetration depth."""
    dx = cx[j] - cx[i]
    dy = cy[j] - cy[i]
    axes = []
    for t in (th[i], th[j]):
        c, s = np.cos(t), np.sin(t)
        axes.append((c, s))
        axes.append((-s, c))
    gap = None
    for ax, ay in axes:
        proj = np.abs(dx * ax + dy * ay)
        hi = 0.5 * (np.abs(ax * np.cos(th[i]) + ay * np.sin(th[i])) + np.abs(-ax * np.sin(th[i]) + ay * np.cos(th[i])))
        hj = 0.5 * (np.abs(ax * np.cos(th[j]) + ay * np.sin(th[j])) + np.abs(-ax * np.sin(th[j]) + ay * np.cos(th[j])))
        g = proj - hi - hj
        gap = g if gap is None else np.maximum(gap, g)
    return gap


def min_gap(cx, cy, th, pairs: np.ndarray) -> float:
    """Smallest signed separation over all pairs (the legality margin)."""
    if len(pairs) == 0:
        return float("inf")
    i, j = pairs[:, 0], pairs[:, 1]
    return float(np.min(pair_gap(cx, cy, th, i, j)))


def all_pairs(n: int) -> np.ndarray:
    if n < 2:
        return np.zeros((0, 2), dtype=np.int64)
    i, j = np.triu_indices(n, k=1)
    return np.stack([i, j], axis=1)


def neighbour_pairs(cx, cy, reach: float) -> np.ndarray:
    """Pairs closer than `reach` in centre distance (cheap spatial hash)."""
    n = len(cx)
    if n < 2:
        return np.zeros((0, 2), dtype=np.int64)
    cell = max(reach, 1e-9)
    keys = np.floor(cx / cell).astype(np.int64) * 100003 + np.floor(cy / cell).astype(np.int64)
    order = np.argsort(keys, kind="stable")
    buckets: dict[int, list[int]] = {}
    for idx in order:
        buckets.setdefault(int(keys[idx]), []).append(int(idx))
    out = []
    reach2 = reach * reach
    for key, members in buckets.items():
        near = list(members)
        kx, ky = key // 100003, key % 100003
        for ddx in (-1, 0, 1):
            for ddy in (-1, 0, 1):
                if ddx == 0 and ddy == 0:
                    continue
                near.extend(buckets.get((kx + ddx) * 100003 + (ky + ddy), ()))
        for a in members:
            for b in near:
                if b <= a:
                    continue
                if (cx[a] - cx[b]) ** 2 + (cy[a] - cy[b]) ** 2 <= reach2:
                    out.append((a, b))
    if not out:
        return np.zeros((0, 2), dtype=np.int64)
    return np.asarray(sorted(set(out)), dtype=np.int64)


def score(n: int, side: float) -> float:
    return side / math.sqrt(n) - 1.0


def grid_side(n: int) -> int:
    k = math.isqrt(n)
    return k if k * k == n else k + 1


def grid_packing(n: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The trivial packing: k full rows plus a partial last row, side ceil(sqrt n)."""
    k = grid_side(n)
    xs, ys = [], []
    for idx in range(n):
        r, c = divmod(idx, k)
        xs.append(c + 0.5)
        ys.append(r + 0.5)
    th = np.zeros(n, dtype=np.float64)
    return np.asarray(xs), np.asarray(ys), th
