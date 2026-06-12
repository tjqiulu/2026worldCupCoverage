# Plan 010 — Match Details (Scores + Goalscorers)

> **状态**: `proposed` → 用户"严格遵循 AGE 方法论，plan 里面细化需求，audit 流程增加测试覆盖需求" → `planned` → 执行 → `completed`
> **创建日期**: 2026-06-12
> **关联 plan**: [009-detail-modal.md](009-detail-modal.md) (前置 modal), [001-initial-skeleton.md](001-initial-skeleton.md) (原计划留 details.json 钩子)
> **用户驱动**: 反馈"赛程界面没有看到已经结束比赛的比分" + "详情页却比分、进球时间和射手是誰等信息"

## 背景

Plan 009 加了详情弹窗，但只显示已有数据（队名、国旗、日期、场地）。**没有**：
- 已结束比赛的**比分**（如 2-1）
- **进球时间和射手**（如 "🇲🇽 H. Herrera 23'"）
- 进行中比赛的**实时比分**（虽然用户不要实时，但有也得能显示）

**数据源问题**：baires/fifa-cal-2026 ICS 只提供**赛程**，**不含比分/射手**。需要手动维护 `data/details.json`（这是 Plan 001 原始 plan 里预留的钩子）。

## 详细需求（细到每条 R 都有 e2e 测试）

### Backend 层

- **R1**. `data/details.json` 文件存在，包含**初始数据**（前 2 场已结束比赛 + 其余未开始）
  - Schema: `{match_id: {status, score?, half_time_score?, goalscorers?}}`
  - status 枚举: `"final"` | `"live"` | `"scheduled"`
  - score: `{home: int, away: int}`
  - goalscorers: `[{team: "home"|"away", player: str, minute: int, type?: "goal"|"penalty"|"own_goal"}]`
  - 测试: `test_details_json_exists_and_valid`

- **R2**. 后端启动时加载 details.json（缓存）
  - 测试: `test_details_loaded_at_startup` (覆盖缓存层)

- **R3**. `/api/matches` 响应**每个 match 包含 `details` 字段**（有就填，没有就 null）
  - 测试: `test_api_matches_includes_details_field`

### Frontend 层（赛程视图）

- **R4**. 比赛卡片显示**状态 badge**：已结束 / 进行中 / 未开始
  - "已结束": 灰底深灰字
  - "进行中": 红底白字 + 脉冲点
  - "未开始": 透明底浅灰字
  - 测试: `test_match_card_shows_status_badge`

- **R5**. 已结束比赛卡片显示**比分**（大号、彩色、放在两队之间）
  - 格式: `2 - 1`（home 黑色，away 黑色，加粗）
  - 测试: `test_final_match_shows_score`

- **R6**. 进行中比赛卡片显示**实时比分**（同上 + 红色 "LIVE" 标签 + 脉冲点）
  - 测试: `test_live_match_shows_live_score`

- **R7**. 未开始比赛卡片显示**vs**（无分数）
  - 测试: `test_scheduled_match_shows_vs_no_score`

- **R8**. 卡片点击**仍打开详情弹窗**（Plan 009 不变）
  - 测试: `test_click_card_opens_modal_regardless_of_status` (覆盖 R4-R7)

### Frontend 层（详情弹窗）

- **R9**. 弹窗显示**比分大区块**（已结束 / 进行中）：
  - 标题"比分 Score"
  - 大号数字 `2 - 1`，居中
  - 已结束: 旁边加 "完场" 小标签
  - 进行中: 旁边加红色 "LIVE" 标签
  - 测试: `test_modal_shows_score_for_final`, `test_modal_shows_live_score`

- **R10**. 弹窗显示**进球列表**（已结束）：
  - 标题"进球 Goals"
  - 每条: `🇲🇽 H. Herrera 23'`（国名 emoji + 球员 + 分钟）
  - penalty 标记: `(点)`、own_goal 标记: `(乌龙)`
  - 测试: `test_modal_shows_goalscorers_list`

- **R11**. 弹窗显示**半场比分**（如 "半场: 1-0"），如果 details.json 有提供
  - 测试: `test_modal_shows_half_time_score`

- **R12**. 未开始比赛弹窗**不显示**比分/进球区块（graceful）
  - 测试: `test_modal_hides_score_section_for_scheduled`

### 数据层

- **R13**. **初始数据**：`data/details.json` 包含前 2 场比赛（MEX vs RSA, KOR vs CZE）作为 "final" 状态，含比分和射手（用 2022 WC 真实球员名，标 "示例数据" 注释）
  - 测试: `test_initial_details_data_has_first_2_matches`

- **R14**. **维护文档**：`docs/maintenance/match-details.md` 写明：
  - schema
  - 如何添加新比赛结果
  - 如何标记 "live" 状态
  - 何时刷新
  - 测试: 文件存在性检查

### 边界情况

- **R15**. **缺失 details.json** → 后端不崩，前端显示 "未开始" 给所有比赛
  - 测试: `test_missing_details_json_graceful`

- **R16**. **某 match 在 details 里但格式错** → 该 match 当作无 details，其他不受影响
  - 测试: `test_malformed_details_entry_isolated`

- **R17**. **R32+ 占位符比赛**（如 W86 vs W88）→ 即使 details.json 标记 "final"，也用占位符显示（因为不知道真实队名）
  - 测试: `test_placeholder_match_no_score_shown`

## 8 闸 Closure Audit

| Gate | 覆盖的 R | 测试方法 |
|------|----------|----------|
| G1: 数据层完整性 | R1, R2, R13, R15, R16 | pytest (data layer tests) |
| G2: API 暴露 details | R3 | pytest (API tests) |
| G3: 状态 badge 显示 | R4, R8 | e2e (Playwright) |
| G4: 比分显示 | R5, R6, R7 | e2e (3 cases) |
| G5: Modal 比分 | R9, R12 | e2e (3 cases) |
| G6: Modal 进球 | R10, R11 | e2e (3 cases) |
| G7: 初始数据 | R13 | pytest (data + e2e) |
| G8: 文档 + 占位符 | R14, R17 | file exists + e2e |

**每个 gate 都有 2+ 测试覆盖。任意一个 fail → plan 不通过。**

## 数据 schema（JSON 例子）

```json
{
  "fifa-wc-2026-11a1dcab930a@worldcup-calendar": {
    "status": "final",
    "score": {"home": 2, "away": 0},
    "half_time_score": {"home": 1, "away": 0},
    "goalscorers": [
      {"team": "home", "player": "H. Lozano", "minute": 23, "type": "goal"},
      {"team": "home", "player": "R. Jiménez", "minute": 67, "type": "penalty"}
    ]
  }
}
```

`score` 字段**总是**是 home 队的分数（按 matches.json 里的 home 队语义）。

## 任务清单

| # | 任务 | 状态 |
|---|------|------|
| 1 | 写 `src/data/details.py` (load + validate) | ⏳ |
| 2 | 写 `data/details.json` (initial 2 matches) | ⏳ |
| 3 | 改 `src/app.py` enrich API response | ⏳ |
| 4 | 改 JS renderMatches 加 status badge + score | ⏳ |
| 5 | 改 JS renderModalTeam 加比分/进球 section | ⏳ |
| 6 | pytest test_details.py (R1, R2, R13, R15, R16) | ⏳ |
| 7 | e2e test_status_badge.py (R4, R8) | ⏳ |
| 8 | e2e test_score_display.py (R5, R6, R7) | ⏳ |
| 9 | e2e test_modal_details.py (R9, R10, R11, R12) | ⏳ |
| 10 | 写 `docs/maintenance/match-details.md` (R14) | ⏳ |
| 11 | 跑全部测试 | ⏳ |
| 12 | 截图 + 视觉 review | ⏳ |
| 13 | commit | ⏳ |

## 验收

### 必须

- [ ] 所有 17 个 R 都有对应测试
- [ ] 8 闸 closure audit 全过
- [ ] 96+ unit + 52+ e2e 全过
- [ ] 视觉评分 ≥ 8/10

## 风险

| 风险 | 缓解 |
|------|------|
| details.json 格式错 → 后端崩 | validate 函数 + R15 测 |
| 用户不知道何时更新 details | 文档明确说明（用 Bing 比对结果） |
| 进球时间格式不一（45+3 vs 45'） | schema 强制 `int`（不含加号），前端显示加 ' |
| 8 个 R 太多，scope 失控 | 分阶段（先 backend + R3 + R13 + R4-R7，再 modal） |

## 决策记录

- **数据源**: 手动 details.json（不用外部 API）—— 用户拒绝实时，且手动维护最稳
- **schema**: 简化（status + score + goalscorers），不存红黄牌 / 控球率 / 传球等
- **R17 占位符比赛**: 即使 details 标 final，UI 也只用占位符（因为不知道真实队名）
- **示例数据**: 前 2 场用 2022 WC 真实球员（Lozano / Jiménez / Son / Schick 等）作为示例，标 "示例" 注释
- **失败隔离**: 单个 match 格式错不影响其他（R16）
- **不**做"添加结果"web 表单（手动编辑 JSON 已够，留 Plan 011+）

## Out of Scope

- ❌ 实时比分（用户不要）
- ❌ 红黄牌 / 控球率 / 阵容
- ❌ Web 维护界面
- ❌ 进球视频链接
- ❌ 自动检测比赛结束（依赖手动标记 status）
