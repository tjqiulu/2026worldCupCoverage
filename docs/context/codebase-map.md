# codebase-map.md — 代码地图

> 每个文件/模块干嘛的。AI 进入项目时第一查这里。

## 当前状态（2026-06-26，Plan 043 同步）

- **代码量**: ~5800 LOC（src + 静态资源 + 启动器，不含测试/文档/data）
- **测试**: 443 个 pytest（tests/ 下 ~11600 行）
- **计划**: 42 个已完成 plan（[plans/README.md](../plans/README.md)）
- **运行形态**: 本地 daemon（`bin/serve.sh`，port 8766）+ Render 云（gunicorn）

## 项目结构

```
2026worldCupCoverage/
├── README.md                  # 人类视角（Quick Start 在这里）
├── AGENTS.md                  # AI 操作契约（宪法）
├── LICENSE                    # MIT
├── pyproject.toml             # 包元数据
├── requirements.txt           # 生产 deps（Render 用）
├── render.yaml                # Render Blueprint
├── .gitignore
│
├── bin/                       # 启动 + 部署脚本（6 个）
│   ├── serve.sh               # 后端 daemon start/stop/status/restart
│   ├── launch.py              # 桌面 kiosk 模式（自动开浏览器全屏）
│   ├── start.sh               # launch.py 的 shell 包装
│   ├── open.sh                # 普通窗口打开
│   ├── tunnel.sh              # Cloudflare quick tunnel
│   └── tunnel-url.sh          # 打印 tunnel 公网 URL
│
├── src/                       # 应用代码
│   ├── __init__.py
│   ├── app.py                 # Flask 入口（10 路由，~280 行）
│   ├── data/                  # 数据层（6 模块，~1900 行）
│   │   ├── __init__.py
│   │   ├── ics_fetcher.py     # baires ICS 拉取 + 缓存
│   │   ├── ics_parser.py      # ICS → matches.json（兼容 post-match 比分格式）
│   │   ├── countries.py       # 国家元数据（48 队，中英 + ISO）
│   │   ├── details.py         # 比赛详情 / 进球 / 比分加载
│   │   ├── worldcup_api.py    # worldcup26.ir API 客户端（5min cache）
│   │   └── qualification.py   # 积分榜 + Best 3rd race 算法
│   ├── templates/
│   │   └── index.html         # 单页（100 行）
│   └── static/
│       ├── css/main.css       # 1723 行（含 5 套主题）
│       ├── js/main.js         # 1438 行（前端所有逻辑）
│       ├── img/icon.svg
│       ├── manifest.json      # PWA manifest
│       └── sw.js              # Service Worker（app-shell 缓存）
│
├── data/                      # 派生数据（git tracked，可重生成）
│   ├── matches.json           # 104 场比赛
│   ├── details.json           # 进球 / 比分（手维护 + API 合并）
│   ├── qualification_cache.json  # 积分榜 + Best 3rd race
│   ├── countries.json         # 48 国元数据
│   ├── scorer_overrides.json  # 进球人姓名手维护覆盖
│   └── .cache/                # 临时 ICS 缓存（gitignore）
│
├── scripts/                   # 一次性脚本
│   ├── fetch_initial_data.py  # 首次拉数据
│   └── run_audit.sh           # plan-doc 一致性 audit
│
├── tests/                     # pytest 套件（443 个用例）
│   ├── conftest.py            # fixtures
│   ├── e2e/                   # Playwright 端到端（10 用例，部分 fixture 漂移）
│   ├── fixtures/              # 测试 fixture
│   ├── test_app.py            # Flask 路由（5）
│   ├── test_ics_parser.py     # ICS parser（13）
│   ├── test_ics_fetcher.py    # ICS fetcher
│   ├── test_countries.py      # 国家元数据
│   ├── test_details.py        # 详情加载（多）
│   ├── test_bracket_pairings.py  # 32 强对阵计算
│   ├── test_qualification.py  # 积分榜 / Best 3rd race（47）
│   ├── test_third_place_top8.py  # Plan 042 面板渲染（4）
│   ├── test_worldcup_api.py   # API 客户端
│   ├── test_launch.py         # 桌面 launcher
│   ├── test_frontend_init.py  # 前端 HTML/CSS 完整性
│   ├── audit_gates.py         # plan 通用 audit gate
│   └── audit_gates_planNNN.py # 各 plan 专项 audit
│
└── docs/                      # 全部文档
    ├── index.md               # 文档入口
    ├── plans/                 # 42 个 plan 文件
    ├── logs/2026/             # 工作日志（06-12 起）
    ├── context/               # 5 个项目快照
    ├── requirements/          # F1-F16
    ├── design/                # UI/UX
    ├── architecture/          # 架构图
    ├── deployment/            # Render / Tunnel
    ├── maintenance/           # 运维手册
    └── backlog/               # 待办
```

## 关键文件入口

| 想看 | 文件 |
|------|------|
| Flask 启动 | `src/app.py`（`create_app()`） |
| 启动服务 | `bin/serve.sh` |
| 前端入口 | `src/static/js/main.js`（`loadMatches()`） |
| 前端 HTML | `src/templates/index.html` |
| Best 3rd 算法 | `src/data/qualification.py::compute_best_3rd_race` |
| 32 强对阵 | `src/data/bracket_pairings.py`（如存在） |
| API 客户端 | `src/data/worldcup_api.py` |
| 数据缓存 | `data/qualification_cache.json`（手维护：可手改，重启失效） |
| 渲染入口 | `src/static/js/main.js::renderMatches / renderBracket` |
| 面板渲染 | `src/static/js/main.js::renderThirdPlaceTop8`（Plan 042） |
| 桌面 kiosk | `bin/launch.py` |
| Render 部署 | `render.yaml` + `requirements.txt` |
| Tunnel | `bin/tunnel.sh` + `bin/tunnel-url.sh` |

## 重要约束

- **端口**: 8766（8765 被本机其他服务占，`src/app.py:65` 注释说明）
- **Python**: 3.10+（pyproject `requires-python = ">=3.10"`）
- **ICS 源**: `https://cdn.jsdelivr.net/gh/baires/fifa-cal-2026@master/calendars/en.ics`
- **实时数据源**: `https://worldcup26.ir`（5 分钟内存缓存）
- **data/ 是 derived**：理论上可重生成，**例外** `data/details.json`（人工维护）和 `data/scorer_overrides.json`（手维护覆盖）
