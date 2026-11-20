# SPEC · 这份提交凭什么算数

赛道 AM / AME-1530。赛规原文取自
https://www.kaggle.com/competitions/squares-in-squares/overview 与 `/rules`
（2026-11-20 抓取）。下面是逐条引文 + 我给自己定的验收条件。

## 1. 题目（原文）

> "In this competition, you'll pack `n` non-overlapping unit squares (squares with a side length
> of 1) into the smallest possible axis-aligned square container across 1,000 puzzles."

> "For each puzzle `n` from 1 to 1,000, you'll output continuous `(x, y)` center coordinates and a
> rotation angle (in radians) for all `n` unit squares. Partial submissions are allowed, so you
> don't need to submit solutions for all 1,000 puzzles at once."

## 2. 合法性（原文）

> "**No two squares overlap.** The interior intersection of any two unit squares must be exactly zero."

> "**Minimize the bounding container length `L`.** The axis-aligned container square should be as
> tight as mathematically possible around all `n` unit squares."

**判据落地**：对方块 i、j 取两者的 4 条边法向做分离轴检验，
`gap = max_axis(|d·a| − h_i(a) − h_j(a))`；`gap ≥ 0` 即内部交集为空（相切允许）。
本作品的容差取 `gap ≥ −1e-9`（浮点舍入），`harness/verify.py` 的 AC-04 逐对复算。

## 3. 计分（原文）

> "**Lower is better.** For each puzzle `n`, your score is the *excess* of your achieved container
> side length `L` over the area-based lower bound: `score(n) = L / √n − 1`.
> The leaderboard is the sum of all puzzles."

> "a missing puzzle scores `L0/√n − 1`, the same as the trivial grid packing for that `n`."

**推论**（本作品的基线）：`L0 = ceil(√n)`，1000 题合計 **28.937669916551**。
这个数是可复算的常数，`verify.py` 的 AC-07 每次重建它。

## 4. 提交格式（原文）

> "The submission file requires a unique integer `id` column."

> "```\nid,n,square_id,x,y,angle\n0,1,0,0.5,0.5,0\n```"

> "Coordinates must be plain decimal literals, optionally in scientific notation. A puzzle whose
> coordinates do not parse is charged the grid ceiling. The container side length L is not
> submitted; it is computed from your squares."

**判据落地**：AC-01（表头与 id 连续）、AC-02（每题恰好 n 行、`square_id` 覆盖 `0..n−1`）、
AC-03（坐标是十进制字面量）、AC-05（L 由 CSV 复算，不信 results.json）。

## 5. 时间、奖金、资格（原文）

> "**October 21, 2026** - Start Date. **January 17, 2027** - 3 Month Milestone Cut-off Date.
> **April 18, 2027** - 6 Month Milestone Cut-off Date. **July 11, 2027** - Entry Deadline.
> **July 18, 2027** - Final Submission Deadline."

> "1st Place - $12,000 / 2nd Place - $10,000 / 3rd Place - $8,000 / 4th Place - $5,000 /
> 5th Place - $5,000" + 两个里程碑各 $5,000。

> "(ii) the older of 18 years old or the age of majority in your jurisdiction ... (iii) not a
> resident of Crimea, so-called Donetsk People's Republic (DNR) or Luhansk People's Republic (LNR),
> Cuba, Iran, or North Korea; and (iv) not a person or representative of an entity under U.S.
> export controls or sanctions."

> "Competitions are open to residents of the United States and worldwide, except that if you are a
> resident of Crimea ... you may not enter the Competition."

**判读**：中国内地不在排除名单；单人可报；免费。

## 6. 外部数据（原文）

> "you may use data other than the Competition Data ("**External Data**") to develop and test your
> Submissions. However, you will ensure the External Data is either publicly available and equally
> accessible to use by all Participants ... at no cost to the other Participants"

**本作品怎么用它**：只用公开记录表（Friedman / Ellsworth packing center）做**逐题对照**，
不读取、不拷贝其中任何坐标；提交里的每一个坐标都由本仓库的 `pipeline/` 生成。
`out/_record_table.html` 是抓下来的对照快照，`scripts/parse_record.py` 只抽边長。

## 7. 验收条件（AC-01…AC-12）

| 编号 | 断言 | 在哪 |
|---|---|---|
| AC-01 | 提交表头恰为 `id,n,square_id,x,y,angle`，`id` 从 0 连续 | `harness/verify.py` |
| AC-02 | 每题恰好 n 行，`square_id` 恰为 `0..n−1` | 同上 |
| AC-03 | 三个数值列都是十进制字面量且有限 | 同上 |
| AC-04 | 逐对分离轴检验，最坏 `gap ≥ −1e-9` | 同上 |
| AC-05 | `L` 由 CSV 重算，与 `results.json` 的最大偏差 ≤ 1e-9 | 同上 |
| AC-06 | 总分 = 逐题 `L/√n − 1` 之和（≤1e-9） | 同上 |
| AC-07 | 方陣基线重建为 28.937669916551 | 同上 |
| AC-08 | 没有任何一题比方陣差；改进题数可从结果复算 | 同上 |
| AC-09 | `out/packings.npz` 重算的 `L` 与 `results.json` 一致（≤1e-12） | 同上 |
| AC-10 | `REPORT.md` 引用的总分/基线/改进数都存在于 `results.json` | 同上 |
| AC-11 | `site/index.html` 单档、无任何外链请求 | 同上 |
| AC-12 | `README.md` 的复现命令都指向真实存在的路径 | 同上 |

## 8. 不做什麼

- 不对隐藏测试集做任何手工摆布（本题没有隐藏测试集，1000 题全公开）。
- 不拷贝记录表里的坐标；记录表只用来算「我们离人类最好还差多少」。
- 不为某几个 n 手工调座標：所有改进必须能被 `scripts/solve.py` 用固定种子重跑出来。
