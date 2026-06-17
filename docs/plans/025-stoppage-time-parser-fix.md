# Plan 025 — 补时进球 parser + 积分榜综合修复

> **状态**: `proposed` → `planned` (2026-06-17 10:05 用户批准) → 执行 ✅ → `completed` (2026-06-17 10:29 用户视觉确认 Gate 8 通过)
> **log**: [`docs/logs/2026/06-17-plan-025.md`](../logs/2026/06-17-plan-025.md)
> **创建日期**: 2026-06-17
> **关联 plan**: [017-incomplete-details-api-override.md](017-incomplete-details-api-override.md)（Plan 017.1 触发点）, [019-standings-gf-ga-gd-columns.md](019-standings-gf-ga-gd-columns.md)
> **Bug 触发**: 2026-06-17 09:35 + 09:48 用户连续截图：法国 vs 塞内加尔、伊拉克 vs 挪威详情页补时进球显示成 "0'"；09:48 截图同时显示 I 组积分榜 Iraq/Norway 仍是 0 MP 0 PTS

## 背景

2026-06-17 09:35 起，用户连续反馈两个相关 bug：

1. **09:35 法国 3-1 塞内加尔详情页**：Mbappé 90+6' 和 Mbaye 90+5' 两条进球右侧时间列显示 0'，但 player 字段尾巴上的 `90+6'` / `90+5'` 是对的
2. **09:48 伊拉克 1-4 挪威详情页**：Aimn Hsin 90+7' 显示成 0'（同样模式）
3. **09:48 同图 I 组积分榜**：Iraq 0 MP 0 PTS、Norway 0 MP 0 PTS（这俩今天刚踢完 1-4）

## 根因（升级版 v2）

### 上游 bug：API parser 正则不认 `90+N'` 格式

`src/data/worldcup_api.py:188-199` 的 `_parse_scorer_strings` 正则：

```python
pattern = re.compile(
    r"^(.+?)\s+"                      # player name
    r"(\d{1,3})"                       # minute
    r"(?:'(\+(\d{1,3}))?)?"            # optional '+N stoppage (preceded by ')
    ...
)
```

只认 `90'+6'` 格式（`'` 在 `+` 前）。但 worldcup26.ir API 实际返回的是 `90+6'` 格式（`'` 在补时数字后）：

| 输入 | 期望输出 | 实际输出 |
|------|---------|---------|
| `"K. Mbappé 90'+6'"` | `{player:"K. Mbappé", minute:90, stoppage:6}` | ✅ 正确 |
| `"K. Mbappé 90+6'"` | `{player:"K. Mbappé", minute:90, stoppage:6}` | ❌ `{player:"K. Mbappé 90+6'", minute:0, stoppage:None}` |

第二种格式下，正则匹配失败，落入 `elif item` fallback：

```python
elif item:
    # No minute found, just add the player with minute 0
    goals.append({"player": item, "minute": 0, "stoppage": None, "type": None})
```

→ **每次 `/api/refresh` 都重新生成 malformed 数据**（`player="K. Mbappé 90+6'"`, `minute=0`）。

### Plan 017.1 检测器被绕过的原因

Plan 017.1 的 `_is_incomplete` 检测到 minute=0 → 触发 `merge_from_api` 用 API 覆盖。但 **API 本身返回的就是 malformed**（parser 没修），所以"覆盖"等于"用同样 malformed 数据替换"。

所以 Plan 017.1 的修复链路**对这类 bug 无效**，因为上游坏掉。

### v1 计划错了什么

v1 我以为跟 Plan 017.1 一样是手维护数据填错，所以只 plan 了「手动修 details.json」。但实际是 **API parser 的 bug**，手修一次，下次 refresh 又会坏。

### Standings 滞后

I 组积分榜 Iraq/Norway 显示 0 PTS。但 worldcup26.ir `/get/groups` 端点**理应**随比赛结束更新 —— 可能是：
- (A) API 收录比分但 standings 计算延迟
- (B) 用户没触发 refresh
- (C) 5 分钟内存缓存未失效

需要先验证 (B)(C)，再考虑 (A) 的备选方案（从本地 details.json 推导 standings）。

## 方案

### Fix 1：修 parser 正则（L2）

`src/data/worldcup_api.py:188-199` 把 `'+(N)'` 和 `+(N)'` 两种格式都支持：

```python
pattern = re.compile(
    r"^(.+?)\s+"                      # player name
    r"(\d{1,3})"                       # minute
    r"(?:'?\(\+(\d{1,3})\)?'?)??"      # optional +N stoppage (apostrophe optional, both sides)
    r"(?:\(([^)]+)\))?"                # optional (suffix) like (OG), (P)
    r"'?\s*$"                          # optional trailing apostrophe + end
)
```

或者更明确的写法：把 stoppage 改成 `(?:'+(\d{1,3})'|\+(\d{1,3})')?`，两个 capture group 都映射到 `stoppage`。

### Fix 2：单元测试覆盖（L5）

`tests/test_worldcup_api.py` 加 parser 测试：
- `test_parses_45_plus_5_apostrophe_after` —— `"F. Balogun 45'+5'"` → minute=45, stoppage=5
- `test_parses_90_plus_6_apostrophe_after` —— `"K. Mbappé 90+6'"` → minute=90, stoppage=6（**当前 bug case**）
- `test_parses_90_plus_6_no_apostrophes` —— `"K. Mbappé 90+6"` → minute=90, stoppage=6（边界）
- `test_parses_og_suffix` —— `"D. Bobadilla 7'(OG)"` → type=own_goal（保持）
- `test_parses_penalty_suffix` —— `"X 67'(p)"` → type=penalty（保持）

### Fix 3：手动修 details.json（L1）

应用我之前 stash 暂存的改动（已包含 5 场新增 + France-Senegal 修复），再补修 Iraq-Norway 的 Aimn Hsin 90+7'：

```diff
  {
-   "player": "Aimn Hsin 90+7'",
-   "minute": 0,
+   "player": "Aimn Hsin",
+   "minute": 90,
+   "stoppage": 7,
    "type": null,
    "team": "away"
  }
```

### Fix 4：触发 refresh 看 standings（L4 — 一次性）

Parser 修完后，跑一次 `/api/refresh`（脚本或 curl），让 merge_from_api 用**修好的 parser 重新拉数据**，覆盖之前所有 malformed entries。再观察 standings 是否同步更新。

### Fix 5（条件性）：Standings 兜底推导（L2）

**仅当** Fix 4 后 standings 仍然滞后 → 加 `compute_standings_from_details(group, all_details)` 函数，从本地 details.json 推导 MP/W/D/L/GF/GA/GD/PTS，作为 API 的 fallback。

**当前不纳入本 plan**，先看 Fix 4 效果。如果需要，单独起 Plan 026。

## 范围

### In Scope

1. **L2 改 parser**：`src/data/worldcup_api.py:188-199` 正则
2. **L5 加测试**：`tests/test_worldcup_api.py` 5 个新 case
3. **L1 改数据**：`data/details.json`（应用 stash + 修 Aimn Hsin 90+7'）
4. **L4 触发 refresh**：跑 `curl -X POST localhost:8766/api/refresh`，验证 details.json 被正确重写
5. **写 log**：`docs/logs/2026/06-17-plan-025.md`
6. **8-gate audit**

### Out of Scope

- ❌ Standings 兜底推导（先看 API 是否更新，不更新再起 Plan 026）
- ❌ 改 `_is_incomplete` 或 `merge_from_api`（现有逻辑对，正确 parser 下能跑通）
- ❌ 改前端渲染（已正确，错在数据）
- ❌ 改 `data/details.json` 里其他非本 bug 的条目
- ❌ 反向修 Plan 017.1 的判定（仍正确，只是被上游 bug 绕过）

## 任务清单

| # | 任务 | 估时 | 自主权 | 状态 |
|---|------|------|--------|------|
| 1 | 用户批准本 plan | - | L1 | ⏳ |
| 2 | 修 parser 正则（Fix 1） | 5 min | L2 | ⏳ |
| 3 | 加 5 个 parser 单元测试（Fix 2） | 5 min | L5 | ⏳ |
| 4 | 跑 pytest 确认 parser 改对 | 1 min | L5 | ⏳ |
| 5 | 应用 stash + 修 Aimn Hsin 90+7'（Fix 3） | 1 min | L1 | ⏳ |
| 6 | 跑 pytest 全套（200 个） | 1 min | L5 | ⏳ |
| 7 | 触发 /api/refresh（Fix 4） | 30s | L4 | ⏳ |
| 8 | 验证 details.json 已被正确重写 | 1 min | L5 | ⏳ |
| 9 | 观察 I 组 standings（fix 后是否同步） | 1 min | L4 | ⏳ |
| 10 | 8-gate audit | 5 min | L5 | ⏳ |
| 11 | 写 log | 5 min | L4 | ⏳ |
| 12 | 用户视觉验证（Gate 8） | - | - | n/a |
| 13 | commit + push | 30s | L4 | ⏳ |

**总估时: ~25 min**

## AGE 8-Gate Closure Audit

| # | Gate | 验证 | 状态 |
|---|------|------|------|
| 1 | parser 正则支持 `90+N'` 格式 | 单元测试 | ✅ |
| 2 | parser 仍支持 `90'+N'` 旧格式（不回归）| 单元测试 | ✅ |
| 3 | parser 仍支持 `(OG)` / `(P)` 后缀（不回归）| 单元测试 | ✅ |
| 4 | `pytest tests/test_worldcup_api.py` 全过（58/58） | pytest | ✅ |
| 5 | `pytest tests/` 全过（213/213） | pytest | ✅ |
| 6 | `/api/refresh` 后 details.json 里无 `minute=0` entry（0/18） | grep | ✅ |
| 7 | I 组 standings Iraq/Norway 已更新（本地推导） | curl `/api/matches` | ✅ |
| 8 | **手动视觉验证**（MANUAL）：用户 2026-06-17 10:29 确认 OK | 用户 | ✅ |

## 风险

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| Parser 改完仍漏某种格式 | 低 | 中 | 单元测试覆盖 5 种格式；运行 `/api/refresh` 实测覆盖全量数据 |
| worldcup26.ir API 还有其他诡异格式 | 中 | 低 | Plan 017.1 的 `_is_incomplete` 兜底，下个 bug 再迭代 |
| `/api/refresh` 后 standings 仍滞后 | 中 | 中 | 已留 Fix 5 条件性兜底（Plan 026 候选） |
| Parser 改完破坏其他 Plan 的测试 | 低 | 高 | Plan 016 / 017 / 018 都有 goalscorers 相关测试，跑全套验证 |
| `data/details.json` JSON 损坏 | 极低 | 高 | 改完 `python -c "import json; ..."` 验证 |

## 验收

- [ ] 用户批准 plan 后才执行
- [ ] 5 个新 parser 单元测试通过
- [ ] 200/200 pytest 全过
- [ ] `/api/refresh` 后 `data/details.json` 里没有 `minute=0` 进球
- [ ] I 组 standings Iraq 显示 1 MP 0 W 0 D 1 L（或 API 已更新 / 留 Plan 026）
- [ ] 用户在页面确认所有补时进球显示成 `90'+N'`

## 决策记录

- **本次升级 plan scope**：v1 只 plan 手动修数据；v2 加入 parser fix（上游）+ standings 调查
- **parser 双向支持**：不删 `90'+N'` 格式，保持向后兼容（万一 API 又改回旧格式）
- **standings 兜底不入本 plan**：避免 scope creep，先看 API 表现
- **测试数据驱动**：5 个新测试覆盖 parser 行为，下次回归一目了然

## 不破坏什么

- `find_group_standings` / `fetch_groups` / 前端 standings 渲染：全不动
- `_is_incomplete` / `merge_from_api`：全不动
- `_parse_scorer_strings` 签名：不动
- 现有 195 个 pytest：全不动
