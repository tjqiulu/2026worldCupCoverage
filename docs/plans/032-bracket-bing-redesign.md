# Plan 032 — Bracket Bing 风格重设计 + 滚动条优化 + SW 修复

> **状态**: proposed
> **创建日期**: 2026-06-19 22:18
> **触发**: 用户 22:16 反馈
> **关联 plan**: [031-qualification-cache-and-fonts.md](031-qualification-cache-and-fonts.md)

## 问题

1. **bracket 初次空白**：reload 页面后数据消失（service worker cache-first 命中 stale main.js）
2. **滚动条丑**：浏览器默认水平滚动条难看
3. **UI 设计**：参考 Bing 重新设计（大卡片、双行 layout、team + Upcoming）

## 根因

### 问题 1
- `sw.js` `CACHE_VERSION = 'wc2026-v6'` 未升级
- main.js 改动但 sw 没变 → cache 命中旧 main.js
- 用户 reload 时 sw 不更新 → 旧 main.js 仍服务

### 问题 2
- 浏览器默认 webkit-scrollbar 样式

### 问题 3
- 现有 renderMirrorCard 单行 vs 设计过时
- Bing 设计：日期/时间在右 / team 名 + status 在左 / 卡片更大

## 修复

### Fix 1: SW 修复
- `sw.js` 升版本 `wc2026-v7`
- 加 `self.skipWaiting()` + `clients.claim()` 强制激活
- main.js 加 fetch 头 `?v=7` cache buster

### Fix 2: Bing 风格重设计
新 `renderMirrorCard()` 结构（参考 Bing）：

```
┌────────────────────────────────────┐
│  🇲🇽 墨西哥       2026-07-01 09:00 │
│  ───────                          │
│  (空) vs         2026-07-01 09:00 │
└────────────────────────────────────┘
```

- 卡片更大：min-height 56px → 80-100px
- 双行：date/time 在右上角 + 队名 + status
- 占位符占位：未锁定时显示 "1A" / "W73" 等
- 锁定队显示 🇲🇽 国旗 + 中文名 + 日期

### Fix 3: 滚动条
- 自定义 webkit-scrollbar
- 细 + 圆角 + 灰色
- 横向滚动条隐藏（grid 自适应）

## 范围

### In Scope
- L2 `src/static/sw.js` 升版本 + skipWaiting
- L2 `src/static/css/main.css` 重设计 + 滚动条
- L2 `src/static/js/main.js` renderMirrorCard 重写
- L4 commit + log

### Out of Scope
- ❌ 算法
- ❌ 后端
- ❌ 模态框 detail page