# Plan 019 — 积分榜增加 GF / GA / GD 三列

> **状态**: `planned`
> **创建日期**: 2026-06-16
> **关联 plan**: [015-detail-page-content.md](015-detail-page-content.md)（modal 积分榜）

## 背景

2026-06-16 11:09，用户截图 G 组积分榜：4 队 1 分平局，4 队 MP/W/D/L/PTS 完全一致（同分无法区分）。用户问："API 数据有净胜球数据吗？或者进球失球数据，计算一下也行？"

## 根因

**API 已经有完整字段，是前端没渲染。**

### 数据流验证

1. `https://worldcup26.ir/get/groups` Group G 实际返回（2026-06-16 11:12 调）：
   ```json
   [
     {"team_id": "25", "mp": "1", "w": "0", "l": "0", "d": "1", "pts": "1", "gf": "1", "ga": "1", "gd": "0"},
     {"team_id": "26", "mp": "1", "w": "0", "l": "0", "d": "1", "pts": "1", "gf": "1", "ga": "1", "gd": "0"},
     {"team_id": "27", "mp": "1", "w": "0", "l": "0", "d": "1", "pts": "1", "gf": "2", "ga": "2", "gd": "0"},
     {"team_id": "28", "mp": "1", "w": "0", "l": "0", "d": "1", "pts": "1", "gf": "2", "ga": "2", "gd": "0"}
   ]
   ```
2. `src/data/worldcup_api.py:71 fetch_groups` 文档说返回 `{team_id, mp, w, d, l, pts, gf, ga, gd}`，实测一致
3. `src/data/worldcup_api.py:400 find_group_standings` 整 dict 透传（含 gf/ga/gd）
4. `src/app.py:106` 注入到 `m["standings"]` 时未做任何过滤
5. **前端 `src/static/js/main.js:910-921` 只渲染了 mp/w/d/l/pts 5 个字段，t.gf/t.ga/t.gd 拿到但没用**

### 排序兜底

`find_group_standings` 已经按 `pts desc, gd desc, gf desc` 排，**排序逻辑不用改**——只是排序结果用户看不到。同分时按 GD、GF 区分是有 FIFA 标准的，这样改完后排序差异就可见了。

## 方案

纯前端改动，< 50 行 JS。

### 1. 改 `src/static/js/main.js:renderModalStandings`

**当前 (L910-921):**
```js
const rows = match.standings.map((t, i) => {
    const rank = i + 1;
    const flag = _teamFlag(t.team_id);
    const name = _teamName(t.team_id);
    return `<tr class="standings-row">
        <td class="standings-rank">${rank}</td>
        <td class="standings-team"><span class="standings-flag">${flag}</span><span class="standings-name">${name}</span></td>
        <td class="standings-num">${_numOrZero(t.mp)}</td>
        <td class="standings-num">${_numOrZero(t.w)}</td>
        <td class="standings-num">${_numOrZero(t.d)}</td>
        <td class="standings-num">${_numOrZero(t.l)}</td>
        <td class="standings-num standings-pts"><strong>${_numOrZero(t.pts)}</strong></td>
    </tr>`;
}).join('');
```

**改为（加 3 列 + GD 加 `+`/`-` 号）:**
```js
const _gd = (v) => {
    const n = _numOrZero(v);
    if (n > 0) return `+${n}`;
    return String(n);
};
const rows = match.standings.map((t, i) => {
    const rank = i + 1;
    const flag = _teamFlag(t.team_id);
    const name = _teamName(t.team_id);
    return `<tr class="standings-row">
        <td class="standings-rank">${rank}</td>
        <td class="standings-team"><span class="standings-flag">${flag}</span><span class="standings-name">${name}</span></td>
        <td class="standings-num">${_numOrZero(t.mp)}</td>
        <td class="standings-num">${_numOrZero(t.w)}</td>
        <td class="standings-num">${_numOrZero(t.d)}</td>
        <td class="standings-num">${_numOrZero(t.l)}</td>
        <td class="standings-num">${_numOrZero(t.gf)}</td>
        <td class="standings-num">${_numOrZero(t.ga)}</td>
        <td class="standings-num standings-gd">${_gd(t.gd)}</td>
        <td class="standings-num standings-pts"><strong>${_numOrZero(t.pts)}</strong></td>
    </tr>`;
}).join('');
```

**thead (L929-936) 加 3 个 `<th>`:**
```html
<th class="standings-num">进 GF</th>
<th class="standings-num">失 GA</th>
<th class="standings-num">净 GD</th>
```

### 2. CSS（最小新增）

`src/static/css/main.css` 已有 `.standings-num` 共享样式。**只加 1 个新规则**让 GD 列正负数有视觉提示（参考 FIFA Live 标准）：

```css
/* Plan 019: GD column — green for positive, red for negative */
.standings-gd { font-variant-numeric: tabular-nums; }
.modal-standings-table td.standings-gd:not(:empty) { font-weight: 500; }
```

颜色用 CSS attribute selector 简化（不引入额外 class）：
```css
/* +GD green-ish, -GD red-ish — color:0 when equal */
.modal-standings-table td.standings-gd[data-pos="1"] { color: #2d7a3e; }
.modal-standings-table td.standings-gd[data-neg="1"] { color: #a83232; }
```
配合 JS 给 GD `<td>` 加 `data-pos` / `data-neg` 属性。

> **简化决策**：第一版只加 `+`/`-` 文本前缀，**不引入颜色**。颜色等用户反馈再迭代（避免一次性把 UX 推得过深）。

### 3. 验收（视觉 + 数据流）

- [ ] G 组 modal 积分榜 7 列 → **10 列**（# / Team / MP / W / D / L / GF / GA / GD / Pts）
- [ ] G 组实际数据（4 队 1 平）：Iran/NZ 各 gf=2 ga=2 gd=0（显示 `0`），Belgium/Egypt 各 gf=1 ga=1 gd=0（显示 `0`）
- [ ] 同一 modal 同时验证**净胜球负数 case**：等任何一场非 1-1 的 group 比赛（6/16 还有 10+ 场），刷新后看 GD 列显示 `-2` 这种格式
- [ ] 没有 standings 数据的比赛（淘汰赛前）：整个积分榜 section 仍 hidden（Plan 015 已有兜底）
- [ ] GF/GA 字段 API 返回 null/空 → `_numOrZero` 兜底显示 `0`（沿用现有 helper）

### 4. 测试

项目**没有 JS 测试框架**（tests/ 全是 Python）。本改动也不引入：
- `_gd()` helper 极简，`< 5 行`，静态可读
- 数据流已在 plan 根因段用 curl 实测过

**改完后做：**
```bash
cd /home/lqiu/.openclaw/workspace/2026worldCupCoverage
pytest -q  # Python 端回归，确保没改到 Python
```

## 范围

### In Scope

- 改 `src/static/js/main.js:renderModalStandings`（+ 3 列）
- 改 `src/static/js/main.js` thead 部分（+ 3 th）
- 改 `src/static/css/main.css`（+ 1 个新 class `.standings-gd` 字号/对齐）
- 跑 `pytest` 确认没改坏 Python 端

### Out of Scope

- 不改后端（数据流已通）
- 不改 `data/details.json` / `data/matches.json`
- 不改 `worldcup_api.py`（API 已有 gf/ga/gd）
- 不加 GD 颜色（V2 再说）
- 不加排序逻辑（后端已按 pts/gd/gf 排好了）

## 风险评估

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| 10 列在窄屏挤 | 低 | 中 | 现有 modal 是宽屏（详情弹窗），`.standings-num` 用 tabular-nums 自然紧凑 |
| GD 文本溢出 | 极低 | 低 | 范围 -50 ~ +50 已能 fit 4 字符 |
| API 某天去掉 gf/ga/gd 字段 | 极低 | 低 | `_numOrZero` 兜底为 0 |
| FIFA 改排序规则 | 极低 | 中 | 排序在后端，本次不动 |

## 影响

- 用户体验：**4 队同分现在能按 GD/GF 区分**（FIFA 标准）
- 性能：0 影响（纯前端字符串拼接）
- 数据：0 变化（用现有 API 字段）

## 不会误伤

- `src/app.py` 没改 → `/api/matches` 响应结构不变
- `worldcup_api.py` 没改 → 其他调用方（如果以后加）不受影响
- 没动 `_gd` helper 之外的任何现有 helper
- 没改 `_numOrZero`，沿用 Plan 015 的兜底语义
