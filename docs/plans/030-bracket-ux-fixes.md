# Plan 030 — Bracket CSS 调整 + Modal placeholder resolve

> **状态**: proposed → completed (实施后回填)
> **创建日期**: 2026-06-19
> **触发**: 用户 16:56 截图反馈
> **关联 plan**: [029-bracket-qualified-teams.md](029-bracket-qualified-teams.md)

## 问题

1. **Bracket 字体偏小 + 显示不全**：R32 卡片太窄，文字被截断
2. **Modal 没显示国家名 + 国旗**：同 Plan 029 根因（`renderModalTeam()` 没用 `resolveBracketPlaceholder()`）

## 根因（AGE）

### 问题 1
- `.bracket-card` 在 9 列 grid 里宽度受限
- `.bc-team` font-size 0.85em 太小
- 双语显示（zh + en）挤爆

### 问题 2
- `renderModalTeam()` (main.js:716) 只检查 `team.code_iso`
- R32 卡片 `m.home.name = "1A"` 字符串占位符无 code_iso → placeholder 分支
- 跟 Plan 029 同样的根因，但 modal 是另一个 surface

## 修复

### Fix 1: bracket CSS
- 调大 `.bracket-card` font-size（0.85em → 1em 或 1.05em）
- 调小 grid columns min-width（让卡片自适应）
- `.bc-team .team-name .zh` 增加 max-width + ellipsis overflow
- 整体 spacing 调整

### Fix 2: modal placeholder resolve
- `renderModalTeam()` 增加接受已 resolve 的 team 对象
- 在 modal open click handler 里调用 `resolveBracketPlaceholder()`（Plan 029 helper）
- 如果 resolve 到 locked team，传入真实 team info
- 否则保留 placeholder

## 范围

### In Scope
- L2 `src/static/css/main.css` 调整 bracket 样式
- L2 `src/static/js/main.js` 改 `renderModalTeam()` + modal open handler
- L4 写 log + commit

### Out of Scope
- ❌ Plan 029 的 best 3rd race UI 区（保留 Plan 030 后续）
- ❌ FIFA 配对表