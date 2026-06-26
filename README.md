# 2026 World Cup Coverage

> 桌面世界杯赛程看板 / Desktop World Cup 2026 Dashboard

A bilingual (中文 + English) desktop dashboard for the 2026 FIFA World Cup, optimized for an Ubuntu desktop running a fullscreen browser. Shows all 104 matches grouped by date, with country flags, team names, scores, click-through match details (goalscorers, goal times, venue), a 32-team bracket view, and a live Best-3rd-place Top 8 panel.

| Matches | Teams | Languages | API | UI |
|---------|-------|-----------|-----|----|
| 104 | 48 | 中文 + 英文 | 5 个 JSON 端点 | 单页，零打包 |

## 快速开始 / Quick Start

### 方式 A：本地后端 + 浏览器（最常用，30 秒）

```bash
# 1. 装依赖（Flask 3 + icalendar + requests + gunicorn）
python3 -m pip install -r requirements.txt

# 2. 启服务（后台 daemon，日志写到 /tmp/wc_server.log）
bin/serve.sh

# 3. 浏览器打开
xdg-open http://127.0.0.1:8766        # Linux
# open http://127.0.0.1:8766          # macOS
# 手动复制 http://127.0.0.1:8766     # Windows
```

服务起来后：

- 顶部 **🔄 刷新** 拉新数据（比分、积分榜、第 3 名晋级）
- 顶部 **📅 今天** 跳到当前日期
- 顶部 **📲 安装**（如出现）把页面装成桌面 PWA

### 方式 B：桌面全屏 kiosk（电视 / 树莓派用）

```bash
python3 -m pip install -r requirements.txt
bin/launch.py     # 或 bin/start.sh（等价）
# 自动检测 chromium / chrome / firefox，全屏启动；Ctrl+C 退出
```

### 方式 C：云端部署（手机 4G 也能访问）

详见 [docs/deployment/render.md](docs/deployment/render.md)。Fork 仓库 → Render Blueprint → 3-5 分钟出 `https://wc2026-coverage.onrender.com`。

### 常用命令速查

| 命令 | 作用 |
|------|------|
| `bin/serve.sh` | 启服务（后台 daemon） |
| `bin/serve.sh --foreground` | 前台跑（Ctrl+C 退出） |
| `bin/serve.sh --status` | 看运行状态 + `/api/health` |
| `bin/serve.sh --stop` | 停服务 |
| `bin/serve.sh --restart` | 重启 |
| `bin/launch.py` | 桌面 kiosk 模式 |
| `bin/open.sh` | 普通窗口打开（不抢焦点） |
| `bin/tunnel.sh` | Cloudflare quick tunnel（无账号临时公网 URL） |
| `bin/tunnel-url.sh` | 打印当前 tunnel 公网 URL |
| `python3 -m pytest` | 跑测试套件（443 个用例） |

## 系统要求

- **Python**: 3.10+（pyproject `requires-python = ">=3.10"`）
- **浏览器**: Chromium / Google Chrome / Firefox（kiosk 需要 chromium 系）
- **网络**: 首次启动会拉 ICS + 调用 worldcup26.ir API（一次 ~5MB）
- **磁盘**: ~50 MB（含缓存）

> **关于 venv**：本仓库不再强制 venv（系统 Python 3.10+ 已够用）。如要隔离，推荐 `uv venv` 或 `pipx`，但 README 不强求。

## 技术栈 / Stack

| 层 | 选型 | 理由 |
|----|------|------|
| 后端 | Python 3.10 + Flask 3 | 轻、跨平台、好爬数据 |
| 前端 | 原生 HTML + ES6 + CSS3 | 零打包负担（无 React/Vue） |
| 桌面 | Chromium / Firefox `--kiosk` | 用户选 A 方案 |
| 数据源 | baires/fifa-cal-2026 ICS + worldcup26.ir API | 双源 + 本地缓存 |
| 国旗 | [lipis/flag-icons](https://github.com/lipis/flag-icons) 6.6.6（CDN） | SVG，150+ 国家 |
| 部署 | gunicorn + Render（免费层） | 零成本 + 自动 HTTPS |
| 国际化 | 中文 + 英文并列 | 双语人群 |

## 特性 / Features

- 🗓 **All 104 matches** grouped by date, current day highlighted
- 🚩 **Country flags** via flag-icons
- ⚽ **Live-ish scores** — click 🔄 刷新 to fetch latest data
- 🖱 **Click any match** for goalscorers, goal times, venue, countdown, group standings
- 🏆 **32-team bracket** with R32 → R16 → QF → SF → Final (Plan 003+, 持续完善)
- 🥇 **Best 3rd-place Top 8 panel** (Plan 042) — 实时显示哪 8 支第 3 名晋级
- 🌐 **Bilingual** (中文 + 英文 并列)
- 🖥 **Desktop-friendly** — kiosk fullscreen, PWA installable, no server admin
- 🪶 **Lightweight** — ~5800 LOC total (src + static + launcher)

## 项目结构 / Project Layout

```
2026worldCupCoverage/
├── README.md                       ← 本文件
├── AGENTS.md                       ← AI 操作契约（宪法）
├── LICENSE                         ← MIT
├── pyproject.toml                  ← 包元数据 + dev deps
├── requirements.txt                ← 生产 deps（Render 用）
├── render.yaml                     ← Render Blueprint 配置
├── bin/                            ← 启动脚本
│   ├── serve.sh                    ← 后端 daemon
│   ├── launch.py / start.sh        ← 桌面 kiosk
│   ├── open.sh                     ← 普通窗口
│   ├── tunnel.sh / tunnel-url.sh   ← Cloudflare quick tunnel
├── src/
│   ├── app.py                      ← Flask 入口（10 路由）
│   ├── data/                       ← 数据层（6 模块）
│   ├── templates/index.html
│   └── static/{css,js,img}/
├── data/                           ← 派生数据（可重生成）
│   ├── matches.json                ← 104 场
│   ├── details.json                ← 进球 / 比分
│   └── qualification_cache.json    ← 积分榜 + 第 3 名排名
├── tests/                          ← 443 个 pytest
└── docs/                           ← 设计 + 决策 + 工作日志
    ├── plans/                      ← 43 个 plan 文件
    ├── logs/2026/                  ← 每日工作日志
    ├── context/                    ← 5 个项目快照文件
    ├── requirements/               ← F1-F16 需求表
    ├── design/                     ← UI/UX 规范
    ├── architecture/               ← 架构图
    ├── deployment/                 ← Render / Tunnel 部署
    └── maintenance/                ← 运维手册
```

## 文档 / Documentation

- [docs/index.md](docs/index.md) — 文档入口
- [AGENTS.md](AGENTS.md) — AI 操作契约
- [docs/plans/](docs/plans/) — 43 个 plan 文件
- [docs/logs/2026/](docs/logs/2026/) — 工作日志
- [docs/deployment/render.md](docs/deployment/render.md) — Render 云部署
- [docs/maintenance/desktop-launcher.md](docs/maintenance/desktop-launcher.md) — 桌面 kiosk 模式
- [docs/maintenance/pwa.md](docs/maintenance/pwa.md) — PWA 安装

## 许可证 / License

[MIT](LICENSE)
