# conventions.md — 项目规范

## 命名

- **目录与 markdown**: `kebab-case`（例：`docs/plans/001-initial-skeleton.md`）
- **Python 文件/模块**: `snake_case`（例：`src/data/ics_parser.py`）
- **Python 类**: `PascalCase`（例：`MatchDetail`）
- **Python 常量**: `UPPER_SNAKE_CASE`（例：`DEFAULT_PORT = 8766`）
- **JSON 字段**: `snake_case`（例：`kickoff_utc`）
- **CSS 类**: `kebab-case`（例：`match-card`）
- **JS 变量/函数**: `camelCase`（例：`renderMatches`）
- **JS 类/组件**: `PascalCase`（例：`MatchList`）

## Python 风格

- PEP 8 + 4 空格缩进
- 全部 public 函数加 type hints
- Docstring 用 Google 风格（Args/Returns/Raises）
- 字符串用双引号 `"`，单引号只在 docstring 内
- `black` 格式化（行宽 100）
- `isort` 排序 import

## JavaScript 风格

- ES6+（async/await、arrow function、template literals）
- 2 空格缩进
- 分号结尾
- 单引号字符串

## 提交规范

- Conventional Commits：`feat:` / `fix:` / `docs:` / `refactor:` / `chore:` / `test:`
- 例：`feat(ics): parse baires calendar into local JSON`
- 提交粒度：一个逻辑变更 = 一个 commit

## 文档规范

- Markdown（CommonMark + GFM tables）
- 不用 emoji（除了 README.md 顶部特性列表用一次）
- 一级标题每文件一个
- 链接用相对路径（`../context/x.md`），不用绝对 URL
- 中英混排时，括号内用英文：`"data parser（数据解析器）"`

## 国际化

- UI 默认中文，文案并列英文：`"刷新 Refresh"`
- `data/i18n/zh.json` 和 `data/i18n/en.json` 维护所有用户可见文案
- 任何 UI 新文案必须两个文件都加

## 目录约定

- `src/` — 应用代码
- `data/` — 派生/缓存数据（ICS 解析结果、手写详情）
- `tests/` — pytest 测试
- `docs/` — 文档
- `scripts/` — 一次性脚本（首次爬数据等）

## 不要做的事

- 不要在 `data/*.json` 改完不写来源（这是 derived 数据）
- 不要 hardcode 端口（用 env var）
- 不要在 `src/` 直接 import `data/`（应通过 Flask config 注入路径）
- 不要在 CSS 用 `!important`（结构上解决）
