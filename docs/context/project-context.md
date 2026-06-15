# project-context.md — 当前快照

> **这是项目最简的"现在长什么样"。** 任何大变化（plan 状态、blocker、新鲜度）改这里。

## 一句话

桌面世界杯赛程看板，Python+Flask 后端 + HTML/JS 前端 + 浏览器全屏展示，按日期分组，国旗+队名+比分，可点击看进球详情，双语 UI。

## Active work 当前快照

- **Active requirement**: `docs/requirements/2026-06-12-wc-coverage-app.md`（待 Plan 002 细化）
- **Active plan**: [`002-ics-parser-and-flask.md`](../plans/002-ics-parser-and-flask.md)（已完成）+ [`017-incomplete-details-api-override.md`](../plans/017-incomplete-details-api-override.md)（2026-06-15 完成）
- **Active backlog item**: `P0-004`（国旗 + 队名）→ Plan 003 候选
- **AI autonomy**: plan-first（任何 `src/` 改动都要先有 plan）
- **Current blocker**: none
- **Documentation freshness**: **fresh**（2026-06-15 Plan 017 完成）

## 用户已确认的关键决策（2026-06-12）

1. UI：中文 + 英文都要
2. 数据源：A 方案——爬 baires/fifa-cal-2026 ICS，补细节
3. 桌面形态：A 方案——浏览器全屏（不打包本地 app）
4. 比分更新：刷新即可，不需要实时
5. 项目路径：`/home/lqiu/.openclaw/workspace/2026worldCupCoverage/`
6. 端口：8765 被占，改用 8766

## 已实现功能（Plan 001 + 002）

- ✅ ICS fetcher（baires 源 + 1h 本地缓存）
- ✅ ICS parser（104 场，7 种 stage）
- ✅ Flask 4 端点（/, /api/matches, /api/refresh, /api/health）
- ✅ 基础 UI（日期分组、今日高亮、刷新按钮）
- ✅ 39 个 pytest 全过
- ⏳ 国旗、详情弹窗、双语切换 → Plan 003+

## 技术栈快照

| 层 | 选型 | 理由 |
|----|------|------|
| 后端 | Python 3.10 + Flask | 轻、跨平台、好爬数据 |
| 前端 | 原生 HTML + ES6 JS + flag-icons CDN | 零打包负担 |
| 桌面 | Chromium / Firefox `--kiosk` 全屏 | 用户选 A |
| 数据 | baires ICS + 本地 JSON 缓存 | 用户选 A |
| 国旗 | lipis/flag-icons 6.6.6 | SVG 成熟，CDN 稳定 |
| 国际化 | zh-CN 默认 + en | 用户要求双语 |

## 下次 session 怎么接上

最重要的文件是 `docs/logs/2026/06-12-plan-002.md` § "Next-Session Pickup Notes"。

按 AGENTS.md 必读顺序读完后，跳到 active plan（目前 002 已完成），看 backlog 选下一步（推荐 P0-004 国旗 + 队名）。

5 种可能场景：
1. **继续推 Plan 003**（国旗 + 队名）→ 从 backlog P0-004 起步
2. **先做详情弹窗**（P1-001）→ 手动维护 `data/details.json`
3. **先做双语**（P1-002）→ `data/i18n/{zh,en}.json`
4. **调整 UI 设计** → 改 `docs/design/app-overview.md`（L1）
5. **修复 bug** → 直接起 plan 描述 bug + 修复
