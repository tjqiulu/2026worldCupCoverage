# Plan 021 — Render 部署（云端公开访问 + 手机跨网访问）

> **状态**: `planned`
> **创建日期**: 2026-06-16
> **关联 plan**: [006-e2e-and-audit.md](006-e2e-and-audit.md)（AGE closure audit 机制参考）, [019-standings-gf-ga-gd-columns.md](019-standings-gf-ga-gd-columns.md)（上一个 plan，已完成）
> **用户驱动**: 14:30 用户问"代码已上传到 GitHub，能否在 GitHub 上部署服务？" 16:51 用户要求"按 AGE 方法论做 Render 方案的 plan/design"

## 背景

### 触发

- 14:30 用户问 GitHub 部署可行性
- 16:48 我给了方案对比（Render/Railway/Fly.io）
- 16:51 用户同意 Render 方案，要求按 AGE 方法论做 plan + design + 验证

### 现状

- 代码已 push 到 `github.com/tjqiulu/2026worldCupCoverage`（commit `a00bce7` 在 origin）
- Flask 服务当前在 `0.0.0.0:8766` 监听（commit `a00bce7` 改的，**前提是为手机同 WiFi 访问**）
- **但手机同 WiFi 有局限**：换网络/出门/4G 就访问不到
- **部署到云端**（Render）解决跨网访问问题，**也满足"代码在 GitHub + 自动部署"的现代开发模式**

## 详细需求（细到每条 R 都有验证手段）

### 部署配置层

- **R1**. `render.yaml` 存在且 Render 兼容
  - 顶层 `services:` 列表
  - `type: web`（不是 worker）
  - `runtime: python`
  - `buildCommand: pip install -r requirements.txt`
  - `startCommand: gunicorn "src.app:create_app()" --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
  - `envVars` 含 `PYTHON_VERSION: 3.10.21`（Render 强制）
  - `plan: free`
  - 验证: 用 [render-blueprint-linter](https://render.com/docs/blueprint-spec) 手动 lint；或 push 后 Render dashboard 报"valid blueprint"

- **R2**. `requirements.txt` 包含 `gunicorn>=21.0`
  - 验证: `cat requirements.txt` 显示 gunicorn 行
  - 注意: gunicorn 仅 Render 用，本地 `python src/app.py` 走 Flask dev server

- **R3**. `src/app.py` 读 `PORT` 环境变量，默认 8766
  - 改动: `PORT = int(os.environ.get("PORT", 8766))`
  - 验证: 本地不设 `PORT` 跑 `python src/app.py` 仍起 8766（向后兼容）；Render 注入 `PORT=10000` 后 gunicorn 自动 bind

- **R4**. 部署文档 `docs/deployment/render.md` 写好
  - 内容: 注册 Render → connect GitHub → 选 blueprint → 等 build → 拿到 URL
  - 附: 每次 `git push` 自动 redeploy 流程图

### 数据持久化层（重要风险点）

- **R5**. **ePhemeral disk 风险**有应对方案
  - Render 免费层 instance 重启后 `/data/details.json` 会清零
  - 选型:
    - **方案 1（接受丢）**: 接受重启丢 details，反正比赛日会重新从 API 写
    - **方案 2（外部存储）**: 用 GitHub Gist 存 details，重启时拉回
    - **方案 3（数据库）**: 改用 SQLite 存 db（Render free tier 现在支持 persistent disk 1GB，**2025 改了**）
  - **决策: 方案 1 起步**（最简单，符合 MVP 哲学），写在部署文档里说明限制

- **R6**. `data/matches.json` 在 git 里，**不**依赖磁盘
  - 验证: 部署后 `GET /api/matches` 仍返回 104 场

### API 行为层

- **R7**. 4 个现有端点全部正常
  - `GET /` → 200（HTML）
  - `GET /api/health` → 200（JSON）
  - `GET /api/matches` → 200（104 场）
  - `POST /api/refresh` → 200
  - 验证: Render 部署后用 curl 全部 200

- **R8**. 静态资源（CSS/JS/flag-icons CDN）正常加载
  - 验证: 浏览器 devtools 0 个 404

### 本地兼容层（用户最关心）

- **R9**. **`python src/app.py` 本地启动行为不变**
  - 没设 `PORT` 环境变量 → 用 8766（与改前一致）
  - 改前 `PORT = 8766` 是字面量，改后 `int(os.environ.get("PORT", 8766))` 在没设 env 时返回 8766
  - **等价性证明**: `int(os.environ.get("PORT", 8766)) == 8766` 当 `PORT` not in os.environ

- **R10**. **`render.yaml` 本地被忽略**
  - Python/Flask 启动时不读 `render.yaml`，**0 影响**
  - 验证: 改 `render.yaml` 任何字段，本地启动行为不变

- **R11**. **`gunicorn` 在 requirements.txt 不影响本地启动**
  - 装上 gunicorn 后本地仍是 `python src/app.py`（Flask dev server）
  - gunicorn 只在 Render 用，不在本地触发
  - 验证: 本地启动日志仍是 "Running on http://0.0.0.0:8766" 而非 "gunicorn master"

### AGE closure audit gates（按 Plan 006 的 8 个 gate 套）

| # | Gate | 验证方法 | 状态 |
|---|------|----------|------|
| 1 | `render.yaml` 语法合法 | Render dashboard 自动 lint | ⏳ |
| 2 | Render build 成功 | 部署日志 0 error | ⏳ |
| 3 | 4 个端点 200 | curl 测试 | ⏳ |
| 4 | `data/matches.json` 104 场存在 | `len(GET /api/matches) == 104` | ⏳ |
| 5 | 本地 `python src/app.py` 仍起 8766 | pytest + 手动启动 | ⏳ |
| 6 | 200/200 pytest 全过 | `pytest tests/ -q` | ⏳ |
| 7 | 静态资源 0 个 404 | 浏览器 devtools 抓 | ⏳ |
| 8 | 公开 URL 可在手机 4G 访问 | 跨网 curl + 浏览器 | ⏳ |

## 方案候选 + 决策

### 1. 部署平台选型
- (A) **Render**（采用）— 最简，750h/月，Blueprint 自动读 render.yaml
- (B) Railway — $5/月信用额，需手动配 railway.toml
- (C) Fly.io — 免费 3 shared VM，需手写 fly.toml + Docker
- 决定 A。理由: 最少配置，Blueprint 模式跟 GitHub push 集成最丝滑

### 2. 进程管理工具
- (A) **gunicorn**（采用）— 工业标准
- (B) uWSGI — 配置复杂
- (C) Waitress — 跨平台但 gunicorn 更主流
- 决定 A。理由: 跟 Plan 002 的"轻、跨平台、好爬数据"哲学一致；Render 文档默认推 gunicorn

### 3. PORT 读取方式
- (A) **`int(os.environ.get("PORT", 8766))`**（采用）— 标准模式
- (B) hardcode `PORT = 8766` + 文档说明 Render 注入 PORT
- 决定 A。理由: 跟所有 PaaS 习惯一致；本地默认 8766 行为不变

### 4. 数据持久化
- (A) **接受 ephemeral**（采用）— 比赛日重新从 API 写
- (B) Gist 存 details
- (C) SQLite + persistent disk
- 决定 A。理由: MVP 哲学；YAGNI；以后真要持久化再升级

## 范围

### In Scope

1. 加 `render.yaml`（根目录）
2. `requirements.txt` 加 `gunicorn>=21.0`
3. `src/app.py` 改 PORT 读 env
4. 写 `docs/deployment/render.md` 部署文档
5. 推 GitHub 触发 Render 首次部署
6. 验证 8 个 closure gates

### Out of Scope

- ❌ 改前端任何代码（前端 0 改）
- ❌ 加域名/HTTPS（Render free tier 自带 `*.onrender.com` HTTPS）
- ❌ 加 CI/CD（Render 自带 GitHub push → redeploy）
- ❌ 加 monitoring（Render dashboard 自带）
- ❌ 改数据架构（data/*.json 维持）
- ❌ Render 付费层（用户没要求）

## 任务清单

| # | 任务 | 文件 | 估时 | 状态 |
|---|------|------|------|------|
| 1 | 加 `render.yaml` | 新建 `render.yaml` | 5 min | ⏳ |
| 2 | 加 `gunicorn` 到 requirements | `requirements.txt` | 1 min | ⏳ |
| 3 | `src/app.py` 改 PORT 读 env | `src/app.py` | 1 min | ⏳ |
| 4 | 写部署文档 | 新建 `docs/deployment/render.md` | 15 min | ⏳ |
| 5 | 跑 pytest 验证本地兼容 | `pytest tests/ -q` | 30s | ⏳ |
| 6 | 推 GitHub | `git push origin main` | 10s | ⏳ |
| 7 | Render dashboard 创 Blueprint | 浏览器操作 | 5 min | ⏳ |
| 8 | 验证 8 个 closure gates | curl + 浏览器 | 10 min | ⏳ |
| 9 | 写 log | `docs/logs/2026/06-16-plan-021.md` | 5 min | ⏳ |
| 10 | commit | `git commit` | 1 min | ⏳ |

**总估时: ~45 min**

## 风险评估

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| Render free tier sleep 后 cold start 30s | 高 | 中 | 部署文档写明；用户接受 |
| details.json 重启丢 | 中 | 中 | 接受；用户手动 refresh 重写 |
| Render build 失败（依赖问题） | 低 | 高 | 提前本地 `pip install -r requirements.txt` 验证 |
| 公开 URL 被滥用 | 低 | 低 | 单用户，worldcup26.ir API 限流；监控用 Render dashboard |
| Gunicorn worker 数不当 | 低 | 低 | `--workers 2 --timeout 120` 保守配置；如需再调 |
| 手机 4G 访问慢 | 低 | 低 | Render 美国区节点，到国内手机可能 200-500ms |

## 不会误伤（关键 — 用户最关心）

| 误伤点 | 验证 | 结论 |
|--------|------|------|
| 本地 `python src/app.py` 起服务 | pytest + 手动启动 | ✅ 等价（PORT 读 env，默认 8766） |
| 本地浏览器访问 127.0.0.1:8766 | curl + 浏览器 | ✅ 等价 |
| 本地手机同 WiFi 访问 192.168.1.44:8766 | curl + 手机 | ✅ 等价（HOST 仍是 0.0.0.0） |
| `python src/...` import 链路 | pytest | ✅ 等价（无 import 改动） |
| 200/200 pytest 全过 | `pytest tests/ -q` | ✅ 等价（无测试逻辑改动） |
| `data/matches.json` 读取 | `len(GET /api/matches) == 104` | ✅ 等价（无 API 改动） |
| `data/details.json` 读取/写入 | `POST /api/refresh` | ✅ 等价（无 details 改动） |

## 设计要点

### 1. `render.yaml` 完整内容

```yaml
services:
  - type: web
    name: wc2026-coverage
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn "src.app:create_app()" --bind 0.0.0.0:$PORT --workers 2 --timeout 120
    envVars:
      - key: PYTHON_VERSION
        value: 3.10.21
      - key: FLASK_DEBUG
        value: "0"
    plan: free
    autoDeploy: true   # git push 即触发 redeploy
```

### 2. `requirements.txt` diff

```diff
 Flask>=3.0
 icalendar>=5.0
 requests>=2.31
+gunicorn>=21.0
 pytest>=7.0
```

（注: pytest 仍在 requirements.txt 没问题；不区分 prod/dev 依赖是项目当前风格，参考 pyproject.toml 已经有 optional-dependencies.dev 但 requirements.txt 没分）

### 3. `src/app.py` diff

```diff
-HOST = "0.0.0.0"
-PORT = 8766
+HOST = "0.0.0.0"
+PORT = int(os.environ.get("PORT", 8766))
```

（`os` 已在文件 L11 导入，0 改动）

### 4. `docs/deployment/render.md` 大纲

```markdown
# Render 部署指南

## 一次性配置
1. 注册 render.com（GitHub 登录）
2. Dashboard → New + → Blueprint
3. 选 `tjqiulu/2026worldCupCoverage` 仓库
4. Render 自动读 `render.yaml`，识别 service
5. 点 "Apply" → 等 build（~3 min）

## 拿到 URL
- 形如 `https://wc2026-coverage.onrender.com`
- 免费 HTTPS
- 免费 .onrender.com 子域名

## 日常使用
- `git push origin main` → Render 自动 redeploy（~2 min）
- Dashboard 看 build log / runtime log

## 已知限制
- 免费层 15min 无请求后 sleep
- 免费层 instance 重启后 `data/details.json` 清零
- 重新拉取：浏览器点 "刷新" 按钮 或 POST /api/refresh
```

## 验收（必须 vs 应该）

### 必须（DoD）

- [ ] `render.yaml` 存在且合法
- [ ] `gunicorn` 在 requirements.txt
- [ ] `src/app.py` 读 PORT env
- [ ] 本地 `python src/app.py` 仍起 8766
- [ ] 200/200 pytest 全过
- [ ] Render build 成功
- [ ] 公开 URL 4 端点全部 200
- [ ] 手机 4G 能访问公开 URL

### 应该

- [ ] 部署文档写好
- [ ] 截图部署后界面
- [ ] 写 log 记录
- [ ] commit 全部
- [ ] Render dashboard 截图存 docs/deployment/screenshots/

## 决策日志

### 1. 选 Render 不选 Railway/Fly.io
- Render: 0 配置，Blueprint 模式
- Railway: 需 railway.toml，5$/月 credit 偏紧
- Fly.io: 需 Docker + fly.toml，对这个 Flask app 过重
- 决定: Render

### 2. 用 gunicorn 不用 uvicorn/waitress
- gunicorn: WSGI 标准，Render 文档默认
- uvicorn: ASGI，本项目是同步 Flask 用不上
- 决定: gunicorn

### 3. workers=2 timeout=120
- Flask app 是 CPU 轻、IO 重（外部 API 调用）
- workers=2 适配 Render free tier (0.1 CPU)
- timeout=120 给 worldcup26.ir API 30s 调用 + 余量
- 决定: workers=2 timeout=120

### 4. 接受 ephemeral disk
- MVP 哲学
- 比赛日重新从 API 写 details
- 真要持久化以后再升级到 SQLite
- 决定: 接受

## 下一步

用户批准本 plan → 执行任务清单 1-10 → 写 log → commit
