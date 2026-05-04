# T029 Tester Agent 最小测试协议报告

## 1. 背景

`multi-agent-runner` 第二阶段实现了 Reviewer Agent 自动审查 MVP，第三阶段已接入 DeepSeek 真实 Reviewer 模型并完成结构化解析。

当前框架已有 Developer Agent 和 Reviewer Agent 两方协作，但缺少 Tester Agent 进行自动化测试验证。

T029 定义 Tester Agent 的最小测试协议，为 T030 本地静态检查实现提供协议基础。

## 2. 目标

定义 Tester Agent 对 Web MVP 项目的最小测试方式和测试报告格式：

- 明确 Tester Agent 职责边界
- 明确 Web MVP 最小静态测试项（4 类 16 项）
- 明确 PASS / FAIL 判定规则
- 定义测试报告格式和完成证据路径
- 不实现测试代码

## 3. Tester Agent 职责

Tester Agent 的核心职责是**验证任务是否满足验收标准**。

| 职责 | 说明 |
|------|------|
| 读取任务要求 | 从 `docs/tasks.md` 或开发报告获取验收标准 |
| 读取项目文件 | 从项目目录读取被测试的文件 |
| 执行静态检查 | 按最小测试项逐项检查 |
| 生成测试报告 | 将检查结果写入标准格式测试报告 |
| 返回结构化结果 | 测试报告中的 Status / Result 字段可被 Main Agent 读取 |

Tester Agent 明确不做：

- 不修改业务代码
- 不做真实浏览器渲染测试
- 不做键盘事件测试
- 不做游戏物理逻辑测试
- 不做微信小游戏 / 抖音小游戏平台测试

## 4. Web MVP 最小测试项

### 4.1 文件存在性检查（3 项）

| 编号 | 测试项 | 必需 |
|------|--------|------|
| F-01 | `index.html` 是否存在 | 是 |
| F-02 | `style.css` 是否存在 | 是 |
| F-03 | `script.js` 是否存在 | 是 |

### 4.2 HTML 关键元素检查（6 项）

| 编号 | 测试项 | 检查关键词 |
|------|--------|------------|
| H-01 | 页面标题是否存在 | `<title>` |
| H-02 | 游戏区域是否存在 | `#game-area` |
| H-03 | 开始按钮是否存在 | `#start-btn` |
| H-04 | 楼层/分数显示是否存在 | `#floor-display` / `#score` |
| H-05 | 状态提示是否存在 | `#status-display` |
| H-06 | 玩家元素是否存在 | `#player` |

### 4.3 CSS 基础样式检查（3 项）

| 编号 | 测试项 | 检查关键词 |
|------|--------|------------|
| C-01 | `.game-area` 样式是否存在 | `.game-area` |
| C-02 | `.player` 样式是否存在 | `.player` |
| C-03 | 按钮样式是否存在 | `#start-btn` / `.btn` / `button` |

### 4.4 JS 基础检查（4 项）

| 编号 | 测试项 | 检查方式 |
|------|--------|----------|
| J-01 | `script.js` 是否可读取 | 文件可读性检查 |
| J-02 | 是否存在初始化逻辑 | 搜索 `init` / `DOMContentLoaded` / `window.onload` |
| J-03 | 是否没有明显空文件 | 文件大小 > 0 |
| J-04 | 是否包含 start button 相关逻辑 | 搜索 `start-btn` / `startBtn` / `start` |

总计 4 类 16 项检查。

## 5. PASS / FAIL 规则

| 条件 | 结果 |
|------|------|
| 全部必需项通过 | `PASS` |
| 任一必需项缺失或失败 | `FAIL` |
| 文件缺失（F-01/F-02/F-03 任一） | `FAIL` |
| 测试条件不足（如缺少输入文件） | `BLOCKED` |
| 需要重新执行开发任务 | `RETRY` |

状态枚举：`PASS` / `FAIL` / `RETRY` / `BLOCKED` / `INFO`

Result 字段：`PASS` / `FAIL`

## 6. 测试报告完成证据

Tester Agent 完成证据路径：

```text
<project-root>/reports/test/<task-id>-test-report.md
```

例如：

```text
projects/down-100-floors-game/reports/test/G003-test-report.md
```

测试报告必须包含：Agent / Task / Status / Test Scope / Test Cases / Result / Failed Items / Evidence / Next Action。

## 7. 当前不做事项

T029 只做协议设计，明确不做：

1. 不实现测试代码（T030 做）
2. 不修改 Python 代码
3. 不修改小游戏业务代码
4. 不调用 DeepSeek API
5. 不执行自动开发命令
6. 不开始 T030

## 8. T030 实现建议

T030 应基于本协议实现 `tools/tester_runner.py`，包含：

1. **文件存在性检查函数** — 接收项目路径，检查 index.html / style.css / script.js 是否存在
2. **HTML 元素检查函数** — 读取 index.html，用字符串匹配检查关键元素
3. **CSS 样式检查函数** — 读取 style.css，用字符串匹配检查关键选择器
4. **JS 基础检查函数** — 读取 script.js，检查初始化逻辑和非空
5. **测试报告生成函数** — 汇总检查结果，按模板生成测试报告
6. **runner.py 命令接入** — 新增 `test-game-task <task-id>` 命令

检查方式统一使用字符串匹配或正则，不引入新依赖。

## 9. 是否完成

是。

本协议已明确定义：

- Tester Agent 职责边界（Section 3）
- Web MVP 最小静态测试项 4 类 16 项（Section 4）
- PASS / FAIL 判定规则（Section 5）
- 测试报告格式和完成证据路径（Section 6）
- 当前不做事项（Section 7）
- T030 实现建议（Section 8）

相关文件：

- `docs/tester-protocol.md` — 完整 Tester Agent 协议
- `templates/agent-output/tester-static-web-test-template.md` — 静态 Web 测试报告模板
- `docs/agent-output-protocol.md` — Tester Agent 输出协议（已更新）
