# Plan 009 — Match Detail Modal

> **状态**: `proposed` → 用户"继续做下一个接真是数据，详情弹窗" → `planned` → 执行 → `completed`
> **创建日期**: 2026-06-12
> **关联 plan**: [008-left-right-symmetric.md](008-left-right-symmetric.md) (前置)
> **用户驱动**: 反馈 bracket 视觉"顺眼不少"后，立即要求下一个：详情弹窗

## 背景

Plan 008 把 bracket 视觉调好（8.5/10，8 闸 audit 全过）。用户认可后要求加详情弹窗——点比赛卡片能看完整信息。

"接真是数据" = 把已有的真实数据（48 队 mapping + baires ICS）展示给用户，而不是只显示 3 字母码 / 抽象占位符。

## 范围

### In Scope

1. **Modal HTML 标记**
   - 固定定位覆盖全屏
   - 中心卡片 (max 600px wide)
   - 半透明背景遮罩
   - 关闭按钮 (X)
   - `hidden` 属性控制显隐

2. **Modal 内容**
   - 顶部: 赛事阶段（"小组赛 Group A · 第 1 轮" / "1/8 决赛 R32" / "决赛 Final"）
   - 中部: 日期 + 北京时间（"7月5日 周六 01:00 北京时间"）
   - 队伍区域: 
     - 真实国家：大国旗 (80x60px) + 中文名 + 英文名
     - 占位符 (1E / W86 / L101)：代码 + 描述（"E 组第一" / "86 场胜者" / "101 场败者"）
   - "vs" 分隔
   - 底部: 场地（"Mexico City, Mexico"）

3. **交互**
   - 点任何比赛卡片（matches 视图 / bracket 视图）→ 打开 modal
   - 卡片 hover 提示可点击（cursor: pointer + 阴影）
   - 关闭方式：X 按钮 / 点背景 / ESC 键
   - 平滑 fade-in 动画

4. **e2e 测试**
   - 点 matches 视图比赛卡片 → modal 打开，含真实队伍信息
   - 点 bracket 视图 R32 卡片 → modal 打开，含占位符描述
   - 关闭按钮工作
   - ESC 键关闭
   - 点击背景关闭

5. **视觉 review**
   - 8.5/10+ 保持
   - Modal 视觉与 bracket 风格一致

### Out of Scope

- ❌ 实时比分
- ❌ 进球详情（要 details.json 维护，留 Plan 010）
- ❌ 阵容/裁判/TV 频道
- ❌ 收藏关注球队
- ❌ 模态框拖动/缩放

## 任务清单

| # | 任务 | 状态 |
|---|------|------|
| 1 | 写 modal HTML 标记 | ⏳ |
| 2 | 写 modal CSS（覆盖+卡片+动画） | ⏳ |
| 3 | 写 modal JS（show/hide/click handlers） | ⏳ |
| 4 | 写 renderModalTeam()（真实国家 vs 占位符） | ⏳ |
| 5 | 给所有比赛卡片加 click handler + cursor | ⏳ |
| 6 | e2e 测试 | ⏳ |
| 7 | 跑全部测试 | ⏳ |
| 8 | 截图 + 视觉 review | ⏳ |
| 9 | commit | ⏳ |

## 验收

### 必须

- [ ] 点 matches 视图卡片 → modal 打开，显示完整赛事信息
- [ ] 点 bracket 视图卡片 → modal 打开
- [ ] 真实国家显示大国旗 + 中英名
- [ ] 占位符（1E/W86/L101）显示代码 + 描述
- [ ] X 按钮、点背景、ESC 三种关闭方式都工作
- [ ] 38+ e2e + 96 unit 全过
- [ ] 8 闸 audit 仍全过

## 风险

| 风险 | 缓解 |
|------|------|
| 占位符描述不准确 | 用 "W##" 简单映射（"## 场胜者"） |
| 点卡片时不小心触发其他操作 | stopPropagation 不需要（卡片没其他 listener） |
| Modal 闪屏/动画卡顿 | CSS transition 0.2s |
| Z-index 冲突 | modal z-index: 1000，足够高 |

## 决策记录

- **触发范围** —— 所有 `.match-card` 和 `.bracket-card`，不论视图
- **国旗大小** —— modal 内用 80x60px（比卡片内大 5x），更有"详情页"感
- **占位符描述** —— 只用通用规则（W## = ## 场胜者, L## = ## 场败者, 1X = X 组第一, 2X = X 组第二, 3X = X 组第三）
- **不**支持点链接/分享
- **不**支持键盘导航（Tab 顺序）
- **不**显示具体比分（无数据源）
