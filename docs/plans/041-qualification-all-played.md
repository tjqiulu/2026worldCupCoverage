# Plan 041 — Qualification: 全部已踢完组别应标 locked_top2 + eliminated

> **状态**: proposed → completed
> **log**: 待实施后写
> **创建日期**: 2026-06-25
> **触发**: 用户 07:38 截图 B 组 3 场全踢完（瑞士 7pts / 加拿大 4pts / 波斯尼亚 4pts / 卡塔尔 1pts），但 32 强对阵表里 `1B` / `2B` 位置还显示 FIFA 占位符，没出现瑞士和加拿大
> **关联 plan**: [029-bracket-qualified-teams.md](029-bracket-qualified-teams.md)

## 问题

B 组 3 场小组赛于 2026-06-25 03:00 北京时间全部结束，瑞士 7pts / 加拿大 4pts（FIFA GD+5 排第 2）/ 波斯尼亚 4pts（GD-1 排第 3）/ 卡塔尔 1pts。

`/api/qualification` 返回的 B 组 4 队**全在 `pending`**——`locked_top2 = []` + `eliminated = []` + `favored_top2 = []`。

前端 `resolveBracketPlaceholder()`（main.js:145）查 `locked_top2` / `favored_top2` 都没有匹配 → 回退到 FIFA 占位符渲染 → 用户看到 `1B` / `2B` 占位符而不是"🇨🇭 瑞士" / "🇨🇦 加拿大"。

## 根因（AGE）

### A — Aggregate
截图证据：
- A 组（mp=2）：Mexico 在 `locked_top2` ✓（前端 R32 卡 1A 显示"🇲🇽 墨西哥"）
- E 组（mp=2）：Germany 在 `locked_top2` ✓
- I 组（mp=2）：France + Norway 在 `locked_top2` ✓
- **B 组（mp=3）**：所有 4 队全在 `pending` ✗（应是 Switzerland + Canada locked_top2，Qatar eliminated）

### G — Get to root cause

**直接原因**：`src/data/qualification.py:compute_per_group` 的循环：

```python
if pts_current > second_best_other and not all_played:
    locked_top2.append(...)
elif pts_best < second_min_other and not all_played:
    eliminated.append(...)
else:
    if (not all_played and pts_current > second_min_other):
        favored_top2.append(...)
    else:
        pending.append(...)
```

当 `all_played = True` 时：三个 `if not all_played` 条件全 False → 所有队落进 `else` → 进 `pending`。

**深层原因（5-Why）**：

- Why 1: 为什么 B 组 `all_played` 但没被标 locked_top2？
- Why 2: `compute_per_group` 在 `all_played=True` 时跳过了所有判定分支
- Why 3: 因为三个判定条件都加了 `and not all_played` 守卫
- Why 4: 为什么加这个守卫？Plan 029 写注释"如果组别 3 场全踢完，'待锁定'概念就不存在了"
- Why 5 (root): **Plan 029 把 `locked_top2` 的语义定义成"未踢完但数学严格锁定"——但用户视觉期望 `locked_top2 = 32 强卡里渲染真队的所有情况**（包括"已踢完 = 已确定"）。两个语义错位。

**测试反映错误语义**：`tests/test_qualification.py:test_all_finals_no_locked`：

```python
def test_all_finals_no_locked(self):
    """如果 3 场都踢完了, locked_top2 应为空 (全部确定)."""
    ...
    assert len(result["locked_top2"]) == 0  # 全踢完了，没"待锁定"
```

——`test_all_finals_no_locked` 把 Plan 029 的错误语义**显式硬编码**进测试。测试和用户需求不一致，是测试错了。

### E — Evaluate 修复方案

| 方案 | 改哪里 | 评估 |
|------|--------|------|
| **A. 修 `compute_per_group`：循环外加 `if all_played` 分支，按 standings index 取 top 2 locked / bot 2 eliminated** | `src/data/qualification.py` +8 行 | **采用**：保持 `locked_top2 = 100% 确定晋级` 语义（最准），最小修改 |
| B. 改前端 `resolveBracketPlaceholder` 兜底"all_played 时直接查 standings" | `main.js` | 后端漏判就修后端，前端兜底会引入重复逻辑 |
| C. 新建 `determined_top2` 字段并存 | `qualification.py` | 复杂化数据模型，没好处 |
| D. 删 `and not all_played` 守卫 | `qualification.py` | 改了之后 locked_top2 语义从"未踢但锁"变成"任何时候的最优"——这才是用户要的。但 favored_top2 也得同样处理（同样有 `not all_played` 守卫），改动更多且需要重排控制流。方案 A 显式分支更可读。 |

**采用 A**。理由：

- 保持 `locked_top2 = 100% 确定晋级` 语义——和 Plan 029 docstring 一致
- 显式 `if all_played` 分支比 4 个 `not all_played` 守卫更易读
- 修改行数 ~8 行 + 1 测试翻转 + 1 新测试
- `eliminated` 在 `all_played` 时也合理（最后 2 名确实 100% 出局）

## 修复

### Fix 1: `src/data/qualification.py:compute_per_group`（L2）

在主循环结束后，加 `all_played` 兜底分支：

```python
# 主循环结束后：

if all_played and len(standings) >= 4:
    # 组别 3 场全踢完：top 2 = 100% 锁定晋级，bot 2 = 100% 出局
    # standings 已经按 FIFA 优先级排好序（compute_standings_from_details
    # 用 pts desc / gd desc / gf desc），所以 index 就是最终排名
    for idx, t in enumerate(standings[:2]):
        # 已存在 locked_top2 里就跳过（防御性）
        if not any(x["team_id"] == t["team_id"] for x in locked_top2):
            locked_top2.append({
                "team_id": t["team_id"],
                "reason": "组别已全部结束，按当前积分榜确定晋级",
            })
    for t in standings[2:]:
        if not any(x["team_id"] == t["team_id"] for x in eliminated):
            eliminated.append({
                "team_id": t["team_id"],
                "reason": "组别已全部结束，按当前积分榜确定淘汰",
            })
```

**为什么放在主循环后**：主循环走 `if not all_played` 分支，最后 else 会把所有队扔进 `pending`。新分支**只在** `all_played=True` 时跑，且**只**把没被标过的队标上，不会污染主循环的输出。

**关于 `favored_top2`**：不动。`favored_top2` 是"未踢完但软状态接近锁"——已踢完没有"软"概念，locked_top2 已经覆盖了。

### Fix 2: 翻转 `tests/test_qualification.py:test_all_finals_no_locked`（L5）

把测试从"断言全空"翻转到"断言 top 2 locked + bot 2 eliminated"：

```python
def test_all_finals_played_top2_locked_bot2_eliminated(self):
    """组别 3 场全踢完：top 2 锁定晋级，bottom 2 锁定淘汰。"""
    result = _run_group("X", [
        _mk_team("a", pts=7, mp=3, w=2, d=1),
        _mk_team("b", pts=6, mp=3, w=2, l=1),
        _mk_team("c", pts=4, mp=3, w=1, d=1, l=1),
        _mk_team("d", pts=0, mp=3, l=3),
    ])
    assert result["all_finals_played"] is True
    locked_ids = {t["team_id"] for t in result["locked_top2"]}
    eliminated_ids = {t["team_id"] for t in result["eliminated"]}
    assert locked_ids == {"a", "b"}, f"top 2 应锁: got {locked_ids}"
    assert eliminated_ids == {"c", "d"}, f"bot 2 应淘汰: got {eliminated_ids}"
    assert result["favored_top2"] == [], "all_played 不应有 favored"
    assert result["pending"] == [], "all_played 不应有 pending"
```

### Fix 3: 加 1 个新测试（边界 case，FIFA GD 平局优先）（L5）

```python
def test_all_played_with_pts_tie_uses_gd_break(self):
    """4pt 平局用 GD 决定排名（FIFA tie-breaker）."""
    # Switzerland 7pts vs Canada 4pts(GD+5) vs Bosnia 4pts(GD-1) vs Qatar 1pt
    # 模拟 B 组真实场景
    result = _run_group("B", [
        _mk_team("sui", pts=7, mp=3, w=2, d=1, gd=4),
        _mk_team("can", pts=4, mp=3, w=1, d=1, l=1, gd=5),
        _mk_team("bih", pts=4, mp=3, w=1, d=1, l=1, gd=-1),
        _mk_team("qat", pts=1, mp=3, w=0, d=1, l=2, gd=-8),
    ])
    assert result["all_finals_played"] is True
    locked_ids = [t["team_id"] for t in result["locked_top2"]]
    # standings 已按 FIFA 排序：sui(7) > can(4,GD+5) > bih(4,GD-1) > qat(1)
    assert locked_ids == ["sui", "can"], f"GD+5 优先: got {locked_ids}"
    eliminated_ids = {t["team_id"] for t in result["eliminated"]}
    assert eliminated_ids == {"bih", "qat"}
```

### Fix 4: 重算 `data/qualification_cache.json`（L4）

```bash
# 重算并落盘
curl -X POST http://localhost:8766/api/refresh
# 或：调用 _compute_and_cache_qualification() 直接重算
```

### Fix 5: 端到端验证（L4）

1. `pytest tests/test_qualification.py` 全过（>50 个 case）
2. `pytest tests/ --ignore=tests/e2e` 不退步
3. `curl /api/qualification | jq '.groups.B.locked_top2'` → 期望 `[{Switzerland, ...}, {Canada, ...}]`
4. 浏览器 R32 卡片 `1B` / `2B` 显示"🇨🇭 瑞士 Switzerland" + "🇨🇦 加拿大 Canada"
5. `curl /api/qualification | jq '.groups.B.eliminated'` → 期望 `[{Bosnia, ...}, {Qatar, ...}]`

## 范围

### In Scope
- L2 `src/data/qualification.py` 修 `compute_per_group`（+8 行）
- L5 `tests/test_qualification.py` 翻转 1 个旧 test + 加 1 个新 test
- L4 重算 `data/qualification_cache.json`
- L4 端到端验证（curl + pytest）
- L4 写 log + commit

### Out of Scope
- ❌ best 3rd race 算法（已正确）
- ❌ 前端 JS（`resolveBracketPlaceholder` 不需要改——`locked_top2` 一旦有数据就自动渲染）
- ❌ 别的组别（A/C/D/.../L）算法
- ❌ 32 强 R16/R8/R4/决赛的 W## 递归解析（Plan 030 候选，不在本 plan 范围）

## 风险

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| 主循环 + all_played 分支双重判定冲突 | 低 | 中 | 加防御性 `if not any(...)` 跳过重复 |
| standings 排序不对导致 top 2 错 | 极低 | 高 | `compute_standings_from_details` 已按 FIFA 排序，且新测试 041 显式覆盖 GD 平局 case |
| 影响 best 3rd race（第三个） | 极低 | 中 | `compute_best_3rd_race` 用 `group.third_place`（standings[2]），不动 |
| 别的组别（K/D/A）被波及 | 极低 | 高 | 加新测试前确认 A/E/I locked_top2 不变 |
| 翻 test 触发 CI 红 | 极低 | 低 | pytest 全过即可，CI 没设 gate |

## 验收

- [ ] `pytest tests/test_qualification.py` 全过
- [ ] `pytest tests/ --ignore=tests/e2e` 全过（不破坏现有 329+ case）
- [ ] `curl /api/qualification | jq '.groups.B'` 显示 Switzerland + Canada locked_top2
- [ ] `curl /api/qualification | jq '.groups.B'` 显示 Bosnia + Qatar eliminated
- [ ] A 组 Mexico 仍在 `locked_top2`（回归测试）
- [ ] I 组 France + Norway 仍在 `locked_top2`（回归测试）
- [ ] 浏览器 R32 卡 1B 显示"🇨🇭 瑞士 Switzerland"
- [ ] 浏览器 R32 卡 2B 显示"🇨🇦 加拿大 Canada"
- [ ] 用户视觉确认通过

## 决策记录

- **方案 A vs D（删守卫）**：选 A，理由：保持 `locked_top2` 显式语义 = "100% 确定晋级"；显式 if 分支可读性 > 4 个守卫；favored_top2 的 `not all_played` 守卫保留（favored 本来就是"未踢但软"概念）
- **测试翻转 vs 删除**：选翻转 + 重命名 `test_all_finals_played_top2_locked_bot2_eliminated`，理由：保留测试意图（验证 all_played 行为），修正断言
- **B 组数据一致性**：新测试用 B 组真实数据（7/4/4/1 pts）覆盖 GD tie-breaker 真实场景
- **不修 `favored_top2`**：`favored_top2 = 未踢完但软接近锁`，已踢完没有"软"概念；locked_top2 已覆盖视觉需求

## Closeout 计划

执行后：
- 状态置 `completed`
- 写 log `docs/logs/2026/06-25-plan-041.md`
- 8-Gate audit 通过
- commit
