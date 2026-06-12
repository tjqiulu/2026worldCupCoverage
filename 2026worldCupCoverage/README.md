# 2026 World Cup Coverage

> 桌面世界杯赛程看板 / Desktop World Cup 2026 Dashboard

A bilingual (中文 + English) desktop dashboard for the 2026 FIFA World Cup, optimized for an Ubuntu desktop running a fullscreen browser. Shows all 104 matches grouped by date, with country flags, team names, scores, and click-through match details (goalscorers, goal times, venue).

## 特性 / Features

- 🗓️ **All 104 matches** grouped by date, with the current day highlighted
- 🚩 **Country flags** via [flag-icons](https://github.com/lipis/flag-icons)
- ⚽ **Live-ish scores** — refresh to fetch latest ICS update (no real-time polling)
- 🖱️ **Click any match** for goalscorers, goal times, venue, kickoff
- 🌐 **Bilingual UI** — switch between 中文 and English
- 🖥️ **Desktop-friendly** — auto-launches in fullscreen browser on Ubuntu
- 🪶 **Lightweight** — Python + Flask + plain HTML/JS, no bundlers

## 快速开始 / Quick Start

```bash
cd /home/lqiu/.openclaw/workspace/2026worldCupCoverage
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # (待 Plan 002 添加)
python src/app.py                 # 启动 Flask
# 浏览器自动开 http://127.0.0.1:8765 全屏
```

## 技术栈 / Stack

- Python 3.10 + Flask
- HTML5 + ES6 + CSS3 (no framework)
- flag-icons 6.6.6 (CDN)
- baires/fifa-cal-2026 ICS (data source)

## 文档 / Documentation

- [docs/index.md](docs/index.md) — 文档入口
- [AGENTS.md](AGENTS.md) — AI 操作契约
- [docs/requirements/2026-06-12-wc-coverage-app.md](docs/requirements/2026-06-12-wc-coverage-app.md) — 完整需求
- [docs/design/app-overview.md](docs/design/app-overview.md) — UI/UX 设计
- [docs/backlog/README.md](docs/backlog/README.md) — 待办

## 许可证 / License

TBD (Plan 002 时确定)
