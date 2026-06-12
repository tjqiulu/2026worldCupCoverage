# docs/index.md — 文档入口

> 顶层路由。从这里出发，按需深入。

## 给 AI

如果你在新的 session 进入本项目，请按 [AGENTS.md § 必读顺序](../AGENTS.md) 读完再动手。

## 目录结构

### Context（5 个上下文文件 + README）
- [context/README.md](context/README.md) — 导航
- [context/project-context.md](context/project-context.md) — 当前快照（活动 plan / blocker / 新鲜度）
- [context/conventions.md](context/conventions.md) — 项目规范
- [context/source-of-truth-and-precedence.md](context/source-of-truth-and-precedence.md) — 真相源优先级
- [context/ai-autonomy-policy.md](context/ai-autonomy-policy.md) — AI 自主权边界
- [context/codebase-map.md](context/codebase-map.md) — 代码地图

### Requirements
- [requirements/2026-06-12-wc-coverage-app.md](requirements/2026-06-12-wc-coverage-app.md) — 项目初始需求文档

### Architecture & Design
- [architecture/README.md](architecture/README.md) — 架构总览
- [design/app-overview.md](design/app-overview.md) — UI/UX 设计

### Plans（每个 plan 一份文件）
- [plans/001-initial-skeleton.md](plans/001-initial-skeleton.md) — 初始骨架（当前 active）

### Backlog
- [backlog/README.md](backlog/README.md) — 待办池（按优先级 P0/P1/P2 排序）

### Logs
- [logs/2026/06-12.md](logs/2026/06-12.md) — 今日工作日志

## 阅读建议

- **人类首次进入**：Context 全部 → Requirements → Design → Backlog
- **AI 首次进入**：AGENTS.md → 上面"给 AI"列的 7 步
- **回到工作中**：`project-context.md` 看 active plan → 跳到 plan 文件 → 跳到 log
