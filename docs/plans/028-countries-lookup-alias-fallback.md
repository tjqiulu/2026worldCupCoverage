# Plan 028 — countries.json lookup 走 3-pass alias fallback（修复波黑/美国/刚果中文名缺失）

> **状态**: `proposed` → 用户批准"开干"（2026-06-19 15:25） → 执行中
> **log**: [`docs/logs/2026/06-19-plan-028.md`](../logs/2026/06-19-plan-028.md)
> **创建日期**: 2026-06-19
> **关联 plan**: [027-standings-team-name-alias-resolver.md](027-standings-team-name-alias-resolver.md)（同源 bug：跨数据源拼写不一致）

## Bug 触发

2026-06-19 15:18 用户截图：波黑在积分榜只显示 "Bosnia and Herzegovina"（无中文名"波黑"），其他 3 队（加拿大/瑞士/卡塔尔）双语都正常。

用户原话："波黑的国家名字咋还是英文？注意 AGE 流程，audit 里面 testcase 要做完善"

## 根因（AGE）

### A — Aggregate

**截图**：
- 🇨🇦 加拿大 / Canada ✓
- 🇨🇭 瑞士 / Switzerland ✓
- 🇧🇦 **Bosnia and Herzegovina** ← 缺中文"波黑"
- 🇶🇦 卡塔尔 / Qatar ✓

**`/api/teams` 实际返回**（curl 验证）：
```json
{
  "6": {
    "name": "Bosnia and Herzegovina",   // API 拼写
    "name_zh": null,                    // ← 缺失
    "code_iso": "ba",
    "code_fifa": "BIH",
    "flag_url": "https://flagcdn.com/w80/ba.png"
  }
}
```

**链路**（`src/app.py:166-183` `/api/teams`）：
```python
teams = get_teams_by_id()
enriched = {}
for tid, t in teams.items():
    meta = lookup_country(t.get("name_en") or "")  # ← "Bosnia and Herzegovina"
    enriched[tid] = {
        "name": t.get("name_en") or tid,
        "name_zh": (meta or {}).get("name_zh"),   # ← None
        ...
    }
```

**`countries.json` 实际 key**：
- `"Bosnia & Herzegovina"`（ICS 拼写，含 `&`）
- `"USA"`（ICS 拼写，缩写）
- `"DR Congo"`（ICS 拼写，缩写）

→ **`/api/teams` 用 API name_en 查 countries.json，key 不匹配**。

### G — Get to root cause

**直接根因**：`lookup_country()` 只做精确字面查找，跨数据源拼写差异即失败。

**深层根因（同 Plan 027）**：项目里两套并行的队伍身份体系（baires ICS + worldcup26.ir API），但 `countries.json` 用 ICS 拼写作 key。Plan 027 修了"积分计算"那条链路（`build_team_id_map`），但**没修"中文名查表"这条链路**（`lookup_country` → `/api/teams` handler）。

**踩坑名单**（同 Plan 027 一致）：

| 队 | API name_en | countries.json key | 缺中文？ |
|---|---|---|---|
| 波黑 (B 组) | `Bosnia and Herzegovina` | `Bosnia & Herzegovina` | ✅ |
| 美国 (D 组) | `United States` | `USA` | ✅（用户在美国用，体感大）|
| 民主刚果 (K 组) | `Democratic Republic of the Congo` | `DR Congo` | ✅ |

### E — Evaluate 修复方案

| 方案 | 改哪里 | 评估 |
|------|--------|------|
| A. `lookup_country` 加 3-pass fallback | `src/data/countries.py` | **采用**：单一职责，Plan 027 的 `_norm_team_key` 抽出来共享 |
| B. `/api/teams` handler 改用 `build_team_id_map` | `src/app.py` | resolver 逻辑泄漏到调用方 |
| C. 改 `countries.json` 增补别名 | `data/countries.json` | 改手维护数据，缩放差；未来 API 又改拼写还要再改 |
| D. 改 ICS parser 把名字统一成 API 拼写 | `src/data/ics_parser.py` | 改真相源侵入大 |

**采用 A**。具体 3-pass lookup 优先级：

1. `name_en` 精确匹配（现状）
2. 字符串 normalize 后查（覆盖 `Bosnia & Herzegovina` ↔ `Bosnia and Herzegovina`，复用 Plan 027 的 `_norm_team_key`）
3. code_fifa/code_iso 反查（覆盖 `USA` ↔ `United States`、`DR Congo` ↔ `Democratic Republic of the Congo`）

## 方案

### Fix 1：`_norm_team_key` 提到 `countries.py` 公开（L2）

`src/data/details.py:_norm_team_key` 改为 re-export 自 `countries.py`，避免循环 import（countries 是底层）。

`src/data/countries.py` 新增：
```python
def norm_team_key(s: str | None) -> str:
    """Normalize a team name for fuzzy lookup (Plan 027 shared helper).

    Covers minor variations between data sources:
      - " & " → " and " (Bosnia & Herzegovina ↔ Bosnia and Herzegovina)
      - lowercase
      - collapse whitespace
      - strip ASCII punctuation

    Returns "" for empty/None input.
    """
    if not s:
        return ""
    s = s.replace("&", "and")
    s = "".join(c for c in s if c.isalnum() or c.isspace())
    s = " ".join(s.split()).lower()
    return s
```

`src/data/details.py` 改为：
```python
from src.data.countries import norm_team_key as _norm_team_key  # Plan 028 共享
```

保留 `_norm_team_key` 别名（带下划线）以维持 Plan 027 测试不破。

### Fix 2：`lookup_country` 加 3-pass fallback（L2）

`src/data/countries.py:lookup()` 改为：
```python
def lookup(name_en: str | None) -> dict[str, str] | None:
    """Look up country info by English name.

    Plan 028: 3-pass fallback. countries.json is keyed by baires ICS
    names (e.g. "Bosnia & Herzegovina", "USA", "DR Congo") but
    worldcup26.ir API uses different spellings ("Bosnia and Herzegovina",
    "United States", "Democratic Republic of the Congo"). Exact match
    fails across data sources; we fall back to:

      1. Exact match (preserved for performance and predictability)
      2. Normalized match (lowercase, & → and, collapse whitespace)
      3. code_fifa / code_iso reverse lookup

    Returns None if all 3 passes fail.
    """
    if not name_en:
        return None
    data = _load()
    # Pass 1: exact
    if name_en in data:
        return data[name_en]
    # Pass 2: normalized
    nk = norm_team_key(name_en)
    if nk:
        for k, v in data.items():
            if norm_team_key(k) == nk:
                return v
    # Pass 3: code_fifa / code_iso reverse lookup
    nk_upper = name_en.strip().upper()
    for v in data.values():
        if (v.get("code_fifa") or "").upper() == nk_upper:
            return v
        if (v.get("code_iso") or "").upper() == nk_upper:
            return v
    return None
```

**性能影响**：`countries.json` 48 队 × 3 pass ≈ 144 次比较，仍在微秒级，可接受。

### Fix 3：完善 testcase（L5，按用户要求"audit 完善"）

`tests/test_countries.py` 新增 `TestLookupAliasFallback` 类，**7 个 case** 覆盖 3-pass 行为 + 边界：

1. `test_exact_match_priority` — 精确匹配仍优先（Pass 1 命中则 Pass 2/3 不跑）
2. `test_ampersand_fallback` — "Bosnia and Herzegovina"（API）→ "波黑"（Pass 2）
3. `test_usa_full_name_fallback` — "United States"（API）→ "美国"（Pass 3 via code_fifa）
4. `test_drc_full_name_fallback` — "Democratic Republic of the Congo"（API）→ "民主刚果"（Pass 3 via code_fifa）
5. `test_normalize_priority_preserved` — 同样字符串 normalize 后能匹配的多个 key 中，先插入的赢
6. `test_unknown_after_all_passes_returns_none` — 3-pass 全失败返回 None
7. `test_api_name_en_returns_zh` — 端到端：从 worldcup26.ir API 实际拼写出发查中文名

外加**端到端 smoke test**（不写进 pytest，CI 不跑）：
```python
# In docstring or comments
# Verify: curl http://127.0.0.1:8766/api/teams | jq '."6"'
#   { "name": "Bosnia and Herzegovina", "name_zh": "波黑", ... }
```

### Fix 4：端到端验证（L4）

- `curl /api/teams` 验证 3 支队 name_zh 都对
- 重启 Flask（端口 8766 旧进程）跑新代码
- 浏览器 F5 刷新 B 组 modal，验证波黑显示"波黑 Bosnia and Herzegovina"
- 顺便验证 D 组 USA modal 是不是也对了

### Fix 5：写 log + commit（L4）

跟 Plan 025/027 模板一致：AGE 8-Gate Audit + 决策记录 + 关键收获。

## 范围

### In Scope
- L2 `src/data/countries.py`：新增 `norm_team_key()` 公开 + 改 `lookup()` 3-pass
- L2 `src/data/details.py`：`_norm_team_key` 改 import 自 countries
- L5 `tests/test_countries.py`：新增 `TestLookupAliasFallback`（7 case）
- L5 跑 `pytest tests/` 全过
- L4 重启 Flask 端到端验证
- L4 写 log + commit

### Out of Scope
- ❌ 改 ICS parser
- ❌ 改 worldcup_api.py
- ❌ 改 countries.json
- ❌ 改前端 main.js（API 修复后前端自动显示）
- ❌ 改 Plan 027 的 `build_team_id_map`（已正确，但顺路复用 `_norm_team_key`）

## 风险

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| Pass 3 误把不相关队合并 | 极低 | 中 | code_fifa/code_iso 全大写比对，且每个值唯一 |
| `_norm_team_key` 重构破坏 Plan 027 测试 | 低 | 中 | `_norm_team_key` 仍可从 details.py import（re-export），测试不破 |
| 改 `lookup()` 性能下降 | 极低 | 低 | 48 队 3 pass ≈ 微秒级 |
| 未来再有第 4 种字符差异 | 中 | 低 | framework 已就位，加新 pass 即可 |
| 现有 TestLookup 测试不回归 | 低 | 中 | pytest 全套验证 |

## 验收

- [ ] `pytest tests/test_countries.py` 全过（21+ 个 case，含新增 7 个）
- [ ] `pytest tests/` 全过（244+/244+）
- [ ] Plan 027 的 13 个新测试不回归
- [ ] `curl /api/teams` 返回波黑 name_zh="波黑"
- [ ] `curl /api/teams` 返回 USA name_zh="美国"
- [ ] `curl /api/teams` 返回 DR Congo name_zh="民主刚果"
- [ ] 浏览器 B 组 modal 显示 "波黑 Bosnia and Herzegovina"

## 决策记录

- **方案 A（lookup 内部加 fallback）vs B（handler 改用 build_team_id_map）**：选 A，因为 lookup 是入口，逻辑收敛
- **`_norm_team_key` 上移到 countries.py**：避免循环 import（details → countries），单一真相源
- **不引 countries.json 反向索引**：48 队规模 O(N) 够用，加索引不值
- **3-pass 而不是 4-pass**：Pass 1 精确 + Pass 2 normalize + Pass 3 code_fifa/code_iso 覆盖全部已知 case
- **完善 testcase**：7 个 case 覆盖每个 pass 至少 1 次，加 1 个端到端

## Closeout 计划

执行后：
- 状态置 `completed`
- 写 log `docs/logs/2026/06-19-plan-028.md`
- AGE 8-Gate audit 通过
- commit
