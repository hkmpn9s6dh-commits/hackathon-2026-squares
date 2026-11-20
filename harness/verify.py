"""Gate B: the checks that decide whether this submission is allowed to exist.

The submission is a table of coordinates. So the harness does not read the report
for reassurance — it re-derives the score from the CSV, tests every pair of
squares with the separating axis theorem, and only then compares the result with
the numbers the report quotes.

    py -3 harness/verify.py          # full run (~2 min)
    py -3 harness/verify.py --quick  # skips the O(n^2) legality sweep for n > 120
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import geometry as g  # noqa: E402

OUT = ROOT / "out"
SUB = OUT / "submission.csv"
RESULTS = OUT / "results.json"
PACK = OUT / "packings.npz"
SITE = ROOT / "site" / "index.html"
REPORT = ROOT / "REPORT.md"

TOL = 1e-9
GRID_TOTAL = 28.937669916551  # sum of ceil(sqrt n)/sqrt n - 1 for n = 1..1000

RESULTS_LIST: list[tuple[str, bool, str]] = []


def check(name):
    def deco(fn):
        def wrapper(*a, **kw):
            t0 = time.time()
            try:
                ok, detail = fn(*a, **kw)
            except Exception as exc:  # a crash is a failed check, not a crash
                ok, detail = False, f"{type(exc).__name__}: {exc}"
            RESULTS_LIST.append((name, ok, detail))
            print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}  ({time.time()-t0:.1f}s)", flush=True)
            return ok

        return wrapper

    return deco


def load_submission():
    with SUB.open(newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        rows = list(reader)
    return header, rows


def puzzles_from_rows(rows):
    """n -> (cx, cy, th) arrays, preserving square_id order."""
    by_n: dict[int, dict[int, tuple]] = {}
    for r in rows:
        n, sid, x, y, a = int(r[1]), int(r[2]), float(r[3]), float(r[4]), float(r[5])
        by_n.setdefault(n, {})[sid] = (x, y, a)
    out = {}
    for n, d in by_n.items():
        cx = np.array([d[i][0] for i in range(n)])
        cy = np.array([d[i][1] for i in range(n)])
        th = np.array([d[i][2] for i in range(n)])
        out[n] = (cx, cy, th)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    quick_cut = 120 if args.quick else 1000

    @check("AC-01 the file is the Kaggle format and nothing else")
    def schema():
        header, rows = load_submission()
        want = ["id", "n", "square_id", "x", "y", "angle"]
        ids = [int(r[0]) for r in rows]
        return (header == want, f"header={header} rows={len(rows)} ids 0..{max(ids)} consecutive={ids == list(range(len(ids)))}")

    @check("AC-02 every puzzle has exactly n squares, square_id 0..n-1")
    def counts():
        _, rows = load_submission()
        per: dict[int, set] = {}
        for r in rows:
            per.setdefault(int(r[1]), set()).add(int(r[2]))
        bad = [(n, len(s)) for n, s in per.items() if s != set(range(n))]
        return (not bad, f"puzzles={len(per)} bad={bad[:5]}")

    @check("AC-03 coordinates are finite decimal literals")
    def numbers():
        _, rows = load_submission()
        bad = 0
        for r in rows:
            for cell in r[3:6]:
                if not re.fullmatch(r"-?\d+\.\d+", cell):
                    bad += 1
                    break
            else:
                if not all(math.isfinite(float(c)) for c in r[3:6]):
                    bad += 1
        return (bad == 0, f"rows={len(rows)} malformed={bad}")

    @check("AC-04 no two squares in a puzzle overlap (SAT, all pairs)")
    def legality():
        _, rows = load_submission()
        data = puzzles_from_rows(rows)
        worst = 0.0
        worst_n = 0
        checked = 0
        for n, (cx, cy, th) in data.items():
            if n > quick_cut:
                pairs = g.neighbour_pairs(cx, cy, reach=2.4)
                if len(pairs) == 0:
                    continue
            else:
                pairs = g.all_pairs(n)
            m = g.min_gap(cx, cy, th, pairs)
            checked += 1
            if m < worst:
                worst, worst_n = m, n
        ok = worst >= -TOL
        return (ok, f"puzzles={checked} worst gap={worst:.3e} at n={worst_n}")

    @check("AC-05 L is recomputed from the CSV, not trusted")
    def sides():
        _, rows = load_submission()
        data = puzzles_from_rows(rows)
        res = json.loads(RESULTS.read_text(encoding="utf-8"))
        dev = 0.0
        for r in res["puzzles"]:
            cx, cy, th = data[r["n"]]
            dev = max(dev, abs(g.side_length(cx, cy, th) - r["side"]))
        return (dev <= 1e-9, f"max |L_csv - L_results| = {dev:.2e}")

    @check("AC-06 the total score is the sum of the per-puzzle scores")
    def total():
        _, rows = load_submission()
        data = puzzles_from_rows(rows)
        res = json.loads(RESULTS.read_text(encoding="utf-8"))
        tot = 0.0
        for n, (cx, cy, th) in data.items():
            L = g.side_length(cx, cy, th)
            tot += L / math.sqrt(n) - 1.0
        return (abs(tot - res["total_score"]) <= 1e-9, f"recomputed {tot:.6f} vs results {res['total_score']:.6f}")

    @check("AC-07 the grid baseline is what the metric says it is")
    def grid_total():
        tot = sum(g.score(n, g.grid_side(n)) for n in range(1, 1001))
        return (abs(tot - GRID_TOTAL) <= 1e-9, f"grid total {tot:.9f} expected {GRID_TOTAL:.9f}")

    @check("AC-08 no puzzle is worse than the grid")
    def no_regression():
        res = json.loads(RESULTS.read_text(encoding="utf-8"))
        bad = [r["n"] for r in res["puzzles"] if r["side"] > r["grid"] + 1e-12]
        better = sum(1 for r in res["puzzles"] if r["side"] < r["grid"] - 1e-12)
        return (not bad, f"worse_than_grid={len(bad)} better_than_grid={better}")

    @check("AC-09 the shipped packings reproduce every reported side")
    def npz_consistency():
        res = json.loads(RESULTS.read_text(encoding="utf-8"))
        z = np.load(PACK)
        dev = 0.0
        for r in res["puzzles"]:
            n = r["n"]
            dev = max(dev, abs(g.side_length(z[f"x{n}"], z[f"y{n}"], z[f"t{n}"]) - r["side"]))
        return (dev <= 1e-12, f"max deviation {dev:.2e} over {len(res['puzzles'])} puzzles")

    @check("AC-10 every number quoted in REPORT.md exists in results.json")
    def report_numbers():
        res = json.loads(RESULTS.read_text(encoding="utf-8"))
        text = REPORT.read_text(encoding="utf-8")
        claims = [
            ("total", f"{res['total_score']:.4f}"),
            ("grid", f"{res['grid_total']:.4f}"),
            ("improved", f"{int(res['improved_count'])}"),
        ]
        missing = [k for k, v in claims if v not in text]
        return (not missing, f"checked {len(claims)} claims, missing={missing}")

    @check("AC-11 the site is one self-contained file")
    def site():
        html = SITE.read_text(encoding="utf-8")
        ext = re.findall(r'(?:src|href)="(https?://[^"]+)"', html)
        return (len(ext) == 0, f"external_refs={len(ext)} bytes={len(html)}")

    @check("AC-12 the README commands name files that exist")
    def readme():
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        cmds = re.findall(r"py -3 ([\w./-]+)", text)
        missing = [c for c in cmds if not (ROOT / c).exists()]
        return (bool(cmds) and not missing, f"{len(cmds)} commands, missing={missing}")

    for fn in (schema, counts, numbers, legality, sides, total, grid_total,
               no_regression, npz_consistency, report_numbers, site, readme):
        fn()

    ok = all(r[1] for r in RESULTS_LIST)
    print(f"\n{sum(1 for r in RESULTS_LIST if r[1])}/{len(RESULTS_LIST)} checks passed in {time.time()-T0:.1f}s")
    (OUT / "verify.json").write_text(json.dumps(
        [{"name": n, "ok": o, "detail": d} for n, o, d in RESULTS_LIST], indent=1), encoding="utf-8")
    return 0 if ok else 1


T0 = time.time()

if __name__ == "__main__":
    raise SystemExit(main())
