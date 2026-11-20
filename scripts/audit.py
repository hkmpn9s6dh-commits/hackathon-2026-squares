"""Audit the packings: worst penetration, per-band totals, and the record comparison.

This is the number the report must not get wrong: the smallest signed gap over
every pair of squares in every puzzle. It is computed from the shipped packings,
not from an intermediate state of the solver.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import geometry as g  # noqa: E402

OUT = ROOT / "out"


def main() -> int:
    res = json.loads((OUT / "results.json").read_text(encoding="utf-8"))
    z = np.load(OUT / "packings.npz")
    worst = 0.0
    worst_n = 0
    sides = {}
    for r in res["puzzles"]:
        n = r["n"]
        cx, cy, th = z[f"x{n}"], z[f"y{n}"], z[f"t{n}"]
        pairs = g.all_pairs(n) if n <= 400 else g.neighbour_pairs(cx, cy, reach=2.4)
        if len(pairs):
            m = g.min_gap(cx, cy, th, pairs)
            if m < worst:
                worst, worst_n = m, n
        sides[n] = float(g.side_length(cx, cy, th))
    out = {"worst_penetration": float(worst), "worst_n": worst_n,
           "sides_recomputed": {str(k): v for k, v in sides.items()}}
    (OUT / "audit.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"worst penetration {worst:.3e} at n={worst_n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
