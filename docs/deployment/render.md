# Render 部署指南

> Plan 021 — 把 `2026worldCupCoverage` 部署到 Render 免费层，让手机 4G 也能访问。

## 一次性配置（10 分钟）

### 1. 注册 Render

1. 浏览器打开 [render.com](https://render.com)
2. 点 "Get Started for Free" → 用 **GitHub 账号登录**（授权 OAuth 读 `tjqiulu/2026worldCupCoverage` 仓库）
3. Dashboard 默认进入

### 2. 创建 Blueprint

1. Dashboard 顶部点 **"New +"** → **"Blueprint"**
2. "Connect a repository" 选 `tjqiulu/2026worldCupCoverage`
3. Render 自动读根目录的 `render.yaml`
4. 看到 service 预览：`wc2026-coverage` (web, free)
5. 点 **"Apply"**

### 3. 等首次部署（3-5 分钟）

- Dashboard 的 "Events" 标签会显示 build progress
- 看到 "Deploy live" = 成功
- 如果 build fail，看 "Logs" 标签

### 4. 拿到 URL

- 格式：`https://wc2026-coverage.onrender.com`
- 自动 HTTPS
- 在 Settings → Custom Domain 可以改子域名（仍免费）

## 日常使用

### 代码改完自动 redeploy

```bash
git push origin main
# Render 检测到 push → 自动重新 build + 重启 instance
# 大约 2 分钟
```

Dashboard 的 "Events" / "Logs" 实时显示进度。

### 看运行时日志

Dashboard → wc2026-coverage → "Logs" 标签

### 重启 instance

Dashboard → wc2026-coverage → 右上角 "Manual Deploy" → "Clear build cache & deploy"

## 已知限制

| 限制 | 说明 | 缓解 |
|------|------|------|
| **Cold start 30 秒** | 免费层 15 分钟无请求后 instance sleep，下次访问需 30s 唤醒 | 比赛日保持浏览器每 5 分钟 F5 一次；或升级 $7/月 plan 无 sleep |
| **Ephemeral disk** | instance 重启后 `/data/details.json` 清零 | 比赛日用浏览器 "刷新" 按钮重写；或升级到 persistent disk 1GB |
| **CPU 0.1 vCPU** | 免费层只有 0.1 核 | 流量低够用；峰值（决赛？）可能慢 |
| **750 小时/月** | 免费层每月 750h 上限 | 单 instance 跑不满；超了自动停机下月 1 号恢复 |
| **Build 限制** | 单次 build 最多 15 分钟 | 当前 build 约 1 分钟，够用 |

## 数据流（云端 vs 本地对比）

```
┌─────────────────────────────────────────────────────────────┐
│                    Render Cloud (Plan 021)                  │
│                                                             │
│  Internet → Render edge → gunicorn (2 workers)             │
│                              │                              │
│                              ▼                              │
│                  src.app:create_app()                       │
│                              │                              │
│  ┌───────────────────────────┼──────────────────────────┐   │
│  │                           │                          │   │
│  ▼                           ▼                          ▼   │
│ data/                worldcup26.ir API          flag-icons CDN│
│ (git tracked:        (outbound HTTPS)          (CDN HTTPS)  │
│  matches.json)                                              │
│                                                             │
│  data/details.json — ephemeral (resets on restart)          │
└─────────────────────────────────────────────────────────────┘
```

**对比本地运行**：

- **同一**：Flask app 行为 100% 一致（gunicorn vs Flask dev server 是接口层差异，app 逻辑 0 改）
- **不同**：`data/details.json` 写盘只活到下次 instance 重启
- **相同点**：4 个端点（/, /api/matches, /api/refresh, /api/health）行为一致

## 手动验证部署成功

```bash
# 部署后跑这 4 行验证
curl -s -o /dev/null -w "HTTP %{http_code}\n" https://wc2026-coverage.onrender.com/api/health
curl -s https://wc2026-coverage.onrender.com/api/matches | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'{len(d)} matches')"
curl -s -o /dev/null -w "HTTP %{http_code}\n" https://wc2026-coverage.onrender.com/
curl -s -X POST -o /dev/null -w "HTTP %{http_code}\n" https://wc2026-coverage.onrender.com/api/refresh
```

期望：4 行都是 200，第二行输出 "104 matches"。

## 故障排查

### Build 失败：ModuleNotFoundError

→ 检查 `requirements.txt` 是否包含所有 import 的包。本项目有 Flask/icalendar/requests/gunicorn 4 个。

### Build 失败：Python version

→ `render.yaml` 的 `PYTHON_VERSION` 设的 3.10.21。如果 Render 不支持该 patch 版本，试试 3.10.0 或 3.11.0。

### 502 Bad Gateway

→ gunicorn 没起来。看 Logs：
- `Address already in use` → PORT 没读 env，改回 `int(os.environ.get("PORT", ...))`
- `ImportError` → 代码语法错或 import 路径错

### Cold start 一直 30s

→ 正常，免费层特性。要消除升级 $7/月 Starter plan。

## 升级到付费层

如果 7 月世界杯决赛日流量大，考虑升级：
- **Starter $7/月**：无 sleep，0.5 CPU，512MB RAM
- **Standard $25/月**：1 CPU，2GB RAM
- **Pro $85/月**：4 CPU，8GB RAM

按需升级，Dashboard → Settings → Plan → Change Plan。

## 回滚到本地

如果 Render 部署出问题想回滚本地：
1. Render Dashboard → wc2026-coverage → Settings → "Suspend Service"
2. 本地 `python src/app.py` 仍可正常起 8766（向后兼容已验证）

## 关联文件

- `render.yaml` — Render 部署配置
- `requirements.txt` — 加了 `gunicorn>=21.0`
- `src/app.py` — PORT 读 env
- `docs/plans/021-render-deployment.md` — Plan 文档
- `docs/logs/2026/06-16-plan-021.md` — 实施 + audit log
