# codebase-map.md — 代码地图

> 每个文件/模块干嘛的。AI 进入项目时第一查这里。

## 当前状态（2026-06-12 Plan 002 完成）

**~440 行代码**（不含测试）。104 场比赛实时解析。

### 已实现文件
- `src/app.py`（~80 行）— Flask 4 端点
- `src/data/ics_fetcher.py`（~50 行）— ICS 拉取 + 1h 缓存
- `src/data/ics_parser.py`（~120 行）— ICS → matches.json
- `src/templates/index.html`（~25 行）
- `src/static/css/main.css`（~150 行）
- `src/static/js/main.js`（~120 行）
- `scripts/fetch_initial_data.py`（~50 行）

### 测试
- `tests/test_ics_parser.py`（~195 行，27 用例）
- `tests/test_app.py`（~100 行，5 用例）

### 重要配置
- **端口**: 8766（8765 被本机其他服务占）
- **ICS 源**: `https://cdn.jsdelivr.net/gh/baires/fifa-cal-2026@master/calendars/en.ics`
- **缓存**: `data/.cache/wc2026.ics`（1h TTL）

## 计划中的目录

```
2026worldCupCoverage/
├── AGENTS.md                  # AI 操作契约
├── README.md                  # 人类视角
├── requirements.txt           # Python deps (待 Plan 002)
├── .gitignore
├── docs/                      # 文档（已建）
├── src/                       # 应用代码（空，待 Plan 002+）
│   ├── app.py                 # Flask 入口
│   ├── data/
│   │   ├── ics_parser.py      # ICS → JSON
│   │   ├── ics_fetcher.py     # 从 baires 拉 ICS
│   │   └── details_loader.py  # 加载手写 details.json
│   ├── templates/
│   │   └── index.html         # 主页
│   └── static/
│       ├── css/main.css
│       └── js/main.js
├── data/                      # 派生/手写数据
│   ├── matches.json           # ICS 解析后（生成）
│   ├── details.json           # 手写进球/场馆
│   └── i18n/
│       ├── zh.json
│       └── en.json
├── tests/                     # pytest
│   ├── test_ics_parser.py
│   ├── test_app.py
│   └── fixtures/
└── scripts/                   # 一次性脚本
    └── fetch_initial_data.py  # 首次拉数据
```

## 入口

- **Flask 启动**: `python src/app.py` → `http://127.0.0.1:8765`
- **桌面模式**: 启动 Flask + `chromium-browser --kiosk http://127.0.0.1:8765`（或 firefox）
- **测试**: `pytest tests/`

## 模块职责（计划）

### `src/app.py`
- Flask app factory
- 路由：`/`（主页）、`/api/matches`、`/api/match/<id>`、`/api/refresh`
- 启动时加载 `data/matches.json` 和 `data/details.json`
- 提供 `/api/refresh` 端点触发重新拉 ICS

### `src/data/ics_parser.py`
- 输入：baires ICS URL 或本地文件
- 输出：list of `{match_id, date_utc, home, away, venue, stage}`
- 用 `icalendar` 库解析
- 处理 4 种语言版本（选 zh + en 双语需要时）

### `src/data/ics_fetcher.py`
- 拉 ICS 文件（带 ETag/Last-Modified 缓存）
- 失败重试 + 离线降级到本地缓存
- 写回 `data/matches.json`

### `src/data/details_loader.py`
- 加载 `data/details.json`（手写的进球/场馆详情）
- 跟 `matches.json` 合并成最终展示数据

### `src/templates/index.html`
- 主视图：按日期分组
- 当前日期高亮
- 比赛卡片：🇧🇷 巴西 vs 🇦🇷 阿森纳 2-1
- 详情弹窗（点卡片触发）
- 语言切换器
- 刷新按钮

### `src/static/css/main.css`
- 响应式（桌面优先，但能缩到手机）
- 暗色 + 亮色模式（自动）
- 国旗 4x3 比例

### `src/static/js/main.js`
- 拉 `/api/matches` + 渲染
- 日期分组 + 高亮今天
- 详情弹窗
- 语言切换（i18n JSON）
- 刷新按钮（call `/api/refresh`）

## 大/脆文件（待 Plan 002+ 标记）

目前无代码。第一个大文件会是 `src/app.py`（预计 < 200 行）。

## 添加新文件时

任何新文件必须：
1. 在本文档"模块职责"段添加说明
2. 如果是 src/ 文件，确认 `ai-autonomy-policy.md` 的自主权级别
3. 写测试（如果是 logic）
