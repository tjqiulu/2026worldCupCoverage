# Plan 017 — 不完整详情条目的 API 覆盖

> **状态**: `planned` → `completed`
> **创建日期**: 2026-06-15
> **关联 plan**: [016-widget-and-refresh-fix.md](016-widget-and-refresh-fix.md) (refresh 缓存修复), [012-worldcup26-api-integration.md](012-worldcup26-api-integration.md) (API 集成)

## 背景

2026-06-15 12:23，用户截图反馈：**瑞典 5-1 突尼斯**详情页只显示 3 个进球（Y.Ayari 7'、A.Isak 30'、O.Rekik 43'），缺 60' 哲凯赖什、84' 斯万贝里、90+' 阿亚里梅开二度。

## 根因

`src/data/details.py` 的 `merge_from_api` 写的是"**已存在的手维护条目优先级最高，永远不覆盖**"：

```python
for mid, api_entry in api_details.items():
    if mid not in merged:
        merged[mid] = api_entry  # 只 ADD
        added += 1
    # else: existing entry wins, skip API  ← 瑞典-突尼斯在这里被跳过
```

后果：
- `data/details.json` 里瑞典-突尼斯是手写的 3 球版（比分 5-1 对，但进球列表只到 43'）
- worldcup26.ir API 即使有完整 6 球数据
- `/api/refresh` 调 `merge_from_api` 时 API 被直接 skip
- 用户点刷新看不到更新

这不是 Plan 016 解决的 5 分钟内存缓存问题，是**合并策略本身**的问题。

## 方案

### 规则：手维护条目"不完整"时，API 覆盖

判定条件（最简单、最不容易误伤）：

```python
def _is_incomplete(entry: dict) -> bool:
    """手维护条目是否不完整（goalscorers 数量 < 比分总和）"""
    score = entry.get("score") or {}
    goals = entry.get("goalscorers") or []
    if "home" not in score or "away" not in score:
        return False  # 没比分无法判断，保守不覆盖
    return len(goals) < (score["home"] + score["away"])
```

新规则：
- existing **不完整**（goalscorers 数量 < 比分总和）→ **API 覆盖**
- existing **完整** → existing 胜（保护手维护的修正，比如 965e9ac9ce78 的 Larin 78' 修正）
- existing **不存在** → API 新增（保持原行为）

返回 `added` 字段语义扩展为 `num_changed`（新增 + 覆盖的总和），同时返回覆盖数量便于日志：

```python
return merged, added, overwritten
```

为不破坏 Plan 016 的 API 签名兼容性（`app.py:118` 在用 `scores_updated`），把 `added` 重命名为 `changed` 并在 `app.py` 改 1 行。

### 诊断告警

`merge_from_api` 检测到 incomplete 条目被覆盖时，打 `logging.warning`，方便 ops 看 log 发现手维护出错的比赛。

### 数据补全

`data/details.json` 里 `fifa-wc-2026-df779f16393a@worldcup-calendar`（瑞典-突尼斯）补全为 6 球完整版（来源：新华社/央视 6/15 12:00-12:15 报道）：

| 时间 | 球员 | 队 |
|------|------|-----|
| 7' | Y. Ayari | 瑞典 |
| 30' | A. Isak | 瑞典 |
| 43' | O. Rekik | 突尼斯 |
| 60' | V. Gyökeres | 瑞典 |
| 84' | Svanberg | 瑞典 |
| 90'+5' | Y. Ayari | 瑞典 |

## 范围

### In Scope

1. `src/data/details.py`
   - 新增 `_is_incomplete(entry)` 内部函数
   - `merge_from_api` 改返回 `(merged, changed, overwritten)` 元组
   - 检测 incomplete 时打 `logging.warning`
2. `src/app.py:118` 改用新的返回值（`scores_updated = changed`）
3. `tests/test_details.py` 加 3 个测试：incomplete → API 覆盖、complete → existing 胜、不存在 → 新增
4. `data/details.json` 补全瑞典-突尼斯 6 球版
5. `docs/logs/2026/06-15-plan-017.md` 决策记录

### Out of Scope

- ❌ 加 `_lock: true` 手动锁定字段（过度设计，目前规则够用）
- ❌ 改 `data/details.json` 里其他条目的进球时间/姓名（除瑞典-突尼斯）
- ❌ 改前端 UI 警告（Plan 3 那个「⚠ 详情可能不完整」是 nice-to-have，先不做）
- ❌ 给 worldcup26.ir API 加更激进的轮询（API 本身是人工更新，没用）

## 风险

| 风险 | 缓解 |
|------|------|
| 不完整判定把手动修正误覆盖 | 只在 `len(goalscorers) < sum(score)` 时覆盖，len 相等时 existing 胜 |
| 改 `merge_from_api` 签名破坏 `app.py` | 同步改 `app.py:118`，所有测试覆盖 |
| 手维护的 stoppage/penalty 信息被 API 覆盖丢失 | API 完整度已经超过手维护（6 球 vs 3 球），丢失的也只是不存在的信息 |
| 世界波体育 API 数据本身有误 | API 是公认比手维护更可靠的源（多个站点交叉验证过瑞典-突尼斯结果） |

## 验收

- [ ] `pytest tests/test_details.py` 全过（含 3 个新测试）
- [ ] `pytest` 全部测试通过
- [ ] 瑞典-突尼斯详情显示 6 个进球
- [ ] 改 `merge_from_api` 后，其他 11 个手维护条目不变（手动 grep 验证）
- [ ] 启动 Flask 调 `/api/refresh` 一次，`logging.warning` 出现 1 次"incomplete, API override"（瑞典-突尼斯）

---

## Follow-up: Plan 017.1 — 把"格式错误"也判为不完整

**触发**: 2026-06-15 13:00 用户反馈德国 7-1 库拉索详情页"K. Havertz 45'+5'(p)"显示成 0'。检查发现这是**另一种** bug：手维护时把 "45+5'(p)" 全部塞进了 `player` 字段里，**真正的 `minute` 反而是 0**。同样毛病的还有卡塔尔 vs 瑞士的 "Breel Embolo 17' (p)"。

**Plan 017 的"_is_incomplete"抓不到**：德国 7-1 有 8 个进球，数量对得上；`len(goals) == score.home + score.away`，原判定返回 False。

### 改动

**`src/data/details.py` `_is_incomplete` 函数**: 增加一条规则——**任何进球 `minute=0` 都视为格式错误**（实际比赛进球至少是 1 分钟）。判定改成：

```python
if len(goals) < (home + away):
    return True
# Plan 017.1: 任何 minute=0 都判格式错误
if any(isinstance(g, dict) and g.get("minute") == 0 for g in goals):
    return True
return False
```

**`data/details.json`**:
- 德国 vs 库拉索 (`764217ec91b0`) Havertz 点球：拆 `"K. Havertz 45'+5'(p)"` → `player="K. Havertz"`, `minute=45, stoppage=5, type="penalty"`
- 卡塔尔 vs 瑞士 (`11a1e8291690`) Embolo 点球：拆 `"Breel Embolo 17' (p)"` → `player="Breel Embolo"`, `minute=17, type="penalty"`

**`tests/test_details.py`**: 加 2 个新测试
- `TestIsIncomplete::test_minute_zero_in_any_goal_is_malformed` —— 验证 7-1 8 球但其中 1 球 minute=0 → incomplete
- `TestMergeFromApi::test_malformed_minute_zero_overridden` —— 验证 API 完整版本（含 `K. Havertz` + minute=45 + stoppage=5 + type=penalty）会覆盖原 malformed 版本

### 不会误伤

- 所有现有 entry 都没有 minute=0（grep 验证后只有这 2 处）
- `_is_incomplete` 的现有 5 个测试都还用 minute > 0 的数据，全过
- 200/200 单元测试全过（之前 198，+2 新测试）

### 影响

下次再有人手维护把"45'+5'(p)"塞进 player 字段，refresh 一次会被 API 自动修正（API 解析器 `worldcup_api.py:_parse_scorer_strings` 本来就支持 (p) 后缀和 +N 伤停时间，输出会拆干净）。
