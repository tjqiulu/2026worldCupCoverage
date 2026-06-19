# Plan 027 — 积分榜 team-name alias resolver（修复 B/D/K 组数据漏算 + 缺队）

> **状态**: `proposed` → 用户批准"开干"（2026-06-19 11:36） → 执行中
> **log**: [`docs/logs/2026/06-19-plan-027.md`](../logs/2026/06-19-plan-027.md)
> **创建日期**: 2026-06-19
> **关联 plan**: [025-stoppage-time-parser-fix.md](025-stoppage-time-parser-fix.md)（`compute_standings_from_details` 调用方）, [019-standings-gf-ga-gd-columns.md](019-standings-gf-ga-gd-columns.md)

## Bug 触发

2026-06-19 11:19 用户截图 B 组积分榜：

| 显示 | 真实 |
|------|------|
| 加拿大 1W 6-0 3分 | 应为 2MP 1W 1D GF=7 GA=1 4分（漏 6/12 vs 波黑 1-1）|
| 瑞士 0W 1D 1-1 1分 | 应为 2MP **1W** 0D 1L GF=5 GA=2 3分（漏 6/19 vs 波黑 4-1）|
| 卡塔尔 0W 1D 1L GF=1 GA=7 1分 | 正确 |
| 波黑 缺失 | 应为 2MP 0W 1D 1L GF=2 GA=5 1分 |

## 根因（AGE）

### A — Aggregate

**字面对比**（同一支队，两套数据源写法不同）：

| ICS (baires) 名字 | worldcup26.ir API `name_en` | 差异 |
|------------------|------------------------------|------|
| `"Bosnia & Herzegovina"` | `"Bosnia and Herzegovina"` | `&` vs `and` |
| `"USA"` | `"United States"` | 缩写 vs 全称 |
| `"DR Congo"` | `"Democratic Republic of the Congo"` | 缩写 vs 全称 |

**代码链路**（`src/app.py:84-110` `_local_or_api_standings`）：

```python
name_to_id: dict[str, str] = {}
for tid, t in teams.items():
    for k in (t.get("name_en"), t.get("fifa_code")):  # ← 只覆盖这俩 key
        if k:
            name_to_id[str(k)] = str(tid)
local = compute_standings_from_details(...)
```

下游 `compute_standings_from_details`（`src/data/details.py:415-420`）：

```python
home_id = team_name_to_id.get(home_name)
away_id = team_name_to_id.get(away_name)
if not home_id or not away_id:
    continue  # ← 整场比赛被静默跳过
```

**踩坑盘点**（group-stage final 比赛）：

| 比赛 | 比分 | 触发原因 |
|------|------|---------|
| B 6/12 加拿大 1-1 波黑 | 1-1 | `Bosnia & Herzegovina` 查无 |
| B 6/18 瑞士 4-1 波黑 | 4-1 | 同上 |
| D 6/13 USA 4-1 巴拉圭 | 4-1 | `USA` 查无（但 `name_to_id["USA"]=13` 实际有，因为 USA 走 fifa_code 通道——不踩坑）|
| K 6/17 葡萄牙 1-1 民主刚果 | 1-1 | `DR Congo` 查无 |

> **修正**：D 组 USA 走的是 `fifa_code="USA"` 通道，已经能匹配。**真正踩坑的只有 B 组波黑（2 场）和 K 组刚果（1 场）**。

### G — Get to root cause

**直接根因**：`name_to_id` 字典只字面匹配 `name_en`/`fifa_code` 两 key，跨数据源字符差异即不匹配。

**深层根因（系统性）**：项目里两套并行的队伍身份体系（baires ICS + worldcup26.ir API），但代码层假设它们用同一份 `name_en`。缺乏跨数据源的**队伍名称归一化层**。这是个通用 bug——任何字符差异（`&` vs `and`、缩写 vs 全称）都会触发。

**为什么 Plan 025 的"本地推导"救不了**：本地推导方向对（不依赖 API），但它吃的是 `name_to_id` 这把锁；锁的精度 = 字面精确匹配，所以只要数据源不一致，本地推导就漏算。

### E — Evaluate 修复方案

| 方案 | 改哪里 | 评估 |
|------|--------|------|
| A. 改 ICS parser 把名字统一成 API 拼写 | `src/data/ics_parser.py` | 改"赛程真相源"侵入大，未来 API 又改拼写还会再踩 |
| **B. 新增多通道 resolver helper** | `src/data/details.py` + 改 `src/app.py` 1 行 | **采用**：解决根因（缺归一化层），自动覆盖未来同类 bug，单元测试容易写 |
| C. 仅在 `app.py` 构建 `name_to_id` 时多查字段 | `src/app.py` | 改最小但把 resolver 泄漏到调用方 |

**采用 B**。具体的多通道查找优先级：

1. `name_en` 精确匹配（API 标准名）
2. `fifa_code` 精确匹配（如 USA 这种 ICS 短名）
3. `iso2` 精确匹配（兜底）
4. 字符串 normalize 后再查：把 `&` → `and`、去标点、压缩空白、小写比对（覆盖 `Bosnia & Herzegovina` 这种字符差异）
5. **不再做** countries.json 反查（Plan 027 范围内不需要——前三步 + normalize 已覆盖全部已知 case；增加复杂度不划算）

## 方案

### Fix 1：新增 helper `build_team_id_map()`（L2）

`src/data/details.py` 末尾新增：

```python
def build_team_id_map(teams: dict[str, dict[str, Any]]) -> dict[str, str]:
    """Build a multi-key team_name -> team_id map for standings resolution.

    Plan 027: worldcup26.ir API and baires ICS use slightly different
    strings for the same team (e.g. "Bosnia & Herzegovina" vs "Bosnia
    and Herzegovina", "USA" vs "United States"). We try multiple keys:

      1. name_en exact (API's canonical name)
      2. fifa_code exact (covers "USA" → "United States" via API's own field)
      3. iso2 exact (lowercase 2-letter)
      4. Normalized: lowercase, strip punctuation, " & " → " and ",
         collapse whitespace. Matches against any of the above normalized.

    Returns: dict {lookup_key: team_id}. Keys may overlap; first wins
    (we walk in priority order).

    Performance: 48 teams × ~3 keys each = ~150 entries. Trivial.
    """
    keys: list[tuple[str, str]] = []  # (lookup_key, team_id)
    for tid, t in teams.items():
        if not tid:
            continue
        for k in (t.get("name_en"), t.get("fifa_code"), t.get("iso2")):
            if k:
                keys.append((str(k), str(tid)))

    out: dict[str, str] = {}
    for k, tid in keys:
        out.setdefault(k, tid)  # first occurrence wins (priority order)

    # Normalized fallback: walk keys, build a second map.
    def _norm(s: str) -> str:
        s = s.replace("&", "and")
        # strip basic punctuation, collapse whitespace, lowercase
        s = "".join(c for c in s if c.isalnum() or c.isspace())
        s = " ".join(s.split()).lower()
        return s

    norm_map: dict[str, str] = {}
    for k, tid in out.items():
        norm_map.setdefault(_norm(k), tid)
    # Merge: only add entries that aren't already in `out` literally
    for nk, tid in norm_map.items():
        out.setdefault(nk, tid)
    return out
```

### Fix 2：改 `app.py:_local_or_api_standings`（L2，1 行）

`src/app.py:101-105` 替换为：

```python
teams = get_teams_by_id()
name_to_id = build_team_id_map(teams)  # Plan 027: multi-key alias resolver
local = compute_standings_from_details(
    group_letter, all_details, matches, name_to_id
)
```

注意 `build_team_id_map` 必须 `import` 到 `app.py`（加在已有 `from src.data.details import (...)` 那行）。

### Fix 3：单元测试（L5）

`tests/test_details.py` 末尾新增 `TestBuildTeamIdMap` 类，覆盖 5 个 case：

1. `test_basic_name_en_match` — 普通过程
2. `test_fifa_code_fallback` — "USA" → 13（team_id of United States）
3. `test_iso2_fallback` — "us" → 13
4. `test_ampersand_normalized_match` — "Bosnia & Herzegovina" → 6（team_id of Bosnia and Herzegovina）
5. `test_priority_first_wins` — 当 name_en 和 fifa_code 互相冲突（极小概率，但保证行为稳定）时取先插入的

```python
class TestBuildTeamIdMap:
    """Plan 027: multi-key team_id_map builder. Worldcup26.ir API and
    baires ICS use slightly different strings for the same team; this
    resolver covers the gap so compute_standings_from_details() doesn't
    silently drop matches with aliased team names."""

    def _sample_teams(self):
        return {
            "5": {"id": "5", "name_en": "Canada", "fifa_code": "CAN", "iso2": "CA"},
            "6": {"id": "6", "name_en": "Bosnia and Herzegovina", "fifa_code": "BIH", "iso2": "BA"},
            "7": {"id": "7", "name_en": "Qatar", "fifa_code": "QAT", "iso2": "QA"},
            "8": {"id": "8", "name_en": "Switzerland", "fifa_code": "SUI", "iso2": "CH"},
            "13": {"id": "13", "name_en": "United States", "fifa_code": "USA", "iso2": "US"},
        }

    def test_basic_name_en_match(self):
        from src.data.details import build_team_id_map
        m = build_team_id_map(self._sample_teams())
        assert m["Canada"] == "5"
        assert m["Qatar"] == "7"
        assert m["Switzerland"] == "8"

    def test_fifa_code_fallback(self):
        """ICS uses 'USA' (fifa_code) instead of 'United States' (name_en).
        Build map must accept both keys."""
        from src.data.details import build_team_id_map
        m = build_team_id_map(self._sample_teams())
        assert m["USA"] == "13"
        assert m["United States"] == "13"

    def test_iso2_fallback(self):
        from src.data.details import build_team_id_map
        m = build_team_id_map(self._sample_teams())
        assert m["US"] == "13"
        assert m["us"] == "13"  # case-insensitive (iso2 from API is already uppercase, but the map doesn't enforce)

    def test_ampersand_normalized_match(self):
        """The bug case: ICS says 'Bosnia & Herzegovina' but API says
        'Bosnia and Herzegovina'. Normalized lookup must resolve this."""
        from src.data.details import build_team_id_map
        m = build_team_id_map(self._sample_teams())
        # After normalize: "bosnia and herzegovina" matches the API name
        assert m["bosnia  herzegovina"] == "6"  # double space, lowercased
        # Note: literal "Bosnia & Herzegovina" is not in map literally,
        # but normalize makes it findable. The ICS home.name string
        # never reaches this map directly (we pre-process via build_team_id_map
        # with normalized fallback).

    def test_ampersand_to_and_via_normalize(self):
        """Direct ampersand case: if ICS sends 'Bosnia & Herzegovina' as
        a key (e.g., when user passes a raw name), normalize collapses
        '&' to 'and' so the lookup still finds it."""
        from src.data.details import build_team_id_map, _norm_team_key
        # _norm_team_key is the internal helper; expose for testability
        assert _norm_team_key("Bosnia & Herzegovina") == "bosnia and herzegovina"
        assert _norm_team_key("USA") == "usa"
        assert _norm_team_key("  multiple   spaces  ") == "multiple spaces"

    def test_priority_first_wins(self):
        """If two teams somehow share a key, the first-inserted wins
        (priority: name_en > fifa_code > iso2)."""
        from src.data.details import build_team_id_map
        teams = {
            "1": {"id": "1", "name_en": "AAA", "fifa_code": "X", "iso2": "X"},
            "2": {"id": "2", "name_en": "X", "fifa_code": "X", "iso2": "X"},
        }
        m = build_team_id_map(teams)
        # name_en "AAA" from team 1 inserted first → "X" maps to "1"
        assert m["X"] == "1"
```

> 上面 `test_ampersand_normalized_match` 写错了——`&` 已经被 normalize 替换成 `and`，所以 key 是 "bosnia and herzegovina"（一个空格）。让我修一下。

正确版：

```python
    def test_ampersand_normalized_match(self):
        """The bug case: ICS says 'Bosnia & Herzegovina' but API says
        'Bosnia and Herzegovina'. After normalize, the ICS key
        'Bosnia & Herzegovina' becomes 'bosnia and herzegovina', same as
        the API key normalized → lookup succeeds."""
        from src.data.details import build_team_id_map
        m = build_team_id_map(self._sample_teams())
        # API's "Bosnia and Herzegovina" is in map literally (via name_en).
        # ICS's "Bosnia & Herzegovina" needs normalize to find it.
        # The map's normalize helper ensures both literal "Bosnia and Herzegovina"
        # and the normalize("Bosnia & Herzegovina") → "bosnia and herzegovina" match.
        assert m["Bosnia and Herzegovina"] == "6"
        # The literal "Bosnia & Herzegovina" string is NOT in the map
        # (because the API only has "and" not "&"), but that's fine:
        # compute_standings_from_details calls _norm_team_key on home.name
        # before looking up, so the lookup path works.
```

实际我应该把 `_norm_team_key` 作为 helper **export**，并在 `compute_standings_from_details` 里用它做 lookup：

```python
def _norm_team_key(s: str) -> str:
    """Normalize a team name for fuzzy lookup.

    Plan 027: covers minor variations between data sources:
      - " & " → " and " (Bosnia & Herzegovina ↔ Bosnia and Herzegovina)
      - lowercase
      - collapse whitespace
      - strip punctuation
    """
    s = s.replace("&", "and")
    s = "".join(c for c in s if c.isalnum() or c.isspace())
    s = " ".join(s.split()).lower()
    return s


def build_team_id_map(teams: dict[str, dict[str, Any]]) -> dict[str, str]:
    """Plan 027: multi-key team_name → team_id map for standings resolution.
    ...
    """
    out: dict[str, str] = {}
    for tid, t in teams.items():
        if not tid:
            continue
        for k in (t.get("name_en"), t.get("fifa_code"), t.get("iso2")):
            if k:
                out.setdefault(str(k), str(tid))
    # Normalized second pass: any literal key not yet present gets a
    # normalized entry, so ICS's "Bosnia & Herzegovina" can resolve via
    # _norm_team_key() at lookup time.
    norm_extra: dict[str, str] = {}
    for k, tid in out.items():
        nk = _norm_team_key(k)
        if nk and nk not in out:
            norm_extra.setdefault(nk, tid)
    out.update(norm_extra)
    return out
```

然后在 `compute_standings_from_details` 里把 lookup 改成：

```python
home_id = team_name_to_id.get(home_name) or team_name_to_id.get(_norm_team_key(home_name))
away_id = team_name_to_id.get(away_name) or team_name_to_id.get(_norm_team_key(away_name))
```

这样：
- 直接匹配（name_en/fifa_code/iso2）走原路径
- 不匹配则尝试 normalize 后的 key
- 两层都失败才 `continue`

**这个设计比单纯在 `build_team_id_map` 里加 norm 更稳**：
- `build_team_id_map` 只产出确定性的 key 集合（避免 key 重复污染）
- `_norm_team_key` 暴露出来供 lookup 时按需调用
- 测试时每个组件独立可测

最终实现就用这个版本。

### Fix 4：端到端验证（L4）

跑一个端到端脚本验证修复后 B 组 4 队齐全、且数据正确：

```python
# Quick smoke test inline (not in pytest)
result = compute_standings_from_details(
    "B",
    all_details,  # includes 4 final matches
    b_matches,
    build_team_id_map(get_teams_by_id()),
)
assert len(result) == 4  # 加拿大/瑞士/波黑/卡塔尔
# Sort: Canada 4pt > Switzerland 3pt > Qatar 1pt > Bosnia 1pt (by GD)
```

### Fix 5（条件性）：写 log + commit（L4）

按惯例写 `docs/logs/2026/06-19-plan-027.md`，记 AGE 8-gate audit 结果。

## 范围

### In Scope
- L2 `src/data/details.py` 新增 `build_team_id_map()` 和 `_norm_team_key()`
- L2 `src/data/details.py:compute_standings_from_details` 用 `_norm_team_key` 兜底 lookup
- L2 `src/app.py` 改 `_local_or_api_standings` 调用新 helper
- L2 `src/app.py` 顶部 `from src.data.details import (...)` 加 `build_team_id_map`
- L5 `tests/test_details.py` 加 `TestBuildTeamIdMap` 类（5-6 个 case）
- L5 跑 `pytest tests/` 全过
- L4 写 log + commit

### Out of Scope
- ❌ 改 ICS parser（不碰 baires 真相源）
- ❌ 改 worldcup_api.py
- ❌ 改前端
- ❌ 改 countries.json（已经包含三支队伍的正确 ISO/FIFA）
- ❌ 改 Plan 017/018/025/026（不动既有逻辑）
- ❌ countries.json 反查通道（前三步 + normalize 已覆盖全部已知 case）

## 风险

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| Normalize 误把不相关队合并 | 极低 | 中 | 三步精确匹配优先，normalize 只在直接匹配失败时启用；测试覆盖 `ampersand_to_and` |
| 改 `compute_standings_from_details` 破坏现有 7 个测试 | 低 | 中 | pytest 全套验证 |
| 改 `app.py` 触发运行时 import 错误 | 低 | 高 | 跑 `python -c "from src.app import create_app"` smoke test |
| worldcup26.ir API 返回结构变化 | 极低 | 低 | `build_team_id_map` 用 `.get()` 防御 |
| 未来再有第 4 种字符差异 | 中 | 低 | normalize 框架已就位，加新规则容易 |

## 验收

- [ ] `pytest tests/` 全过（220+/220+）
- [ ] B 组 6/19 4 场 final 后，本地推导 standings 包含 4 队（加拿大/瑞士/卡塔尔/波黑）
- [ ] B 组 standings 排序：加拿大 4 分 > 瑞士 3 分 > 卡塔尔 1 分 = 波黑 1 分（按 GD 排：卡塔尔 -6、波黑 -3）
- [ ] K 组 6/17 1 场 final 后，本地推导包含民主刚果
- [ ] D 组保持 4 队（USA 走 fifa_code 通道不受影响）
- [ ] 用户视觉确认 modal 积分榜正确

## 决策记录

- **方案 B（多通道 resolver）vs A（改 ICS parser）**：选 B 解决根因，不碰真相源
- **helper 拆分 `_norm_team_key` + `build_team_id_map` vs 单函数**：拆分便于单元测试和未来扩展
- **不加 countries.json 反查通道**：前三步 + normalize 已覆盖全部已知 case，复杂度/收益比不合算
- **不引线程/异步**：纯同步函数，48 队规模 O(N) 远低于 1ms
