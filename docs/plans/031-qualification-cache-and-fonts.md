# Plan 031 — Qualification 落地 cache + bracket 字体更激进

> **状态**: proposed → completed (实施后回填)
> **创建日期**: 2026-06-19
> **触发**: 用户 17:15 反馈
> **关联 plan**: [029-bracket-qualified-teams.md](029-bracket-qualified-teams.md), [030-bracket-ux-fixes.md](030-bracket-ux-fixes.md)

## 问题

1. **bracket 字体还是小**：Plan 030 改 11→12px 不够，需要更大
2. **bracket 初次空白**：必须点刷新才显示

## 根因（AGE）

### 问题 1: 字号
- Plan 030 改了 11px→12px（差 1px）肉眼几乎看不出
- 需要更激进：12px→14-15px + font-weight 700

### 问题 2: 初次空白
- `/api/qualification` 每次 fetch 实时计算 12 组 × standings × best 3rd race
- 几百 ms + service worker cache-first 命中 stale main.js → 用户看到空白卡 loading
- **解药**：qualification 落地 JSON cache，秒读

## 修复

### Fix 1: qualification 落地 JSON
**新增文件** `data/qualification_cache.json`（auto-generated）：
```json
{
  "groups": {...},  // compute_per_group result per letter
  "best_3rd_race": {...},  // 跨组 race
  "generated_at": "2026-06-19T17:15:00+08:00",
  "version": 1
}
```

**修改** `src/app.py`：
- `/api/qualification` 优先读 `data/qualification_cache.json`（存在且版本对 → 直接返回）
- 不存在或版本旧 → 实时计算并写 cache
- `/api/refresh` 加一步：刷新后重算 qualification cache

### Fix 2: CSS 字号
- `.bracket-card` font-size 12px → **14px**
- `.bc-teams` font-size 13px → **15px**, font-weight 700
- `.bc-date` font-size 10px → **11px**
- grid minmax 110px → **120px** 让卡片更宽

## 范围

### In Scope
- L2 `src/app.py`：cache 读写 + refresh 触发
- L2 `src/data/qualification.py`：暴露 `compute_full_qualification()` helper（一次算出全部）
- L2 `src/static/css/main.css`：字号再调
- L4 写 log + commit

### Out of Scope
- ❌ qualification 算法
- ❌ 前端 JS
- ❌ UI（best 3rd race 区域留 Plan 032）