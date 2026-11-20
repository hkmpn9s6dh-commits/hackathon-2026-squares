"""Solve all 1000 puzzles and write the Kaggle submission.

Budget policy (wall clock, single core, numpy only):

    n <= 64     12.0 s   the bands where the excess is largest and the search is cheapest
    65..200      2.0 s   the same solver, far less time
    n > 200      keep the grid

Everything is seeded by n, so a re-run on a clean clone reproduces the same file.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import geometry as g  # noqa: E402
from pipeline import relax as R  # noqa: E402
from pipeline import small  # noqa: E402

OUT = ROOT / "out"
SEED = 20260131


def budget_for(n: int, scale: float) -> float:
    if n <= 24:
        return 6.0 * scale
    return 0.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", type=float, default=1.0, help="multiply every per-n budget")
    ap.add_argument("--nmax", type=int, default=1000)
    ap.add_argument("--quick", action="store_true", help="tiny budgets, for the harness")
    args = ap.parse_args()
    scale = 0.02 if args.quick else args.scale

    OUT.mkdir(exist_ok=True)
    t0 = time.time()
    results: list[dict] = []
    grids: list[dict] = []
    pack: dict[str, np.ndarray] = {}
    for n in range(1, args.nmax + 1):
        budget = budget_for(n, scale)
        if budget <= 0 or n <= 2:
            cx, cy, th = g.grid_packing(n)
            side = float(g.side_length(cx, cy, th))
        else:
            cx, cy, th, side = small.brute(n, budget_s=budget, seed=SEED + n)
        l0 = float(g.grid_side(n))
        results.append({"n": n, "side": side, "grid": l0,
                        "score": g.score(n, side), "grid_score": g.score(n, l0)})
        grids.append({"n": n, "side": l0, "score": g.score(n, l0)})
        pack[f"x{n}"], pack[f"y{n}"], pack[f"t{n}"] = cx, cy, th
        if n % 25 == 0 or n <= 5:
            print(f"[{time.time()-t0:6.1f}s] n={n}: side {side:.6f} (grid {l0}) "
                  f"score {g.score(n, side):.4f}", flush=True)

    total = sum(r["score"] for r in results)
    grid_total = sum(r["grid_score"] for r in results)
    improved = [r for r in results if r["side"] < r["grid"] - 1e-12]
    print(f"\nTOTAL {total:.6f}  grid {grid_total:.6f}  improved {len(improved)}/{len(results)}")

    np.savez_compressed(OUT / "packings.npz", **pack)
    summary = {
        "total_score": total,
        "grid_total": grid_total,
        "improved_count": len(improved),
        "budget_scale": scale,
        "seconds": round(time.time() - t0, 1),
        "seed": SEED,
        "puzzles": results,
    }
    (OUT / "results.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")

    rows = []
    rid = 0
    for r in results:
        n = r["n"]
        cx, cy, th = pack[f"x{n}"], pack[f"y{n}"], pack[f"t{n}"]
        for s in range(n):
            rows.append((rid, n, s, cx[s], cy[s], th[s]))
            rid += 1
    with (OUT / "submission.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "n", "square_id", "x", "y", "angle"])
        for row in rows:
            w.writerow([row[0], row[1], row[2], f"{row[3]:.12f}", f"{row[4]:.12f}", f"{row[5]:.12f}"])
    print(f"submission.csv: {len(rows)} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
