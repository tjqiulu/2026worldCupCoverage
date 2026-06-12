# Plan 004 — Flags + Country Names

> **状态**: `proposed` → 用户"继续"批准 → `planned` → 执行 → `completed`
> **创建日期**: 2026-06-12
> **关联 plan**: [003-bracket-view.md](003-bracket-view.md) (前置)
> **下一 plan**: 005 (详情弹窗) 或 006 (双语 UI)

## 背景

数据层 + list + bracket 视图都跑通了。但视觉上还是"裸队名"——没有国旗，没有中文译名，对国内用户不友好。

这是 P0-004 backlog 项，是 MVP 视觉的核心。

## 范围

### In Scope

1. **国家映射表** (`data/countries.json`)
   - 48 支参赛队，每队包含：
     - `name_en`（与 baires ICS 一致）
     - `name_zh`（中文译名）
     - `code_iso`（ISO 3166-1 alpha-2，给 flag-icons 用）
     - `code_fifa`（FIFA 3 字母码，参考用）
   - 2 个特殊队（England/Scotland）用 sub-national flag：gb-eng / gb-sct
   - 占位符（1E/2A/W86/L101）不进表，由前端识别后直接显示

2. **数据层 enrich**
   - `src/data/countries.py` 提供 lookup
   - `src/app.py` 在返回 matches 前注入 `name_zh`/`code_iso`/`code_fifa`
   - `data/matches.json` 不变（derived 字段不进文件）

3. **前端展示**
   - 引入 flag-icons 6.6.6 CSS via CDN
   - 队名前显示小国旗
   - 已知国家：🇲🇽 墨西哥 Mexico（zh 在前，en 在后）
   - 占位符（1E/W86 等）：原样显示，无国旗
   - 卡片和小屏幕都适配

4. **测试**
   - 新增 `test_countries.py`：lookup 48 队、缺失报错、enrich 逻辑

### Out of Scope

- ❌ 比赛详情弹窗（Plan 005）
- ❌ 顶部语言切换器（Plan 006：双语 UI）
- ❌ 球队详情页 / 关注球队
- ❌ 完整 i18n（先把队名搞定，UI 文案留 Plan 006）

## 任务清单

| # | 任务 | 状态 |
|---|------|------|
| 1 | 建 `data/countries.json`（48 队） | ⏳ |
| 2 | 写 `src/data/countries.py` | ⏳ |
| 3 | 改 `src/app.py` 调用 enrich | ⏳ |
| 4 | `index.html` 引入 flag-icons CSS | ⏳ |
| 5 | `main.css` 加 `.fi` 样式 | ⏳ |
| 6 | `main.js` 渲染 flag + 双语队名 | ⏳ |
| 7 | 写 `tests/test_countries.py` | ⏳ |
| 8 | 跑全部测试 | ⏳ |
| 9 | 烟测 | ⏳ |
| 10 | commit | ⏳ |

## 验收

### 必须

- [ ] 48 队映射全有
- [ ] 卡片显示国旗 + 中文 + 英文（如 `🇲🇽 墨西哥 Mexico`）
- [ ] 占位符原样显示，无国旗
- [ ] 49+ pytest 全过（含新增）
- [ ] 4 端点仍 200

### 应该

- [ ] 国旗清晰、与队名对齐
- [ ] flag-icons CDN 失败时降级（CSS 不加载，队名仍显示）
- [ ] 国家表缺失某队时 enrich 不抛异常（留 None，前端兜底）

## 风险

| 风险 | 缓解 |
|------|------|
| 48 队中文译名不一致 | 我手维护（标准译法），用户后审 |
| flag-icons 不支持 sub-national（gb-eng） | 试 gb-eng，回退到 gb |
| CDN 失败 | 加 crossorigin + 失败兜底（无国旗） |
| 任何匹配不到的国家 | lookup 返回 None，enrich 跳过，前端显示原名 |

## 决策记录

- **flag-icons 6.6.6** —— 最成熟的国旗 SVG 库，CDN 稳定
- **不下载到本地** —— 一次会话足够，CDN 更省事
- **不写 i18n JSON** —— 队名双语直接在 countries.json，UI 文案留 Plan 006
- **占位符特殊处理** —— 1E/W86/L101 既是"分组种子"也是"未知队伍"标记，前端识别为 placeholder 不查表
- **不破坏 matches.json** —— enrich 是运行时计算，不污染 derived 数据
