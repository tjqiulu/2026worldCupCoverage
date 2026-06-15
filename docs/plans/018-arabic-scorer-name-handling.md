# Plan 018 — 阿拉伯文进球者名字处理（Belgium vs Egypt 脏数据）

> **状态**: `planned`（待 user 决定方案）
> **创建日期**: 2026-06-16
> **关联 plan**: [017-incomplete-details-api-override.md](017-incomplete-details-api-override.md)（覆盖策略）, [012-worldcup26-api-integration.md](012-worldcup26-api-integration.md)（API 集成）

## 背景

2026-06-16 07:08，用户截图反馈：比利时 1-1 埃及 详情页的进球者显示为阿拉伯文：

```
进球 GOALS
比利时  محمد هانی                       66'
埃及    امام آشور                       19'
```

## 根因

`data/details.json` 里 `fifa-wc-2026-323786f24db4@worldcup-calendar` 这条 entry 的 `goalscorers[].player` 字段直接是阿拉伯文，UI 渲染时浏览器 font fallback 到系统阿拉伯文字体。

### 1. 数据来源（已查清）

直接调 `https://worldcup26.ir/get/games` 验证：

```json
{
  "home_team_name_en": "Belgium",
  "away_team_name_en": "Egypt",
  "home_score": "1",
  "away_score": "1",
  "home_scorers": "{\"محمد هانی 66'\"}",
  "away_scorers": "{\"امام آشور 19'\"}",
  "group": "G",
  "matchday": "1",
  "finished": "TRUE"
}
```

### 2. 全局排查

调 API 拉全部 15 场已结束比赛，过滤进球者含非 ASCII 字符的：

| 比赛 | home_scorers | away_scorers | 是否纯 Arabic |
|------|--------------|--------------|---------------|
| South Korea vs Czech | I.B. Hwang, H.G. Oh | L. Krejčí | 否（带重音） |
| USA vs Paraguay | D. Bobadilla, F. Balogun, ... | Maurício | 否 |
| Sweden vs Tunisia | Y.Ayari, A.Isak, V.Gyökeres, ... | O. Rekik | 否（带重音） |
| Mexico vs South Africa | J. Quiñones, R. Jiménez | null | 否 |
| Brazil vs Morocco | V. Júnior | I. Saibari | 否 |
| Canada vs BIH | C. Larin | Jovo Lukić | 否 |
| **Belgium vs Egypt** | **محمد هانی** | **امام آشور** | **是** |

**结论**：Belgium vs Egypt 是**唯一**纯阿拉伯文 case；其它比赛即使有重音也用 Latin 字母。

### 3. 数据脏在哪一层

世界主流比利时国脚（卢卡库、德布劳内、Trossard、De Ketelaere 等）没有 "Mohamed" 或 "Imam" 名字。而：

- **Mohamed Hany** = 埃及国脚（Al Ahly 前锋）
- **Imam Ashour** = 埃及国脚（Al Ahly 中场）

**两个进球者都是埃及球员**，但被 API 错分配到了不同队。这意味着 worldcup26.ir 这场比赛的 scorer 字段**底层数据就是脏的**（可能是占位/测试数据，或录入错误）。这不是"API 没给 transliteration"的问题——是**这场比赛本身没有正确的进球者信息**。

### 4. 现状限制

Plan 017 的 `_is_incomplete` 判定是 `len(goals) < home+away`。Belgium vs Egypt 现在 goalscorers 数=2 = 1+1，判定"完整"，API 已成功覆盖，**Plan 017 救不了这个**。

`_corrections` 锁机制（参考 965e9ac9ce78 的 Larin 78' 修正）也救不了——因为它只在"已存在手维护条目"时生效，且 Plan 017 之后手维护会被 API 覆盖。

## 待选方案

### 方案 A：手维护覆盖 + `_corrections` 锁

**操作**：
1. 在 `data/details.json` 里把这条改成 Latin 转写 + 修正主客归属：
   ```json
   {
     "status": "final",
     "score": {"home": 1, "away": 1},
     "goalscorers": [
       {"player": "TBD", "minute": 66, "stoppage": null, "type": null, "team": "home", "_note": "worldcup26.ir 给了埃及球员 Mohamed Hany 给比利时队，疑似数据错误，待用户确认真实进球者"},
       {"player": "Imam Ashour", "minute": 19, "stoppage": null, "type": null, "team": "away"}
     ],
     "_corrections": {"_protected_from_api": true, "_reason": "worldcup26.ir scorer 字段疑似脏数据（两进球者均为埃及球员名字）"}
   }
   ```
2. `_corrections._protected_from_api` 标志位需要 Plan 017 之后新增代码支持

**优点**：立竿见影，UI 立刻显示 Latin 文
**缺点**：
- 66' 主队进球者**根本不知道是谁**（真实比利时国脚中没有匹配），写 TBD 不诚实
- 引入新的 `_protected_from_api` 标志位，需要改 `src/data/details.py` merge 逻辑 + 加测试
- 脏数据认知被锁在 `data/details.json` 里，下次有人查 API 又会困惑

### 方案 B：API 拉取层做 Arabic → Latin transliteration

**操作**：在 `src/data/worldcup_api.py:parse_scorers` 或 `_parse_scorer_strings` 之后，对 player 字段跑 transliteration（如 `arabic-reshaper` + `transliteration` 库，或手写映射表）。

**优点**：通用，所有未来 Arabic 国家比赛都受益
**缺点**：
- transliteration 库选型工作量大，Arabic 名字转写规则不统一（محمد→Mohamed/Mohammed/Muhammad 都对）
- **修不了根因**：transliteration 后你会得到 "Mohamed Hany" 给比利时、"Imam Ashour" 给埃及，但实际两人都不是比利时人，UI 看起来"对"但数据是错的
- 工程量大，不符合"数据脏了先别动 src/"的 plan-first 原则

### 方案 C：UI 层做 fallback 显示（最小改动）

**操作**：在 `src/templates/` 的进球列表渲染处加一段 JS：
- 如果 `player` 字段含非 ASCII，先尝试调一个本地 transliteration 端点
- 实在不行就显示 ⚠️ 图标 + tooltip "数据源未提供英文名"

**优点**：不改数据层，不动 src/data/，纯前端
**缺点**：
- transliteration 还是要做（方案 B 的工作量）
- "⚠️ 提示"会让用户每次都看到脏数据标记，治标不治本

### 方案 D：暂时不修，记到 backlog 当 P2 bug

**操作**：把 Belgium vs Egypt 的脏数据现象记到 `docs/backlog/` 当 P2-XXX，等 6/17 后更多比赛结束后回头看是不是单例 bug（如果其它 Arabic 国家比赛也是 Arabic-only，可能就是 API 长期行为需要适配；如果只是这一场，可能就是数据录入错误）。

**优点**：不引入半成品改动，符合 plan-first
**缺点**：用户刷新看一次脏数据就要纠结一次

## 推荐

**方案 D 起步 + 方案 A 兜底**：
1. **今天**先方案 D：把这条数据加到 `docs/backlog/README.md` 的 P2 段，等比赛日推进（6/16 还有很多场）后再回看
2. **如果** 6/16 结束后发现 Arabic-only 仍是孤例 → 走方案 A：手维护 + 新增 `_protected_from_api` 标志位 + 测试
3. **如果** 6/16 结束后发现 Arabic 国家比赛普遍 Arabic-only → 走方案 B：在 API 拉取层做 transliteration

理由：根因是"数据脏"而不是"缺转写"，过早做方案 A/B 都是在掩盖脏数据；让数据自曝其短（多观察几天）再做决策更稳。

## 待用户决策

1. 走推荐（方案 D → 看几天）？
2. 还是现在就 A（手动改 + 加 `_protected_from_api` 标志）？
3. 还是 B（加 transliteration，赌这是个普遍问题）？
4. 还是 C（前端兜底 + tooltip）？

## 影响

不管选哪个：
- 都需要在 `docs/logs/2026/06-16.md` 记 Decision Log
- 如果动 `data/details.json`，AGENTS.md 红线要求注明来源（写 `_note` / `_corrections._source` 字段）
- 如果动 `src/`，按 AGENTS.md 要先有 plan（本文件即是）

## 调研证据

```bash
# 2026-06-16 07:13 调用 worldcup26.ir/get/games 真实响应
curl -A "wc2026-coverage/0.1" https://worldcup26.ir/get/games | jq '.games[] | select(.home_team_name_en=="Belgium" and .away_team_name_en=="Egypt")'
# 返回 home_scorers='{"محمد هانی 66\'"}', away_scorers='{"امام آشور 19\'"}'

# 拉所有已结束比赛 + 过滤非 ASCII
# 结果：Belgium vs Egypt 是唯一纯 Arabic case
```
