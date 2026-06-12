# Plan 013 — Desktop Browser Fullscreen Launcher

> **状态**: `proposed` → 用户"做这个吧。桌面浏览器全屏启动" → `planned` → 执行 → `completed`
> **创建日期**: 2026-06-12
> **关联 plan**: 无（独立 UX 改进）
> **用户驱动**: "桌面浏览器全屏启动" (P1-003 backlog item)

## 背景

之前所有 plan 都假设用户**手动**在浏览器开 `http://127.0.0.1:8766/`。但用户想要**桌面应用体验**——一条命令启动全屏，不用手动操作。

## 范围

### In Scope

1. **`bin/launch.py`** - Python 启动器
   - 启动 Flask (subprocess, 后台)
   - 等 Flask ready (HTTP 健康检查)
   - 检测可用浏览器 (chromium, google-chrome, firefox)
   - 启动浏览器在 kiosk 模式 (全屏无 chrome)
   - 等浏览器关闭
   - 关闭 Flask 进程 (clean shutdown)
   - Ctrl+C 处理

2. **`bin/start.sh`** - Shell 包装（更简单调用）
   - `exec python3 bin/launch.py`

3. **`--no-browser` 模式** (调试用)
   - 只启动 Flask，不开浏览器
   - 适合无 GUI 环境（CI / SSH）

4. **8 闸 closure audit**:
   - G1: Script exists + executable
   - G2: Browser detection (chromium, chrome, firefox)
   - G3: Flask server starts + ready check
   - G4: Browser launches in kiosk mode (含正确 args)
   - G5: Browser close → Flask stops (clean shutdown)
   - G6: Ctrl+C → 全部 cleanup
   - G7: Missing browser → graceful error
   - G8: --no-browser mode works

5. **README 文档**：如何使用 + 安装浏览器

### Out of Scope

- ❌ 系统托盘图标 / 后台常驻（一次性命令）
- ❌ 开机自启 (systemd / LaunchAgent)——留 Plan 014
- ❌ 多显示器支持
- ❌ Windows / macOS（先支持 Linux）
- ❌ 自定义浏览器 args（用合理默认值）

## 任务清单

| # | 任务 | 状态 |
|---|------|------|
| 1 | 写 `bin/launch.py` (Python 启动器) | ⏳ |
| 2 | 写 `bin/start.sh` (shell 包装) | ⏳ |
| 3 | 写 `tests/test_launch.py` (unit tests) | ⏳ |
| 4 | 写 `docs/maintenance/desktop-launcher.md` | ⏳ |
| 5 | 跑全部测试 | ⏳ |
| 6 | 实际启动一次验证 (smoke test) | ⏳ |
| 7 | commit | ⏳ |

## 验收

### 必须

- [ ] `python3 bin/launch.py` 启动 Flask + 全屏浏览器
- [ ] 关闭浏览器 → Flask 自动停止
- [ ] Ctrl+C → 全部 cleanup
- [ ] 没装浏览器 → 友好错误 + 仍然启动 Flask
- [ ] 8 闸 closure audit 全过

## 风险

| 风险 | 缓解 |
|------|------|
| 没装浏览器 | 检测 + 友好错误，建议 `apt install chromium` |
| 多个 Flask 实例 | 检查端口占用？先不处理（简单）|
| 浏览器崩溃但 launcher 不知 | 轮询健康检查（先不实现）|
| Windows 兼容性 | 先 Linux，README 注明 |

## 决策记录

- **Python 而非 shell** —— 跨平台 + 错误处理 + 可测试
- **检测浏览器顺序**: chromium-browser → chromium → google-chrome → firefox
- **Kiosk mode args**: `--kiosk --noerrdialogs --disable-infobars` (Chrome 系列)，`--kiosk` (Firefox)
- **不需要 sudo** —— 用户用 `pip install --user` 装的 playwright
- **5min Flask 启动超时** (拉 scores API 可能慢)
- **关闭浏览器 = 关闭 Flask** —— 标准桌面 app 行为
