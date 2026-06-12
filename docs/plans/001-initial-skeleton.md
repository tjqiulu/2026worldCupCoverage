# Plan 001 — Initial Skeleton

> **状态**: `proposed` → `planned`（用户批准后）→ 执行 → `completed`
> **创建日期**: 2026-06-12
> **目标**: AGE Phase 1 — 项目骨架（0 代码，文档 + 目录）

## 背景

项目从零开始。按 AGE 方法论，第一步是**显式化项目结构**——AGENTS.md、5 个 context 文件、backlog、plan、log 全建好，让未来的 AI session 进入时能快速理解项目全貌。

## 范围

### In Scope（要做）

1. **根文件**
   - `AGENTS.md` — AI 操作契约
   - `README.md` — 人类视角项目说明
   - `.gitignore` — Python + node 标准

2. **docs/ 顶层**
   - `docs/index.md` — 文档入口路由

3. **docs/context/**（5 个）
   - `README.md` — context 导航
   - `project-context.md` — 当前快照
   - `conventions.md` — 项目规范
   - `source-of-truth-and-precedence.md` — 真相源优先级
   - `ai-autonomy-policy.md` — 5 级自主权
   - `codebase-map.md` — 代码地图

4. **docs/requirements/**
   - `2026-06-12-wc-coverage-app.md` — 完整需求

5. **docs/architecture/ & docs/design/**
   - `architecture/README.md` — 架构总览
   - `design/app-overview.md` — UI/UX 设计

6. **docs/backlog/**
   - `README.md` — 14 个 work items + 4 阶段路线图

7. **docs/plans/**
   - `001-initial-skeleton.md`（本文件）

8. **docs/logs/**
   - `logs/2026/06-12.md` — 今日日志

9. **空目录 + .gitkeep**
   - `src/`、`src/data/`、`src/templates/`、`src/static/{css,js,img}/`
   - `data/`、`data/i18n/`（待 Plan 002）
   - `tests/`

### Out of Scope（不做）

- ❌ 任何 Python 代码
- ❌ 任何 HTML/CSS/JS 代码
- ❌ 任何数据文件
- ❌ requirements.txt（等 Plan 002 加依赖时再建）

## 任务清单

| # | 任务 | 文件 | 状态 |
|---|------|------|------|
| 1 | 建目录结构 | （9 个目录） | ✅ done |
| 2 | 写 AGENTS.md | `AGENTS.md` | ✅ done |
| 3 | 写 README.md | `README.md` | ✅ done |
| 4 | 写 docs/index.md | `docs/index.md` | ✅ done |
| 5 | 写 5 个 context 文件 | `docs/context/*` | ✅ done |
| 6 | 写 requirements | `docs/requirements/2026-06-12-wc-coverage-app.md` | ✅ done |
| 7 | 写 architecture + design | `docs/architecture/README.md`, `docs/design/app-overview.md` | ✅ done |
| 8 | 写 backlog | `docs/backlog/README.md` | ✅ done |
| 9 | 写本 plan | `docs/plans/001-initial-skeleton.md` | ✅ done |
| 10 | 写今日 log | `docs/logs/2026/06-12.md` | ✅ done |
| 11 | 建空目录占位 | `src/`、`data/`、`tests/` | ⏳ |

## 验收标准

### 必须

- [x] 所有 16 个文件存在
- [ ] 零占位符（`<fill xxx>`、`xxx...` 等模板字段全替换）
- [ ] 0 代码改动
- [ ] 所有链接有效（相对路径都指向存在的文件）
- [ ] AGENTS.md 必读顺序可走通

### 应该

- [ ] docs 文件大小合理（README 1-2KB，context 1-2KB，requirements 3-5KB）
- [ ] 每个文件有清晰的一句话说清"干嘛的"
- [ ] 项目结构符合 AGE 约定（与 image-indexer 项目的 AGE 模式一致）

## 风险

| 风险 | 缓解 |
|------|------|
| 文件太多，一次写不完 | 已经在并行 batch 中 |
| 占位符残留 | 写完后 grep 验证 |
| 链接 404 | 写完后用 markdown linter 验证 |

## 关联

- **Backlog item**: P0-001
- **Next plan**: 002 (ICS parser + Flask skeleton) — 需用户批准

## 决策记录

- 用 Flask 而不是 FastAPI（更轻、更熟）
- 桌面形态用浏览器而非 PyWebView（用户选 A）
- 国际化用 JSON + JS 而非 gettext（更简单）
- 不在 Plan 001 写任何代码（保持骨架纯净）
- 不复用 image-indexer 的 harness（不同项目，重新搭轻量级 harness）
