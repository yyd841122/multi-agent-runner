# T115 Dev Report

## Task

设计 Stage 7 no-tool-use safe real single-task execution fallback strategy。

## Scope

本轮只做策略设计，不实现代码，不真实执行任务。

## Background

- T113 Layer 1 text-only validation: 6/6 pass（text-only 链路稳定）
- T114 Layer 2 tool-use validation: 0/3 pass（第 1 次 timeout，acceptEdits + tool-use 不稳定）
- T114.1 已归档失败报告并推送到远程仓库
- Layer 2 失败后按协议停止，不再继续 Layer 3 验证
- 需要设计不依赖 tool-use 的安全执行路径

## Changed Files

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| docs/stage-7-no-tool-use-safe-execution-fallback-strategy.md | new | Fallback strategy 设计文档 |
| reports/dev/T115-dev-report.md | new | 本文件 |
| docs/tasks.md | modified | T115 重新定义 + 状态更新 |

## Strategy Summary

### 核心决策

将 Claude Code 从"直接执行者"转变为"结构化输出提供者"，runner 接管实际执行控制权。

### 执行流程

1. runner 选择真实单任务
2. runner 生成结构化 prompt
3. Claude Code / 国内模型返回 text-only structured execution proposal
4. runner 解析 proposal
5. runner 检查范围（文件、命令、安全声明）
6. runner 应用 patch（Python 直接操作文件）
7. runner 执行允许的 test command
8. runner 生成 execution report
9. human review 后决定下一步

### 安全门

设计 11 个安全门覆盖执行前、解析中、执行后和全局四个层面。

### 失败处理

定义 10 种失败停止条件，每种条件有明确的检测方式和恢复策略。

### 后续任务

拆解 T116-T122 共 7 个后续任务，覆盖从 schema 设计到 dry-run 验证到提交推送的完整流程。

## Safety Rules

| 检查项 | 结果 |
|--------|------|
| no run-project-task-full call | yes |
| no Claude Code tool-use call | yes |
| no business code modification | yes |
| no real task execution | yes |
| no auto-continue | yes |
| no auto Git backup | yes |
| human review required | yes |
| no bypass permissions | yes |

## Proposed Next Tasks

| 任务 | 角色 | 目标 |
|------|------|------|
| T116 | Architect | 设计 no-tool-use execution proposal schema |
| T117 | Developer | 实现 proposal parser dry-run |
| T118 | Developer | 实现 allowed scope validator dry-run |
| T119 | Developer | 实现 controlled patch apply dry-run |
| T120 | Tester | 执行 first no-tool-use real single-task dry-run |
| T121 | Tester | 验证 first no-tool-use execution pass/fail 场景 |
| T122 | Developer | 提交并推送 Stage 7 no-tool-use execution reports |

## Verification

- `pwd`: /e/github_project/multi-agent-runner
- `git status --short`: 预期有 3 个文件变更
- `git diff --stat`: 预期变更量在合理范围内

## Next

NEXT_PENDING=T116
NEXT_STAGE=Stage 7
