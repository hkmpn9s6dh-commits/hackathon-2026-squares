"""Audit the *shipped file*: worst penetration over every pair in submission.csv.

The report must quote the number the submission actually has, not an
intermediate state of the solver, so this reads the CSV (12 decimal places) and
recomputes everything from it.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import geometry as g  # noqa: E402

OUT = ROOT / "out"


def main() -> int:
    res = json.loads((OUT / "results.json").read_text(encoding="utf-8"))
    by_n: dict[int, dict[int, tuple]] = {}
    with (OUT / "submission.csv").open(newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        next(reader)
        for row in reader:
            by_n.setdefault(int(row[1]), {})[int(row[2])] = (float(row[3]), float(row[4]), float(row[5]))

    worst, worst_n = 0.0, 0
    sides = {}
    for n, d in by_n.items():
        cx = np.array([d[i][0] for i in range(n)])
        cy = np.array([d[i][1] for i in range(n)])
        th = np.array([d[i][2] for i in range(n)])
        pairs = g.all_pairs(n) if n <= 400 else g.neighbour_pairs(cx, cy, reach=2.4)
        if len(pairs):
            m = g.min_gap(cx, cy, th, pairs)
            if m < worst:
                worst, worst_n = m, n
        sides[n] = float(g.side_length(cx, cy, th))

    dev = max(abs(sides[r["n"]] - r["side"]) for r in res["puzzles"])
    out = {
        "worst_penetration": float(worst),
        "worst_n": worst_n,
        "max_side_deviation_from_results": float(dev),
        "sides_recomputed": {str(k): v for k, v in sides.items()},
    }
    (OUT / "audit.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"worst penetration {worst:.3e} at n={worst_n}; max |L - results| = {dev:.2e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
