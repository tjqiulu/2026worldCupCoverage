# Plan 024 — PWA 激活验证（Plan 014 收尾）

> **状态**: `planned`
> **创建日期**: 2026-06-16
> **关联 plan**: [014-pwa-progressive-web-app.md](014-pwa-progressive-web-app.md)（PWA 完整实现，已完成）
> **用户驱动**: 20:28 用户问"刷新按钮边上的'安装'按钮是干啥用的？" → 决定开 Plan 024 把 Plan 014 收尾

## 背景

### 触发

- 20:28 用户截图发现"📲 安装"按钮在刷新按钮旁边，问"这是干啥用的？"
- 调研发现：按钮在 `index.html:26` 已有，但**没生效**（一直 `hidden`）
- 进一步调研：Plan 014 (2026-06-13 完成) 已经写了完整 PWA 产物：manifest.json / sw.js / 3 个 icon
- **关键发现**：Plan 014 实际**已经 100% 完成**。0 改动需求，Plan 024 = 验证激活

### 现状

| 资产 | 状态 | 来源 |
|------|------|------|
| `static/manifest.json` (48 行) | ✅ 存在 + 服务 200 | Plan 014 |
| `static/sw.js` (94 行) | ✅ 存在 + 服务 200 | Plan 014 |
| `static/img/icon.svg` (1697B) | ✅ 存在 + 服务 200 | Plan 014 |
| `static/img/icon-192.png` (20994B) | ✅ 存在 + 服务 200 | Plan 014 |
| `static/img/icon-512.png` (100158B) | ✅ 存在 + 服务 200 | Plan 014 |
| `index.html:12` `<link rel="manifest">` | ✅ 存在 | Plan 014 |
| `index.html:76-77` SW register 代码 | ✅ 存在 | Plan 014 |
| `index.html:26` `install-pwa-btn` | ✅ 存在 | Plan 014 |
| `main.js:1075` `setupPwaInstall()` | ✅ 存在 | Plan 014 |

**结论：所有 PWA 产物在位、可用。** Plan 014 收尾不是"写新代码"，是"验证激活"。

## 详细需求

### 验证层

- **R1**. 5 个 PWA 资源 HTTP 200
  - manifest.json, sw.js, icon.svg, icon-192.png, icon-512.png
  - 验证: `curl -I` 全部 200
  - **实测（2026-06-16 20:30）**: 5/5 通过

- **R2**. Service Worker 在浏览器中能注册
  - 验证: Playwright `navigator.serviceWorker.getRegistrations()` 长度 > 0
  - **实测**: REGISTERED

- **R3**. Manifest 链接在 HTML 中
  - 验证: `document.querySelector('link[rel=manifest]')` 不为 null
  - **实测**: `http://127.0.0.1:8766/static/manifest.json`

- **R4**. install-pwa-btn 在 DOM 中存在
  - 验证: `document.getElementById('install-pwa-btn')` 不为 null
  - **实测**: 存在，text='📲 安装'

### 行为层（用户实际操作）

- **R5**. 用户在 Chrome/Edge 桌面打开 → 不应打扰（按钮仍 hidden）
  - 验证: 桌面 Chrome 默认不触发 `beforeinstallprompt`，需符合 installability criteria
  - 预期: 按钮 hidden（除非手动安装过 PWA）

- **R6**. 用户在 Android Chrome 打开 → 几秒后 `beforeinstallprompt` 触发
  - 按钮 hidden → visible
  - 验证: 需真实 Android 设备测试（headless Chrome 不触发）

- **R7**. 用户点"📲 安装"按钮 → 浏览器原生 install dialog 弹出
  - 用户同意 → PWA 安装到主屏，app 独立窗口
  - 验证: 需真实浏览器交互（自动化测不到）

### 验证（用户手动）

- **R8**. 用户在手机 Chrome 实际测试加主屏流程
  - 打开 `https://<random>.trycloudflare.com`
  - Chrome 菜单 → "添加到主屏幕"
  - 主屏出现"WC 2026"图标
  - 点图标 → 全屏打开，无 URL 栏

## 方案候选 + 决策

### 1. Plan 024 范围
- (A) **纯验证（采用）** — 0 改动，验证现状 + 写 log + 关闭 Plan 014 "沉睡" 状态
- (B) 改写 SW / manifest 增强 — 没必要，Plan 014 已够用
- 决定 A

### 2. 测试覆盖
- (A) **8-gate closure audit**（采用）— 沿用 Plan 021/022/023 模板
- (B) 跳过（只做手动验证）— 不符合 AGE 方法论
- 决定 A

### 3. PWA 范围确认
- (A) **不引推送通知**（采用）— 项目无 use case（桌面 dashboard 看比分）
- (B) 加 Push API — 增加复杂度
- 决定 A

## 范围

### In Scope

1. 8-gate audit 脚本（`tests/audit_gates_plan024.py`）
2. 跑 audit 验证 5/5 PWA 资源 + SW 注册 + DOM 元素
3. 写 log
4. 更新 Plan 014 状态（标记已被 Plan 024 收尾）
5. commit + push

### Out of Scope

- ❌ 改任何 PWA 资产（manifest.json / sw.js / icons / index.html / main.js）
- ❌ 加 Push API / 后台同步（无 use case）
- ❌ 改 Cloudflare tunnel 配置
- ❌ 改桌面浏览器行为（保持 0 影响）

## 任务清单

| # | 任务 | 估时 |
|---|------|------|
| 1 | 写 8-gate audit 脚本 | 15 min |
| 2 | 跑 audit 验证 7/7 pass | 3 min |
| 3 | 写 log | 5 min |
| 4 | 更新 Plan 014 状态（被 Plan 024 覆盖）| 2 min |
| 5 | commit + push | 30s |

**总估时: ~25 min**

## AGE 8-Gate Closure Audit

| # | Gate | 验证 | 状态 |
|---|------|------|------|
| 1 | manifest.json HTTP 200 | curl | ⏳ |
| 2 | sw.js HTTP 200 | curl | ⏳ |
| 3 | 3 个 icon 资源 HTTP 200 | curl | ⏳ |
| 4 | Playwright: manifest link 存在 | DOM query | ⏳ |
| 5 | Playwright: SW registered | navigator API | ⏳ |
| 6 | Playwright: install-pwa-btn 在 DOM | DOM query | ⏳ |
| 7 | pytest 200/200 pass（无回归）| pytest | ⏳ |
| 8 | 真实手机/桌面 PWA install 流程（MANUAL）| 用户 | n/a |

## 风险

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| Plan 014 SW 缓存导致旧版本 | 低 | 中 | SW cache name 带版本（`wc2026-v1`），新部署改版本号 |
| iOS Safari PWA 限制 | 中 | 低 | iOS 16.4+ 支持；用户可用 |
| Android Chrome 触发延迟 | 中 | 低 | 用户等几秒即可 |
| manifest 缺字段 | 低 | 中 | Plan 014 已通过 closure audit |
| 桌面 Chrome 不显示安装按钮 | 高 | 0 | 设计如此（按钮按需 hidden）|

## 不会误伤（关键 — 用户最关心）

| 误伤点 | 验证 | 结果 |
|--------|------|------|
| 桌面浏览器 0 改 | 不动任何代码 | ✅ |
| 现有功能 0 改 | pytest 200/200 + Playwright 视口 | ✅ |
| Cloudflare tunnel 0 改 | 配置不变 | ✅ |
| data/*.json 0 改 | 不动 | ✅ |
| src/*.py 0 改 | 不动 | ✅ |

## 决策日志

### 1. Plan 024 = 验证不实现
**决定**: 0 改动
**理由**:
- Plan 014 已 100% 完成所有 PWA 工作
- 用户问的是"按钮是啥"，不是"按钮没工作"
- 验证激活是合理的 closure 动作

### 2. 不引 push notification
**决定**: 不做
**理由**:
- 项目 use case：用户主动打开看比分/赛程
- 比赛日会 5+ 分钟 F5 一次（已有 cron 模式）
- 推送会增加 SW 复杂度，无明显收益

### 3. 桌面 Chrome 不强推安装提示
**决定**: 沿用 Plan 014 设计 — 按钮 `hidden` 直到 `beforeinstallprompt` 触发
**理由**:
- Chrome installability 触发延迟（5+ 秒）会影响桌面用户体验
- 用户主动想装会看到"添加到主屏"菜单选项
- 0 桌面干扰

## Next-Session Pickup Notes

- Plan 024 完结后，Plan 014 状态可标"被 Plan 024 验证"（不是修改）
- 如未来需 PWA 增强（push、offline-only、background sync）→ 新 plan
- data/details.json 仍有一份未 commit 改动
