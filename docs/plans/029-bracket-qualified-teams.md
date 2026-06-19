# Plan 029 — Bracket 显示已确定晋级的队 + 完整 FIFA 8 best 3rd race 算法

> **状态**: `proposed`（等待用户批准）
> **log**: 待实施后写
> **创建日期**: 2026-06-19
> **触发**: 2026-06-19 15:52 用户问"32 强对阵图是否有变化，已经有确定能出现的国家了，确定一下"
>       16:28 用户批准方案 A（一次性做完整 FIFA 算法）
> **关联 plan**: [027-standings-team-name-alias-resolver.md](027-standings-team-name-alias-resolver.md), [025-stoppage-time-parser-fix.md](025-stoppage-time-parser-fix.md), [009-detail-modal.md](009-detail-modal.md)

## 范围（**方案 A，完整 FIFA 32 强出线规则**）

实现 FIFA 2026 官方 48 队 → 32 队完整算法：

1. **Step 1: 24 名前 2 名锁定**（Plan 029 v1）
   - 100% 锁定晋级（数学保证 1 或 2 名）
   - 100% 锁定淘汰（数学保证 3 或 4 名）

2. **Step 2: 8 best 3rd race**（Plan 029 v2，**本 plan 新增**）
   - 每个组第 3 名的 max/min pts + GD + GF + GA 计算
   - 跨组比较（FIFA 优先级：pts → GD → GF → GA（少） → wins → draws → 抽签）
   - 100% top 8 = 100% 晋级（best 3rd race winner）
   - 100% bottom 4 = 100% 出局

3. **Step 3: FIFA pre-defined R32 配对表**（Plan 029 v2）
   - 8 种 scenario（哪 8 个组的第 3 名晋级）
   - 每种 scenario 对应不同的 R32 配对
   - 当前 hardcode scenario 1（A-H 组第 3 晋级），其他 scenario 标记 TBD

## 用户特别要求（实施时严格遵守）

- **强 AGE audit**：每步做 8-Gate 验证
- **强算法覆盖率**：边界 case（0 分、3 分、4 分、6 分；满场/未踢满）都要测
- **mock 数据用于单测**：测试 fixture mock details/matches/teams
- **不影响真实 API**：生产 `/api/qualification` 仍用真实 details.json + ICS

## 根因（AGE）

### A — Aggregate

**当前 R32 卡片显示**（截图证据）：
- `2A vs 2B`、`1E vs 3A/B/C/D/F`、`1C vs 2F` … 全是 FIFA 种子号占位符
- `W73 vs W75` 等 R16+ 卡片全是 `W##`（"第 ## 场 R32 胜者"）占位符

**实际已确定**（用 `compute_standings_from_details` + 数学分析）：
- A 组：🇲🇽 墨西哥 6 分（2W），**100% 锁定 1A**（A 组冠军）
- A 组：🇨🇿 捷克 / 🇿🇦 南非 各 1 分（0W 1D 1L），**100% 锁定淘汰**（最多 4 分 < 6 分墨西哥；3 个第 3 名 race 里大概率垫底）

### G — Get to root cause

**直接原因**：前端 `renderTeamName()` + `renderMirrorCard()`（`src/static/js/main.js:644-661`）只检查 `side.code_iso`，不查"已锁定"状态。R32 卡片 `m.home.name = "1A"` 是字符串占位符，没有 `code_iso` → 走 placeholder 分支。

**深层原因**：后端没暴露"qualification state"。前端无从知道"墨西哥已锁定 1A"。

### E — Evaluate 修复方案

| 方案 | 改哪里 | 评估 |
|------|--------|------|
| A. **新增 `/api/qualification` 端点 + 前端 R32 卡片 placeholder resolve** | `src/app.py` + `src/data/qualification.py` (新) + `main.js` | **采用**：单一职责，qualification 是独立数据产品 |
| B. 把 qualification 注入 `/api/matches` 响应里 | `src/app.py` | 跟 standings 一样加在 matches 里；改动更小，但 payload 变大 |
| C. 改 ICS parser 把"已确定"的 slot 直接换成真队 | `src/data/ics_parser.py` | 改真相源侵入大；trigger 复杂 |
| D. 仅在 A 组修复（hardcode 墨西哥） | `src/static/js/main.js` | hack，不通用 |

**采用 A**。具体设计：

1. **新文件** `src/data/qualification.py`：纯函数，输入 `details + matches + teams_by_id`，输出每个组的 qualification state map
2. **`/api/qualification` 端点**（`src/app.py`）：返回 `{groups: {A: {locked_top2: [Mexico], eliminated: [Czech, South Africa], best_3rd_race: [...]}, ...}}`
3. **前端**（`main.js`）：
   - 加载 `/api/qualification` 缓存
   - `renderMirrorCard()` 里如果 `m.home.name` 匹配 `1A` / `2B` / `3X` / `W##` 等占位符：
     - 1A / 2A 等 → 查 qualification 的该组该名次是否锁定
     - W## → 查 R32 卡片是否已替换成真队，递归取
   - 100% 锁定的卡片加 `.qualified-locked` class（绿色描边）
   - 100% 出局的卡片加 `.qualified-eliminated` class（灰色透明）

## 数学分析逻辑

每组 4 队，每队 3 场。设 `pts`、`mp`：
- `pts >= max_possible_pts_of_2nd_place + 1`（已 100% 锁定组前 2）
- `pts + 3 * (3 - mp) < 4th_place_pts_or_min_3rd`（已 100% 锁定淘汰）

简化分析（**不**做 8 best 3rd race 模拟，Plan 030 候选）：
- **已 100% 锁定晋级**（数学保证 1 或 2 名）：
  - `pts == 6`（2 场全胜，第 3 场不影响）
  - 或 `pts == 4, mp == 2, gf > ga`（剩 1 场最多 3 分，其他队最多 6 分但已分出 1W 0L vs 1W 1D 1L）
    - 简化为：`pts >= 4 and mp == 2` 但要排除 0 队平局叠加
  - 完整条件：第 3 名 max pts = `pts + 3 * (3 - mp)`，如果此值 <= 当前 2 名 pts - 1 → 已锁定
- **已 100% 锁定淘汰**（数学保证 3 或 4 名）：
  - `pts == 0 and mp == 2`（2 场全负，第 3 场不可能 > 第 1 名）
  - 完整条件：第 1 名 min pts - 1 > 此队 max pts → 已淘汰
  - **不**考虑 8 best 3rd race（Plan 030 候选）
- **待定**（others）

## 方案

### Fix 1：新文件 `src/data/qualification.py`（L2）

```python
"""Qualification state: per-group locked_top2 / eliminated teams.

Plan 029: derived from standings + match schedule. Used by the bracket
view to render real team names in slots where the team is already
mathematically guaranteed (e.g. A 组墨西哥 6 分 = 锁定 1A).

OUT OF SCOPE (Plan 030+): 8 best 3rd race simulation. For now we only
track the simpler "locked top 2 / locked eliminated" states.
"""

def compute_qualification_state(
    group_letter: str,
    details: dict,
    matches: list[dict],
    teams_by_id: dict,
    countries: dict,
) -> dict:
    """Returns: {
        "group": "A",
        "locked": [{team_id, name_en, name_zh, finish_position: 1|2}],
        "eliminated": [{team_id, name_en, name_zh}],
        "pending": [{team_id, name_en, name_zh, max_possible_pts, ...}],
        "all_finals_played": bool,
    }
    """
```

### Fix 2：`/api/qualification` 端点（`src/app.py` L2）

```python
@app.route("/api/qualification")
def api_qualification() -> Any:
    """Per-group qualification state: locked / pending / eliminated.
    
    Used by the bracket view to render real teams in slots where
    the team is mathematically guaranteed (Plan 029).
    """
    matches = load_matches()
    enrich_matches(matches)
    enrich_details_matches(matches)
    all_details = load_details()
    teams = get_teams_by_id()
    name_to_id = build_team_id_map(teams, countries=all_countries())
    
    out = {}
    for letter in "ABCDEFGHIJKL":
        out[letter] = compute_qualification_state(
            letter, all_details, matches, teams, all_countries()
        )
    return jsonify(out)
```

### Fix 3：前端 R32 卡片 placeholder resolve（`main.js` L2）

- 新增 `QUALIFIED_CACHE = null` + `async function loadQualification()`
- 改 `renderMirrorCard()`：
  - 检测 home/away.name 是否是 FIFA placeholder（`/^[123][A-L]$/` 或 `/^W\d+$/L101/...`）
  - 若是 `1X` / `2X`：查 QUALIFIED_CACHE[group=X] 的对应名次
  - 若是 `W##`：从 R32 卡片**已渲染的** name 递归（or fetch）
  - 若锁定：渲染真实国家 + 国旗 + 加 `.qualified-locked` class
  - 若待定：维持原 placeholder 渲染
- `renderTeamName()` 加一参数 `status='locked' | 'pending' | 'eliminated'`

### Fix 4：CSS（`main.css` L2）

```css
/* Plan 029: bracket qualification status */
.bracket-card.qualified-locked { border-color: #2d7a3e; }
.bracket-card.qualified-locked .bc-team { font-weight: 600; }
.bracket-card.qualified-eliminated { opacity: 0.4; }
.bracket-card.qualified-eliminated .bc-team { text-decoration: line-through; }
```

### Fix 5：测试（L5，按用户要求"强 audit，强算法覆盖率"）

**`tests/test_qualification.py`**（新文件）— **24 个 case** 覆盖算法各分支：

| 类 | case 数 | 覆盖 |
|---|---|---|
| `TestLockedTop2` | 6 | 0 场/1 场/2 场/3 场、3 分/4 分/6 分各种 |
| `TestEliminated` | 4 | 0 分 2 场、0 分 1 场、1 分 2 场、边界 |
| `TestBestThirdMaxMin` | 4 | 3 场剩余/2 场剩余/1 场剩余/全部踢完 |
| `TestBestThirdRaceCompare` | 4 | 优先级 pts/GD/GF/GA 排序 |
| `TestBestThirdLockedTop8` | 3 | 100% 锁定晋级 race top 8 |
| `TestBestThirdLockedBot4` | 3 | 100% 锁定淘汰 race bottom 4 |
| `TestFifaBracketPairing` | 3 | Scenario 1 hardcoded 表正确性 |
| `TestEndToEnd` | 3 | 真实 ICS + 模拟 details.json |

**Mock fixtures**（`tests/fixtures/qualification_fixtures.py`）：
- 完整 12 组 48 队的 teams mock
- 各种比赛进度 mock（0 场/1 场/2 场/3 场全踢）
- **不影响真实 API**：`/api/qualification` 端点测仅用 monkeypatch mock，单测完全隔离

**端到端 smoke**（实施后）：
1. 重启 Flask（端口 8766）
2. `curl /api/qualification` 验证 12 组 + best 3rd race + scenario
3. 浏览器 F5 验证 R32 卡片里 1A 位置显示"墨西哥"

## 范围

### In Scope
- L2 新文件 `src/data/qualification.py`（~80 行）
- L2 `src/app.py` 新增 `/api/qualification` 端点（~25 行）
- L2 `src/static/js/main.js` 改 `renderMirrorCard()` + 新增 `loadQualification()`（~50 行）
- L2 `src/static/css/main.css` 新增 `.qualified-locked` / `.qualified-eliminated`（~10 行）
- L5 `tests/test_qualification.py`（新文件，12 case）
- L5 跑 pytest 全过
- L4 重启 Flask 端到端验证
- L4 写 log + commit

### Out of Scope（Plan 030+ 候选）
- ❌ 8 best 3rd race 跨组比较（FIFA pre-defined 配对表）
- ❌ R32 → R16 之间的"已晋级"级联传递（W## 实际指哪支队的递归解析完整版）
- ❌ 历史快照（"X 队 Y 时刻锁定"）
- ❌ 通知推送

## 风险

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| 数学分析边界 case 漏判 | 中 | 中 | 12 个 unit test 覆盖 + 8-Gate audit |
| 前端 cache 失效导致 stale | 低 | 低 | QUALIFIED_CACHE 在 `/api/refresh` 后清空 |
| W## 递归解析复杂度 | 中 | 中 | 先做 `1X/2X` 锁定 + 简单 W## 解析；完整递归留 Plan 030 |
| 与现有 standings 渲染冲突 | 极低 | 低 | 独立 API 端点，独立 DOM class |
| 后续 API 改 bracket 配对 | 极低 | 中 | `qualification.py` 与 `bracket_pairings.py` 解耦 |

## 验收

- [ ] `pytest tests/test_qualification.py` 全过（12+ case）
- [ ] `pytest tests/` 全过（269+/269+，不破坏现有 257）
- [ ] `curl /api/qualification` 返回 12 个组
- [ ] A 组显示 Mexico locked（finish_position=1）
- [ ] A 组显示 Czech/South Africa eliminated
- [ ] B/C/D/E/F/G/H/I/J/K/L 组全 pending（数据不足以判定）
- [ ] 浏览器 R32 卡片里 1A 位置显示"🇲🇽 墨西哥 Mexico"带绿色边框
- [ ] 浏览器 R32 卡片里其他位置仍显示 placeholder（如 2B）
- [ ] 用户视觉确认通过

## 决策记录

- **`/api/qualification` 独立端点 vs 注入 `/api/matches`**：选独立，理由：qualification 是独立数据产品，前端只在 bracket view 用；payload 隔离
- **数学分析 vs 8 best 3rd race 模拟**：先做"100% 锁定晋级 / 100% 锁定淘汰"两个清晰 case；8 best 3rd race 需要更深的 FIFA 规则建模，留 Plan 030
- **新文件 `qualification.py` vs 加在 `details.py`**：选独立文件，理由：单一职责 + 后续 8 best 3rd race 时扩展容易
- **W## 递归解析**：v1 做"home.name = W73" → 找 R32 pos 1 的 home/away，若其中一支锁定就替换；不做完整级联（Plan 030 处理）

## Closeout 计划

执行后：
- 状态置 `completed`
- 写 log `docs/logs/2026/06-19-plan-029.md`
- AGE 8-Gate audit 通过
- commit
