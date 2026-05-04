# Tester Agent Protocol

## 1. 协议目标

Tester Agent Protocol 定义 Tester Agent 对 Web MVP 项目的最小测试方式和测试报告格式。

目标：

- 明确 Tester Agent 的职责边界
- 定义 Web MVP 最小静态测试项
- 定义 PASS / FAIL 判定规则
- 定义测试报告格式和完成证据路径
- 为 T030 本地静态检查实现提供协议基础

本协议只做设计，不实现测试代码。

## 2. Tester Agent 职责

Tester Agent 的核心职责是**验证任务是否满足验收标准**。

具体职责：

1. **读取任务要求** — 从 `docs/tasks.md` 或开发报告获取验收标准
2. **读取项目文件** — 从项目目录读取被测试的文件
3. **执行静态检查** — 按最小测试项逐项检查
4. **生成测试报告** — 将检查结果写入标准格式测试报告
5. **返回结构化结果** — 测试报告中的 Status / Result 字段可被 Main Agent 读取

## 3. Tester Agent 不做什么

Tester Agent 的明确边界：

1. **不修改业务代码** — Tester 只读不写，测试结果通过报告传递
2. **不做真实浏览器渲染测试** — 当前 MVP 只做本地静态检查
3. **不做键盘事件测试** — 运行时交互测试不在当前范围
4. **不做游戏物理逻辑测试** — 重力、平台、碰撞等不在静态检查范围
5. **不做微信小游戏 / 抖音小游戏平台测试** — 当前只测 Web MVP
6. **不做性能测试** — 加载速度、内存占用等不在当前范围
7. **不做安全测试** — XSS、CSRF 等不在当前范围

## 4. 测试输入

Tester Agent 的输入包括：

| 输入 | 来源 | 说明 |
|------|------|------|
| 任务要求 | `docs/tasks.md` | 任务编号、名称、验收标准 |
| 开发报告 | `reports/dev/<task-id>-dev-report.md` | Developer 完成内容 |
| 项目文件 | `<project-root>/` | 被测试的文件 |

对于 Web MVP 项目，项目文件通常包括：

- `index.html` — 页面结构
- `style.css` — 样式
- `script.js` — 逻辑

## 5. 测试输出

Tester Agent 的输出：

| 输出 | 路径 | 说明 |
|------|------|------|
| 测试报告 | `<project-root>/reports/test/<task-id>-test-report.md` | 标准格式测试报告 |

测试报告中的关键字段：

| 字段 | 必填 | 说明 |
|------|------|------|
| `Agent` | 是 | 固定值 `Tester Agent` |
| `Task` | 是 | 任务编号和名称 |
| `Status` | 是 | `PASS` / `FAIL` / `RETRY` / `BLOCKED` / `INFO` |
| `Test Scope` | 是 | 测试范围描述 |
| `Test Cases` | 是 | 测试用例表格（编号、测试项、必需、结果、说明） |
| `Result` | 是 | `PASS` / `FAIL` |
| `Failed Items` | 是 | 失败项列表，无失败为空 |
| `Fix Suggestions` | 否 | 修复建议 |
| `Evidence` | 是 | 完成证据路径 |
| `Next Action` | 是 | 建议下一步动作 |

## 6. Web MVP 最小静态测试项

T030 第一版要支持的最小检查项：

### 6.1 文件存在性检查

| 编号 | 测试项 | 必需 | 检查方式 |
|------|--------|------|----------|
| F-01 | `index.html` 是否存在 | 是 | 文件存在性检查 |
| F-02 | `style.css` 是否存在 | 是 | 文件存在性检查 |
| F-03 | `script.js` 是否存在 | 是 | 文件存在性检查 |

### 6.2 HTML 关键元素检查

| 编号 | 测试项 | 必需 | 检查方式 |
|------|--------|------|----------|
| H-01 | 页面标题是否存在（`<title>` 标签） | 是 | 字符串匹配 `<title>` |
| H-02 | 游戏区域是否存在（`#game-area`） | 是 | 选择器匹配 `id="game-area"` 或 `#game-area` |
| H-03 | 开始按钮是否存在（`#start-btn`） | 是 | 选择器匹配 `id="start-btn"` |
| H-04 | 楼层或分数显示是否存在 | 是 | 选择器匹配 `id="floor-display"` 或 `id="score"` 或类似标识 |
| H-05 | 状态提示是否存在 | 是 | 选择器匹配 `id="status-display"` 或类似标识 |
| H-06 | 玩家元素是否存在（`#player`） | 是 | 选择器匹配 `id="player"` |

### 6.3 CSS 基础样式检查

| 编号 | 测试项 | 必需 | 检查方式 |
|------|--------|------|----------|
| C-01 | `.game-area` 样式是否存在 | 是 | 字符串匹配 `.game-area` |
| C-02 | `.player` 样式是否存在 | 是 | 字符串匹配 `.player` |
| C-03 | 按钮样式是否存在 | 是 | 字符串匹配按钮相关选择器（`#start-btn` 或 `.btn` 或 `button`） |

### 6.4 JS 基础检查

| 编号 | 测试项 | 必需 | 检查方式 |
|------|--------|------|----------|
| J-01 | `script.js` 是否可读取 | 是 | 文件可读性检查 |
| J-02 | 是否存在初始化逻辑 | 是 | 搜索 `init` 或 `DOMContentLoaded` 或 `window.onload` |
| J-03 | 是否没有明显空文件 | 是 | 文件大小 > 0 |
| J-04 | 是否包含 start button 相关逻辑 | 是 | 搜索 `start-btn` 或 `startBtn` 或 `start` |

### 6.5 检查关键词参考

HTML/CSS 选择器关键词：

```text
#game-area
#start-btn
#floor-display
#score
#status-display
#player
.game-area
.player
```

JS 关键词：

```text
init
DOMContentLoaded
window.onload
start-btn
startBtn
start
```

## 7. PASS / FAIL 规则

### 7.1 判定规则

| 条件 | 结果 |
|------|------|
| 全部必需项通过 | `PASS` |
| 任一必需项缺失或失败 | `FAIL` |
| 文件缺失（F-01/F-02/F-03 任一） | `FAIL` |
| 测试条件不足（如缺少输入文件） | `BLOCKED` |
| 需要重新执行开发任务 | `RETRY` |

### 7.2 状态枚举

状态遵循 T014 Agent 输出协议的统一状态枚举：

| 状态 | 含义 | 说明 |
|------|------|------|
| `PASS` | 全部必需项通过 | 测试通过 |
| `FAIL` | 至少一个必需项失败 | 测试失败 |
| `RETRY` | 需要重新执行 | 建议重新开发或重新测试 |
| `BLOCKED` | 被外部条件阻塞 | 如缺少输入文件 |
| `INFO` | 仅信息记录 | 不影响判定 |

### 7.3 Result 字段

测试报告的 `Result` 字段只使用两个值：

| 值 | 说明 |
|-----|------|
| `PASS` | 测试通过 |
| `FAIL` | 测试失败 |

`Result` 字段与 `Status` 字段的对应关系：

- `Status=PASS` → `Result=PASS`
- `Status=FAIL` → `Result=FAIL`
- `Status=RETRY` → `Result=FAIL`（需返工）
- `Status=BLOCKED` → `Result=FAIL`（条件不足）

## 8. 测试报告格式

测试报告使用 markdown 格式，标准结构如下：

```markdown
# <task-id> Test Report

## Agent

Tester Agent

## Task

任务编号：<task-id>
任务名称：<任务名称>

## Status

PASS / FAIL / RETRY / BLOCKED / INFO

## Project

项目路径：<project-root>

## Test Scope

- 文件存在性检查
- HTML 关键元素检查
- CSS 基础样式检查
- JS 基础检查

## Test Cases

| 编号 | 测试项 | 必需 | 结果 | 说明 |
|------|--------|------|------|------|
| F-01 | index.html 存在 | 是 | PASS | 文件存在 |
| ... | ... | ... | ... | ... |

## Result

PASS / FAIL

## Failed Items

- （无失败项则留空）

## Fix Suggestions

- （无建议则留空）

## Evidence

- <project-root>/reports/test/<task-id>-test-report.md

## Next Action

建议下一步：
```

## 9. 完成证据规则

### 9.1 Tester Agent 完成证据

Tester Agent 的最小完成证据：

```text
<project-root>/reports/test/<task-id>-test-report.md
```

例如：

```text
projects/down-100-floors-game/reports/test/G003-test-report.md
```

### 9.2 完成证据要求

1. 测试报告文件必须存在
2. 测试报告必须包含 `Status` 字段
3. 测试报告必须包含 `Result` 字段
4. 测试报告必须包含 `Test Cases` 表格
5. 测试报告必须包含 `Evidence` 路径

### 9.3 完成证据与 Main Agent 的关系

后续 Main Agent（T031）会综合三方结果决策：

| Agent | 完成证据 | 关键字段 |
|-------|----------|----------|
| Developer Agent | `reports/dev/<task-id>-dev-report.md` | `Status` |
| Tester Agent | `reports/test/<task-id>-test-report.md` | `Status` / `Result` |
| Reviewer Agent | `reports/review/<task-id>-review-report.md` | `Status` / `Decision` |

Main Agent 综合决策规则：

- Developer done + Tester PASS + Reviewer APPROVE → COMPLETE
- 任一方 FAIL → 对应 RETRY 或 REQUEST_CHANGES

## 10. 后续自动化扩展方向

当前 Tester Agent 只做本地静态检查。后续可扩展：

1. **浏览器自动化测试** — 使用 Playwright / Puppeteer 进行真实渲染和交互测试
2. **键盘事件测试** — 模拟 ArrowLeft / ArrowRight 等键盘事件
3. **游戏物理逻辑测试** — 验证重力、碰撞、平台等逻辑
4. **多平台测试** — 微信小游戏 / 抖音小游戏平台测试
5. **性能测试** — 加载速度、帧率、内存占用
6. **回归测试** — 每次修改后自动运行全量测试
7. **覆盖率报告** — JS 代码覆盖率统计

以上扩展均不在 T030 第一版范围内。
