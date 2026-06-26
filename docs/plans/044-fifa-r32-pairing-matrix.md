# Plan 044 — FIFA 2026 R32 第 3 名配对矩阵 + 锁定算法修正

> **状态**: proposed → in-progress（用户口头确认"深修"视为草稿通过）
> **创建日期**: 2026-06-26
> **触发**: 12:14 用户截图 USA vs 3B/E/F/I/J，问"32 强对手应该已经能确定了"

## 背景

当前 `src/data/qualification.py:271` 的锁定判定要求 `min_pts > eighth_max + 3`（3 分缓冲），导致 **4 分全打完的 B/E/F/D 都没进 `locked_top8`**，I（0 分）也没进 `locked_bot4`。算法过于保守。

更深的：FIFA 2026 官方对 R32 第 3 名配对有完整矩阵（每个 1st 组对应的 3rd 备选集），按"最高 FIFA 优先级 + 最早分配"贪心匹配。当前 bracket UI 只把 `3B/E/F/I/J` 当原始字符串渲染，没解析。

**结论**：对 USA（1D）来说，按当前数据 B/E/F 锁定 4 分晋级，I 0 分锁定出局，D/L 都不在 USA 池中。FIFA 矩阵贪心匹配后 USA 的对手是 **🇧🇦 波黑**（3B）。

## 范围

### In Scope

1. **`src/data/qualification.py`**：放宽 `+ 3` 安全缓冲 → 改为 `min_pts > eighth_max`（精确判定）；保留 `count_better < 7` 跨组校验。
2. **新文件 `src/data/fifa_bracket_matrix.py`**：
   - `R32_3RD_OPPONENT_SETS`：1A-1L 各自的 3rd 备选组别集合（FIFA 官方矩阵，硬编码）
   - `resolve_r32_3rd_opponents(rankings, locked_3rds, eliminated_3rds)`：贪心配对
   - 处理"3rd 在多个 1st 备选集中"问题（按 FIFA 1A→1B→1D→1E→1G→1I→1K→1L 顺序分配）
3. **`src/app.py::api_matches`**：对 R32 比赛，识别 `1X vs 3Y/Z/...` 形态，调用 `resolve_r32_3rd_opponents` 计算对手，把 `r32_resolved_opponent` 字段挂到 match dict
4. **`src/static/js/main.js::resolveBracketPlaceholder`**：扩展解析支持"3X/Y/Z"形态的 3rd 对手
5. **`src/static/js/main.js::renderBracket`**：用 resolved 替换 placeholder 文本，locked/pending 视觉化
6. **新测试 `tests/test_fifa_bracket_matrix.py`**：覆盖
   - 当前场景（B/E/F/D locked → USA = 波黑）
   - I 锁定出局不影响结果
   - J 升级到 6 分时 USA 重新计算
   - 多 1st 共用 3rd 时的贪心顺序
7. **Plan + log**

### Out of Scope

- R16/QF/SF/Final 的对位（这些在 R32 踢完前无法确定）
- 1X vs 2Y 的 1st 对 2nd 配对（FIFA 矩阵已写死，不需解析）
- 3rd 对 3rd 的 R32（不存在）

## 设计

### FIFA 矩阵（硬编码）

从 `data/matches.json` 反向提取 1X vs 3Y/Z 形式（已验证，16 场 R32 中 8 场是 1st-vs-3rd）：

```python
R32_3RD_OPPONENT_SETS = {
    "A": {"C", "E", "F", "H", "I"},  # 1A (Mexico) vs ?
    "B": {"E", "F", "G", "I", "J"},  # 1B (Canada) vs ?
    "D": {"B", "E", "F", "I", "J"},  # 1D (USA) vs ?
    "E": {"A", "B", "C", "D", "F"},  # 1E (Germany) vs ?
    "G": {"A", "E", "H", "I", "J"},  # 1G vs ?
    "I": {"C", "D", "F", "G", "H"},  # 1I vs ?
    "K": {"D", "E", "I", "J", "L"},  # 1K vs ?
    "L": {"E", "H", "I", "J", "K"},  # 1L vs ?
}
# 1C / 1F / 1H / 1J 玩 1st vs 2nd，不在矩阵
```

### 贪心算法

```python
def resolve_r32_3rd_opponents(rankings, locked_3rds, eliminated_3rds):
    """贪心：按 FIFA 1A→1B→1D→1E→1G→1I→1K→1L 顺序，
    把每个 1st 备选集中 FIFA 优先级最高的、未分配的 3rd 分给它。
    
    Returns: {
        "USA": {"team_id": "6", "name_zh": "波黑", "state": "locked"|"pending"},
        "Mexico": {"team_id": "23", "name_zh": "瑞典", "state": "locked"},
        ...
    }
    """
    BRACKET_ORDER = ["A", "B", "D", "E", "G", "I", "K", "L"]
    assigned = {}  # group_letter -> team dict
    used_team_ids = set()
    
    # 用 locked_3rds 优先分配（不会变）
    pending_pool = [r for r in rankings if r["team_id"] not in locked_3rds 
                                        and r["team_id"] not in eliminated_3rds]
    
    for group_letter in BRACKET_ORDER:
        allowed = R32_3RD_OPPONENT_SETS[group_letter]
        # 在 allowed 集合中找 FIFA 优先级最高的、未分配的 3rd
        # 优先从 locked 池中取（更稳定）
        for source in (locked_3rds, pending_pool, rankings):
            for r in source:
                if r["group"] in allowed and r["team_id"] not in used_team_ids:
                    assigned[group_letter] = r
                    used_team_ids.add(r["team_id"])
                    break
            if group_letter in assigned:
                break
        # 标 state: locked or pending
        if group_letter in assigned:
            tid = assigned[group_letter]["team_id"]
            state = "locked" if tid in locked_3rds else "pending"
            assigned[group_letter]["state"] = state
    
    return assigned
```

### 验证（当前数据）

```
rankings: 1=3F(瑞典,4pt), 2=3E(厄瓜多尔,4pt), 3=3B(波黑,4pt), 4=3D(巴拉圭,4pt),
          5=3L(克罗地亚,3pt,mp=2/3), 6=3A(韩国,3pt), 7=3J(阿尔及利亚,3pt,mp=2/3),
          8=3C(苏格兰,3pt), 9-12=排除
locked_3rds = {F, E, B, D}  (4 分全打完)
eliminated_3rds = {I}  (0 分)

按 BRACKET_ORDER 分配：
- A: 备选 {C,E,F,H,I}. 锁定 4pt 中: F(瑞典) 命中 → 1A(Mexico) = 瑞典 ✅ locked
- B: 备选 {E,F,G,I,J}. 锁定: E(厄瓜多尔) → 1B(Canada) = 厄瓜多尔 ✅ locked
- D: 备选 {B,E,F,I,J}. 锁定: B(波黑) → 1D(USA) = 波黑 ✅ locked
- E: 备选 {A,B,C,D,F}. 锁定: D(巴拉圭) → 1E(Germany) = 巴拉圭 ✅ locked
- G: 备选 {A,E,H,I,J}. 锁定无. pending 池: J(阿尔及利亚) 命中 → 1G = 阿尔及利亚 ⚠️ pending
- I: 备选 {C,D,F,G,H}. 锁定: D 已用. pending: 无. fallback: C(苏格兰) → 1I = 苏格兰 ⚠️ pending
- K: 备选 {D,E,I,J,L}. 锁定: D,E 已用. pending: L(克罗地亚) → 1K = 克罗地亚 ⚠️ pending
- L: 备选 {E,H,I,J,K}. 锁定: E 已用. pending: J 已用. fallback: H/K (均不在 top 8)
   → 1L = None（暂无）
```

**关键结论**：USA 对手是 **🇧🇦 波黑**（locked）。

## 前端渲染

```js
// 新函数：在 resolveBracketPlaceholder 已有逻辑上加 3X/Y/Z 处理
function resolveR32ThirdOpponent(placeholder) {
    if (!allR32Resolution) return null;
    // placeholder = "3B/E/F/I/J" → 解析出最高优先级组别 → 查 allR32Resolution
    const m = placeholder.match(/^3([A-L])(\/[A-L])*$/);
    if (!m) return null;
    const groups = placeholder.split('/');
    // 按 FIFA 矩阵：USA 的对手 = 在 groups 中且 assigned 给 USA 的那个
    // ... 实际上后端已经算好了，前端只需从 allR32Resolution["USA"] 取
}
```

更简单：后端把 `r32_resolved_opponent` 字段直接挂到 R32 match dict，渲染时优先用。

```js
function renderBracketCard(m) {
    const opponentText = m.r32_resolved_opponent 
        ? `${m.r32_resolved_opponent.name_zh} (${m.r32_resolved_opponent.state === 'locked' ? '✅' : '⏳'})`
        : m.away.name;  // fallback 到原始 "3B/E/F/I/J"
}
```

## 验收

- [x] Plan 文件
- [x] qualification.py 修过：+ 3 → 0，B/E/F/D 入 locked_top8，I 入 locked_bot4
- [x] fifa_bracket_matrix.py 新建
- [x] api_matches 挂 r32_resolved_opponent
- [x] main.js 渲染 resolved opponent
- [x] 测试：当前数据 → USA = 波黑
- [x] pytest 通过
- [x] live server 刷新 → bracket UI 显示 🇧🇦 波黑
- [x] git commit + push
- [x] log

## 风险

- **FIFA 矩阵是硬编码**：未来 FIFA 改规则要更新 `R32_3RD_OPPONENT_SETS` dict。可能性极低（2026 还没开赛，已公布的官方对阵不变）。
- **3 个 R32 比赛当前 resolve 出 None（pending）**：1G/1I/1K/1L 还不能 100% 确定。UI 用"⏳"图标 + tooltip 说明原因。
- **`count_better < 7` 跨组校验**：L/J 还在 pending，校验会有边界。Plan 内加 e2e 测试覆盖。
