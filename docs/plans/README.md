# docs/plans/ — Plan 索引

> 每个 plan 一份文件，按编号顺序命名：`NNN-slug.md`。
> Active plan 在 [docs/index.md § 当前状态](../index.md) 和 [docs/context/project-context.md](../context/project-context.md) 里标出。

## 完整索引（001 - 043）

| # | 标题 | 完成日期 | 类别 |
|---|------|----------|------|
| [001](001-initial-skeleton.md) | Initial Skeleton | 2026-06-12 | skeleton |
| [002](002-ics-parser-and-flask.md) | ICS Parser + Flask Skeleton | 2026-06-12 | data + API |
| [003](003-bracket-view.md) | Bracket View | 2026-06-13 | UI |
| [004](004-flags-and-country-names.md) | Flags + Country Names | 2026-06-13 | UI |
| [005](005-bracket-mirror.md) | Bracket Mirror | 2026-06-13 | UI |
| [006](006-e2e-and-audit.md) | E2E + Audit | 2026-06-14 | qa |
| [007](007-bracket-connecting-lines.md) | Bracket Connecting Lines | 2026-06-14 | UI |
| [008](008-left-right-symmetric.md) | Bracket Symmetric | 2026-06-14 | UI |
| [009](009-detail-modal.md) | Detail Modal | 2026-06-15 | UI |
| [010](010-match-details-scores-goalscorers.md) | Match Details (Score + Goalscorers) | 2026-06-15 | data + UI |
| [012](012-worldcup26-api-integration.md) | worldcup26.ir API Integration | 2026-06-15 | data |
| [013](013-desktop-launcher.md) | Desktop Launcher | 2026-06-16 | deployment |
| [014](014-pwa-progressive-web-app.md) | PWA | 2026-06-16 | PWA |
| [015](015-detail-page-content.md) | Detail Page Content | 2026-06-16 | UI |
| [016](016-widget-and-refresh-fix.md) | Widget + Refresh Fix | 2026-06-16 | UI + bugfix |
| [017](017-incomplete-details-api-override.md) | Incomplete Details API Override | 2026-06-16 | bugfix |
| [018](018-arabic-scorer-name-handling.md) | Arabic Scorer Name Handling | 2026-06-16 | bugfix |
| [019](019-standings-gf-ga-gd-columns.md) | Standings GF/GA/GD Columns | 2026-06-17 | UI |
| [021](021-render-deployment.md) | Render Deployment | 2026-06-17 | deployment |
| [022](022-cloudflare-quick-tunnel.md) | Cloudflare Quick Tunnel | 2026-06-17 | deployment |
| [023](023-mobile-responsive.md) | Mobile Responsive | 2026-06-18 | UI |
| [024](024-pwa-activation.md) | PWA Activation | 2026-06-18 | PWA |
| [025](025-stoppage-time-parser-fix.md) | Stoppage Time Parser Fix | 2026-06-19 | bugfix |
| [026](026-arabic-scorer-transliteration.md) | Arabic Scorer Transliteration | 2026-06-19 | bugfix |
| [027](027-standings-team-name-alias-resolver.md) | Team-Name Alias Resolver | 2026-06-19 | bugfix |
| [028](028-countries-lookup-alias-fallback.md) | Countries Lookup Alias Fallback | 2026-06-19 | bugfix |
| [029](029-bracket-qualified-teams.md) | Bracket Qualified Teams | 2026-06-19 | feature |
| [030](030-bracket-ux-fixes.md) | Bracket UX Fixes | 2026-06-19 | UI |
| [031](031-qualification-cache-and-fonts.md) | Qualification Cache + Fonts | 2026-06-19 | data + UI |
| [032](032-bracket-bing-redesign.md) | Bracket Bing Redesign | 2026-06-19 | UI |
| [033](033-bracket-overlap-and-init-race.md) | Bracket Overlap + Init Race | 2026-06-20 | bugfix |
| [041](041-qualification-all-played.md) | Qualification All-Played | 2026-06-25 | feature |
| [042](042-third-place-top8-panel.md) | Best 3rd Top 8 Panel | 2026-06-26 | feature |
| [043](043-doc-refresh-quickstart-and-current-state.md) | Doc Refresh + Quick Start | 2026-06-26 | docs |

## 编号缺口

- 011、020、034-040：保留编号但未起 plan（跳号是项目惯例，避免重构时误用）。如有 plan 落到这些号，**先 PR 改本 README** 再起 plan 文件。

## 按类别

- **skeleton**: 001
- **data + API**: 002, 012
- **UI**: 003, 004, 005, 007, 008, 009, 015, 019, 023, 030, 032
- **bugfix**: 016, 017, 018, 025, 026, 027, 028, 033
- **feature**: 029, 031, 041, 042
- **deployment**: 013, 021, 022
- **PWA**: 014, 024
- **qa**: 006
- **docs**: 043

## 跳号理由

项目从 Plan 011 起遇到连续几次「v1 完成不算 plan 也不是 bug」的 polish 改动，没起 plan 文件就 commit 了。038-040 之间也有类似情况。**新 plan 必须从下一个未用号起**，不要复填空号。
