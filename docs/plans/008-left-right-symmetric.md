# Plan 008 — Left-Right Symmetric Bracket Layout

> **状态**: `proposed` → 用户"测试代码要改进，确保达到设计效果" → `planned` → 执行 → `completed`
> **创建日期**: 2026-06-12
> **关联 plan**: [007-bracket-connecting-lines.md](007-bracket-connecting-lines.md) (前置)
> **用户驱动**: "左右没有对齐，他是左右对称结构的"
> **诊断**: Plan 005/007 是"垂直镜像"（top 半区在 col 1-4 rows 1-8，bot 半区在 col 6-9 rows 9-16）——数学上对称但视觉上 top 在左上、bot 在右下，"不并列"。用户要的是"水平镜像"：top 和 bot 都在同一行高。

## 背景

之前的 16 行布局：
- LEFT 半区（col 1-4）= 小组赛上半段，rows 1-8
- RIGHT 半区（col 6-9）= 小组赛下半段，rows 9-16
- Final 跨 rows 1-16

虽然 R16 居中 0.00px 完美，但视觉上"上半区都在上面"和"下半区都在下面"，不是用户期望的"左右并列对称"。

## 范围

### In Scope

1. **重新布局为 8 行**（核心）
   - 全部 8 行都用，**不留空白**
   - Top 半区 R32 (col 1) rows 1-8
   - Top 半区 R16 (col 2) rows 1,3,5,7 (span 2)
   - Top 半区 QF (col 3) rows 1,5 (span 4)
   - Top 半区 SF (col 4) row 1 (span 8)
   - Final (col 5) row 1 (span 8)
   - Bot 半区 SF (col 6) row 1 (span 8)
   - Bot 半区 QF (col 7) rows 1,5 (span 4)
   - Bot 半区 R16 (col 8) rows 1,3,5,7 (span 2)
   - Bot 半区 R32 (col 9) rows 1-8

2. **Connecting lines 方向智能**
   - Top 半区: parent 在 col 1-4, child 在右 → line 从 parent.right 到 child.left（向右）
   - Bot 半区: parent 在 col 6-9, child 在左 → line 从 parent.left 到 child.right（向左）
   - `connect()` 函数需要判断方向

3. **e2e 测试严格化**（用户要求）
   - **新测试**: 左右对称性严格断言
     - R32[col 1, pos i].center_y == R32[col 9, pos (15-i)].center_y (i=0..7)
     - R16[col 2].center_y == R16[col 8, mirrored].center_y
     - 同理 QF 和 SF
     - tolerance < 2px
   - 这些测试会**强制**设计为左右对称，否则 FAIL
   - 用户具体要求："测试代码要改进，确保达到设计效果"

4. **视觉评分目标**
   - Vision model ≥ 8.5/10 (现在 8.5)
   - 8 闸 audit 仍全过

### Out of Scope

- ❌ 改 Final 居中方式（仍在 col 5）
- ❌ 改卡片大小（保持当前）
- ❌ 加更多功能
- ❌ 重新设计整张图

## 任务清单

| # | 任务 | 状态 |
|---|------|------|
| 1 | 改 CSS: `repeat(8, ...)` rows | ⏳ |
| 2 | 改 JS renderBracket: 8 行布局 | ⏳ |
| 3 | 改 JS connect: 支持双向 | ⏳ |
| 4 | 改 e2e: 左↔右镜像测试 | ⏳ |
| 5 | 跑测试 | ⏳ |
| 6 | 截图 + vision model 评分 | ⏳ |
| 7 | commit | ⏳ |

## 验收

### 必须

- [ ] 8 行布局，**全部使用**，不留空白
- [ ] e2e: 严格左↔右镜像测试通过（< 2px tolerance）
- [ ] 38/38 e2e + 96/96 unit 全过
- [ ] 视觉评分 ≥ 8.5/10（与上次持平或更高）
- [ ] Connecting lines 方向正确（top 向右，bot 向左）

## 风险

| 风险 | 缓解 |
|------|------|
| 卡片位置变化导致旧测试失败 | 改测试以匹配新布局 |
| Final 跨 8 行（vs 16 行）视觉变扁 | 接受——本来更紧凑是好事 |
| 8 行 grid 高度只有 ~430px | 紧凑，反而不占屏 |

## 决策记录

- **8 行 vs 16 行** —— 用户要"左右并列"，8 行让两半区在同 y 位置
- **保留 T 型连接线结构** —— 不变
- **智能方向 detect** —— connect() 函数根据 parent/child 相对位置决定用哪条边
- **不改 card 大小** —— 保持现样
- **不**让 Final 居中跨 16 行——在 8 行布局里，Final 跨全部 8 行就够"居中"
