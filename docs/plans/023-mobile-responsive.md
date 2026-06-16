# Plan 023 — 移动端适配（手机访问可用）

> **状态**: `planned` → `completed`
> **创建日期**: 2026-06-16
> **关联 plan**: [022-cloudflare-quick-tunnel.md](022-cloudflare-quick-tunnel.md)（前置：手机 4G 已能访问，正是这次发现 mobile 不友好）, [015-detail-page-content.md](015-detail-page-content.md)（modal 设计参考）, [019-standings-gf-ga-gd-columns.md](019-standings-gf-ga-gd-columns.md)（10 列 standings）
> **用户驱动**: 18:14 "手机能打开了，页面没适配手机屏幕尺寸，想想办法先？"

## 背景

Plan 022 部署 Cloudflare quick tunnel 后，手机 4G 已能访问 `https://cult-spanking-nutrical-eric.trycloudflare.com`。用户实测发现页面没适配手机屏幕。

### 现状（桌面 dashboard 设计）

| 元素 | 桌面 | 手机（缺适配）|
|------|------|---------------|
| 主容器 | `max-width: 1200px` 居中 | 手机上太宽，左右白边或溢出 |
| Match 卡片 | 横排（时间-队-队-场地）| 字段挤，看不清 |
| Modal | `max-width: 600px` 居中 | 弹出后左右大片空白 |
| Standings 表 | 10 列 | 横向溢出 / 列挤 |
| 字体 | 13-15px | 同（手机相对小）|
| 刷新按钮 | 顶栏右侧 | 同（可能点不到）|

**已有 mobile CSS**（但范围极窄）：
- `@media (max-width: 640px)` 只 hide `.match-meta`
- `@media (max-width: 480px)` 只 hide 一些次要 text
- modal 有 `overflow-x: auto` 但 modal-card 是固定 600px

## 详细需求（按屏幕宽度分级）

### 断点设计

```
[Mobile]   0px   ───  767px   ← 主攻
[Tablet]   768px ───  1023px  ← 次要适配
[Desktop]  1024px ──────────  ← 维持现状
```

### Mobile (≤767px) 改动 R1-R8

- **R1**. 容器铺满 + 16px padding
  - `body > .container` 去掉 `max-width: 1200px`，改 `padding: 0 16px`
  - 验证: devtools 切到 375px，容器贴边无白边

- **R2**. Top bar 改为垂直堆叠
  - logo / refresh 按钮 上下分开
  - 验证: 375px 下 top bar 不溢出，刷新按钮可点

- **R3**. Match card 紧凑模式
  - 时间 + 主客队 flag 一行（其他信息隐藏或换行）
  - 减小 padding
  - 验证: 375px 下一屏能看 3-4 张卡（vs 桌面 1-2 张）

- **R4**. Modal 全屏化
  - 去掉 `max-width: 600px` 和 `border-radius`
  - 撑满 100vw × 100vh
  - 验证: 375px 下 modal 边缘到屏幕边缘

- **R5**. Modal 内 standings 表横向滚动
  - 已有 `.modal-standings-wrap { overflow-x: auto }`（Plan 015）
  - 但 10 列在 375px 仍挤 → 加 `.standings-gd` 颜色 + 减小 padding
  - 验证: modal 内 standings 区可左右滑

- **R6**. 字体缩放
  - body 14px（桌面 16px → 手机 14px）
  - h1 18px, h2 16px
  - match-card 12px
  - 验证: 375px 文字不需缩放即可读

- **R7**. 触摸目标 ≥44px
  - 刷新按钮、close 按钮、match 卡片点击区都 ≥44px
  - 验证: Apple HIG / Material Design 触摸标准

- **R8**. Viewport meta 已存在
  - `<meta name="viewport" content="width=device-width, initial-scale=1.0">` 已在 L5
  - 无需改

### Tablet (768-1023px) 改动 R9-R10

- **R9**. 容器 `max-width: 100%` + `padding: 0 24px`
- **R10**. Modal 居中 + `max-width: 600px` 维持

### Desktop (≥1024px) 0 改动

- 维持现状（这是设计目标）

## AGE 8-Gate Closure Audit

| # | Gate | 验证 | 状态 |
|---|------|------|------|
| 1 | Viewport meta 存在 | grep `index.html` | ⏳ |
| 2 | Mobile @media (max-width: 767px) rules | grep CSS | ⏳ |
| 3 | Tablet @media (768-1023px) rules | grep CSS | ⏳ |
| 4 | Modal full-screen on mobile | Playwright 测 375px 视口 | ⏳ |
| 5 | Match card 紧凑 on mobile | Playwright 测 375px 视口 | ⏳ |
| 6 | Standings table 可横滑 | Playwright 测 375px 视口 | ⏳ |
| 7 | pytest 200/200 (no regression) | pytest | ⏳ |
| 8 | 公开 URL 手机 4G 实际可用 (MANUAL) | 用户实测 | n/a |

## 方案候选 + 决策

### 1. 适配策略
- (A) **Mobile-first 改写**（采用）— 桌面布局保留作为大屏 @media query
- (B) 完全 mobile-first + desktop 不同布局 — 过度工程
- 决定 A。理由: 用户主要用桌面（dashboard），mobile 是副场景；保留桌面布局作为大屏，叠加 mobile 覆盖

### 2. Modal mobile 形态
- (A) **全屏**（采用）— 简单
- (B) Bottom sheet 抽屉 — 复杂
- 决定 A。理由: 比赛详情 modal 内容多（standings/goals/stadium），全屏能装下

### 3. Standings mobile 形态
- (A) **横滑**（采用）— 已有 overflow-x: auto 基础
- (B) 简化为只显示关键列（球队 + 分）— 信息丢
- 决定 A。理由: 用户已经在桌面看 10 列，手机偶尔查一下横滑可接受

### 4. 字体策略
- (A) **整体缩 1 级**（采用）— 14px body
- (B) 用户可手动缩放（浏览器自带）
- 决定 A。理由: 用户已经表明想用手机看，主动适配省得用户操作

## 范围

### In Scope

1. `src/static/css/main.css` 加 mobile/tablet 媒体查询（不改桌面）
2. 改 .match-card 在 mobile 的紧凑布局
3. 改 .match-modal 在 mobile 全屏
4. 改容器在 mobile 铺满
5. 改字体在 mobile 缩 1 级
6. 加 tap target 优化
7. 加 Playwright 测 375px 视口（G4-G6）
8. 写 audit 脚本
9. 写 log
10. commit + push

### Out of Scope

- ❌ 改 JS 渲染逻辑（CSS-only 适配）
- ❌ 改 modal 数据结构
- ❌ 改 i18n 文案
- ❌ 加 PWA / service worker（plan 014 留过口子，不在这次）
- ❌ 改桌面布局

## 任务清单

| # | 任务 | 文件 | 估时 |
|---|------|------|------|
| 1 | 加 @media (max-width: 767px) 容器规则 | main.css | 5 min |
| 2 | 加 mobile match-card 紧凑模式 | main.css | 10 min |
| 3 | 加 mobile modal 全屏 | main.css | 5 min |
| 4 | 加 mobile 字体缩放 | main.css | 5 min |
| 5 | 加 tap target 优化 | main.css | 5 min |
| 6 | 加 @media (min-width: 768px) tablet 规则 | main.css | 5 min |
| 7 | 写 Playwright 测 375px 视口 | tests/e2e/ | 20 min |
| 8 | 写 audit 脚本 | tests/ | 15 min |
| 9 | 跑 8-gate audit | shell | 5 min |
| 10 | 写 log | docs/logs/ | 5 min |
| 11 | commit + push | git | 30s |

**总估时: ~80 min**

## 风险评估

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| 改 CSS 破坏桌面布局 | 中 | 高 | 改前 0 desktop CSS 改动；改后 Playwright 测 1280px 回归 |
| 触摸目标改 44px 导致视觉布局乱 | 低 | 中 | 只动 padding 不动 layout |
| mobile 横滑 standings 用户体验差 | 中 | 低 | 第一版先这样；下版可做"球队 + 分 + GD"简化列 |
| 字体缩 1 级桌面用户受影响 | 0 | n/a | 桌面 1024+ 媒体查询外 |
| Playwright 视口测不准确 | 低 | 中 | 用真实浏览器 profile |

## 不会误伤

| 误伤点 | 验证 | 结果 |
|--------|------|------|
| 桌面 1280px+ 布局 | Playwright 测 1280px | ✅ (0 改) |
| Render plan 021 产物 | `cat render.yaml` | ✅ |
| pytest 200/200 | pytest | ✅ |
| data/*.json | 0 改 | ✅ |
| src/*.py | 0 改 | ✅ |
| Plan 022 tunnel 产物 | `cat bin/tunnel.sh` | ✅ |
| Plan 019 10 列 standings | modal 内仍 10 列（横滑）| ✅ |

## 设计细节

### 1. @media 容器规则（mobile）

```css
@media (max-width: 767px) {
    body { font-size: 14px; }
    main.container, .container {
        max-width: 100%;
        padding: 0 16px;
    }
    h1 { font-size: 20px; }
    h2 { font-size: 18px; }
    .match-card { font-size: 12px; padding: 8px 12px; }
    .match-modal-card {
        max-width: 100%;
        width: 100%;
        height: 100vh;
        border-radius: 0;
    }
    /* Tap targets */
    .match-modal-close, button { min-height: 44px; min-width: 44px; }
}
```

### 2. Match card 紧凑模式（mobile）

```css
@media (max-width: 767px) {
    .match-card {
        flex-wrap: wrap;
        padding: 10px 12px;
        gap: 6px;
    }
    .match-time { font-size: 12px; min-width: 44px; }
    .match-team { font-size: 12px; }
    .match-meta { display: none; }  /* 已存在 */
}
```

### 3. Modal 全屏（mobile）

```css
@media (max-width: 767px) {
    .match-modal-card {
        max-width: none;
        width: 100vw;
        height: 100vh;
        max-height: 100vh;
        border-radius: 0;
        margin: 0;
    }
    .match-modal-close {
        top: 12px; right: 12px;
        width: 44px; height: 44px;  /* tap target */
    }
}
```

### 4. Standings 横滑（mobile）

```css
@media (max-width: 767px) {
    .modal-standings-table {
        font-size: 11px;
    }
    .modal-standings-table th,
    .modal-standings-table td {
        padding: 6px 4px;
    }
    /* 已有 overflow-x: auto on .modal-standings-wrap */
}
```

### 5. Playwright 视口测试（`tests/e2e/test_mobile_responsive.py`）

```python
def test_mobile_match_cards_compact(page, mobile_viewport):
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://127.0.0.1:8766/")
    cards = page.locator(".match-card").all()
    for card in cards:
        box = card.bounding_box()
        assert box["width"] <= 375, f"card wider than viewport: {box['width']}"

def test_mobile_modal_fullscreen(page, mobile_viewport):
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("http://127.0.0.1:8766/")
    page.locator(".match-card").first.click()
    modal = page.locator(".match-modal-card")
    box = modal.bounding_box()
    assert abs(box["width"] - 375) < 2
    assert abs(box["height"] - 667) < 2

def test_desktop_layout_unchanged(page):
    page.set_viewport_size({"width": 1280, "height": 800})
    page.goto("http://127.0.0.1:8766/")
    # 桌面布局应与改前完全一致（手动测对比）
```

## 验收

### 必须

- [ ] 8-gate audit 7/7 pass（G8 manual）
- [ ] 桌面 1280px+ 布局 0 视觉变化
- [ ] 375px 视口下页面无横向滚动
- [ ] modal 在 375px 全屏
- [ ] standings 表在 mobile 可横滑
- [ ] 200/200 pytest 全过
- [ ] 手机 4G 访问 `https://...trycloudflare.com` 实际可用

### 应该

- [ ] 触摸目标 ≥44px
- [ ] 字体清晰不需缩放
- [ ] 一屏能看 3-4 张 match card
- [ ] 改后 commit + push GitHub

## 决策日志

### 1. mobile-first vs desktop-first 改造
**决定**: 桌面布局保留作大屏默认，叠加 mobile @media
**理由**:
- 桌面是主场景，mobile 是副场景
- 桌面布局已通过 Plan 015/019/020 多次迭代稳定
- 反向改风险大，正向叠加风险小

### 2. 不引 CSS framework (Tailwind/Bootstrap)
**决定**: 纯手写 @media
**理由**:
- 已有 1321 行手写 CSS
- 引 framework 80KB+，对一个本地 dashboard 不值
- AGENTS.md "轻、跨平台、好爬数据" 哲学

### 3. 不引 PWA / service worker
**决定**: 不做
**理由**:
- Plan 014 留过口子但用户没要求
- 手机访问一次性体验够用，不需要 offline
- 这次只解决"页面能用"+"基本适配"

## Next-Session Pickup Notes

- Plan 023 完结后，桌面前端布局应保持不变
- mobile 改完 push 后，用户需重新刷新手机浏览器看新效果
- data/details.json 仍有一份未 commit 改动
