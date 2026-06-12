# ai-autonomy-policy.md — AI 自主权

> AI 在本项目能做什么、必须问什么。本项目以"显式化边界"为核心——不确定就问，不假设。

## 5 级自主权

| 级别 | 含义 | 何时用 |
|------|------|--------|
| **L1 ask-first** | 必须先问，批准才能动 | 架构、合同、用户偏好 |
| **L2 plan-first** | 必须有 plan 文件，批准后执行 | 任何代码改动 |
| **L3 propose-then-act** | 自己写 plan，然后执行，最后报告 | 文档/注释/小重构 |
| **L4 act-then-notify** | 干了，然后告诉用户 | 自动化（重跑解析、修小 typo） |
| **L5 full-auto** | 干就完了 | 测试代码、CI |

## 默认级别（按文件类型）

| 路径 | 默认级别 | 备注 |
|------|----------|------|
| `AGENTS.md` | **L1** | 宪法 |
| `docs/context/*.md` | **L1** | 改上下文 = 改决策 |
| `docs/requirements/*.md` | **L1** | 需求定锚 |
| `docs/plans/*` | **L1（关闭）** | 写 plan 可 L3，**关闭** 必须 L1 |
| `docs/architecture/`, `docs/design/` | **L1** | 架构决策 |
| `docs/backlog/README.md` | **L3** | 加/移/排序条目 |
| `docs/logs/*` | **L4** | 写日志是 routine |
| `src/**.py` | **L2** | 任何代码改动 |
| `src/templates/*.html` | **L2** | UI 改动也算代码 |
| `src/static/**` | **L2** | UI 改动 |
| `data/matches.json` | **L4** | 派生数据，可重生成 |
| `data/details.json` | **L1** | 手写维护，删了数据丢 |
| `data/i18n/*.json` | **L2** | 用户可见文案，需双语同步 |
| `tests/**.py` | **L5** | 测试代码，CI 验证 |
| `requirements.txt`, `pyproject.toml` | **L1** | 加依赖 = 决定 |
| `scripts/*.py` | **L3** | 一次性脚本 |
| `.gitignore` | **L3** | |
| `README.md` | **L3** | 顶部说明 |

## Protected Areas（绝对不能动，动了先 L1）

- `AGENTS.md`（本文件不重命名/不移动，是 OpenClaw 硬约束）
- 用户家目录以外的位置
- 任何外部资源 URL（用 config，不 hardcode）

## Override 规则

- 用户口头说"先干吧"或类似话语 → 视为 plan 草稿通过，可执行 L2 工作
- 用户说"就这样" → 视为 plan 关闭（closure audit 通过）
- 但 **L1 操作永远不能被 override**，必须显式确认

## 出错时

- 写了不该写的文件 → 在 `docs/logs/YYYY-MM-DD.md` 记录 + `git revert` + 在 log 里说明
- 越权动了 protected area → 立即停止 + 在 log 里 "Decision Log" 段报告
- 不确定时 → 默认 L1，宁可多问
