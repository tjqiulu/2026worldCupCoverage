# AGENTS.md - AI 操作契约

> 本文件是 AI agent 在本项目工作的**操作契约**。必读，所有行为以本文件为准。
> 本文件不移动、不重命名（OpenClaw 硬约束）。

## 项目一句话

**2026 世界杯赛程桌面看板**：Ubuntu 上浏览器全屏展示 104 场比赛，按日期分组、国旗+队名+比分、点击看进球详情，双语（中文+英文）。

## 必读顺序（新 session 进入时）

1. `docs/index.md` — 顶层路由
2. `docs/context/project-context.md` — 当前快照（活动 plan / blocker / 新鲜度）
3. `docs/context/ai-autonomy-policy.md` — 自主权边界
4. `docs/context/codebase-map.md` — 代码地图
5. `docs/backlog/README.md` — 找 active item
6. `docs/plans/<active-plan>.md` — 当前 plan
7. `docs/logs/<latest>.md` — 上次工作记录

读完才能动手。

## 技术栈

- **后端**: Python 3.10 + Flask（轻、跨平台、好爬数据）
- **前端**: 原生 HTML + ES6 JS + flag-icons CDN（零打包负担）
- **桌面形态**: Chromium/Firefox 浏览器全屏（auto-launch + fullscreen）
- **数据源**:
  - 基础赛程: baires/fifa-cal-2026 ICS（拉一次解析成本地 JSON）
  - 比分: 用户手动刷新（拉 baires 更新后的 ICS）
  - 进球详情: 本地 JSON 维护
  - 国旗: lipis/flag-icons CDN（运行时拉 SVG）
- **国际化**: zh-CN 默认 + en，二者并列

## 风格

- 简洁、信息密度高、不堆砌
- 双语并列（用户群体多语言）
- 永远先有 plan，再有代码
- 文档用 markdown，不用 emoji
- 表格能清晰表达就用表格

## 红线

- 不得在 `data/*.json` 手改后不说明来源（这是 derived 数据，应可重生成）
- 不得跳过 plan 阶段直接动 `src/`
- 不得改 AGENTS.md 内容（这是宪法，要改先问用户）
- 不得部署到用户家目录以外

## 决策记录

所有大决策（技术选型、删文件、改架构）必须进 `docs/logs/YYYY-MM-DD.md` 的"Decision Log"段。
