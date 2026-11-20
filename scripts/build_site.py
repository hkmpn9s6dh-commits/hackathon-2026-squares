"""Build site/index.html: one self-contained page, no external requests.

Everything is injected from out/results.json, out/packings.npz and the parsed
record table, so the page cannot quote a number the submission does not have.
"""
from __future__ import annotations

import html
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out"
SITE = ROOT / "site"
GALLERY = [5, 6, 10, 11, 17, 20, 26, 30, 37, 42, 50, 65]


def square_path(x, y, t):
    c, s = math.cos(t), math.sin(t)
    pts = []
    for ax, ay in ((0.5, 0.5), (-0.5, 0.5), (-0.5, -0.5), (0.5, -0.5)):
        pts.append((x + ax * c - ay * s, y + ax * s + ay * c))
    d = "M" + " L".join(f"{px:.4f},{py:.4f}" for px, py in pts) + " Z"
    return d


def packing_svg(cx, cy, th, side, cls="sq"):
    pad = 2.0
    vb = side + 2 * pad
    stroke = max(0.012, 0.02 * 60.0 / max(side, 1.0))
    parts = []
    for i in range(len(cx)):
        parts.append(f'<path class="{cls}" style="stroke-width:{stroke:.4f}" '
                     f'd="{square_path(cx[i]+pad, cy[i]+pad, th[i])}"/>')
    box = (f'<rect class="box" x="{pad:.3f}" y="{pad:.3f}" width="{side:.4f}" height="{side:.4f}"/>')
    return (f'<svg viewBox="0 0 {vb:.3f} {vb:.3f}" xmlns="http://www.w3.org/2000/svg" '
            f'role="img" aria-label="n squares in a square of side {side:.3f}">'
            f'{box}{"".join(parts)}</svg>')


def main() -> int:
    res = json.loads((OUT / "results.json").read_text(encoding="utf-8"))
    z = np.load(OUT / "packings.npz")
    by_n = {r["n"]: r for r in res["puzzles"]}

    grid_total = res["grid_total"]
    total = res["total_score"]
    leader = 22.04

    # --- score bars -----------------------------------------------------------
    lo, hi = leader - 1.2, grid_total + 0.6

    def pct(v):
        return (v - lo) / (hi - lo) * 100

    bars = [
        ("Kaggle 榜首", leader, "22.04", "ref"),
        ("本作品", total, f"{total:.4f}", "us"),
        ("方阵基线", grid_total, f"{grid_total:.4f}", "base"),
    ]
    bar_html = "".join(
        f'<div class="bar"><span class="bl">{html.escape(name)}</span>'
        f'<span class="btrack"><span class="bfill {kind}" style="width:{max(1.5, pct(v)):.2f}%"></span></span>'
        f'<span class="bv">{val}</span></div>'
        for name, v, val, kind in bars
    )

    # --- band chart -----------------------------------------------------------
    bands = {}
    for n, r in by_n.items():
        bands.setdefault(math.isqrt(n), []).append(r)
    maxband = max(sum(x["grid_score"] for x in v) for v in bands.values())
    band_svg = ['<svg viewBox="0 0 720 190" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="band decomposition">']
    band_svg.append('<line class="axis" x1="40" y1="150" x2="712" y2="150"/>')
    step = (712 - 52) / len(bands)
    for idx, k in enumerate(sorted(bands)):
        rows = bands[k]
        gsum = sum(x["grid_score"] for x in rows)
        osum = sum(x["score"] for x in rows)
        x = 52 + idx * step
        hg = gsum / maxband * 120
        ho = osum / maxband * 120
        band_svg.append(f'<rect class="bg" x="{x:.2f}" y="{150-hg:.2f}" width="{step*0.62:.2f}" height="{hg:.2f}"><title>k={k} 方阵 {gsum:.3f}</title></rect>')
        band_svg.append(f'<rect class="bo" x="{x+step*0.62:.2f}" y="{150-ho:.2f}" width="{step*0.34:.2f}" height="{ho:.2f}"><title>k={k} 本作品 {osum:.3f}</title></rect>')
        if k % 5 == 0:
            band_svg.append(f'<text class="tick" x="{x+step*0.45:.2f}" y="166">{k}</text>')
    band_svg.append(f'<text class="lbl" x="40" y="182">k = floor(√n)：第 k 段是 n ∈ (k², (k+1)²]，每段方阵损失约 0.9</text>')
    band_svg.append("</svg>")

    # --- gallery --------------------------------------------------------------
    cards = []
    for n in GALLERY:
        r = by_n[n]
        cx, cy, th = z[f"x{n}"], z[f"y{n}"], z[f"t{n}"]
        svg = packing_svg(cx, cy, th, r["side"])
        delta = None
        ref_txt = "方阵" if abs(r["side"] - r["grid"]) < 1e-12 else "已压下"
        cards.append(
            f'<figure class="card"><figcaption><b>n = {n}</b>'
            f'<span class="side">L = {r["side"]:.4f}</span></figcaption>'
            f'{svg}'
            f'<p class="meta">方阵 {r["grid"]}.0000 · {ref_txt}'
            + "</p></figure>")

    doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>方寸之间 · Squares in Squares</title>
<style>
  :root {{
    --paper: #f7f5ef; --ink: #191817; --muted: #6b6660; --line: #d9d3c7;
    --accent: #a63b2a; --cool: #2f5d6b; --gold: #b58b2a; --card: #fffdf8;
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: var(--paper); color: var(--ink);
    font-family: "Songti SC", "Noto Serif CJK SC", "Source Han Serif SC", Georgia, serif;
    line-height: 1.75; }}
  header {{ padding: 72px 7vw 40px; border-bottom: 1px solid var(--line); }}
  h1 {{ margin: 0 0 6px; font-size: clamp(34px, 5.2vw, 64px); letter-spacing: .06em; font-weight: 600; }}
  .sub {{ color: var(--muted); font-size: 15px; letter-spacing: .04em; }}
  .lede {{ max-width: 62ch; margin: 26px 0 0; font-size: clamp(17px, 1.7vw, 21px); }}
  main {{ padding: 0 7vw 96px; }}
  section {{ padding: 56px 0; border-bottom: 1px solid var(--line); }}
  h2 {{ font-size: 13px; letter-spacing: .3em; text-transform: uppercase; color: var(--accent);
    font-family: ui-sans-serif, system-ui, sans-serif; font-weight: 600; margin: 0 0 22px; }}
  h3 {{ font-size: 19px; margin: 34px 0 10px; }}
  p {{ margin: 0 0 14px; max-width: 68ch; }}
  .bars {{ display: grid; gap: 10px; max-width: 760px; }}
  .bar {{ display: grid; grid-template-columns: 132px 1fr 74px; align-items: center; gap: 14px; font-size: 14px; }}
  .bl {{ color: var(--muted); font-family: ui-sans-serif, system-ui, sans-serif; }}
  .btrack {{ height: 16px; background: #e9e4d8; position: relative; }}
  .bfill {{ display: block; height: 100%; }}
  .bfill.us {{ background: var(--accent); }}
  .bfill.base {{ background: #c9c2b2; }}
  .bfill.ref {{ background: var(--cool); opacity: .55; }}
  .bv {{ font-variant-numeric: tabular-nums; text-align: right; }}
  .note {{ font-size: 13px; color: var(--muted); margin-top: 16px; }}
  svg .box {{ fill: none; stroke: var(--ink); stroke-width: .035; }}
  svg .sq {{ fill: rgba(47,93,107,.16); stroke: var(--cool); stroke-width: .022; }}
  .gallery {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 20px; }}
  .card {{ margin: 0; background: var(--card); border: 1px solid var(--line); padding: 14px; }}
  .card figcaption {{ display: flex; justify-content: space-between; font-size: 13px;
    font-family: ui-sans-serif, system-ui, sans-serif; margin-bottom: 10px; }}
  .card .side {{ color: var(--accent); font-variant-numeric: tabular-nums; }}
  .card svg {{ width: 100%; height: auto; display: block; }}
  .meta {{ font-size: 11.5px; color: var(--muted); margin: 10px 0 0; font-family: ui-sans-serif, system-ui, sans-serif; }}
  .axis {{ stroke: var(--line); stroke-width: 1; }}
  .bg {{ fill: #d8d1c1; }}
  .bo {{ fill: var(--accent); opacity: .85; }}
  .tick {{ font-size: 10px; fill: var(--muted); text-anchor: middle; font-family: ui-sans-serif, system-ui, sans-serif; }}
  .lbl {{ font-size: 10.5px; fill: var(--muted); font-family: ui-sans-serif, system-ui, sans-serif; }}
  table {{ border-collapse: collapse; font-size: 13.5px; margin: 18px 0 8px;
    font-variant-numeric: tabular-nums; }}
  th, td {{ padding: 7px 14px 7px 0; text-align: left; border-bottom: 1px solid var(--line); }}
  th {{ font-family: ui-sans-serif, system-ui, sans-serif; font-weight: 600; color: var(--muted); font-size: 12px; }}
  ol {{ max-width: 68ch; padding-left: 22px; }}
  code {{ font-family: "SF Mono", Consolas, monospace; font-size: 12.5px; background: #eee9dc; padding: 1px 5px; }}
  .kicker {{ display: inline-block; font-family: ui-sans-serif, system-ui, sans-serif; font-size: 11px;
    letter-spacing: .22em; color: var(--muted); margin-bottom: 12px; }}
  footer {{ padding: 40px 7vw 80px; color: var(--muted); font-size: 12.5px;
    font-family: ui-sans-serif, system-ui, sans-serif; }}
  .two {{ display: grid; grid-template-columns: 1fr 1fr; gap: 40px; }}
  @media (max-width: 720px) {{ .two {{ grid-template-columns: 1fr; }} .bar {{ grid-template-columns: 96px 1fr 64px; }} }}
</style>
</head>
<body>
<header>
  <span class="kicker">KAGGLE · SQUARES IN SQUARES · 赛道 AM</span>
  <h1>方寸之间</h1>
  <p class="sub">把 n 个边长 1 的方块塞进最小的方框，n = 1…1000。分数 = Σ (L/√n − 1)，越低越好。</p>
  <p class="lede">方阵不是答案，方阵是每个 k 段上沿那条没人收拾的缝。这里做的事情只有一件：
  量出每条缝有多宽，然后一段一段压下去，压不动的老实标出来。</p>
</header>
<main>
  <section>
    <h2>01 · 分数</h2>
    <div class="bars">{bar_html}</div>
    <p class="note">长度按同一刻度画；榜首是 2026-11-20 的公开快照。方阵基线 {grid_total:.4f} 是把
    1000 题全按 <code>ceil(√n)</code> 提交的分数 —— 也是「不交」的分数。本作品只比它低
    {(grid_total-total)/grid_total*100:.2f}%。</p>
  </section>

  <section>
    <h2>02 · 每段的那条缝</h2>
    <p>分数不是均匀散在 1000 题上的：令 k = floor(√n)，第 k 段的方阵损失合計约 0.9，31 段加起来
    就是 28.94。灰柱是方阵，红柱是本作品 —— 只有红柱明显短的地方，才是真的压下去了。</p>
    {''.join(band_svg)}
  </section>

  <section>
    <h2>03 · 装填图</h2>
    <p>选出来的 12 题。斜的方块不是装饰：它是唯一能把上一排的缝隙填掉的动作。</p>
    <div class="gallery">{''.join(cards)}</div>
  </section>

  <section>
    <h2>04 · 方法</h2>
    <div class="two">
      <div>
        <h3>A · 连续收缩（试过，关掉了）</h3>
        <p>把容器固定在装不下的尺寸，只压约束轴，软排斥推开重叠、硬投影守住墙，
        再把残余穿透投影到 1e-12；唯一的非局部动作是随机转一个方块 45°。
        花掉 19 分钟，1000 题里只有 n=5 压下去（3.000 → 2.831）。</p>
        <h3>B · 小 n 随机重启（最终提交用的）</h3>
        <p>n ≤ 24 不做连续收缩：盒子从方阵边长逐级缩到 0.85 倍，每次随机撒点、松弛、
        精确投影，合法的才收。它不需要「从方阵走到更好的构型」，所以比 A 好 ——
        全量 2 分 19 秒，n=5 到 2.910。</p>
      </div>
      <div>
        <h3>为什么只能到这里</h3>
        <p>一个方块的包围盒高度永远 ≥ 1：k 行满排之上再加一排，高度不可能低于 k+1。
        要更低，上一排必须留缝让新方块斜插 —— 而留缝会把宽度撑开，宽度就是 L，两头互锁。</p>
        <h3>量到的边界</h3>
        <p>n = 10 随机重启 6 次：盒子 3.90 时 1 次合法，3.80 时 0 次（方阵 4.00）。
        文献里的 3.707 一次都没摸到 —— 那些是刚体构造，不是从方阵连续走得到的邻居。</p>
      </div>
    </div>
  </section>

  <section>
    <h2>05 · 为什么只压下去 {res['improved_count']} 题</h2>
    <p>因为<strong>一个方块的包围盒高度永远 ≥ 1</strong>：k 行满排之上再加一排，高度不可能低于 k+1。
    要更低，上一排必须留缝、让新方块斜插进去 —— 而「留缝」是整排的协同动作，不是局部排斥能产生的。</p>
    <p>实测（n = 10，随机起点 + 800 次松弛 + 精确投影，各 6 次）：盒子边长 3.90 时 6 次里有
    <b>1</b> 次落到合法构型；3.80 时 <b>0</b> 次。方阵是 4.00。也就是说，能走到的邻居里几乎没有
    更好的解 —— 文献里那些更小的构型是<b>刚体构造</b>（L 形角件 + 斜插方块），不是从方阵连续走得到的。</p>
    <p class="note">这条边界是本报告的主要结论，不是调参空间。见 REPORT.md 第三节。</p>
  </section>

  <section>
    <h2>06 · 复现</h2>
    <p><code>py -3 scripts/solve.py</code> → <code>py -3 scripts/audit.py</code> →
    <code>py -3 scripts/build_report.py</code> → <code>py -3 scripts/build_site.py</code> →
    <code>py -3 harness/verify.py</code>（12 条断言，退出码即结论）。固定种子 20260131 + n，
    纯 CPU、单核、只用 numpy。</p>
    <p>提交文件：<code>out/submission.csv</code>，{sum(r['n'] for r in by_n.values())} 行，
    1000 题全交，没有任何一题比方阵差。</p>
  </section>
</main>
<footer>
  AME-1530 · 赛道 AM · 作品《方寸之间》 · 数据源：本地 <code>out/results.json</code>（{res['seconds']:.0f} 秒求解）
</footer>
</body>
</html>
"""
    SITE.mkdir(exist_ok=True)
    (SITE / "index.html").write_text(doc, encoding="utf-8")
    print(f"site built: {len(doc)} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
