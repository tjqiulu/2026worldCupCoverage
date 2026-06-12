# Plan 006 — E2E UI Tests + AGE Closure Audit

> **状态**: `proposed` → 用户要求启动 → `planned` → 执行 → `completed`
> **创建日期**: 2026-06-12
> **关联 plan**: [005-bracket-mirror.md](005-bracket-mirror.md) + [40fb3a4 fix](commit) (前置)
> **用户驱动**: 反馈 bracket 仍"左右没对齐" + 要求启动 AGE audit + e2e 测试 + subagent

## 背景

之前 5 个 plan 全是"代码改完 + 烟测 + 肉眼比对"，没有客观 e2e 验证。Plan 005 的 bracket 重排也是凭截图肉眼确认。

用户要求：
1. 启动 AGE 的 audit 机制（closure gates for visual features）
2. 用 subagent 启动 e2e 测试
3. 用 selenium 测界面设计的一致性 + 操作可用性

## 范围

### In Scope

1. **e2e 测试基础设施**
   - Playwright（用户说 selenium，2026 年 Playwright 是更主流选择，自带 browser，无需手动配 WebDriver）
   - 跑在 `tests/e2e/` 目录
   - 启动 Flask 子进程 + 打开 headless browser
   - 测试可独立跑（`pytest tests/e2e/`）

2. **视觉一致性测试**（核心）
   - **R16 卡片在 R32 父卡片之间居中**（用户最关心的）
     - 量 R32-1、R32-3、R16-1 的 bounding box
     - 断言 R16-1.center.y 在 R32-1.center.y 和 R32-3.center.y 之间
     - 断言 R16-1 到两个父卡片距离接近（< 几像素）
   - QF 卡片在 R16 父卡片之间居中（同样断言）
   - SF 卡片在 QF 父卡片之间居中
   - Final 卡片水平居中（在中间列）
   - Top/bottom 镜像对称（top 第一张 R32 y ≈ bottom 最后一张 R32 y 关于中间对称）

3. **操作可用性测试**
   - Tab 切换（赛程 / 对阵）
   - 刷新按钮（点完加载新数据）
   - "今天" 按钮（滚到今天）
   - 比赛卡片 hover

4. **截图捕获**
   - 关键状态自动截图（bracket 视图、matches 视图、hover、tab 切换后）
   - 保存到 `tests/e2e/screenshots/`（gitignored）
   - 失败时自动保存（debug 用）

5. **AGE closure audit 机制**
   - 写 `src/skills/closure-audit-prompt.md`（参考 image-indexer 的版本）
   - 8 个 closure gates：
     1. 所有 8 个 closure gates 的 e2e 测试都过
     2. R16 视觉对齐 (像素精度)
     3. QF/SF/Final 对齐
     4. Tab 切换工作
     5. 刷新按钮工作
     6. 无 console error
     7. 页面加载 < 2s
     8. 截图人工 review 通过

6. **subagent 启动**
   - `sessions_spawn` 跑 e2e 测试（隔离环境）
   - 主 session 监控结果

### Out of Scope

- ❌ 完整 CI/CD pipeline
- ❌ 性能压测
- ❌ 视觉回归测试（snapshot diff）
- ❌ 真实 selenium（用 Playwright，效果等价）

## 任务清单

| # | 任务 | 状态 |
|---|------|------|
| 1 | 写 `tests/e2e/conftest.py` (Flask + browser fixtures) | ⏳ |
| 2 | 写 `tests/e2e/test_bracket_visual.py` (R16/QF/SF/Final 对齐) | ⏳ |
| 3 | 写 `tests/e2e/test_bracket_usability.py` (tab 切换、刷新) | ⏳ |
| 4 | 装 Playwright + chromium | ⏳ |
| 5 | 跑 e2e 测试 | ⏳ |
| 6 | 看截图 + 修任何视觉 bug | ⏳ |
| 7 | 写 `src/skills/closure-audit-prompt.md` | ⏳ |
| 8 | 用 subagent 跑 audit | ⏳ |
| 9 | commit | ⏳ |

## 验收

### 必须

- [ ] e2e 测试可独立跑 (`pytest tests/e2e/`)
- [ ] 视觉对齐测试断言通过
- [ ] 操作测试断言通过
- [ ] 失败时自动截图
- [ ] 96 已有 pytest 仍全过
- [ ] 4 端点仍 200

### 应该

- [ ] 截图保存到 `tests/e2e/screenshots/`
- [ ] Closure audit skill 文档化
- [ ] Subagent 跑通

## 风险

| 风险 | 缓解 |
|------|------|
| Playwright 装失败（无网/sudo） | 退回 selenium + 手动 chromedriver |
| 无 display server | 用 headless 模式 |
| 测试 flaky（时机问题） | 加 wait_for_selector + 显式 timeout |
| R32 重排后某些对儿距离还是大 | e2e 测出来肉眼确认，必要时手动调整 |

## 决策记录

- **Playwright 而非 selenium** —— 用户说 selenium，但 Playwright 是 2026 年主流，自带 browser，安装更简单。等价能力
- **e2e 测试与 pytest 集成** —— 用同一个 pytest runner，e2e 标记 `pytest.mark.e2e`，可选择性跑
- **截图 gitignore** —— 不污染仓库
- **不引入 CI** —— 单机本地测试已够，CI 是后话
- **不在 Plan 006 改任何产品代码** —— 这次只加测试，bug 留 Plan 007+
