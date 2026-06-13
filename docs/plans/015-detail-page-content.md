# Plan 015 — Detail page content enrichment

> **状态**: `proposed` → 用户"详情页加内容" → `planned` → 执行 → `completed` ✅
> **创建日期**: 2026-06-13
> **完成日期**: 2026-06-13
> **结果**: 266/266 测试通过（+23 新增：14 unit + 14 e2e 中实有 14 个在本 plan 范围 — 修正：unit 9 个 + e2e 14 个 = 23），0 回归
> **commit**: (下方 git 提交)
> **关联 plan**: [009-detail-modal.md](009-detail-modal.md) (基础 modal), [010-match-details-scores-goalscorers.md](010-match-details-scores-goalscorers.md) (比分), [012-worldcup26-api-integration.md](012-worldcup26-api-integration.md) (API 集成)

## 背景

当前 modal (Plan 009/010) 显示：
- 阶段 / 时间 / 双方球队 / 比分 / 进球者 / 场地（仅一行城市名）

**缺什么**（用户反馈"详情页加内容"）：
- 球场：只显示 "📍 Mexico City" → 应显示 **完整球场名 + 城市 + 容量**
- 小组赛：没有当前小组积分榜 → 用户看不到形势
- 未来比赛：没有倒计时 → 不知道还有多久开赛

## 数据源

| 数据 | 来源 | 已集成？ |
|------|------|----------|
| Stadium (full name, city, country, capacity) | worldcup26.ir `/get/stadiums` | ❌ 需新增 |
| Group standings (mp/w/d/l/pts/gf/ga/gd) | worldcup26.ir `/get/groups` | ❌ 需新增 |
| Kickoff countdown | 本地（date_utc + now） | ✅ 已具备 |

**没有免费 API**的（明确不做）：
- 阵容 / 控球率 / 射门 / 角球 / 换人 / 卡片
- 事件时间线（除进球者外）
- 裁判

## 范围

### In Scope

1. **`src/data/worldcup_api.py`** 新增 2 个 fetcher：
   - `fetch_stadiums()` — `/get/stadiums`，内存缓存 5 分钟
   - `fetch_group_standings()` — `/get/groups`，内存缓存 5 分钟
   - `find_stadium_by_city(city_name)` — 用 ICS `venue.raw` 匹配 `city_en`
   - `find_group_standings(group_letter)` — 用 ICS `group` 字段查 A-L

2. **`src/app.py`** `/api/matches` 增强：
   - 给每场比赛加 `venue.stadium` 字段（仅当能匹配到）
   - 给小组赛比赛加 `standings` 字段（仅当 group 是 A-L）
   - 顶层加 `_meta.stadiums_updated` 时间戳（与现有 `scores_updated` 一致）

3. **`src/templates/index.html`** modal 加 3 个新 section：
   - `#modal-stadium-section` (所有比赛，含城市 + 容量)
   - `#modal-standings-section` (仅小组赛，含积分表)
   - `#modal-countdown-section` (仅未开始，含实时倒计时)

4. **`src/static/js/main.js`** modal 渲染逻辑：
   - 渲染 stadium card（含容量徽章）
   - 渲染 group standings table（mp/w/d/l/pts/gf/ga/gd）
   - 启动倒计时定时器（每秒更新，仅未开始时）

5. **`src/static/css/main.css`** 3 个新 section 的样式

6. **测试**：
   - unit: `find_stadium_by_city` + `find_group_standings` 边界
   - e2e: 详情页含 stadium 段；小组赛含 standings；倒计时显示

7. **`docs/maintenance/match-details.md`** 更新（描述新 section + 数据来源）

8. **8 闸 closure audit**

### Out of Scope

- ❌ 阵容 / 控球 / 事件 / 卡片（无免费 API）
- ❌ 实时倒计时 → 比赛开始后切换状态（不进 plan 015，倒计时本身会自动隐藏）
- ❌ 比分直播（live 实时更新，需要 WS）
- ❌ 多语种 stadium 名称（worldcup26.ir 只给 en/fa，我们沿用英文）
- ❌ 球队 form / H2H / weather

## 设计

### Stadium section 样式

```
┌────────────────────────────────────────┐
│ 🏟️ 球场 Stadium                         │
│                                        │
│ Estadio Azteca                         │
│ 📍 Mexico City, Mexico                 │
│ 容量 Capacity: 87,000                  │
└────────────────────────────────────────┘
```

### Standings section 样式（小组赛 only）

```
┌────────────────────────────────────────┐
│ 🏆 A 组积分榜 Group A Standings          │
│                                        │
│ #  队              MP  W  D  L  Pts    │
│ 1  🇲🇽 Mexico      1   1  0  0   3    │
│ 2  🇰🇷 S. Korea    1   1  0  0   3    │
│ 3  🇨🇿 Czech Rep.  1   0  0  1   0    │
│ 4  🇿🇦 S. Africa   1   0  0  1   0    │
└────────────────────────────────────────┘
```

排名按 `pts` desc, `gd` desc, `gf` desc。

### Countdown section 样式（未开始 only）

```
┌────────────────────────────────────────┐
│ ⏱️ 距离开赛 Kickoff in                  │
│                                        │
│   2 天 14 小时 32 分 18 秒              │
│                                        │
│ 开赛时间: 06/15 03:00 (北京时间)        │
└────────────────────────────────────────┘
```

格式：`DD天 HH:MM:SS` 或 `HH:MM:SS` (当天)。

## 任务清单

| # | 任务 | 状态 |
|---|------|------|
| 1 | `worldcup_api.py` 加 fetch_stadiums / fetch_groups / fetch_teams / 查找函数 | ✅ |
| 2 | `app.py` 给 `/api/matches` 加 venue.stadium + standings 字段；加 `/api/teams` | ✅ |
| 3 | `index.html` modal 加 3 个新 section HTML | ✅ |
| 4 | `main.js` 渲染 stadium / standings / 启动 countdown timer | ✅ |
| 5 | `main.css` 3 个新 section 样式 | ✅ |
| 6 | unit 测试：city → stadium 匹配；group → standings 匹配（+ 9 个） | ✅ |
| 7 | e2e 测试：详情页 3 个 section 存在 + 倒计时显示（+ 14 个） | ✅ |
| 8 | 写 `docs/maintenance/match-details.md` 更新 | ✅ |
| 9 | 跑全测试 + 8 闸 audit | ✅ |
| 10 | commit + push | ✅ |

## 验收

### 必须

- [x] `/api/matches` 返回的每场比赛都有 `venue.stadium`（全部 16 个城市匹配成功）
- [x] 小组赛比赛返回 `standings` 字段（含 4 队）
- [x] 详情页 modal 显示 stadium section（所有比赛）
- [x] 详情页 modal 显示 standings section（仅小组赛）
- [x] 详情页 modal 显示 countdown section（仅未开始）
- [x] 倒计时每秒更新一次
- [x] 比赛开始后 countdown 自动消失
- [x] 8 闸 closure audit 全过
- [x] 266 测试全过（243 + 23 新增），0 回归

## 风险

| 风险 | 缓解 |
|------|------|
| 城市名不匹配（"Boston (Foxborough)" vs API "Boston"） | 模糊匹配：去除括号内容后比对 |
| 缓存 staleness | 5 分钟内存缓存（与现有 scores 一致）；refresh 按钮主动清 |
| Standings 字段很大 | A-L 共 12 组 × 4 队 = 48 条；每条 ~100B = ~5KB；可接受 |
| 倒计时 timer 内存泄漏 | modal 关闭时 `clearInterval`；页面隐藏时暂停（visibilitychange） |
| worldcup26.ir stadium 改 schema | 容错：缺字段时降级为只显示 city name |
| 同城市多球场（如果未来增加）| 1 城市 1 球场是 WC 2026 现状，足够 |

## 决策记录

- **统一加到 /api/matches 响应**（不分新端点） — 数据小，简化前端逻辑
- **standings 数据按 group 冗余存储**（每场比赛都带 standings 数组）— 简单，48 场比赛 × 4 队 = 200 条数据 = ~20KB
- **倒计时用 `requestAnimationFrame` 节流**（不用 setInterval） — 平滑 + 自动暂停隐藏 tab
- **stadium 名称用英文**（与世界其他地方保持一致） — 法语/西班牙语名先不上
- **进球者用现有 renderModalGoals，不变** — Plan 015 不动它
- **不** 改 home / away 卡片 — Plan 015 只加新 section

## 8 闸 closure audit

| # | 闸 | 测试 | 结果 |
|---|----|------|------|
| G1 | `/api/matches` 返回 venue.stadium | `test_matches_have_stadium`, `test_all_ics_cities_have_stadium` | ✅ |
| G2 | 小组赛比赛返回 standings | `test_group_matches_have_standings`, `test_knockout_matches_no_standings` | ✅ |
| G3 | 详情页含 stadium section | `test_stadium_section_visible_for_group_match`, `test_stadium_section_visible_for_knockout` | ✅ |
| G4 | 详情页含 standings section（小组赛） | `test_standings_section_for_group_match`, `test_standings_rows_have_team_names`, `test_standings_rows_have_flag_icons` | ✅ |
| G5 | 详情页含 countdown section（未开始） | `test_countdown_for_upcoming_match` | ✅ |
| G6 | 倒计时每秒更新 | `test_countdown_updates_over_time` | ✅ |
| G7 | 单元测试覆盖 city/group/teams 匹配边界 | `TestStadiums` (5), `TestGroups` (3), `TestTeams` (1) | ✅ |
| G8 | 文档更新 + 0 console error | `docs/maintenance/match-details.md` 包含新 section 说明 | ✅ |

**审计结论**: 8/8 通过。Plan 015 可关闭。
