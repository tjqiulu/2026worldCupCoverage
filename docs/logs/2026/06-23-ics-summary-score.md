# 2026-06-23 Bug 修复 — 已结束比赛 SUMMARY 解析失败

## 状态

Hotfix（小）：`src/data/ics_parser.py::_parse_summary` + `data/matches.json` 重新生成

## 触发

用户 09:01 反馈：赛程页只显示 6月23日（今天）及之后，6月11日-6月22日的 41 场比赛全部消失。

## 根因

baires/fifa-cal-2026 仓库对每场比赛的 `SUMMARY` 字段是**就地更新**的：

- 比赛前：`🇲🇽 Mexico vs 🇿🇦 South Africa`
- 比赛后：`🇲🇽 Mexico 2-0 🇿🇦 South Africa`

我们原 `_parse_summary` 的正则 `^(.+?)\s+vs\.?\s+(.+?)$` 只匹配 `vs` 形式。一旦比赛结束、ICS 同步过来，41 场已结束比赛就因为"team 解析失败"在 `_parse_vevent` 里被 `if len(teams) < 2: return None` 静默丢掉——`matches.json` 只剩 63 场（全部是 6月22日 21:00 UTC 之后还没踢的或刚踢的）。

数据源 ICS 本身没问题（`grep -c BEGIN:VEVENT` 始终是 104），丢失发生在解析层。

## 修复

### Fix 1: 兼容带比分 SUMMARY

`src/data/ics_parser.py::_parse_summary`：

- 用 `re.sub(r"\s+\d+\s*-\s*\d+\s+", " vs ", summary)` 把 `X 2-0 Y` 先归一为 `X vs Y`
- 再走原来的 vs 解析逻辑
- 兼容 `France 3 - 0 Iraq` 这种带空格的写法

### Fix 2: 重新生成 `data/matches.json`

调用 `fetch_ics(force=True)` + `parse_ics` + 写盘，验证：

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| 解析出比赛数 | 63 | **104** |
| 最早日期 | 2026-06-22 | 2026-06-11 |
| 最晚日期 | 2026-07-19 | 2026-07-19 |
| 日期分组数 | 24 | 35 |

### Fix 3: 5 个新 testcase

`tests/test_ics_parser.py::TestParseSummary` 加 5 个 case 锁定"比分格式"防回归：

- `test_with_score` — `Mexico 2-0 South Africa`
- `test_with_score_zero` — `Scotland 0-1 Morocco`
- `test_with_score_draw` — `Czech Republic 1-1 South Africa`
- `test_with_score_spaces_around_dash` — `France 3 - 0 Iraq`
- `test_with_score_multibyte_country` — `Bosnia & Herzegovina 1-0 Qatar`

## 验证

- `tests/test_ics_parser.py` 39/39 pass
- `tests/test_app.py` 5/5 pass
- `curl http://localhost:8766/api/health` → `{"matches_loaded":104,"status":"ok"}`
- 服务（pid 18085 `python3 -m src.app`）未重启，每次请求都重新读 `matches.json`，刷新即生效

## 决策记录

**为什么 baires 仓库要就地改 SUMMARY？** 因为它面向人——日历 app 显示 "Mexico vs South Africa" 没结果字样很丑。这个习惯我们早该预期到，初始设计没考虑"已结束比赛 SUMMARY 格式变化"是疏漏。

**未来防御**：
- 计划 038 候选：在 `fetch_ics` 后 + `parse_ics` 前，加一道"解析数量 vs VEVENT 数量"对账日志，如果 dropped > 阈值就发 warning。`fetch_ics` 已经知道 VEVENT 计数，对账成本零。

## 已知问题（与本次修复无关）

跑 `pytest tests/ --ignore=...` 仍有 5 个 fail（`test_bracket_pairings`、`test_details::test_real_data_*`、`test_worldcup_api::test_fetches_known_matches`），都是依赖外部 worldcup26.ir API + 实时数据的，跟本次修复无关，单独处理。
