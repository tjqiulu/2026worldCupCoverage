# Plan 007 — Bracket Connecting Lines

> **状态**: `proposed` → 用户要求 audit gate 8 通过 → `planned` → 执行 → `completed`
> **创建日期**: 2026-06-12
> **关联 plan**: [005-bracket-mirror.md](005-bracket-mirror.md) (前置)
> **用户驱动**: 反馈"还是不对齐"+ audit 8 闸全过要求
> **诊断**: 像素测量 R16 居中 0.00px 完美，但视觉 6/10 因为**缺 SVG 连接线**——R32→R16→QF→SF→Final 树状关系要靠猜

## 背景

Plan 005 做了镜像布局，Plan 005+fix 修了 R32 顺序让 R16 居中。客观测量 R16 居中 imbalance = 0.00px（完美）。

但 Plan 006 closure audit gate 8 视觉 review 只给了 6/10。Vision model 反馈：
- 缺 SVG 连接线（elbow pattern）——R32→R16 路径要靠空间位置猜
- 整体"中空感"重——没有视觉张力
- 左右镜像在视觉上不"对称"（虽然 R32 顺序对称）

## 范围

### In Scope

1. **SVG 连接线**（核心）
   - 在 bracket-mirror 容器内加 `<svg>` 覆盖层
   - SVG 在卡片**下方**（z-index: 0，卡片 z-index: 1）
   - Elbow 路径：水平短线（4px 已有）+ 真实连接线
   - 30 条线：
     - R32 → R16: 16 条
     - R16 → QF: 8 条
     - QF → SF: 4 条
     - SF → Final: 2 条
   - 颜色：浅灰 `#bbb` 或 `#999`，1px 粗
   - 端点：方头（不是 round，避免视觉噪点）

2. **布局逻辑**
   - Elbow pattern：从父卡片右边缘 → 垂直下降到子卡片高度 → 水平到子卡片左边缘
   - 或：父右边缘 → 水平短出 → 垂直下降到子高度 → 水平到子左边缘
   - 用最简 `L` 形（垂直 + 水平两段）

3. **e2e 测试**
   - SVG 元素存在
   - 30 条 line/path 元素
   - 每条线的起点在父卡片右边缘（±2px）
   - 每条线的终点在子卡片左边缘（±2px）
   - 至少 1 张新截图（视觉 review）

4. **视觉评分目标**
   - Vision model 评分 ≥ 8/10
   - 8 闸 closure audit 全过

### Out of Scope

- ❌ 改产品代码除 SVG 外的部分
- ❌ 动态高亮（hover 父卡→高亮子卡+线）—— 留 Plan 008
- ❌ 颜色主题切换
- ❌ 动画效果

## 任务清单

| # | 任务 | 状态 |
|---|------|------|
| 1 | 改 HTML/CSS：wrapper + SVG 容器 + z-index | ⏳ |
| 2 | 改 JS：渲染 SVG 连接线（基于 pairings） | ⏳ |
| 3 | e2e 测试：line count + 端点位置 | ⏳ |
| 4 | 跑全部测试 | ⏳ |
| 5 | 截图 + vision model 评分 | ⏳ |
| 6 | 8 闸 audit 全过 | ⏳ |
| 7 | commit | ⏳ |

## 验收

### 必须

- [ ] 30 条 line/path 渲染正确
- [ ] 起点在父卡片右边缘 ±2px
- [ ] 终点在子卡片左边缘 ±2px
- [ ] 96 unit + 33 e2e + N line tests 全过
- [ ] 8 闸 closure audit 全过
- [ ] Vision model 评分 ≥ 8/10

## 决策记录

- **SVG 而非 canvas** —— 30 条线不需要 canvas 的性能，SVG 更易维护
- **SVG 在卡片下方** —— 卡片 hover 仍能正常显示
- **Elbow 走垂直段** —— 走垂直段后到子卡片左边缘，避免横穿其他卡片
- **不动态计算颜色/动画** —— 留 Plan 008
- **不加端点标记** —— 朴素线段，避免视觉噪点
