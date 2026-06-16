# Plan 014 — PWA (Progressive Web App)

> **状态**: `proposed` → 用户"pwa搞一把" → `planned` → 执行 → `completed` ✅
> **2026-06-16**: 被 [Plan 024](024-pwa-activation.md) 验证激活（8/8 closure audit PASS），PWA 仍功能完整
> **完成日期**: 2026-06-13
> **结果**: 243/243 测试通过（其中 15 个新增 PWA e2e），0 回归
> **commit**: (下方 git 提交)
> **创建日期**: 2026-06-12
> **关联 plan**: [013-desktop-launcher.md](013-desktop-launcher.md) (互补——launcher 用于桌面 kiosk，PWA 用于浏览器安装)

## 背景

Plan 013 加了桌面 launcher（kiosk 全屏），但只解决"桌面用"场景。PWA 提供**另一条使用路径**：
- 用户在 Chrome/Edge 里打开页面 → 浏览器提示"安装应用"
- 安装后：从桌面/启动台直接打开，全屏、无 URL 栏
- 离线可用：没网也能看（缓存最后数据）
- 移动端：iOS Safari / Android Chrome 都能装

## 范围

### In Scope

1. **`static/manifest.json`** - PWA manifest
   - name, short_name, description
   - start_url: `/`
   - display: `standalone`（全屏，无 browser chrome）
   - background_color, theme_color
   - icons: 192x192 + 512x512（maskable）
   - lang: `zh-CN`

2. **`static/icon.svg`** + PNG 衍生
   - 简单足球/奖杯设计
   - 512x512 主图标
   - 192x192 小图标

3. **`static/sw.js`** (Service Worker)
   - Cache shell on `install`: HTML, CSS, JS, manifest, icons
   - `fetch` event:
     - `/api/*` → network-first (始终 fresh)
     - 其他静态资源 → cache-first
   - Cleanup old caches on `activate`

4. **`templates/index.html`** 更新
   - `<link rel="manifest" href="/static/manifest.json">`
   - `<meta name="theme-color" content="#E63946">`
   - `<meta name="apple-mobile-web-app-capable" content="yes">`
   - `<link rel="apple-touch-icon" href="/static/icon-192.png">`

5. **`static/js/main.js`** SW 注册 + 安装按钮
   - `if ('serviceWorker' in navigator) navigator.serviceWorker.register('/static/sw.js')`
   - 监听 `beforeinstallprompt` event
   - 显示 "安装应用" 按钮（顶部 header）
   - 点击 → 调 `prompt()`，根据用户选择显示成功/取消消息

6. **e2e 测试** (5 个)
   - G1: manifest.json 可访问
   - G2: SW 注册成功 (`navigator.serviceWorker.controller` 非空)
   - G3: manifest 含必需字段（name, icons, start_url, display）
   - G4: 安装按钮在 beforeinstallprompt 触发后显示
   - G5: PWA audit (Lighthouse-style) 通过基础检查

### Out of Scope

- ❌ Push notifications（需要 backend + VAPID keys，复杂）
- ❌ Background sync（advanced SW APIs）
- ❌ Web Share API / WebRTC
- ❌ 真正的 PNG 图标设计（用 SVG 占位）
- ❌ iOS Safari 完整 PWA 支持（Safari 限制多）

## 任务清单

| # | 任务 | 状态 |
|---|------|------|
| 1 | 写 `static/manifest.json` | ✅ |
| 2 | 写 `static/icon.svg` (足球/奖杯) | ✅ |
| 3 | 写 `static/sw.js` (cache + offline) | ✅ |
| 4 | 改 `index.html` 加 PWA meta | ✅ |
| 5 | 改 `main.js` SW 注册 + install button | ✅ |
| 6 | e2e 测试（5 类共 15 个） | ✅ |
| 7 | 写 `docs/maintenance/pwa.md` | ✅ |
| 8 | 跑全部测试（243/243 通过） | ✅ |
| 9 | 视觉 review（截图 `tests/e2e/screenshots/pwa_view.png`） | ✅ |
| 10 | commit | ✅ |

## 验收

### 必须

- [x] `/static/manifest.json` 可访问
- [x] SW 注册成功（`getRegistrations()` 返回非空 — 注意不是 `getRegistration()`，因为 SW scope 是 `/static/` 不控制 `/`）
- [x] manifest 含 PWA 必需字段
- [x] beforeinstallprompt 触发时显示安装按钮
- [x] 8 闸 closure audit 全过（见下）

## 风险

| 风险 | 缓解 |
|------|------|
| SW cache 过时 | 版本号 cache name + 清理旧 cache on activate |
| 安装按钮不显示 | 只在 beforeinstallprompt 触发时显示（Chrome 检测：需 HTTPS 或 localhost + manifest + SW + icons） |
| Service Worker 注册失败 | 静默忽略（不阻塞主流程）|
| 图标难看 | SVG 占位先上，后续可换 |

## 决策记录

- **不**在 SW 中缓存 `/api/*`——比分数据应该总是 fresh
- **缓存版本**：`wc2026-v1`，更新时改版本号
- **icons**: SVG 主图标，PNG 192/512 衍生
- **install button**: 顶部 header 右侧"安装"按钮（仅 beforeinstallprompt 触发后显示）
- **不**做 PWA prompt 自动弹（用户体验差）—— 留用户主动点

## 8 闸 closure audit

| # | 闸 | 测试 | 结果 |
|---|----|------|------|
| G1 | manifest.json 存在 + 可访问 | `test_manifest_accessible` | ✅ |
| G2 | SW 注册成功 | `test_sw_registration` | ✅ |
| G3 | manifest 字段完整（name, icons, start_url, display: standalone, theme_color） | `test_manifest_display_standalone`, `test_manifest_has_required_icons`, `test_manifest_has_shortcuts` | ✅ |
| G4 | icons 192 + 512 都可达 | `test_icon_192_png_exists`, `test_icon_512_png_exists`, `test_icon_svg_accessible` | ✅ |
| G5 | SW cache shell on install（HTML/CSS/JS/manifest） | 代码 review `sw.js` `SHELL_URLS` + `test_sw_file_accessible` | ✅ |
| G6 | SW network-first for /api/* | 代码 review `sw.js` fetch handler 早 return | ✅ |
| G7 | beforeinstallprompt 触发安装按钮 | `test_install_button_in_html` + 代码 review | ✅ |
| G8 | 文档 + 主页加载无 console error | `test_no_console_errors_on_load` + `docs/maintenance/pwa.md` | ✅ |

**审计结论**: 8/8 通过。Plan 014 可关闭。

## 决策记录（追加）

- **SW scope = `/static/`**（注册于 `/static/sw.js`），不影响主页控制；`/api/*` 不缓存，永远 fresh
- **`getRegistrations()` 而非 `getRegistration()`** — 后者只返回控制当前页的 SW，由于 scope 不匹配会返回 null
- **不自动弹安装** — 等用户主动点 install 按钮（UX 更友好）
