# Plan 002 — ICS Parser + Flask Skeleton

> **状态**: `proposed`（用户口头批准 "好先A" → 视为 `planned`）→ 执行 → `completed`
> **创建日期**: 2026-06-12
> **关联 plan**: [001-initial-skeleton.md](001-initial-skeleton.md) (前置)
> **下一 plan**: 003 (国旗 + 队名 + 详情)

## 背景

Plan 001 把项目骨架搭好（0 代码）。下一步是"把数据跑通"——按用户原话"把数据逻辑跑通再润色"。

合并 P0-002 (ICS parser) + P0-003 (Flask skeleton)，**不含国旗/详情弹窗/i18n**（这些留 Plan 003）。

## 范围

### In Scope

1. **依赖管理**
   - `requirements.txt` — Flask、icalendar、requests、pytest
   - 用户级 pip install（系统无 venv，apt 装 python3-venv 需 sudo 密码）

2. **数据层（src/data/）**
   - `ics_fetcher.py` — 拉 baires ICS，1 小时本地缓存
   - `ics_parser.py` — 解析 ICS → 标准 match dict

3. **API 层（src/app.py）**
   - Flask app factory
   - 路由：`/`、`GET /api/matches`、`POST /api/refresh`

4. **展示层（src/templates + src/static/）**
   - 极简 index.html（标题 + 刷新按钮 + 比赛列表容器）
   - 极简 main.css（卡片样式 + 今日高亮）
   - 极简 main.js（拉 /api/matches 渲染日期分组）

5. **脚本（scripts/）**
   - `fetch_initial_data.py` — 一次性拉数据

6. **测试（tests/）**
   - `test_ics_parser.py` — parser 单元测试
   - `test_app.py` — Flask 端点测试
   - `fixtures/wc2026-sample.ics` — 测试用 ICS（3 个事件）

### Out of Scope（Plan 003+ 才做）

- ❌ flag-icons 集成
- ❌ 队名翻译（中英）
- ❌ 详情弹窗（进球详情）
- ❌ i18n 切换器
- ❌ 浏览器全屏启动
- ❌ 数据 details.json（进球/场馆手写）

## 任务清单

| # | 任务 | 状态 |
|---|------|------|
| 1 | 写 requirements.txt | ⏳ |
| 2 | 写 src/data/ics_fetcher.py | ⏳ |
| 3 | 写 src/data/ics_parser.py | ⏳ |
| 4 | 写 src/__init__.py + src/data/__init__.py | ⏳ |
| 5 | 写 src/app.py | ⏳ |
| 6 | 写 src/templates/index.html | ⏳ |
| 7 | 写 src/static/css/main.css | ⏳ |
| 8 | 写 src/static/js/main.js | ⏳ |
| 9 | 写 scripts/fetch_initial_data.py | ⏳ |
| 10 | 写 tests/fixtures/wc2026-sample.ics | ⏳ |
| 11 | 写 tests/test_ics_parser.py | ⏳ |
| 12 | 写 tests/test_app.py | ⏳ |
| 13 | 写 pyproject.toml（pytest config） | ⏳ |
| 14 | 跑 pytest | ⏳ |
| 15 | 跑 fetch_initial_data.py 拉真实数据 | ⏳ |
| 16 | 启动 Flask 烟测 | ⏳ |
| 17 | git commit | ⏳ |

## 验收

### 必须

- [ ] `python3 -m pytest` 全绿
- [ ] `python3 scripts/fetch_initial_data.py` 拉出 >= 70 场比赛（小组赛 72 场）
- [ ] `python3 src/app.py` 启动后访问 `/` 返回 200
- [ ] `GET /api/matches` 返回 JSON 数组
- [ ] `POST /api/refresh` 重新拉数据
- [ ] 浏览器看到日期分组列表，"今天" 高亮
- [ ] 比赛卡片显示 3 字母队码 + 时间 + 场地

### 应该

- [ ] 测试覆盖 4 种 stage（group / r16 / qf / final）
- [ ] 解析器对 SUMMARY 格式变化鲁棒（regex 容错）
- [ ] fetcher 有 1 小时缓存
- [ ] `data/matches.json` 是 pretty-printed JSON（好 diff）

## Match 数据结构（Plan 002 简化版）

```json
{
  "match_id": "wc2026-xxx",
  "summary": "MEX vs RSA (Group A)",
  "date_utc": "2026-06-11T23:00:00+00:00",
  "home": {"code": "MEX"},
  "away": {"code": "RSA"},
  "stage": "group",     // group | r32 | r16 | qf | sf | third | final | unknown
  "group": "A",         // null for knockout
  "venue": {"raw": "Estadio Azteca, Mexico City"}
}
```

## 风险

| 风险 | 缓解 |
|------|------|
| baires ICS SUMMARY 格式与预期不符 | 写 robust regex，多种变体都试 |
| 系统没装 venv 需要的包 | 用 --user pip install，文档记录这个限制 |
| ICS 有 timezone（TZID=America/Mexico_City） | 全部转 UTC，前端按本地时区显示 |
| 真实数据有 70+ 场，全 render 慢 | 分页 or 滚动加载（先不做，看性能） |
| pip --user 装的位置 PATH 找不到 | 用 `python3 -m pip` 调用，不用直接 pip |

## 决策记录

- 不用 venv：因为 `python3-venv` 系统包未装，`ensurepip` 也缺，且 `apt install` 需 sudo 密码 → 改用 `pip install --user`，并在 README/AGENTS 记录这个限制
- pytest config 用 `pyproject.toml`（最现代）
- Flask 3.1（最新稳定版）+ icalendar 7.1（最新）
- 缓存 TTL 1 小时（用户说"刷新即可"，不需要更短）
- 不在 Plan 002 写 country 映射表（48 队太多，Plan 003 做）
- 不做 favicon / 浏览器兼容性 / 响应式细节（"数据跑通再润色"）
