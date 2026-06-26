# architecture/README.md — 架构总览

> 模块拆分、数据流、技术选型理由。**架构级决策**改这里要 L1。

## 一句话架构

```
[ICS 源] ──fetch──> [parser] ─> [data/matches.json]
                            │
                            ├──merge──> [data/details.json]
                            │            │
                            ▼            ▼
                       [Flask API] <──┘
                            │
                            ▼
                       [HTML/JS Frontend] ──> [flag-icons CDN]
                            │
                            ▼
                       [Browser 全屏]
```

## 模块分层

### 1. Data Layer（数据层）

- **职责**: 拉外部数据 + 解析 + 缓存 + 合并手写数据
- **输入**: baires ICS URL、`data/details.json`（手写）
- **输出**: 内存中的统一 `matches` 数据结构
- **文件**: `src/data/*.py`

### 2. API Layer（接口层）

- **职责**: 把数据层结果暴露成 HTTP API
- **输入**: HTTP 请求
- **输出**: JSON
- **文件**: `src/app.py`（Flask 路由）
- **端点**:
  - `GET /api/matches?date=YYYY-MM-DD` — 某日所有比赛
  - `GET /api/matches` — 全部比赛
  - `GET /api/match/<match_id>` — 单场详情
  - `POST /api/refresh` — 重新拉 ICS

### 3. Presentation Layer（展示层）

- **职责**: 渲染 + 交互
- **输入**: API JSON
- **输出**: DOM
- **文件**: `src/templates/index.html`、`src/static/`

### 4. i18n（国际化）

- **职责**: 文案多语言
- **存储**: `data/i18n/zh.json`、`data/i18n/en.json`
- **运行时**: 浏览器拉 JSON，JS 替换 DOM

## 关键技术决策

| 决策 | 备选 | 选择 | 理由 |
|------|------|------|------|
| 后端框架 | FastAPI / Django / Flask | **Flask** | 最小、最熟、够用 |
| 前端框架 | Vue / React / 原生 | **原生** | 项目简单，无需框架 |
| 桌面形态 | Electron / PyWebView / 浏览器 | **浏览器** | 用户选 A；轻量 |
| 数据缓存 | Redis / SQLite / JSON | **JSON** | 数据小（< 100KB），无并发 |
| 国际化 | gettext / JSON / JS | **JSON + JS** | 简单，双语 |
| ICS 库 | icalendar / 自写正则 | **icalendar** | 成熟、支持时区 |

## 数据结构

### `Match`（核心）

```json
{
  "match_id": "wc2026-gs-A1-1",
  "stage": "group",
  "group": "A",
  "date_utc": "2026-06-11T23:00:00Z",
  "home": {
    "code": "MEX",
    "country_en": "Mexico",
    "country_zh": "墨西哥",
    "flag": "mx"
  },
  "away": {
    "code": "RSA",
    "country_en": "South Africa",
    "country_zh": "南非",
    "flag": "za"
  },
  "score": {
    "home": 0,
    "away": 0,
    "status": "scheduled"  // scheduled | live | final
  },
  "venue": {
    "name": "Estadio Azteca",
    "city": "Mexico City",
    "country": "Mexico",
    "capacity": 87523
  },
  "goals": [
    {
      "team": "home",
      "player": "Player Name",
      "minute": 23,
      "type": "goal"  // goal | penalty | own_goal
    }
  ]
}
```

## 部署形态

详细 Quick Start 见 [README.md](../../README.md)。本地 daemon 启动：

```bash
python3 -m pip install -r requirements.txt
bin/serve.sh                      # 后台 daemon，日志 /tmp/wc_server.log
xdg-open http://127.0.0.1:8766    # 或打开浏览器手动访问
```

桌面 kiosk 模式（一键启动 + 全屏浏览器）：

```bash
bin/launch.py                     # 自动检测 chromium/chrome/firefox
# 等价于 bin/start.sh
```

云端 Render 部署见 [deployment/render.md](../deployment/render.md)，Cloudflare quick tunnel 见 [maintenance/tunnel.md](../maintenance/tunnel.md)（如存在）或 `bin/tunnel.sh --help`。

## 后续演进

- 如果以后要做移动端 PWA → 前端结构不变，加 service worker
- 如果要支持多赛事 → 加 `data/sources/` 目录，按赛事隔离
- 如果要实时比分 → 加 WebSocket，不改 REST API
