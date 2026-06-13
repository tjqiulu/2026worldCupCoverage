# Plan 016 — Widget mode + refresh cache fix

> **状态**: `proposed` → 用户"比赛结束还没出来成绩？...怎么推出全屏模式，最好做成桌面背景" → `planned` → 执行 → `completed`
> **创建日期**: 2026-06-13
> **关联 plan**: [013-desktop-launcher.md](013-desktop-launcher.md) (kiosk 全屏), [015-detail-page-content.md](015-detail-page-content.md) (modal 已经有内容)

## 背景

用户反馈两个问题：
1. **比赛结束还没出成绩** — Canada-Bosnia (6/13 03:00 BJT) 已经过 6 小时但 modal 显示"待更新"
2. **桌面背景模式** — 当前 Plan 013 launcher 是 kiosk 全屏，挡住工作。需要小巧、可放在屏幕侧边、不抢焦点的 widget

## 问题分析

### 问题 1：比分延迟
- worldcup26.ir `/get/games` API 是**人工更新**（不是实时的），截至 6/13 09:00 只标了 MD1 3 场完赛
- Canada-Bosnia MD2 还没录入
- 我们的 auto-detect 正确判定为"已结束"，但 API 无数据 → 显示"待更新"
- **真 bug**: `/api/refresh` 受 5 分钟内存缓存挡 — 5 分钟内多次刷新看到的都是旧数据

### 问题 2：桌面 widget
- Plan 013 launcher 是 kiosk fullscreen → 抢焦点
- 想要：可缩放、贴在屏幕一角、不挡其他应用、自动刷新

## 方案

### Fix 1: /api/refresh 强制清缓存
- 调用 `clear_cache()` 后再 `fetch_details_for_matches()`
- 用户点刷新 → 总是拉到最新 API
- 5 分钟缓存保留给"页面静默轮询"用（如果将来加）

### Feature 2: Widget mode
- URL `/?view=widget`
- 隐藏 header/tabs/footer，只显示比赛卡片
- 紧凑单卡：左边国旗 + 队名 | 中间比分/vs | 右边国旗 + 队名
- 底部小字：时间 + 阶段 + 状态徽章
- 自动 60s 静默刷新（不打断）
- 点击卡片仍能弹 modal（看 Plan 015 的完整详情）
- 适配 380x500 视口，无横向滚动

## 范围

### In Scope

1. **`src/app.py`** `/api/refresh` 调 `clear_api_cache()` 在 fetch 之前
2. **`src/static/js/main.js`**
   - `initWidgetMode()` — 检测 URL 参数，切到 widget 渲染
   - `renderWidget(matches)` — 选今日本日 + 最近 3 小时已结束 + 未来 5 场
   - `renderWidgetCard(m)` — 单卡 HTML
   - `setInterval` 60s 后台 fetch
3. **`src/templates/index.html`** 加 `#widget-view` 容器
4. **`src/static/css/main.css`** widget 样式（紧凑、半透明背景、live 红边、徽章）
5. **点击 modal** 复用 Plan 015 的 `showMatchModal`（含 stadium/standings/countdown）
6. **e2e 测试** 11 个
7. **Plan 016 doc + audit**

### Out of Scope

- ❌ 真正的 always-on-top 窗口（OS 层面）— 浏览器做不到，需要 native app (Tauri)
- ❌ 多 widget 缩略图（一个 widget 看多个比赛/赛事）
- ❌ 用户拖拽 / 调整大小（浏览器原生 window 控制）
- ❌ 系统托盘图标

## 决策

- **Widget 不用 native 框架** — 浏览器 PWA 够用，零额外构建复杂度
- **60s 静默刷新** — 不打扰用户，比 5min 缓存更实时
- **首选"今日"比赛** — 大多数时候用户看的是"今天有哪些比赛"
- **如今日无比赛** — 显 next 5 upcoming
- **如今日有比赛** — 也插最近 3 场已结束（避免错过刚完赛的）
- **点击 modal** — 复用 Plan 015，不重写
- **小屏优先** — 设计 380x500，向上兼容到 800x600

## 使用方式

### 用户在桌面开 widget
```bash
# 1. 启动 Flask（如果还没跑）
cd /home/lqiu/.openclaw/workspace/2026worldCupCoverage
bin/launch.py  # 或 python3 -m src.app

# 2. 浏览器打开
# Linux:   chromium --window-size=380x500 --window-position=1500,100 http://127.0.0.1:8766/?view=widget
# macOS:   Chrome → 调整窗口大小到 380x500，移动到右上角
# Windows: 同上

# 3. (可选) 设置 always-on-top
# Linux:   wmctrl -r "WC 2026" -b add,above
# macOS:   Afloat 插件 / Rectangle + Always On Top
# Windows: AutoHotkey 脚本
```

### 截图位置
`tests/e2e/screenshots/widget_view.png` — 380x500 实际渲染

## 测试

- 11 个 e2e 测试（widget 布局 + 分数 + 交互 + 缓存 bypass）
- 全测试 266+11=277 应全过

## 风险

| 风险 | 缓解 |
|------|------|
| 60s 静默刷新在断网时刷屏错 | catch + log warning，不打断 |
| Widget 卡片在极窄屏（<280px）破裂 | 设计下限 380px，更小浏览器横滚 |
| Always-on-top 需 OS 配置 | 文档指引 wmctrl 等；不强制 |
| Modal 在 widget 模式弹出太大 | modal 仍 480px 居中，不超 viewport |
| clear_cache() 误清 stadium/groups/teams 缓存 | 一次清 4 个 cache，刷新会重拉 4 个端点（4s 内完成）|

## 验收 / 8 闸 closure audit

- G1: `/?view=widget` 渲染紧凑卡片
- G2: header/tabs/footer 在 widget 隐藏
- G3: 卡片含时间/双方/状态
- G4: 完场/进行中比赛显示分数
- G5: 点击卡片弹 modal（含 Plan 015 所有 section）
- G6: `/api/refresh` 强制清缓存
- G7: 60s 自动刷新（测试验证 fetch 调用）
- G8: 380x500 视口无横滚
