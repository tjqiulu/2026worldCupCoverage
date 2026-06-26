# docs/index.md — 文档入口

> 顶层路由。从这里出发，按需深入。

## 给 AI

如果你在新的 session 进入本项目，请按 [AGENTS.md § 必读顺序](../AGENTS.md) 读完再动手。

## 当前状态 / Current state（2026-06-26）

- **Active plan**: [043-doc-refresh-quickstart-and-current-state.md](plans/043-doc-refresh-quickstart-and-current-state.md)（Quick Start 现代化 + 文档同步，本页即配套更新）
- **Latest log**: [logs/2026/06-26-plan-042.md](logs/2026/06-26-plan-042.md)（Best 3rd Top 8 面板）
- **Project freshness**: 🟢 fresh（今天有提交）
- **Tests**: 443 个 pytest 全过
- **Code size**: ~5800 LOC（src + 静态资源 + 启动器）
- **Plans shipped**: 42 个（[plans/README.md](plans/README.md) 看索引）

## 目录结构

### [Context](context/) — 5 个项目快照
回答"项目现在长什么样？怎么动？"

- [context/README.md](context/README.md) — 导航
- [context/project-context.md](context/project-context.md) — 当前快照（active plan / blocker / 新鲜度）
- [context/conventions.md](context/conventions.md) — 命名 / 风格 / 提交规范
- [context/source-of-truth-and-precedence.md](context/source-of-truth-and-precedence.md) — 真相源优先级
- [context/ai-autonomy-policy.md](context/ai-autonomy-policy.md) — AI 自主权边界
- [context/codebase-map.md](context/codebase-map.md) — 代码地图（每个文件干嘛的）

### [Requirements](requirements/)
- [requirements/2026-06-12-wc-coverage-app.md](requirements/2026-06-12-wc-coverage-app.md) — F1-F16 需求表

### [Architecture & Design](architecture/) / [Design](design/)
- [architecture/README.md](architecture/README.md) — 架构总览 + 数据流
- [design/app-overview.md](design/app-overview.md) — UI/UX 规范

### [Plans](plans/) — 每个 plan 一份文件
- [plans/README.md](plans/README.md) — **001-042 索引**
- [plans/043-doc-refresh-quickstart-and-current-state.md](plans/043-doc-refresh-quickstart-and-current-state.md) — 本次 active

### [Logs](logs/2026/) — 工作日志
- [logs/2026/](logs/2026/) — 06-12 起至今所有日志
- 命名规范：`YYYY-MM-DD[-plan-NNN].md`

### [Deployment](deployment/) — 部署
- [deployment/render.md](deployment/render.md) — Render 免费层部署

### [Maintenance](maintenance/) — 运维手册
- [maintenance/desktop-launcher.md](maintenance/desktop-launcher.md) — `bin/launch.py` 桌面 kiosk
- [maintenance/pwa.md](maintenance/pwa.md) — PWA 安装与离线
- [maintenance/match-details.md](maintenance/match-details.md) — 进球详情数据维护

### [Backlog](backlog/)
- [backlog/README.md](backlog/README.md) — 待办池 + 阶段路线图

## 阅读建议

- **人类首次进入**：[Context](context/) 全部 → [Requirements](requirements/) → [Design](design/) → [Backlog](backlog/)
- **AI 首次进入**：[AGENTS.md](../AGENTS.md) → 上面"给 AI"列的 7 步
- **回到工作中**：[context/project-context.md](context/project-context.md) 看 active plan → 跳到 plan 文件 → 跳到 log
- **新人部署**：[README.md](../README.md) Quick Start 3 步法
