# Plan 033 — Bracket 卡片重叠 + loadQualification 同步化

> **状态**: proposed
> **创建日期**: 2026-06-19 22:33
> **触发**: 用户 22:32 反馈
> **关联 plan**: [032-bracket-bing-redesign.md](032-bracket-bing-redesign.md), [031-qualification-cache-and-fonts.md](031-qualification-cache-and-fonts.md)

## 问题

1. **载入页面，bracket 初次空白**：reload 仍可能空（qualification 未就位时 render）
2. **卡片纵向重叠**：grid row 110px 不足
3. **水平滚动条**：min-width 1100px 超过 viewport

## 根因

### 问题 1
- `loadMatches()` 流程：
  ```js
  await loadTeams();
  loadQualification();   // fire-and-forget，不 await
  renderBracket(allMatches);
  ```
- bracket 渲染时 allQualification 还是 null → resolveBracketPlaceholder() 都返回 null → 全部按 placeholder 渲染
- 即使 qualification 永远失败（cache miss + 实时计算失败），bracket 也应该能显示

### 问题 2
- grid `grid-template-rows: repeat(8, 110px)`
- 卡片实际高度 = padding(20) + 内容(85) ≈ 105px
- gap 8px → 113px / row 110px → 视觉重叠 3-5px

### 问题 3
- `.bracket-mirror` `min-width: 1100px`
- viewport < 1100 → 横向滚动
- body max-width 1400px → bracket 容器有 max-width 但 grid 有 min-width → 滚动

## 修复

### Fix 1: await loadQualification
```js
await loadTeams();
await loadQualification();  // 同步等待
renderBracket(allMatches);
```

并加 try/catch 让 qualification 失败不影响 bracket 渲染：
```js
try { await loadQualification(); } catch (e) { console.warn(...); }
```

### Fix 2: grid row 调整
- `grid-template-rows: repeat(8, 110px)` → `repeat(8, 100px)`
- 卡片 min-height 96px → 92px
- 减小 padding 10px→8px

### Fix 3: 去掉水平滚动
- `.bracket-mirror` min-width 1100px → 0
- `.bracket-labels-mirror` min-width 1100px → 0
- 容器加 `overflow-x: hidden` 或 `width: 100%` 强制 fit viewport

## 范围

### In Scope
- L2 `src/static/js/main.js` await loadQualification
- L2 `src/static/css/main.css` grid row + min-width 调整
- L5 新增 `tests/test_frontend_init.py`：mock loadQualification 验证
- L4 commit + log

### Out of Scope
- ❌ 卡片内容
- ❌ 后端
- ❌ 算法