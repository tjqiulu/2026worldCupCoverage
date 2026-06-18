# Plan 026 — Arabic 进球者名字 transliteration + 漏标 own_goal 修复

> **状态**: `proposed` (2026-06-18 11:59) → `planned` (2026-06-18 12:04 plan-audit APPROVED-WITH-MINOR) → `completed` (2026-06-18 16:13 用户 G8 视觉确认通过)
> **plan-audit**: 独立 subagent 审于 2026-06-18 12:04，4 条建议全部采纳（见决策记录）
> **log**: [`docs/logs/2026/06-18-plan-026.md`](../logs/2026/06-18-plan-026.md)（执行后）
> **创建日期**: 2026-06-18
> **关联 plan**: [017-incomplete-details-api-override.md](017-incomplete-details-api-override.md)（保护机制）, [018-arabic-scorer-name-handling.md](018-arabic-scorer-name-handling.md)（误判修正）
> **Bug 触发**: 2026-06-18 11:36 用户截图：Belgium 1-1 Egypt 详情页进球者显示阿语 `محمد هانی` / `امام آشور`

## 背景

2026-06-18 11:36，用户在 Feishu 群贴 Belgium vs Egypt 详情页截图：进球者名字是阿语而不是英文。Plan 018 当时（2026-06-16）选了"方案 D 仅入 P2-008 backlog，不改代码"，理由是"两人都埃及，错分配+数据脏"。

## 根因（v2 重新调研，纠正 Plan 018 误判）

通过对 ESPN 报告（https://www.espn.com.soccer/report/_/gameId/760426）和 The Guardian 报告交叉验证，**真实比赛数据是**：

| 时间 | 事件 | 球员（英文） | 球员（阿语原名） | 归属 |
|------|------|--------------|------------------|------|
| 19' | 进球 | Emam Ashour (Egypt midfielder) | امام آشور | away (Egypt) |
| 66' | **OG** | Mohamed Hany (Egypt defender) 自摆乌龙 | محمد هانی | home (Belgium 扳平，FIFA 标准 OG 归对方) |

**Plan 018 当时误判**：
- "两人都埃及，错分配到不同队" → 错。19' Emam Ashour 是埃及射门得分（away），66' Mohamed Hany 是埃及乌龙算比利时得分（home，按 FIFA 标准），**API 团队归属完全对**。
- "66' 主队进球者根本不知道是谁" → 错。**Lukaku 66' 上场后导致 Mohamed Hany 乌龙**，ESPN 原文 "Egypt defender Mohamed Hany did that instead, scoring an own-goal"。
- "这场比赛本身没有正确的进球者信息" → 错。**数据完全对**，只是显示层 + type 字段没处理好。

**Plan 018 实际只猜对了一半**：API 用阿语原名而不是英文转写，这部分是对的。

### 2 个独立 bug

| Bug | 描述 | 严重度 |
|-----|------|--------|
| **A. 编码** | API `player` 字段返回阿语原名（不是英文转写），UI 直接显示阿语 | 中（用户能看但是非英文） |
| **B. type 字段缺失** | 66' Mohamed Hany 应标 `type=own_goal`，但 API 给 `type=None` | 中（UI 没有 OG badge 提示） |

### 现有保护机制（Plan 017）已足够

`_is_incomplete(entry)` 判定：
- `len(goalscorers) < sum(score)` 才覆盖 → Belgium vs Egypt 是 2 < 2 = False
- `any(goals.minute == 0)` 才覆盖 → 19' / 66' 都 > 0

**结论**：手维护条目**已自动被 Plan 017 规则保护**，不需要新加 `_protected_from_api` 锁字段。

## 方案

### Fix 1: data/details.json 加 correct data（L1）

把 Belgium vs Egypt 这条（`fifa-wc-2026-323786f24db4@worldcup-calendar`）从阿语 + type=None 改成英文 + type=own_goal：

```diff
  "fifa-wc-2026-323786f24db4@worldcup-calendar": {
    "status": "final",
    "score": {"home": 1, "away": 1},
    "goalscorers": [
-     {"player": "محمد هانی", "minute": 66, "stoppage": null, "type": null, "team": "home"},
-     {"player": "امام آشور", "minute": 19, "stoppage": null, "type": null, "team": "away"}
+     {"player": "Mohamed Hany", "minute": 66, "stoppage": null, "type": "own_goal", "team": "home",
+      "_note": "OG (FIFA rules: own goal counts for opposing team). ESPN: 'Egypt defender Mohamed Hany did that instead, scoring an own-goal' after Lukaku 66' sub."},
+     {"player": "Emam Ashour", "minute": 19, "stoppage": null, "type": "goal", "team": "away",
+      "_note": "Real name 阿语: امام آشور"}
    ]
  }
```

UI 渲染代码（Plan 015/016）已有 `goal-badge goal-og` 支持 `type=own_goal`，会自动显 "OG" badge。

### Fix 2: 新建 data/scorer_overrides.json（L1）

防御性层：未来任何 API 阿语输入自动 transliterate 为英文。文件结构：

```json
{
  "_comment": "Arabic -> English player name overrides. Applied after API parse, before display. Source: Wikipedia/FIFA/transliteration.org",
  "mappings": [
    {"ar": "محمد هانی",  "en": "Mohamed Hany",  "team": "Egypt"},
    {"ar": "امام آشور",  "en": "Emam Ashour",  "team": "Egypt"},
    {"ar": "محمد صلاح",  "en": "Mohamed Salah", "team": "Egypt"},
    {"ar": "عمر مرموش",  "en": "Omar Marmoush", "team": "Egypt"},
    {"ar": "ترزيغيه",    "en": "Mahmoud Trezeguet", "team": "Egypt"}
  ]
}
```

**范围**：首期 5-10 条覆盖 Egypt / Tunisia / Morocco / Saudi / Iran 已知国脚。**不追求穷举**——新球员等用户反馈再加。`team` 字段是 hint，便于未来加 "这条只在 home/Belgium 这场有效" 等限定。

### Fix 3: src/data/details.py 加 apply_scorer_overrides() 函数（L2）

```python
def _load_overrides() -> dict:
    """Load scorer_overrides.json fresh from disk (no cache).

    Plan 026 audit fix: must NOT use @lru_cache — Plan 016 修过的 bug
    (`details.py:_load` 曾用 lru_cache 导致手维护修改不生效) 不能在
    overrides 层重演。文件很小 (<2KB) + 读取频率低，无 lru_cache 必要。
    """
    path = _PROJECT_ROOT / "data" / "scorer_overrides.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logging.warning(f"scorer_overrides.json load failed: {e}")
        return {}


def apply_scorer_overrides(entry: dict) -> dict:
    """Apply Arabic -> English name overrides to a details entry.

    Reads data/scorer_overrides.json, replaces any goalscorer.player
    that matches an Arabic mapping with its English equivalent.
    Idempotent (re-applying is a no-op since the Arabic string is gone).
    """
    overrides = _load_overrides()
    if not overrides:
        return entry
    new_entry = dict(entry)
    new_goals = []
    for g in new_entry.get("goalscorers", []):
        g = dict(g)
        for m in overrides.get("mappings", []):
            if g.get("player") == m["ar"]:
                g["player"] = m["en"]
                # _note for audit trail
                if "_override_source" not in g:
                    g["_override_source"] = f"scorer_overrides.json ({m.get('team', '?')})"
                break
        new_goals.append(g)
    new_entry["goalscorers"] = new_goals
    return new_entry
```

在 `enrich_match()` 里调用，**在 `_load()` 之后、返回前**。

### Fix 4: 单元测试（L5）

`tests/test_details.py` 加 `TestScorerOverrides` 类，7 个 case：
- `test_arabic_player_transliterated` — player="محمد هانی" → "Mohamed Hany"
- `test_english_player_unchanged` — player="K. Mbappé" → 不变
- `test_unknown_arabic_passthrough` — 没在字典的阿语原样保留
- `test_empty_overrides_file` — overrides 文件缺失/空 → no-op
- `test_apply_after_api_parse` — 模拟 API 返回阿语 → override 后是英文
- `test_overrides_json_malformed` — overrides 文件 JSON 损坏 → no-op + 记录 warning（**audit 建议 3**）
- `test_arabic_with_latin_suffix` — "محمد Salah" 这种混合不被错误整词替换（**audit 建议 3**）

### Fix 5: 8-gate closure audit script（L5）

新建 `tests/audit_gates_plan026.py`，按 Plan 021/022/023 模板：
- G1: data/details.json 包含 Belgium vs Egypt
- G2: Belgium vs Egypt 那条 player 是英文
- G3: 66' Mohamed Hany 有 `type=own_goal`
- G4: data/scorer_overrides.json 存在且包含 5+ mappings
- G5: apply_scorer_overrides() 单测 5/5 pass
- G6: pytest 全套 (200+ expected) 全过
- G7: 前端 /api/matches?match_id=... 实际返回 player 是英文
- G8: 用户视觉确认浏览器 Modal 显示 "Mohamed Hany 66' [OG]"

## 范围

### In Scope
1. L1 `data/details.json` — Belgium vs Egypt 改英文 + type=own_goal
2. L1 `data/scorer_overrides.json` — 新建
3. L2 `src/data/details.py` — `apply_scorer_overrides()` + `enrich_match` 集成
4. L5 `tests/test_details.py` — `TestScorerOverrides` 5 个 case
5. L5 `tests/audit_gates_plan026.py` — 8-gate 脚本
6. L4 `docs/logs/2026/06-18-plan-026.md` — 执行 log
7. commit + push

### Out of Scope
- ❌ 改 `merge_from_api`（Plan 017 规则已够用）
- ❌ 引 arabic-reshaper/transliteration 库（库依赖 +50KB，方案 B 字典优先观察）
- ❌ 改前端渲染（Plan 015 已有 `goal-badge goal-og` 处理 type=own_goal）
- ❌ 加 `_protected_from_api` 锁字段（Plan 017 规则已经保护）
- ❌ 重新打开 P2-008（关闭 P2-008：本 plan 解决）
- ❌ 改其它 Arabic 国家比赛（首期只 Belgium vs Egypt，等用户反馈加新 override）

## 任务清单

| # | 任务 | 估时 | 自主权 | 状态 |
|---|------|------|--------|------|
| 1 | 写本 plan → proposed | - | L4 | ✅ 11:59 |
| 2 | 独立 subagent plan-audit | 5 min | L5 | ⏳ |
| 3 | 用户批准 plan-audit | - | - | n/a |
| 4 | L1 改 data/details.json | 2 min | L1 | ⏳ |
| 5 | L1 新建 data/scorer_overrides.json | 2 min | L1 | ⏳ |
| 6 | L2 src/data/details.py 加 apply_scorer_overrides | 5 min | L2 | ⏳ |
| 7 | L2 enrich_match 集成 apply_scorer_overrides | 2 min | L2 | ⏳ |
| 8 | L5 写 5 个单测 | 5 min | L5 | ⏳ |
| 9 | L5 跑单测 5/5 pass | 1 min | L5 | ⏳ |
| 10 | L5 写 tests/audit_gates_plan026.py | 5 min | L5 | ⏳ |
| 11 | L5 跑 pytest 全套 200+ | 2 min | L5 | ⏳ |
| 12 | L5 跑 audit 7/8 pass (G8 待用户视觉) | 2 min | L5 | ⏳ |
| 13 | L4 写 log docs/logs/2026/06-18-plan-026.md | 5 min | L4 | ⏳ |
| 14 | 独立 subagent closure-audit | 5 min | L5 | ⏳ |
| 15 | G8 用户视觉确认 | - | - | n/a |
| 16 | commit + push | 30s | L4 | ⏳ |

**总估时: ~40 min**

## AGE 8-Gate Closure Audit

| # | Gate | 验证 | 状态 |
|---|------|------|------|
| 1 | data/details.json 包含 Belgium vs Egypt | grep | ⏳ |
| 2 | Belgium vs Egypt player 是英文 (Mohamed Hany / Emam Ashour) | grep | ⏳ |
| 3 | 66' Mohamed Hany 有 `type=own_goal` | grep | ⏳ |
| 4 | data/scorer_overrides.json 存在且 5+ mappings | jq | ⏳ |
| 5 | `pytest tests/test_details.py::TestScorerOverrides` 5/5 pass | pytest | ⏳ |
| 6 | `pytest tests/` 全套 200+ pass | pytest | ⏳ |
| 7 | `/api/matches` 返回 Belgium vs Egypt player 是英文 | curl | ⏳ `[BLOCKED: worldcup26.ir API 现离线；Fix 1 完成后细节中文 player 已落地，G7 待 API 恢复后复核集成链路]` |
| 8 | **手动视觉验证** (MANUAL): 浏览器 Modal 显示 "Mohamed Hany 66' [OG]" | 用户 | ✅ 2026-06-18 16:13 |

## 风险

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| worldcup26.ir API 现在不在线（curl 试 3 次都返回空）| 高 | 中 | 单测用 mock；G7 闸允许 stale-or-fresh；标注"API 恢复后再 G7 复核" |
| scorer_overrides.json 维护工作量大（新球员要加）| 中 | 低 | 字典模式，可加；首期 5 条够用；plan-026 后只加新发现的 |
| `apply_scorer_overrides` 改了原 dict，破坏调用方 | 低 | 中 | 函数内 `dict(g)` 深 copy 每次新建对象 |
| 数据冲突：override 与手维护 details.json 不一致 | 低 | 低 | 手维护优先（overrides 只在 player 是阿语时替换） |
| 阿拉伯球员拼写不固定（Emam/Imam, Mohamed/Mohammed）| 中 | 低 | 字典里 `ar` 字段是原文匹配，英文写法按 FIFA 官方（球员 Wikipedia 主页） |

## 验收

- [ ] Plan 文档 + log 写好
- [ ] 5 个新单测通过
- [ ] 200+ pytest 全过
- [ ] 8-gate audit 7/7 pass（G8 manual）
- [ ] data/details.json 里 Belgium vs Egypt 显示英文 + OG 标注
- [ ] 用户在浏览器 Modal 看到 "Mohamed Hany 66' [OG]" / "Emam Ashour 19'"
- [ ] commit + push 干净

## 决策记录

- **Plan 018 误判承认**：当时没对照 ESPN 等真实数据源，盲信"两人都埃及=脏数据"是错的
- **方案 B（手维护字典）vs 方案 A（库自动 transliterate）**：选 B，理由是 0 依赖 + 维护成本可控 + 等观察 6/18-6/30 看新比赛阿语出现频率
- **不加 `_protected_from_api` 锁字段**：Plan 017 的 `_is_incomplete` 规则已经保护手维护条目（`len(goals)=2=sum(score)=2`），新增字段属过度设计
- **66' Mohamed Hany type 必标 own_goal**：FIFA 规则 OG 归对方 → team=home（Belgium 得分），type=own_goal 显 OG badge
- **plan-audit 4 条建议全部采纳**：G7 闸标注 API 阻塞 + `_load_overrides` 显式无缓存 + 2 个边界测试 + countries.py 区分说明（详见 plan 顶部 audit 决策）

## 不破坏什么

- `merge_from_api` / `_is_incomplete` / `_load` / `save_details`：全不动
- `_parse_scorer_strings` (Plan 025 parser)：不动
- 前端 Modal 渲染（Plan 015/016）：不动（type=own_goal 已有 badge 支持）
- `compute_standings_from_details` (Plan 025)：不动
- 其它 19+ 场手维护 details.json 条目：不动
- **`src/data/countries.py:32` 也有同名 `enrich_match`**（**audit 建议 4**：加 `name_zh/code_iso/flag`），本 plan **只改** `src/data/details.py:70` 的 `enrich_match`（加 `details` 字段）。两个函数都通过 `app.py:127-128` 顺序调用，互不影响

## Next-Session Pickup Notes

- 6/18 后新比赛如有 Arabic 国家 → 用户会反馈 → 加 scorer_overrides.json mapping
- 如果 6/18-6/30 期间 Arabic 出现频率高 → 考虑升级到方案 A（arabic-reshaper 库）
- P2-008 backlog 条目本 plan 关闭

## P2-008 closeout

| 字段 | 值 |
|------|-----|
| **Backlog ID** | P2-008 |
| **Plan** | 026 |
| **关闭原因** | 实施 transliteration + type=own_goal 修复 + Plan 017 规则保护 |
| **关闭日期** | 2026-06-18 |

## Closeout（2026-06-18 16:13 G8 用户视觉确认通过）

> **状态**: `completed`

### 最终 8-Gate 总结
- **G1-G6 自动化 ✅**：plan / 实施 / 6/6 自动闸 + 220/220 pytest
- **G7 ⏸️ SKIP**：worldcup26.ir API 离线，待恢复后单独跑（修复 API 后 `python3 tests/audit_gates_plan026.py`）
- **G8 ✅**：用户 2026-06-18 16:13 视觉确认 Modal 正确显示 "Mohamed Hany 66' [OG]" / "Emam Ashour 19'"

### 闭环数字
- **1 个 commit** (`6e06605`)
- **7 个文件改动**：+896 行 / -6 行
- **3 改 + 4 新**（数据 / 代码 / 测试 / 文档 / 脚本）
- **220/220 pytest** 全过（+7 新增，0 回归）
- **P2-008 关闭**（Plan 018 误判 2 天后正式 fix）

### 关键收获（适合未来参考）
1. **不照外部源数据就下结论会出 bug**：Plan 018 当时盲信"两人都埃及=脏数据"，没去对照 ESPN/Guardian。Plan 026 调研第一步就 external source verify，纠正了误判
2. **AGE plan-audit 4 条建议全是"非阻塞但有价值"**：闸标注、缓存策略、边界测试、文档区分 — 每条对应一个潜在回归点
3. **Plan 017 规则足够保护手维护条目**：2 < 2 是 False，永久不被覆盖 — 避免加新锁字段的过度设计
4. **API 离线时 audit 策略**：自动 SKIP 而不是 FAIL，避免误报；G7 等 API 恢复单独跑
5. **subagent 任务拆小**：closure-audit subagent 5 分钟超时 0 tokens — 未来拆成 5 子任务而不是 1 大任务

### Next-Session Pickup Notes
- 6/18 后新比赛如有 Arabic 国家进球 → 用户会反馈 → 加 `data/scorer_overrides.json` mapping
- 如果 6/18-6/30 期间 Arabic 出现频率高（>5 条/周）→ 考虑升级到方案 A（arabic-reshaper 库）
- G7 闸待 worldcup26.ir API 恢复后单独跑一次
- Plan 018 历史决策保持记录在 P2-008 closeout 段（如未来有人问"为什么 Plan 018 当时没做"，有 audit trail 可查）
