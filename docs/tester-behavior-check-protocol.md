# Tester Behavior Check Protocol

## 1. 协议目标

Tester Behavior Check Protocol 定义 Tester Agent 对 Web MVP 项目的行为逻辑静态检查方式和报告格式。

目标：

- 补充基础静态结构检查的不足
- 通过源码静态分析验证交互行为逻辑是否存在
- 为 T036 实现键盘移动逻辑静态检查提供协议基础
- 保持与现有 tester-protocol.md 的一致性

本协议只做设计，不实现测试代码。

## 2. 为什么需要行为检查

T030 的 Tester 静态检查已经可以确认：

- 文件是否存在
- HTML 是否包含关键元素（game-area、player、start-btn 等）
- CSS 是否包含基础样式
- JS 是否包含基础逻辑（初始化、start button）

但基础静态检查不能充分证明：

- 键盘事件是否真的被监听
- 左右方向键是否被正确识别
- 玩家位置是否有移动逻辑
- 移动是否受边界限制
- DOM 位置是否在移动后更新

G004 的 Tester PASS 说明基础结构存在，不代表交互行为已经被充分验证。

## 3. 当前静态测试的不足

| 方面 | 基础静态检查 | 行为检查（本协议） |
|------|-------------|-------------------|
| 文件存在 | 已覆盖 | 不重复 |
| HTML 元素 | 已覆盖 | 不重复 |
| CSS 样式 | 已覆盖 | 不重复 |
| JS 非空 | 已覆盖 | 不重复 |
| 键盘事件监听 | 未覆盖 | 新增 |
| 方向键处理 | 未覆盖 | 新增 |
| 移动逻辑 | 未覆盖 | 新增 |
| 边界限制 | 未覆盖 | 新增 |
| 位置更新 | 未覆盖 | 新增 |

结论：行为检查是基础静态检查的补充，不是替代。

## 4. 行为检查范围

第一版行为检查仍然基于源码静态检查，不打开浏览器。

检查对象：

- `script.js` — 主要检查目标
- `index.html` — 辅助检查
- `style.css` — 辅助检查

优先检查：

1. 键盘事件监听
2. 左右方向键识别
3. 玩家位置状态
4. 移动步长
5. 边界限制
6. DOM 位置更新

## 5. 不做什么

1. **不引入浏览器自动化** — 暂不使用 Playwright / Puppeteer
2. **不打开页面验证渲染效果** — 只读源码
3. **不模拟键盘事件** — 只检查代码中是否有对应逻辑
4. **不做运行时断言** — 只做静态分析
5. **不修改业务代码** — Tester 只读不写
6. **不替代基础静态检查** — 行为检查是补充，不是替代

## 6. 键盘事件检查项

| 编号 | 测试项 | 检查目标 | 必需 |
|------|--------|----------|------|
| B-01 | 键盘事件监听存在 | `keydown` 或 `addEventListener('keydown'` 或 `onkeydown` | 是 |
| B-02 | 左方向键处理存在 | `ArrowLeft` 或 `keyCode === 37` 或 `key === 'ArrowLeft'` 或 `37` | 是 |
| B-03 | 右方向键处理存在 | `ArrowRight` 或 `keyCode === 39` 或 `key === 'ArrowRight'` 或 `39` | 是 |

检查方式：在 `script.js` 源码中搜索关键词。

## 7. 左右移动逻辑检查项

| 编号 | 测试项 | 检查目标 | 必需 |
|------|--------|----------|------|
| M-01 | 玩家横向位置变量存在 | `playerState.x` 或 `playerX` 或 `player.x` 或类似位置变量 | 是 |
| M-02 | 左移逻辑存在 | `x -` 或 `x -=` 或 `position -` 或左移相关赋值 | 是 |
| M-03 | 右移逻辑存在 | `x +` 或 `x +=` 或 `position +` 或右移相关赋值 | 是 |
| M-04 | 移动速度或步长存在 | `moveSpeed` 或 `speed` 或数值步长（如 `+= 5`） | 是 |

检查方式：在 `script.js` 源码中搜索关键词和模式。

## 8. 边界限制检查项

| 编号 | 测试项 | 检查目标 | 必需 |
|------|--------|----------|------|
| L-01 | 左边界限制存在 | `Math.max` 或 `>= 0` 或 `x < 0` 或左边界判断 | 是 |
| L-02 | 右边界限制存在 | `Math.min` 或 `areaWidth - playerWidth` 或 `clientWidth` 或右边界判断 | 是 |
| L-03 | 玩家不能移出游戏区域 | 同时存在左边界和右边界判断 | 是 |

检查方式：在 `script.js` 源码中搜索边界相关关键词和模式。

## 9. 玩家位置更新检查项

| 编号 | 测试项 | 检查目标 | 必需 |
|------|--------|----------|------|
| U-01 | 位置更新函数存在 | `updatePlayerPosition` 或 `updatePosition` 或 `render` 或 `draw` 等更新函数 | 是 |
| U-02 | DOM left 或 transform 更新存在 | `style.left` 或 `style.transform` 或 `translateX` 等位置更新 | 是 |
| U-03 | 移动后调用更新函数 | 移动逻辑中调用位置更新函数 | 是 |

检查方式：在 `script.js` 源码中搜索函数调用和位置更新模式。

## 10. PASS / FAIL 规则

### 10.1 判定规则

| 条件 | 结果 |
|------|------|
| 全部必需项通过 | `PASS` |
| 任一必需项失败 | `FAIL` |
| 源码文件缺失 | `BLOCKED` |
| 源码无法读取 | `BLOCKED` |

### 10.2 状态枚举

状态遵循 tester-protocol.md 的统一状态枚举：

| 状态 | 含义 |
|------|------|
| `PASS` | 全部必需项通过 |
| `FAIL` | 至少一个必需项失败 |
| `BLOCKED` | 被外部条件阻塞（如源码文件缺失） |

### 10.3 与基础静态检查的关系

- 基础静态检查和行为检查独立判定
- 两者都 PASS 才能视为 Tester 整体 PASS
- Main Agent 应同时读取两个 Tester 证据

## 11. 测试报告格式

行为检查报告使用 markdown 格式，标准结构如下：

```markdown
# <task-id> Behavior Check Test Report

## Agent

Tester Agent

## Task

任务编号：<task-id>
任务名称：<任务名称>

## Status

PASS / FAIL / BLOCKED

## Project

项目路径：<project-root>

## Test Scope

- 键盘事件检查
- 左右移动逻辑检查
- 边界限制检查
- 玩家位置更新检查

## Test Cases

| 编号 | 测试项 | 必需 | 结果 | 说明 |
|------|--------|------|------|------|
| B-01 | 键盘事件监听存在 | 是 | PASS/FAIL | |
| B-02 | 左方向键处理存在 | 是 | PASS/FAIL | |
| B-03 | 右方向键处理存在 | 是 | PASS/FAIL | |
| M-01 | 玩家横向位置变量存在 | 是 | PASS/FAIL | |
| M-02 | 左移逻辑存在 | 是 | PASS/FAIL | |
| M-03 | 右移逻辑存在 | 是 | PASS/FAIL | |
| M-04 | 移动速度或步长存在 | 是 | PASS/FAIL | |
| L-01 | 左边界限制存在 | 是 | PASS/FAIL | |
| L-02 | 右边界限制存在 | 是 | PASS/FAIL | |
| L-03 | 玩家不能移出游戏区域 | 是 | PASS/FAIL | |
| U-01 | 位置更新函数存在 | 是 | PASS/FAIL | |
| U-02 | DOM 位置更新存在 | 是 | PASS/FAIL | |
| U-03 | 移动后调用更新函数 | 是 | PASS/FAIL | |

## Result

PASS / FAIL / BLOCKED

## Failed Items

- （无失败项则留空）

## Fix Suggestions

- （无建议则留空）

## Evidence

- reports/test/<task-id>-behavior-test-report.md

## Next Action

建议下一步：
```

## 12. 完成证据规则

### 12.1 行为检查完成证据

行为检查的完成证据路径：

```text
<project-root>/reports/test/<task-id>-behavior-test-report.md
```

例如：

```text
projects/down-100-floors-game/reports/test/G004-behavior-test-report.md
```

### 12.2 与基础静态检查证据的关系

| 检查类型 | 完成证据 |
|----------|----------|
| 基础静态检查 | `<project-root>/reports/test/<task-id>-test-report.md` |
| 行为检查 | `<project-root>/reports/test/<task-id>-behavior-test-report.md` |

说明：

- 原有 `<task-id>-test-report.md` 代表基础静态结构检查
- 新增 `<task-id>-behavior-test-report.md` 代表行为逻辑静态检查
- 两个报告独立存在，便于 Main Agent 综合判断

### 12.3 完成证据要求

1. 行为检查报告文件必须存在
2. 报告必须包含 `Status` 字段
3. 报告必须包含 `Result` 字段
4. 报告必须包含 `Test Cases` 表格（13 项检查）
5. 报告必须包含 `Evidence` 路径

## 13. T036 实现建议

### 13.1 实现方向

T036 应在 `tools/tester_runner.py` 中新增行为检查函数：

1. 新增 `run_behavior_check(project_path, task_id)` 函数
2. 读取 `script.js` 源码内容
3. 按 B / M / L / U 四组检查项逐项搜索关键词
4. 生成行为检查报告到 `<project>/reports/test/<task-id>-behavior-test-report.md`

### 13.2 实现约束

1. 不引入浏览器自动化
2. 不修改小游戏业务代码
3. 不破坏已有的基础静态检查功能
4. 新增行为检查函数与已有静态检查函数分离

### 13.3 关键词匹配策略

- 使用简单的字符串包含检查（`in` 操作）
- 每个检查项定义多个候选关键词，任一匹配即通过
- 不做语法分析，不做 AST 解析
- 保持实现简洁，便于后续扩展

### 13.4 命令扩展建议

建议新增命令或扩展现有命令：

```text
python runner.py test-game-task <task-id> --behavior
```

或保持现有命令，在 `test-game-task` 中自动判断是否需要行为检查。

具体由 T036 实现时决定。
