# Plan 012 — World Cup 2026 API Integration (Live Scores)

> **状态**: `proposed` → 用户"数据是 api 传来的，点击刷新按钮就应该刷新数据" → `planned` → 执行 → `completed`
> **创建日期**: 2026-06-12
> **关联 plan**: [010-match-details-scores-goalscorers.md](010-match-details-scores-goalscorers.md) (手动), [011-auto-status.md](011-auto-status.md) (auto-detect)
> **用户驱动**: 反馈"数据应该 API-driven，刷新按钮应该拉新数据"

## 背景

之前 2 个 plan 的方案：
- Plan 010: 手动 `data/details.json`（用户嫌麻烦）
- Plan 011: auto-detect from `date_utc`（无真实比分）

**用户正确指出**：比分应该从 API 拉，刷新按钮应该一键全更新。

**找到的免费资源**：`worldcup26.ir` (GitHub: `rezarahiminia/worldcup2026`)
- 100% 免费、open-source、专 WC 2026 设计
- REST API, JSON 格式
- 无需 API key（read access）
- 含 `home_score`, `away_score`, `home_scorers`, `away_scorers`, `finished` (TRUE/FALSE)
- 当前已有 2 场已结束比赛（MEX 2-0 RSA, KOR 2-1 CZE）

## 范围

### In Scope

1. **`src/data/worldcup_api.py`** 新模块
   - `fetch_games()` 拉取 `/get/games`
   - `parse_scorers(str)` 解析 `{"J. Quiñones 9',R. Jiménez 67'"}` JSON 串
   - `game_to_match_id(game, matches)` 用队名匹配我们的 match_id
   - `fetch_details_for_matches(matches)` 返回 `{match_id: details}` dict
   - 内存缓存 5 分钟（避免每次刷新都打 API）

2. **`src/data/details.py`** 改造
   - `merge_from_api(matches)` 合并 API 数据到 details
   - 现有 details.json 优先（手动 entries 保留）
   - 缺失的 match 用 API 数据填

3. **`/api/refresh` 升级**
   - 现在：只重拉 ICS
   - 以后：ICS + worldcup26.ir 比分，两边合并到 details.json
   - 返回 `{status, count, scores_updated, last_refresh}`

4. **前端状态显示**
   - 刷新按钮：显示 "上次更新: 3 分钟前"
   - 比分更新后，自动重渲染（refreshData 已调用 renderMatches）
   - live（进行中）状态也支持（API 应该有 live 数据）

5. **测试 + audit (8 闸)**

### Out of Scope

- ❌ Standings/teams/stadiums endpoints（已有 baires ICS 队数据）
- ❌ 自动轮询（refresh 仍然手动）
- ❌ 多个 API 源备份
- ❌ 国际化（API 数据是英文，已满足）

## 任务清单

| # | 任务 | 状态 |
|---|------|------|
| 1 | 写 `src/data/worldcup_api.py` | ⏳ |
| 2 | 改 `src/data/details.py` 加 `merge_from_api` | ⏳ |
| 3 | 改 `src/app.py` `/api/refresh` 同时拉 API | ⏳ |
| 4 | 加 last-refresh 时间戳 | ⏳ |
| 5 | 前端刷新按钮显示 "上次更新 X 分钟前" | ⏳ |
| 6 | pytest: worldcup_api parse_scorers | ⏳ |
| 7 | e2e: 刷新后比分显示 | ⏳ |
| 8 | audit 8 闸 | ⏳ |
| 9 | commit | ⏳ |

## 验收

### 必须

- [ ] `/api/refresh` 同时拉 ICS + worldcup26.ir
- [ ] 刷新后，赛程卡显示真实比分（2-0, 2-1）
- [ ] Modal 显示进球列表（球员 + 分钟）
- [ ] 队名匹配成功（Mexico/South Africa, etc.）
- [ ] scorers 解析正确
- [ ] 8 闸 closure audit 全过
- [ ] 122+ unit + 67+ e2e 全过

## 风险

| 风险 | 缓解 |
|------|------|
| API 慢/超时 | 5min 内存缓存，timeout 30s |
| 队名不匹配（"Korea Republic" vs "South Korea"）| 模糊匹配 / 手动 alias 表 |
| API 改 schema | 解析失败 graceful fall back（不显示分数）|
| 同时改 details.json 冲突 | 用户手动 entries 优先 |

## 决策记录

- **缓存策略**: 5 分钟内存缓存 + 启动时加载到 details.json（持久）
- **匹配规则**: 队名（EN）严格匹配
- **保留手动 entries**: 用户手填的 details 永远不被 API 覆盖
- **错误处理**: API 失败 → log + 用现有 details.json，不报错
- **不**实现自动轮询（保持手动刷新）
- **不**用 API-Football/football-data.org（要 key，免费额度小）
