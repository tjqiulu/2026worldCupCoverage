# Plan 043 — 文档刷新：Quick Start 现代化 + 现状同步

> **状态**: proposed → in-progress（用户口头要求 "Quick Start 已经落后了，重新做 + review 一下其他的文档是否更新了" 视为 plan 草稿通过）
> **创建日期**: 2026-06-26
> **目标**: 让一个 2026-06-26 的新人 clone + 跑通 + 看文档不再踩坑

## 背景

09:58 用户反馈：README.md 的 Quick Start 段落完全过时：

- 端口 8765 → 实际 8766（早期就改了）
- `pip install -r requirements.txt   # (待 Plan 002 添加)` → Plan 002 是 14 天前的事，requirements.txt 早就填了
- `python src/app.py` → 实际推荐用 `bin/serve.sh`（daemon 化 + 日志 + PID）
- "浏览器自动开 http://127.0.0.1:8765 全屏" → 没有自动开

顺手 review，发现一堆文档停留在 Plan 001/002 阶段，2 周积累的 plan 003-042 都没回填。

## 范围

### In Scope（要改）

| # | 文件 | 问题 | 修法 |
|---|------|------|------|
| 1 | `README.md` | Quick Start 段落整体过时 | 重写：3 步法（安装 → `bin/serve.sh` → 浏览器），加桌面/Render 两条次要路径，加 Stack / Project layout 章节 |
| 2 | `docs/index.md` | "active plan = 001"、"logs/2026/06-12.md"、Plans 只有 001 | 改为 042、logs/2026/06-26、加 plans/README.md 索引、补 deployment/ + maintenance/ 段落 |
| 3 | `docs/context/project-context.md` | "Active plan: 041"、已实现列只到 Plan 002、39 pytest | 升 042、补全已实现（Plan 003-042）、pytest 数量补到 435+、清 backlog 状态 |
| 4 | `docs/context/codebase-map.md` | "Plan 002 完成"、行数严重低估、文件列表不全 | 重写：现在 ~2100 行、文件按层分组、关键 API 列表 |
| 5 | `docs/context/conventions.md` | `DEFAULT_PORT = 8765` 错 | 改 8766，注脚说明 |
| 6 | `docs/design/app-overview.md` | 老 layout（无 bracket / modal / Top 8 / 刷新 3 件套） | 加新 section：Bracket view、Match modal、Third-place Top 8 panel、Header actions、Footer / status |
| 7 | `docs/requirements/2026-06-12-wc-coverage-app.md` | F1-F16 没标 ✅/❌、关联 plan 001 | 表格加 status 列，列出哪些 F 在哪个 plan 完成 |
| 8 | `docs/architecture/README.md` | 部署形态段落说 `src/start.sh`、端口 8765 | 改为 `bin/serve.sh`、端口 8766、链接到 README Quick Start |
| 9 | `docs/backlog/README.md` | Phase 表还显示 "Phase 1 进行中"、P0-001/002/003/004 还 open | 全部标 done，新增 "未来 5-10 个" 候选 backlog item（来自 Plan 029/041 的衍生需求） |
| 10 | `docs/plans/README.md` | **不存在** | 新建：001-042 一行摘要索引 + 跳转链接 |

### Out of Scope

- 不改 AGENTS.md（宪法文件，红线）
- 不改 `src/` 任何代码
- 不动 `data/`
- 不重写 doc 内容（只是 sync；doc 写得不好的不在本 plan 修）

## 设计

### Quick Start 新结构

```markdown
## 快速开始 / Quick Start

### 方式 A：本地后端 + 浏览器（最常见，30 秒）

```bash
# 1. 装依赖（Flask 3 + icalendar + requests）
python3 -m pip install -r requirements.txt

# 2. 启服务（后台 daemon，日志 /tmp/wc_server.log）
bin/serve.sh

# 3. 浏览器打开
xdg-open http://127.0.0.1:8766   # Linux
# 或 open http://127.0.0.1:8766   # macOS
```

服务起来后：右上角「🔄 刷新」按钮拉新数据，「📅 今天」跳到当前日期。

### 方式 B：桌面全屏（kiosk，电视/树莓派用）

```bash
python3 -m pip install -r requirements.txt
bin/launch.py      # 或 bin/start.sh
# 自动检测 chromium/chrome/firefox，全屏启动；Ctrl+C 退出
```

### 方式 C：Render 云部署（手机 4G 也能访问）

详见 [docs/deployment/render.md](docs/deployment/render.md)。Fork 仓库 → Render Blueprint → 3-5 分钟出 `https://wc2026-coverage.onrender.com`。

### 常用命令

| 命令 | 作用 |
|------|------|
| `bin/serve.sh` | 启服务（后台） |
| `bin/serve.sh --status` | 看运行状态 |
| `bin/serve.sh --stop` | 停服务 |
| `bin/serve.sh --foreground` | 前台跑（Ctrl+C 退出） |
| `bin/launch.py` | 桌面 kiosk 模式 |
| `bin/open.sh` | 普通窗口打开（不占焦点） |
| `bin/tunnel.sh` | Cloudflare quick tunnel（外网访问） |
| `bin/tunnel-url.sh` | 打印当前 tunnel 公网 URL |

## 系统要求

- **Python**: 3.10+（pyproject `requires-python = ">=3.10"`）
- **浏览器**: Chromium / Google Chrome / Firefox（kiosk 模式需要 chromium 系）
- **网络**: 首次启动会拉 ICS + 调用 worldcup26.ir API（仅 5MB 左右）
```

### 不再需要 venv

原 Quick Start 用 `python3 -m venv .venv` 是历史习惯，但本机没有 `ensurepip`，venv 创建会失败。改用**系统 Python**（Ubuntu 22.04+ 默认装的就是 3.10，Flask/requests 也都能 apt 装）。如果用户非要隔离，建议用 `pipx` 或 `uv`，但本 README 不强求。

## 验收

- [x] Plan 文件
- [x] README.md Quick Start 改完，新用户 3 步跑通
- [x] `docs/index.md` 反映 042 现状
- [x] `docs/context/project-context.md` 同步
- [x] `docs/context/codebase-map.md` 行数/文件清单准
- [x] `docs/context/conventions.md` 端口 8766
- [x] `docs/design/app-overview.md` 含新 view
- [x] `docs/requirements/...` F1-F16 标 status
- [x] `docs/architecture/README.md` 部署形态
- [x] `docs/backlog/README.md` Phase + P0 全标 done
- [x] `docs/plans/README.md` 新建索引
- [x] pytest 通过
- [x] git commit + push

## 风险

- **L1 文档**（`docs/index.md`, `docs/context/*`, `docs/requirements/*`）按 policy 改前要 L1 批准。**Override**: 用户口头说"重新做 + review 一下其他文档是否更新了" = 显式批准，按 L2 plan-first + execute 处理（与 Plan 042 同款）
