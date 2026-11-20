"""Parse the published packing record table (Friedman / Ellsworth) into n -> s(n).

Only the *side lengths* are kept: the record table is used as a yardstick in the
report, never as a source of coordinates. See docs/09-REFERENCE.md.
"""
from __future__ import annotations

import html
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "out" / "_record_table.html"
DST = ROOT / "out" / "record_table.json"

NUM = re.compile(r"\\Nn\{([0-9.]+)\}")


def text_lines(raw: str) -> list[str]:
    t = re.sub(r"<script.*?</script>", "", raw, flags=re.S)
    t = re.sub(r"<style.*?</style>", "", t, flags=re.S)
    t = re.sub(r"<[^>]+>", "\n", t)
    t = html.unescape(t)
    return [ln.strip() for ln in t.split("\n") if ln.strip()]


def main() -> int:
    raw = SRC.read_text(encoding="utf-8", errors="replace")
    lines = text_lines(raw)
    rec: dict[int, float] = {}
    for i, line in enumerate(lines):
        if not re.fullmatch(r"\d{1,4}", line):
            continue
        n = int(line)
        for j in range(i + 1, min(i + 6, len(lines))):
            m = NUM.search(lines[j])
            if m:
                v = float(m.group(1))
                if 0.9 < v <= 40 and n not in rec:
                    rec[n] = v
                break
    if not rec:
        print("FAIL: parsed nothing", file=sys.stderr)
        return 1

    grid_total = 0.0
    rec_total = 0.0
    improved = 0
    for n in range(1, 1001):
        k = math.isqrt(n)
        l0 = k if k * k == n else k + 1
        grid_total += l0 / math.sqrt(n) - 1.0
        s = rec.get(n, l0)
        if s < l0 - 1e-12:
            improved += 1
        rec_total += s / math.sqrt(n) - 1.0

    DST.write_text(json.dumps({str(k): v for k, v in sorted(rec.items())}, indent=1), encoding="utf-8")
    print(f"parsed {len(rec)} entries, n in [{min(rec)}, {max(rec)}]")
    print(f"grid total   {grid_total:.6f}")
    print(f"record total {rec_total:.6f}  (improved on grid at {improved} values of n)")
    for n in (5, 10, 11, 17, 26, 37, 50, 100, 101):
        print(f"  n={n:4d} record {rec.get(n, float('nan')):.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
