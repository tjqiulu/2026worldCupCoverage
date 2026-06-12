# Plan 003 — Bracket View

> **状态**: `proposed` → 用户"干"批准 → `planned` → 执行 → `completed`
> **创建日期**: 2026-06-12
> **关联 plan**: [002-ics-parser-and-flask.md](002-ics-parser-and-flask.md) (前置)
> **用户驱动**: 用户看到 Plan 002 截图后说"我希望是这样，方便看分组和对阵关系"，并附参考图

## 背景

Plan 002 做出了按日期分组的"赛程"列表视图。用户想要的还有"对阵"视图——经典 tournament bracket，把 32 场 R32 → 8 R16 → 4 QF → 2 SF → 1 Final 画成树状结构，一眼看清谁打谁。

## 范围

### In Scope

1. **Tab 导航**（顶部）
   - 两个 tab：赛程 Matches / 对阵 Bracket
   - 默认 Bracket（用户重点要这个）
   - 切 tab 切换 view，不重新拉数据

2. **对阵视图**（新）
   - 5 列网格：R32 | R16 | QF | SF | Final
   - 每列卡片上下居中对齐（用 CSS grid + row span）
     - R32: 16 张，每张 1 行
     - R16: 8 张，每张跨 2 行
     - QF: 4 张，每张跨 4 行
     - SF: 2 张，每张跨 8 行
     - Final: 1 张，跨 16 行
   - 季军战单独一行在 bracket 下方
   - 卡片显示：日期、时间、双方（占位符 1E/W73/L101 等）
   - 顶部列名标签
   - 时间继续用北京时间（Plan 002 改的）

3. **赛程视图保留**
   - 原 list 视图不变
   - 切到 Bracket 时不卸载（切回来仍在）

### Out of Scope（后续 plan 再说）

- ❌ R32 → R16 的连接线（需要维护 FIFA bracket pairing map）
- ❌ Standings tab / Stats tab
- ❌ 国旗（Plan 004+）
- ❌ 详情弹窗（Plan 005+）
- ❌ 点击交互（点卡片啥也不做，下个 plan 加）
- ❌ 响应式断点优化（最小可滚动即可）

## 任务清单

| # | 任务 | 状态 |
|---|------|------|
| 1 | 改 index.html 加 tab nav + bracket view 容器 | ⏳ |
| 2 | 改 main.css 加 tab/bracket 样式 | ⏳ |
| 3 | 改 main.js 加 renderBracket() + showTab() | ⏳ |
| 4 | 烟测（启动 Flask + 看两个 tab 都显示） | ⏳ |
| 5 | git commit | ⏳ |

## 验收

### 必须

- [ ] 顶部两个 tab 可见
- [ ] 默认选中"对阵"
- [ ] Bracket 视图显示 32+8+4+2+1=47 场淘汰赛 + 1 场季军战
- [ ] R32 16 张卡片垂直堆叠
- [ ] R16 8 张卡片在 R32 视觉中线上
- [ ] QF/SF/Final 同样视觉居中
- [ ] 时间是北京时间
- [ ] 切到"赛程"tab 还能看到 list
- [ ] 切回"对阵"tab 状态保持
- [ ] 39 pytest 仍全过

### 应该

- [ ] 卡片 hover 有视觉反馈
- [ ] 横向滚动在窄屏可用
- [ ] 季军战有独立视觉（灰色或单独行）

## 不动的文件

- `src/data/*` — 数据不变
- `src/app.py` — API 不变（前端用现有 `/api/matches`）
- `tests/*` — 不加新测试（bracket 渲染是纯 JS，视觉验证足够）

## 风险

| 风险 | 缓解 |
|------|------|
| 32+8+4+2+1 卡片在小屏挤一起 | `overflow-x: auto` 横向滚动 |
| 卡片高度不一致导致对齐丑 | 用固定 `min-height` + `align-self: center` |
| 16 行 grid 占太多垂直空间 | 卡片紧凑（每张 50-60px 高），整体 ~900px 高 |
| tab 切换闪烁 | tab 只是 display 切换，无重新渲染开销 |

## 决策记录

- **CSS Grid 而非 SVG/Canvas** —— 简单、维护性高，视觉够用
- **不画连接线** —— 减少复杂度，连接线等知道 FIFA bracket map 后再加
- **顺序按日期** —— 不强行按 FIFA bracket 顺序排序（不知道确切顺序）
- **默认 Bracket 视图** —— 用户重点要这个
- **季军战单独行** —— 不放进 SF 区域（结构上是单独的）
