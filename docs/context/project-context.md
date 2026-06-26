# project-context.md — 当前快照

> **这是项目最简的"现在长什么样"。** 任何大变化（plan 状态、blocker、新鲜度）改这里。

## 一句话

桌面世界杯赛程看板，Python+Flask 后端 + 原生 HTML/JS 前端 + 浏览器全屏 / Render 云端双形态。按日期分组赛程、国旗+队名+比分、点击看进球详情，32 强对阵表、Best 3rd Top 8 实时面板；中英双语并列。

## Active work 当前快照（2026-06-26）

- **Active plan**: [`043-doc-refresh-quickstart-and-current-state.md`](../plans/043-doc-refresh-quickstart-and-current-state.md)（Quick Start 现代化 + 文档同步）
- **Previous plan (042)**: Best 3rd Top 8 面板 — [06-26-plan-042.md](../logs/2026/06-26-plan-042.md)
- **AI autonomy**: plan-first（任何 `src/` 改动都要先有 plan）
- **Current blocker**: none
- **Documentation freshness**: 🟢 **fresh**（2026-06-26 Plan 043 进行中）

## 用户已确认的关键决策

1. UI：中文 + 英文并列（2026-06-12）
2. 数据源：baires/fifa-cal-2026 ICS + worldcup26.ir API（Plan 012）
3. 桌面形态：浏览器全屏（kiosk），不打包本地 app（2026-06-12）
4. 比分更新：手动刷新（不轮询，Plan 016 修过几次刷新行为）
5. 项目路径：`/home/lqiu/.openclaw/workspace/2026worldCupCoverage/`
6. 端口：8766（8765 被本机其他服务占，2026-06-12）
7. Render 部署：用免费层 + gunicorn（Plan 021）
8. Cloudflare quick tunnel：作为 0 账号外网访问方案（Plan 022）

## 已实现功能（Plan 001 - 042 累计）

### 数据层（src/data/）

- ✅ ICS fetcher（baires 源 + 本地缓存）
- ✅ ICS parser（104 场，兼容 post-match `X 2-0 Y` 格式，Plan 037+）
- ✅ World Cup 26 API 集成（实时比分、积分榜、球队信息）
- ✅ Standings 计算（FIFA 顺序：pts → GD → GF）
- ✅ Qualification 状态（locked_top2 / favored / eliminated / pending）
- ✅ Best 3rd race（12 队 → 8 晋级，Plan 029/031/041/042）
- ✅ Bracket pairings（FIFA 32 强对阵树，Plan 029-033）

### API 层（src/app.py，10 路由）

- `GET /` — 主页面
- `GET /api/matches` — 比赛列表（按日期过滤）
- `POST /api/refresh` — 拉新数据（ICS + API + qualification）
- `GET /api/health` — 健康检查
- `GET /api/teams` — 球队元数据
- `GET /api/qualification` — 积分榜 + 第 3 名排名（带 cache）
- `GET /static/*` — 静态资源

### 前端（src/templates + src/static）

- ✅ 104 场按日期分组，今日高亮
- ✅ 国旗（flag-icons CDN）+ 中英双语队名
- ✅ 比分 + 状态（scheduled / live / final）
- ✅ 比赛详情弹窗（进球人、进球时间、场馆、倒计时、积分榜）
- ✅ 32 强对阵表（Bing-style 镜像布局）
- ✅ Best 3rd Top 8 面板（Plan 042）
- ✅ 双 tab（赛程 Matches / 对阵 Bracket）
- ✅ Widget 模式（`?view=widget` 紧凑卡片，60s 自动刷新）
- ✅ PWA（manifest + service worker，可安装到桌面）
- ✅ 桌面 kiosk launcher（`bin/launch.py`）

### 部署 / 运维

- ✅ Render 免费层（render.yaml + gunicorn）
- ✅ Cloudflare quick tunnel（`bin/tunnel.sh`）
- ✅ 桌面 / 启动器（`bin/launch.py` / `bin/open.sh`）
- ✅ 后端 daemon（`bin/serve.sh` start/stop/status）

### 测试 / 文档

- ✅ 443 个 pytest（qualification / bracket / parser / API / 渲染 / 启动器）
- ✅ 6 个 plan-doc 配套 audit gate 脚本
- ✅ 42 个 plan 文件 + 16 个日志
- ✅ 5 个 context + 完整 requirements / design / architecture

## 技术栈快照

| 层 | 选型 | 理由 |
|----|------|------|
| 后端 | Python 3.10 + Flask 3 + gunicorn | 轻、跨平台、好爬数据 |
| 前端 | 原生 HTML + ES6 JS + flag-icons CDN | 零打包负担（无 React/Vue） |
| 桌面 | Chromium / Firefox `--kiosk` | 用户选 A 方案 |
| 数据 | baires ICS + worldcup26.ir API + 本地 JSON 缓存 | 双源 + 离线可用 |
| 国旗 | lipis/flag-icons 6.6.6 | SVG 成熟，CDN 稳定 |
| 部署 | gunicorn + Render（free） | 零成本 + 自动 HTTPS |
| 国际化 | 中文 + 英文并列 | 双语人群 |

## 关键文件入口

- 启动: [`bin/serve.sh`](../bin/serve.sh)
- Flask 入口: [`src/app.py`](../src/app.py)
- 前端: [`src/static/js/main.js`](../src/static/js/main.js) + [`src/templates/index.html`](../src/templates/index.html)
- 数据层: [`src/data/`](../src/data/)
- 配置: [`pyproject.toml`](../pyproject.toml) + [`requirements.txt`](../requirements.txt) + [`render.yaml`](../render.yaml)

## 下次 session 怎么接上

最重要的文件是 [docs/logs/2026/06-26-plan-042.md](../logs/2026/06-26-plan-042.md) § "验证" 段（Plan 042 端到端验证），以及 [docs/logs/2026/06-23-ics-summary-score.md](../logs/2026/06-23-ics-summary-score.md)（ICS parser hotfix）。

按 AGENTS.md 必读顺序读完后，跳到 active plan 043（Quick Start 现代化 + 文档同步，本 doc 自身的源头），完成后看 backlog 选下一步。

## 已知非问题

- `data/qualification_cache.json` `locked_top8` 暂时为空（3 个组别 L/D/J 还有末轮未踢）—— 这是设计预期，非 bug
- 10 个 e2e/bracket-pairing 测试因为 fixture 与实时数据漂移而失败 —— **预先存在**，与最近 5 个 plan 无关
