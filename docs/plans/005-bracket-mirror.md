# Plan 005 — Bracket Mirror Layout

> **状态**: `proposed` → 用户"干"批准 → `planned` → 执行 → `completed`
> **创建日期**: 2026-06-12
> **关联 plan**: [003-bracket-view.md](003-bracket-view.md) (前置单列版)
> **用户驱动**: 用户再次贴 Bing 对阵图说"还是这个对阵图好看"

## 背景

Plan 003 做了单列 5 列对阵图（R32 → Final 单行）。但 Bing 的镜像式布局（8 R32 左 + 8 R32 右 → 居中 Final）视觉上更"tree"、更有"对阵"感。

刚才分析数据时**意外发现**：R16 的 `W73 vs W75` 是**显式配对信号**——W73 是 R32 第 1 场胜者，W75 是 R32 第 3 场胜者。意味着 R16-1 = R32-1 + R32-3，可以反推完整 bracket 树。

## 范围

### In Scope

1. **Bracket pairings 模块** (`src/data/bracket_pairings.py`)
   - 从 R16 的 W## 引用反推 R32 配对
   - 推导 R16→QF、QF→SF、SF→Final 标准配对
   - 配对逻辑有 pytest 覆盖

2. **镜像布局**（替换 Plan 003 的单列）
   - 9 列 CSS grid：R32-top | R16-top | QF-top | SF-top | **Final** | SF-bot | QF-bot | R16-bot | R32-bot
   - 16 行：上半场占 1-8，下半场占 9-16，Final 跨全部 16 行
   - 行 span：R32=1, R16=2, QF=4, SF=8, Final=16

3. **基础连接线**（CSS pseudo-elements）
   - 每张卡片 `::after` 向右延伸、`::before` 向左延伸
   - R32 第一列和最右列不画左/右线（无邻居）
   - Final 不画线（终态）
   - 不用 SVG，不用 elbow，先做"dotted 暗示"视觉

4. **R32 按 bracket 位置重排**
   - 用日期升序 = FIFA bracket 位置（巧合但好用）
   - 配对逻辑依赖这个顺序

5. **更紧凑的卡片**
   - 适配 9 列窄屏
   - 日期用短格式（"7/04" 代替 "2026-07-04"）

### Out of Scope（下次 plan）

- ❌ 完整 elbow 风格连接线（需要更复杂的 CSS 或 SVG）
- ❌ 比赛详情弹窗（Plan 006）
- ❌ 双语 UI 切换（Plan 007）
- ❌ 比分实时更新（Plan 008）
- ❌ Standings tab

## 任务清单

| # | 任务 | 状态 |
|---|------|------|
| 1 | 写 `src/data/bracket_pairings.py` | ⏳ |
| 2 | 写 `tests/test_bracket_pairings.py` | ⏳ |
| 3 | 改 `main.js` 的 `renderBracket` 用镜像布局 | ⏳ |
| 4 | 改 `main.css` 替换单列 `.bracket` 为 `.bracket-mirror` | ⏳ |
| 5 | 跑全部测试 | ⏳ |
| 6 | 烟测 | ⏳ |
| 7 | commit | ⏳ |

## 验收

### 必须

- [ ] 9 列镜像布局显示
- [ ] Top half 8 R32 + 4 R16 + 2 QF + 1 SF（rows 1-8）
- [ ] Bot half 8 R32 + 4 R16 + 2 QF + 1 SF（rows 9-16）
- [ ] Final 居中跨 16 行
- [ ] 季军战仍在下方
- [ ] R16 卡片视觉在 2 个 R32 父卡片中间
- [ ] QF 卡片视觉在 2 个 R16 父卡片中间
- [ ] 配对函数测试通过
- [ ] 原有 68 pytest 仍全过
- [ ] 4 端点仍 200

### 应该

- [ ] 卡片间有基础连接线
- [ ] 横向滚动可用
- [ ] 卡片在窄列里文字不溢出

## Bracket 配对表（推导结果）

| 子轮 | 子 | 子 | 父轮 | 父 |
|------|----|----|------|----|
| R32-1 (W73) | 2A vs 2B | R16-1 | W73 vs W75 |
| R32-3 (W75) | 1E vs 3A/B/C/D/F | | |
| R16-1 | W73 vs W75 | QF-1 | W89 vs W90 |
| R16-2 | W74 vs W77 | | |

（详见代码和测试）

## 风险

| 风险 | 缓解 |
|------|------|
| 9 列在窄屏挤 | `min-width: 900px` + `overflow-x: auto` 横向滚动 |
| 连接线不画 elbow 看起来"断" | 加细灰色虚线，视觉上"暗示"路径 |
| 配对错位 | 严格按 W## 数字反推，测试覆盖 |
| 卡片太挤显示不下 | 短日期格式 + 字号缩小 |

## 决策记录

- **不在 API 暴露 pairings** —— 数据量小，前端用相同算法推导（Python 实现供测试，JS 重复实现）
- **R32 顺序** —— 日期升序 = bracket 位置，巧合不需硬编码
- **Final 跨 16 行** —— 视觉"树"汇于一点
- **连接线** —— 只画水平短线（pseudo-element），不画 elbow。elbow 太复杂，下个 plan 再升级
- **季军战** —— 单独一列在镜像下方，不参与镜像结构
