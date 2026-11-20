"""Inject the measured numbers into REPORT.template.md -> REPORT.md.

Every figure in the report comes from out/results.json (or out/audit.json).
Nothing is typed by hand, so the report cannot drift away from the submission.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out"


def main() -> int:
    res = json.loads((OUT / "results.json").read_text(encoding="utf-8"))
    audit = json.loads((OUT / "audit.json").read_text(encoding="utf-8"))
    puzzles = res["puzzles"]

    bands: dict[int, list] = {}
    for r in puzzles:
        bands.setdefault(math.isqrt(r["n"]), []).append(r)
    band_rows = []
    for k in sorted(bands):
        rows = bands[k]
        band_rows.append(
            f"| {k} | {len(rows)} | {sum(r['grid_score'] for r in rows):.3f} | "
            f"{sum(r['score'] for r in rows):.3f} | {sum(r['grid_score'] - r['score'] for r in rows):.3f} |")

    gain_pct = (res["grid_total"] - res["total_score"]) / res["grid_total"] * 100
    sha = hashlib.sha256((OUT / "submission.csv").read_bytes()).hexdigest()
    rows_total = sum(r["n"] for r in puzzles)

    repl = {
        "{{grid_total}}": f"{res['grid_total']:.4f}",
        "{{total}}": f"{res['total_score']:.4f}",
        "{{improved_count}}": str(res["improved_count"]),
        "{{worst_gap}}": f"{audit['worst_penetration']:.2e}（n={audit['worst_n']}）",
        "{{band_rows}}": "\n".join(band_rows),
        "{{gain_pct}}": f"{gain_pct:.2f}",
        "{{solve_seconds}}": f"{res['seconds']:.0f}",
        "{{sub_sha}}": sha,
        "{{rows}}": str(rows_total),
    }
    text = (ROOT / "REPORT.template.md").read_text(encoding="utf-8")
    for k, v in repl.items():
        text = text.replace(k, v)
    (ROOT / "REPORT.md").write_text(text, encoding="utf-8")
    print("REPORT.md written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
