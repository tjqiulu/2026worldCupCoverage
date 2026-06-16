# Plan 022 — Cloudflare Quick Tunnel（不绑卡、手机随时访问）

> **状态**: `planned`
> **创建日期**: 2026-06-16
> **关联 plan**: [021-render-deployment.md](021-render-deployment.md)（已 abandoned，用户选 B 方案）, [019-standings-gf-ga-gd-columns.md](019-standings-gf-ga-gd-columns.md)（AGE 8-gate audit 模板参考）
> **用户驱动**: 17:09 用户在 Render 绑卡步骤退出，17:22 选 B 方案（Cloudflare Tunnel / Tailscale / ngrok 中最简、零注册），17:25 确认"装 cloudflared，开 plan 022 走一遍"

## 背景

### Plan 021 替代方案

之前 Plan 021 把代码部署到 Render，build 成功前需要绑卡。用户在 17:09 到达 Render 绑卡步骤后退回，**要求完全不绑卡的方案**。

### 三方案对比（用户原文 17:20）

| 工具 | 注册？ | 复杂度 | 选？ |
|------|--------|--------|------|
| **Cloudflare quick tunnel** | ❌ 不要 | 1 命令 | ✅ |
| ngrok | ⚠️ 需账号拿 authtoken | 中 | ❌ |
| Tailscale | ❌ 需账号 + 手机装 App | 高 | ❌ |

**用户原话**："Cloudflare Tunnel / Tailscale / ngrok 哪个部署最简单，也不用注册啥的。。url变化无所谓"

## 详细需求

### 安装层

- **R1**. `cloudflared` 在系统里装好
  - 验证: `which cloudflared` 找到路径；`cloudflared --version` 输出版本号
  - 优先级: ① apt (Ubuntu 22.04 源里有) → ② GitHub binary download (fallback)
  - 选 apt 优先因为: 自动更新、systemd 集成、`cloudflared` 包名稳定

### 配置层

- **R2**. Flask 仍在 `0.0.0.0:8766` 监听（不改）
  - cloudflared 跟 Flask 解耦，cloudflared 通过 `http://localhost:8766` 转发
  - 验证: `curl 127.0.0.1:8766/api/health` 仍 200

- **R3**. cloudflared quick tunnel 模式（`--url` flag）启动
  - 命令: `cloudflared tunnel --url http://localhost:8766`
  - 不写任何 config.yml（quick tunnel 模式 0 配置）
  - 不需要 `cloudflared tunnel login`（quick tunnel 不要账号）
  - 验证: 启动后日志最后 5 行显示 `https://<random>.trycloudflare.com` URL

### 进程管理层

- **R4**. 用 nohup + 后台进程跑（不用 systemd unit）
  - 原因: 用户的桌面 Ubuntu，重启频率不高，手动 start/stop 够用
  - 命令: `nohup cloudflared tunnel --url http://localhost:8766 > /tmp/cf_tunnel.log 2>&1 &`
  - 验证: 进程在 `ps` 列表里；日志文件有内容

- **R5**. URL 提取脚本（`bin/tunnel-url.sh`）
  - 用户需要从日志里 grep URL 复制到手机
  - 脚本: `grep -oE 'https://[a-z-]+\.trycloudflare\.com' /tmp/cf_tunnel.log | head -1`
  - 验证: 跑脚本输出一个 URL

### 兼容性层（不会误伤本地）

- **R6**. **0 改 `src/`、0 改 `data/`、0 改 `requirements.txt`、0 改 `render.yaml`**
  - cloudflared 是 host 层面工具，跟项目代码完全解耦
  - 验证: `git status` 只有 `bin/tunnel-url.sh` 一个新文件

- **R7**. 本地 `python src/app.py` 行为不变
  - cloudflared 不影响 Flask 启动
  - 验证: G3 显式验证

- **R8**. Render plan (021) 不被破坏
  - `render.yaml` + `gunicorn` 留着不删，未来想用还能切回
  - 验证: `cat render.yaml` 仍存在

### AGE 8-Gate Closure Audit

| # | Gate | 验证 | 状态 |
|---|------|------|------|
| 1 | cloudflared installed | `which cloudflared && cloudflared --version` | ⏳ |
| 2 | cloudflared binary executable | `cloudflared --help` 退出 0 | ⏳ |
| 3 | Flask still on 8766 (backward compat) | `curl 127.0.0.1:8766/api/health` 200 | ⏳ |
| 4 | Quick tunnel starts without auth | `cloudflared tunnel --url ...` 不报 "login required" | ⏳ |
| 5 | Public URL generated | 日志含 `https://*.trycloudflare.com` | ⏳ |
| 6 | Public URL reachable from outside | `curl <url>/api/health` 200 | ⏳ |
| 7 | pytest 200/200 still pass | `pytest tests/ -q --ignore=tests/e2e` | ⏳ |
| 8 | Phone can access public URL (MANUAL) | 用户 4G 浏览器开 URL | n/a |

## 方案候选 + 决策

### 1. 安装方式
- (A) **apt 装**（采用）— Ubuntu 22.04 jammy 源有 `cloudflared` 包
- (B) GitHub binary download — fallback if apt 不可用
- 决定: 试 A，失败走 B

### 2. Quick tunnel 持久化
- (A) **nohup + log file**（采用）— 简单，URL 变化无所谓
- (B) systemd user service — 过度工程，重启换 URL
- (C) tmux/screen — 用户已经用 systemd 习惯
- 决定: A

### 3. URL 提取
- (A) **写一个 `bin/tunnel-url.sh` 脚本**（采用）— 用户跑一行拿 URL
- (B) 让 cloudflared 写到指定文件 — 加参数复杂
- 决定: A，最简单

### 4. 是否删 Render plan 021 的产物
- (A) **保留 render.yaml + gunicorn**（采用）— 未来想切回不用重建
- (B) 删 render.yaml — 干净但回不来
- 决定: A，删了可惜

## 范围

### In Scope

1. apt 装 cloudflared
2. 写 `bin/tunnel-url.sh`（URL 提取小工具）
3. nohup 启动 quick tunnel
4. 8-gate audit
5. 写 log
6. commit + push

### Out of Scope

- ❌ 改 Flask 代码（0 改）
- ❌ 改 render.yaml / requirements.txt
- ❌ Cloudflare 账号 / named tunnel（用户不要）
- ❌ systemd unit（用户没要求）
- ❌ 自定义域名（用户不要稳定 URL）
- ❌ 删 Render plan 021 产物（保留备选）

## 任务清单

| # | 任务 | 估时 |
|---|------|------|
| 1 | apt install cloudflared | 30s |
| 2 | 验证 cloudflared --version | 5s |
| 3 | 启动 Flask（仍在 8766） | 5s |
| 4 | nohup 启动 cloudflared quick tunnel | 10s |
| 5 | 写 bin/tunnel-url.sh | 5 min |
| 6 | 验证 8 个 closure gates | 3 min |
| 7 | 写 log | 5 min |
| 8 | commit + push | 30s |

**总估时: ~15 min**

## 风险评估

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| cloudflared apt 源不可用 | 低 | 中 | fallback 到 GitHub binary |
| Quick tunnel 启动后服务偶尔断 | 中 | 低 | 重启 cloudflared 进程即可 |
| 手机访问冷启动慢 | 低 | 低 | Cloudflare edge 节点比 Render 美国节点近 |
| 公网 URL 被爬 | 低 | 低 | worldcup26.ir API 限流；单用户数据无价值 |
| HTTPS 证书 | 0 | n/a | Cloudflare 自动签发 + 自动续 |

## 不会误伤（关键）

| 误伤点 | 验证 | 结果 |
|--------|------|------|
| Flask 8766 行为 | G3 | ✅ |
| Render plan 021 产物 | `cat render.yaml` | ✅ 保留 |
| pytest 200/200 | G7 | ✅ |
| data/*.json | 0 改 | ✅ |
| src/*.py | 0 改 | ✅ |

## 设计

### 1. apt 装 cloudflared

```bash
# Ubuntu 22.04
sudo apt-get update
sudo apt-get install -y cloudflared
```

### 2. `bin/tunnel-url.sh`（URL 提取小工具）

```bash
#!/usr/bin/env bash
# Print the current Cloudflare quick tunnel URL from /tmp/cf_tunnel.log
set -e
LOG="/tmp/cf_tunnel.log"
if [ ! -f "$LOG" ]; then
    echo "ERROR: $LOG not found. Is the tunnel running?" >&2
    echo "Start: nohup cloudflared tunnel --url http://localhost:8766 > $LOG 2>&1 &" >&2
    exit 1
fi
URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$LOG" | head -1)
if [ -z "$URL" ]; then
    echo "ERROR: no trycloudflare.com URL in $LOG. Tunnel may still be starting." >&2
    echo "Last 10 lines:" >&2
    tail -10 "$LOG" >&2
    exit 1
fi
echo "$URL"
```

### 3. 启动命令

```bash
# 1. Make sure Flask is up
PYTHONPATH=. nohup python3 -m src.app > /tmp/wc_app.log 2>&1 &

# 2. Start Cloudflare quick tunnel
nohup cloudflared tunnel --url http://localhost:8766 > /tmp/cf_tunnel.log 2>&1 &

# 3. Get URL
sleep 5
bin/tunnel-url.sh
```

### 4. 8-gate audit 脚本（`tests/audit_gates_plan022.py`）

按 Plan 021 的 audit_gates_plan021.py 模板，照搬结构：
- G1-G2 静态检查（which / version）
- G3 HTTP probe（Flask 8766）
- G4-G6 tunnel 启动 + URL 提取 + 外部可达性
- G7 pytest
- G8 manual

## 验收

### 必须

- [ ] cloudflared 装好
- [ ] Quick tunnel 启动成功
- [ ] 拿到 `https://*.trycloudflare.com` URL
- [ ] URL 外部 curl 200
- [ ] 8-gate audit 7/7 pass（G8 manual）
- [ ] 0 改 src/ data/ render.yaml requirements.txt

### 应该

- [ ] `bin/tunnel-url.sh` 脚本可用
- [ ] log 写好
- [ ] commit + push
- [ ] Render plan 021 产物保留
