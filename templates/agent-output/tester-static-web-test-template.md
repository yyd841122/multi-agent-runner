# Static Web Test Report

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
| F-01 | index.html 存在 | 是 | PASS/FAIL | |
| F-02 | style.css 存在 | 是 | PASS/FAIL | |
| F-03 | script.js 存在 | 是 | PASS/FAIL | |
| H-01 | 页面标题存在 | 是 | PASS/FAIL | |
| H-02 | 游戏区域存在 (#game-area) | 是 | PASS/FAIL | |
| H-03 | 开始按钮存在 (#start-btn) | 是 | PASS/FAIL | |
| H-04 | 楼层/分数显示存在 | 是 | PASS/FAIL | |
| H-05 | 状态提示存在 | 是 | PASS/FAIL | |
| H-06 | 玩家元素存在 (#player) | 是 | PASS/FAIL | |
| C-01 | .game-area 样式存在 | 是 | PASS/FAIL | |
| C-02 | .player 样式存在 | 是 | PASS/FAIL | |
| C-03 | 按钮样式存在 | 是 | PASS/FAIL | |
| J-01 | script.js 可读取 | 是 | PASS/FAIL | |
| J-02 | 存在初始化逻辑 | 是 | PASS/FAIL | |
| J-03 | 文件非空 | 是 | PASS/FAIL | |
| J-04 | 包含 start button 相关逻辑 | 是 | PASS/FAIL | |

## Result

PASS / FAIL

## Failed Items

-

## Fix Suggestions

-

## Evidence

- reports/test/<task-id>-test-report.md

## Next Action

建议下一步：

## Behavior Check Extension

本模板只覆盖基础静态 Web 检查。

如果任务涉及交互行为，例如键盘移动、点击响应、边界限制，应额外生成：

`reports/test/<task-id>-behavior-test-report.md`

行为检查协议详见：`docs/tester-behavior-check-protocol.md`
