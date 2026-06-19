# backlog/README.md — 待办池

> 按优先级 P0/P1/P2 排序。每个条目包含：描述、验收、关联 plan、状态。

## 状态: open / in-progress / done / blocked / dropped

## 迁移路线图

按 AGE 方法论，本项目分 4 阶段：

| 阶段 | 状态 | 内容 |
|------|------|------|
| **Phase 1** | 🔄 进行中 | 项目骨架（AGENTS.md + context + 目录） |
| **Phase 2** | ⏳ 待开始 | ICS parser + Flask skeleton + 基础页面 |
| **Phase 3** | ⏳ 待开始 | 国旗 + 详情弹窗 + 双语切换 |
| **Phase 4** | ⏳ 待开始 | 桌面全屏 + 刷新 + 端到端验收 |

## P0 — 必须（MVP）

### P0-001: 初始骨架（Plan 001）
- **状态**: in-progress
- **Plan**: [001-initial-skeleton.md](../plans/001-initial-skeleton.md)
- **完成定义**: AGENTS.md + 5 个 context + backlog + plan + log + 空目录全部建好，0 占位符

### P0-002: ICS parser
- **状态**: open
- **描述**: 拉 baires ICS → 解析 → 输出统一 `matches.json`
- **验收**:
  - `python -m src.data.ics_parser --url <ics_url> --out data/matches.json` 跑通
  - 输出包含 104 场比赛
  - 日期、主场、客场、轮次字段都对
  - pytest 覆盖 4 种比赛状态（scheduled / live / final / postponed）

### P0-003: Flask skeleton + 基础页面
- **状态**: open
- **描述**: Flask app + index.html + 静态资源 + 路由
- **验收**:
  - `python src/app.py` 启动后访问 `http://127.0.0.1:8765` 看到日期分组列表
  - 不需要国旗、不需要详情、不需要 i18n
  - 至少展示 5 场比赛（用 fixture 数据）
  - pytest 覆盖 GET `/` 和 `/api/matches`

### P0-004: 国旗 + 队名 + 比分
- **状态**: open
- **描述**: 集成 flag-icons，显示在卡片上
- **验收**:
  - 卡片显示 🇲🇽 MEX vs 🇿🇦 RSA（用 flag-icons 类，不是 emoji）
  - 比分字段正确显示
  - 状态字段（scheduled / live / final）有视觉差异
  - 主场在前，客场在后

## P1 — 应该做（V1.1）

### P1-001: 详情弹窗
- **描述**: 点比赛卡片弹窗显示进球详情
- **验收**: 弹窗内显示进球人 + 进球时间 + 场馆 + 城市

### P1-002: 双语 UI
- **描述**: zh + en 切换
- **验收**:
  - 顶部有切换器
  - 切换后所有 UI 文案同步
  - 队名同时显示中英（如"🇧🇷 巴西 Brazil"）
  - 切换状态保存到 localStorage

### P1-003: 桌面浏览器全屏
- **描述**: 启动后自动全屏，无边框
- **验收**:
  - `src/start.sh` 一条命令启动 Flask + 全屏浏览器
  - F11 退出全屏后再开应用回到全屏
  - 关闭浏览器会同时关闭 Flask 进程

### P1-004: 刷新按钮
- **描述**: 拉最新 ICS 并更新本地 JSON
- **验收**:
  - 点 "刷新" 按钮
  - 后端 POST `/api/refresh` 拉 ICS
  - 前端收到新数据自动重渲染
  - 失败时显示 toast 错误

## P2 — 以后做（V1.2+）

### P2-001: 暗色/亮色模式
### P2-002: 桌面通知（开赛前 N 分钟）
### P2-003: 关注球队高亮
### P2-004: 下一场比赛倒计时
### P2-005: 比赛集锦/视频链接
### P2-006: 移动端 PWA
### P2-007: 多赛事支持（欧冠、欧洲杯等）

### P2-008: worldcup26.ir 阿拉伯文进球者名字（Belgium vs Egypt 脏数据）
- **状态**: open
- **创建日期**: 2026-06-16
- **Plan**: [018-arabic-scorer-name-handling.md](../plans/018-arabic-scorer-name-handling.md)
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

## 修订日志

- 2026-06-12: 创建，初始化 4 阶段路线图 + 14 个条目
- 2026-06-16: 新增 P2-008（worldcup26.ir 阿拉伯文进球者名字）
- 2026-06-19: Plan 027 完成（team-name alias resolver，修复 B/D/K 积分榜）
- 2026-06-19: Plan 028 完成（countries.json lookup 3-pass fallback，修复波黑/美国/刚果中文名）
