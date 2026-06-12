# source-of-truth-and-precedence.md — 真相源优先级

> 多个数据源给出不同答案时，听谁的？

## 优先级表（从高到低）

| 优先级 | 源 | 例子 | 说明 |
|--------|----|------|------|
| 1 | 用户口头/书面明确指令 | chat 里的"用中文" | **最高**，永远 override 任何自动源 |
| 2 | FIFA 官方 / Bing sports 页面 | fifa.com、cn.bing.com/sportsdetails | 比分/赛程/场馆的官方真相 |
| 3 | baires/fifa-cal-2026 ICS | 196 份 ICS 文件 | 用户选定的赛程数据源 |
| 4 | `data/*.json` | `matches.json`、`details.json` | derived 数据，可重生成 |
| 5 | flag-icons CDN | cdn.jsdelivr.net | 运行时拉的外部资源，无本地副本 |

## 冲突时如何裁决

**新 vs 旧**：
- FIFA 官方 > 任何缓存（缓存是 derived）
- 新的 baires ICS > 旧的 `matches.json`（每次启动重新解析）
- 新的 user 指令 > 旧的 `details.json`（手动维护的部分）

**主源 vs 派生**：
- 任何 derived 数据（`data/*.json`）都可被主源覆盖
- 例：手改了 `matches.json` 但 baires 更新了 → 下次启动会覆盖手改内容，**这是预期行为**

**外部资源**：
- flag-icons CDN 失败时降级到 emoji 国旗或国家代码
- 永远不 hardcode 外部 URL 在代码里（用 config）

## 数据流

```
[baires ICS] ──parser──> [data/matches.json] ──loader──> [Flask] ──API──> [Frontend]
                                                                       │
[FIFA / Bing] ──manual──> [data/details.json] ────────────────────────>│
                                                                       │
[flag-icons CDN] ─────────────────────────────────────────────────────>│
```

`data/matches.json` 可被删（会重生成），`data/details.json` 是手写维护的（删了数据就丢了）。

## 责任划分

- **baires 负责**: 赛程基础数据（时间、对阵、轮次）
- **我们手写负责**: 进球详情（人名、时间）、场馆详情（容量、地址）
- **FIFA 官方负责**: 任何 baires 没覆盖的元数据（裁判、转播频道等可选）
