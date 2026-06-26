# backlog/README.md — 待办池

> 按优先级 P0/P1/P2 排序。每个条目包含：描述、验收、关联 plan、状态。

## 状态: open / in-progress / done / blocked / dropped

## 迁移路线图

按 AGE 方法论，本项目分 4 阶段：

| 阶段 | 状态 | 内容 | 完成 plan |
|------|------|------|----------|
| **Phase 1** | ✅ done | 项目骨架（AGENTS.md + context + 目录） | 001 |
| **Phase 2** | ✅ done | ICS parser + Flask skeleton + 基础页面 | 002 |
| **Phase 3** | ✅ done | 国旗 + 详情弹窗 + 双语并列 | 004 + 009 + 010 |
| **Phase 4** | ✅ done | 桌面全屏 + 刷新 + 端到端验收 | 013 + 016 + 021 (Render) |
| **Phase 5** | ✅ done | 对阵表 + 第3名 Top 8 + 状态锁 | 003 + 029 + 031 + 041 + 042 |

**当前状态**：所有 MVP + V1.1 功能已完成（44 个 plan 落地的成果）。后续是 polish + V2 探索。

## P0 — 必须（MVP）

### P0-001: 初始骨架（Plan 001）
- **状态**: ✅ done
- **Plan**: [001-initial-skeleton.md](../plans/001-initial-skeleton.md)
- **完成日期**: 2026-06-12

### P0-002: ICS parser
- **状态**: ✅ done
- **Plan**: [002-ics-parser-and-flask.md](../plans/002-ics-parser-and-flask.md) + [037](../plans/037-...md) (post-match SUMMARY fix)
- **完成日期**: 2026-06-12（原始）+ 2026-06-23（hotfix）

### P0-003: Flask skeleton + 基础页面
- **状态**: ✅ done
- **Plan**: [002-ics-parser-and-flask.md](../plans/002-ics-parser-and-flask.md)
- **完成日期**: 2026-06-12
  - pytest 覆盖 GET `/` 和 `/api/matches`

### P0-004: 国旗 + 队名 + 比分
- **状态**: ✅ done
- **Plan**: [004-flags-and-country-names.md](../plans/004-flags-and-country-names.md) + 后续 8 (England/Scotland flag) + 19 (standings columns)
- **完成日期**: 2026-06-13

## P1 — 应该做（V1.1）

### P1-001: 详情弹窗
- **状态**: ✅ done
- **Plan**: [009-detail-modal.md](../plans/009-detail-modal.md) + [010-match-details-scores-goalscorers.md](../plans/010-match-details-scores-goalscorers.md) + [015](../plans/015-...)
- **完成日期**: 2026-06-15

### P1-002: 双语 UI
- **状态**: 🟡 调整（改双语并列代替切换器，见 requirements § F6）
- **Plan**: [004-flags-and-country-names.md](../plans/004-flags-and-country-names.md)

### P1-003: 桌面浏览器全屏
- **状态**: ✅ done
- **Plan**: [013-desktop-launcher.md](../plans/013-desktop-launcher.md)
- **完成日期**: 2026-06-16

### P1-004: 刷新按钮
- **状态**: ✅ done
- **Plan**: [002](../plans/002-ics-parser-and-flask.md) + [016-widget-and-refresh-fix.md](../plans/016-widget-and-refresh-fix.md)
- **完成日期**: 2026-06-12（原始）+ 2026-06-16（修过几次刷新行为）

## P2 — 以后做（V1.2+）

### P2-001: 暗色/亮色模式
- **状态**: ❌ dropped
- **不做的理由**: 番茄红主色 + 浅色背景效果最好，浏览器原生滚动条已随系统变暗

### P2-002: 桌面通知（开赛前 N 分钟）
- **状态**: ❌ dropped
- **不做的理由**: 桌面 PWA 通知 API 受限，本项目不是 “提醒型” 产品，用户主动开页面看即可

### P2-003: 关注球队高亮
- **状态**: ❌ open
- **描述**: 用户飞书记录中提到自选股（康方、诺诚健华、中芯国际、瑞芯微、深信服、百度…）。可考虑在「下场比赛」卡片加自选股高亮。
- **验收**: 在 localStorage 保存球队 id 列表，Top 8 / Bracket 面板中高亮这些队的行

### P2-004: 下一场比赛倒计时
- **状态**: ✅ done
- **Plan**: [010](../plans/010-match-details-scores-goalscorers.md) + [040](../plans/040-...)（widget 模式 countdown）

### P2-005: 比赛集锦/视频链接
- **状态**: ❌ open
- **描述**: worldcup26.ir 详情页有视频链接，但需要发现路径

### P2-006: 移动端 PWA
- **状态**: ✅ done
- **Plan**: [014-pwa-progressive-web-app.md](../plans/014-pwa-progressive-web-app.md) + [024-pwa-activation.md](../plans/024-pwa-activation.md)

### P2-007: 多赛事支持（欧冠、欧洲杯等）
- **状态**: ❌ dropped
- **不做的理由**: 项目是个人世界杯玩具，不在多赛事路线上

### P2-008: worldcup26.ir 阿拉伯文进球者名字（Belgium vs Egypt 脏数据）
- **状态**: open
- **创建日期**: 2026-06-16
- **Plan**: [018-arabic-scorer-name-handling.md](../plans/018-arabic-scorer-name-handling.md) + [026-arabic-scorer-transliteration.md](../plans/026-arabic-scorer-transliteration.md)
- **描述**: worldcup26.ir API 对某些比赛（目前发现 Belgium vs Egypt match_id `fifa-wc-2026-323786f24db4`）返回的 `home_scorers` / `away_scorers` 是纯阿拉伯文，且疑似字段错位（两进球者 Mohamed Hany、Imam Ashour 都是埃及 Al Ahly 球员，被错分配到不同队）
- **验收**:
  - 6/16 比赛日结束后，重新跑全量排查（`fetch /get/games` 过滤非 ASCII scorer 名字）
  - 如果 Arabic-only 仍只此 1 场 → 走 Plan 018 方案 A：手维护 + 新增 `_protected_from_api` 标志位
  - 如果出现第 2 场 → 走 Plan 018 方案 B：在 `src/data/worldcup_api.py` 拉取层做 Arabic → Latin transliteration
  - 修复后 Belgium vs Egypt 详情页显示 Latin 转写（如 "Imam Ashour"）而非阿拉伯文
- **暂不修原因**: 根因是数据脏（不是缺 transliteration），过早修会掩盖问题；等更多比赛结束后看趋势再决策更稳

## 长期（V2+）

- 多用户/账号系统
- 实时比分 WebSocket
- 投注/预测（明确不做，纯娱乐）

## 未来候选 backlog item（Plan 043 起 抽取）

这些项从 Plan 029-042 的「身有隐忧」段落中抽取，本轮未做但明显是“收个尾”级别的 polish。

| ID | 标题 | 源 plan | 优先级 |
|----|------|---------|--------|
| F1-001 | e2e test 重写：e2e/ 下 10 个 fixture-drift 失败用例（bracket pairings / auto status / modal placeholder / worldcup API end-to-end）需同步 live data | 021-022 | P1 |
| F1-002 | 后台 daemon 装为 systemd unit（`bin/serve.sh` → `wc2026.service`）开机自启 | 016 | P2 |
| F2-001 | Bracket 面板中“所有未踢的 R32”链接到「下场比赛倒计时」 widget | 030 | P2 |
| F2-002 | 在 Best 3rd Top 8 面板上添加「点击球队 → 在 Bracket 中定位」跳转 | 042 | P2 |
| F2-003 | Top 8 面板添加 “靠别人” 列：各队锁定的最佳 / 最差场景（locked_top8 后填充） | 031 | P2 |
| F2-004 | PWA 离线后点 `🔄 刷新` 友好 fallback（现在只是 alert 错误） | 014 + 040 | P2 |
| F2-005 | `data/.cache/` cleanup（只要删除就不上重生成） | 002 | P3 |

## 修订日志

- 2026-06-12: 创建，初始化 4 阶段路线图 + 14 个条目
- 2026-06-16: 新增 P2-008（worldcup26.ir 阿拉伯文进球者名字）
- 2026-06-19: Plan 027 完成（team-name alias resolver，修复 B/D/K 积分榜）
- 2026-06-19: Plan 028 完成（countries.json lookup 3-pass fallback，修复波黑/美国/刚果中文名）
- 2026-06-19: Plan 029 完成（bracket qualification + 完整 FIFA 8 best 3rd race 算法）
- 2026-06-26: Plan 042 完成（Best 3rd Top 8 面板）
- 2026-06-26: Plan 043 完成（Quick Start 现代化 + 全文档同步，Phase 1-5 全 done，新增「未来候选」段）
