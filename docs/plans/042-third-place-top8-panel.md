# Plan 042 — 第 3 名晋级 Top 8 面板

> **状态**: proposed → in-progress（用户口头要求 "在赛程表的最后显示一下这个top8列表，点刷新能刷新数据" 视为 plan 草稿通过）
> **创建日期**: 2026-06-26
> **关联**: Plan 029 (qualification 状态) + Plan 031 (qualification cache API)

## 背景

`/api/qualification` 已能返回 `best_3rd_race.rankings`（12 支第 3 名按 FIFA 顺序排名）。bracket tab 已经在每张 R32 卡片里把 `1A/2B/3X` 解析成实队，但**没有一站式的 top 8 视图**。

用户（飞书群）2026-06-26 09:37 提出：在赛程表最后面显示一下 top 8 列表，刷新能拉新数据。

## 范围

### In Scope

1. **HTML**（`src/templates/index.html`）：在 `</main>` 与 `<footer>` 之间新增一个 `<section id="third-place-top8-panel">`。
2. **CSS**（`src/static/css/main.css`）：新增 top 8 列表样式——表格化布局，第 1-8 名绿色高亮（晋级），9-12 名灰底（淘汰）。
3. **JS**（`src/static/js/main.js`）：
   - 新增 `renderThirdPlaceTop8()`，从 `allQualification.best_3rd_race.rankings` 读
   - 在 `loadMatches()` 末尾 `loadQualification()` 成功后调用
   - 刷新时已由 `loadMatches()` 重跑覆盖，无需额外改 `refreshData()`
4. **测试**（`tests/test_app.py` 或新建 `test_third_place_top8.py`）：mock `/api/qualification` 响应，验证渲染函数输出 HTML 包含 12 行 + 8 晋级 + 4 淘汰。

### Out of Scope

- 不改 API（`/api/qualification` 已存在并返回所需数据）
- 不改后端计算逻辑
- 不做 i18n 切换面板（用现有双语并列）
- 不做 R32 对阵搭配（bracket 已有）

## 设计

### 位置

`</main>` 之后、`<footer>` 之前，独立 `<section>`，**不依赖任何 tab**——Matches 和 Bracket 都能看到。

### 视觉

```
┌────────────────────────────────────────────────────────────────────┐
│  🏆 小组赛第 3 名晋级 Top 8 — Best 3rd Race (12 → 8 advance)         │
│  数据更新于 2026-06-26 01:11 UTC                                   │
├────┬────┬──────────────┬──────┬────┬────┬────┬────┬─────┬──────────┤
│ #  │ 组 │ 球队         │ 场   │ 胜 │ 平 │ 负 │ 净 │ 分 │ 状态     │
├────┼────┼──────────────┼──────┼────┼────┼────┼────┼─────┼──────────┤
│ 1  │ F  │ 🇸🇪 瑞典      │ 3    │ 1  │ 1  │ 1  │ 0  │ 4  │ ✅ 晋级  │
│ 2  │ E  │ 🇪🇨 厄瓜多尔   │ 3    │ 1  │ 1  │ 1  │ 0  │ 4  │ ✅ 晋级  │
│ ...│    │              │      │    │    │    │    │   │          │
│ 8  │ C  │ 🏴 苏格兰      │ 3    │ 1  │ 0  │ 2  │ -3 │ 3  │ ✅ 晋级  │
├────┼────┼──────────────┼──────┼────┼────┼────┼────┼─────┼──────────┤
│ 9  │ H  │ 🇨🇻 佛得角     │ 2    │ 0  │ 2  │ 0  │ 0  │ 2  │ ❌ 淘汰  │
│ ...│    │              │      │    │    │    │    │   │          │
└────┴────┴──────────────┴──────┴────┴────┴────┴────┴─────┴──────────┘
```

- 1-8 名：浅绿底 + ✅ 晋级
- 9-12 名：浅灰底 + ❌ 淘汰
- 表格在窄屏自动横向滚动（保持桌面看板主要使用场景）

### 状态处理

- `allQualification === null` → 显示 "加载中…"
- `best_3rd_race.rankings` 为空 → 显示 "暂无数据"
- 网络失败 → 静默（不影响主界面；console.warn 已足够）

## 验收

- [x] Plan 文件落地
- [x] HTML section 出现
- [x] CSS 表格化 + 颜色对比
- [x] JS 渲染逻辑 + 刷新触发
- [x] pytest 通过
- [x] git commit
- [x] log 更新

## 风险

- 极低：纯前端 + 已存在数据源，不改后端，不改 schema
