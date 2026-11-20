# 方寸之间 · Squares in Squares

2026 **Squares in Squares**（Kaggle）参赛作品（赛道 AM / AME-1530）。

把 `n` 个边长 1 的方块（可任意旋转）塞进最小的轴对齐方框，`n = 1…1000`；
分数 `score(n) = L/√n − 1` 逐题求和，越低越好，缺题按方阵 `ceil(√n)` 计分。

- 站点（单档，离线可开）：`site/index.html`
- 提交档：`out/submission.csv`（1000 题、Σn = 500500 行）
- 技术报告：`REPORT.md`
- 赛规逐条引文与验收条件：`SPEC.md`

## 结果

| | 总分（越低越好） |
|---|---|
| 方阵基线（trivial） | 28.9377 |
| **本作品** | 见 `out/results.json` 的 `total_score` |
| 已发表记录表（142 个 n） | 26.8475 |
| Kaggle 榜首（2026-11-20） | 22.04 |

分数不是均匀散在 1000 题上的：第 k 段（`k² < n ≤ (k+1)²`）的方阵损失合計约 0.9，
31 段加起来就是 28.94。所以问题只有一个 —— **每段上沿那条缝能不能压下去**。

## 复现

```bash
py -3 scripts/solve.py          # 全量求解 -> out/packings.npz, out/results.json, out/submission.csv
py -3 scripts/audit.py          # 最坏穿透 -> out/audit.json
py -3 scripts/build_report.py   # REPORT.md（数字从 results.json 注入）
py -3 scripts/build_site.py     # site/index.html
py -3 harness/verify.py         # 12 条断言，退出码即结论（--quick 跳过大 n 的逐对扫描）
```

- 固定种子 `20260131 + n`；纯 CPU、单核、只用 numpy；除抓记录表那一步外不需要网络。
- 全量求解约 18 分钟（本机），`verify.py` 约 2 分钟。
- `bash scripts/run_all.sh` 是上面六条的顺序版。

## 目录

```
squares/
├── SPEC.md                 闸 A：赛规原文 + AC-01…AC-12
├── REPORT.md               技术报告（由 REPORT.template.md 注入生成）
├── pipeline/
│   ├── geometry.py         顶点 / 分离轴 / 包围盒 L / 方阵基线
│   ├── relax.py            软排斥 + 硬投影墙 + 45° 非局部动作
│   └── grow.py             逐题加一的链式构造（本版未启用，留作对照）
├── scripts/                solve · audit · build_report · build_site
├── harness/verify.py       闸 B：12 条断言
├── site/index.html         闸 C：单档可視化
└── out/                    submission.csv · results.json · packings.npz · audit.json
```

## 两条已知限制

1. 软排斥停在力學平衡，不是最优；要更低必须整排协同留缝，本方法做不到（报告 §失败模式）。
2. 只在 142 个有公开记录的 n 上做过逐题对照，其余 n 没有可信参照。
