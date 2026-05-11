# T154 Dev Report：Stage 8 monitor → verify → report 架构设计

## 基本信息

- TASK=T154
- ROLE=Architect Agent + Stage 8 Safety Workflow Architect
- DATE=2026-05-11
- PROJECT_ROOT=E:/github_project/multi-agent-runner
- LAST_COMMIT=5272e8b test: validate stage 8 max tasks one controlled trial

## 设计目标

设计 Stage 8 monitor → verify → report 架构，吸收外部自动维护流水线思想但不直接接入 Claude Agent SDK。

## 设计内容

### 新增设计文档

1. docs/stage8-monitor-verify-report-architecture.md

### 设计模块

| 模块 | 文件 | 实现阶段 | 职责 |
|------|------|----------|------|
| TaskMonitor | tools/task_monitor.py | T155 | 执行前状态采集与预检 |
| ContinuousVerifier | tools/continuous_verifier.py | T156 | 执行后结果验证 |
| ExecutionReportWriter | tools/execution_report_writer.py | T157 | 执行报告统一生成 |

### Future 模块（不在 T154 实现）

| 模块 | 文件 | 说明 |
|------|------|------|
| AutoMendingPlanner | tools/auto_mending_planner.py | 自动返工计划生成 |
| RunStateManager | tools/run_state_manager.py | 运行状态持久化与恢复 |

### External Pattern Mapping

| 外部模式 | 本项目对应 | 阶段 |
|----------|-----------|------|
| monitor.sh | tools/task_monitor.py | T155 |
| state.json | reports/state/ (future) | future |
| verify.sh | tools/continuous_verifier.py | T156 |
| mending-agent.ts | tools/auto_mending_planner.py (future) | future |
| report-agent.ts | tools/execution_report_writer.py | T157 |

### Stage 8 Flow

```
TaskMonitor → SafetyGate (G1-G21) → ControlledRunner → ContinuousVerifier → ExecutionReportWriter → Stop
```

### Safety Rules

12 条安全规则覆盖：dirty workspace stop、unclassified changes stop、forbidden paths fail closed、missing report fail、missing CHECK_RESULT fail、max_tasks=1 限制、no auto commit、no auto push、no silent continuation、no auto Stage 9 transition、no Claude Agent SDK、no new dependency。

### Report Format

定义 reports/continuous-runs/Txxx-run-report.md 标准模板，包含 8 个章节：Task Info、Monitor Result、Safety Gate Result、Execution Result、Verify Result、Rework Decision、Git Decision、Final Status。

### 后续任务链

| 任务 | 目标 | 依赖 |
|------|------|------|
| T155 | 实现 task_monitor.py | T154 |
| T156 | 实现 continuous_verifier.py | T154 |
| T157 | 实现 execution_report_writer.py | T154 |
| T158 | 接入 run-project-loop --real-execution --max-tasks 1 | T155, T156, T157 |
| T159 | 验证 monitor → verify → report 闭环 | T158 |

## 安全保证

- TASK=T154
- DESIGN_STATUS=done
- BUSINESS_CODE_CHANGED=no
- FRAMEWORK_CODE_CHANGED=no
- REAL_EXECUTION_CHANGED=no
- RUNNER_CHANGED=no
- TOOLS_CHANGED=no
- CLAUDE_AGENT_SDK_INTEGRATED=no
- AUTO_MENDING_PLANNER_IMPLEMENTED=no
- RUN_STATE_MANAGER_IMPLEMENTED=no
- MAX_TASKS_EXCEEDED_1=no
- REAL_CONTINUOUS_EXECUTION_STARTED=no
- AUTO_COMMIT_TRIGGERED=no
- AUTO_PUSH_TRIGGERED=no
- STAGE9_ENTERED=no

## 文件清单

### 本次新增文件

- docs/stage8-monitor-verify-report-architecture.md
- reports/dev/T154-dev-report.md

### 本次修改文件

- docs/tasks.md（T154 状态更新为 done，新增 T155-T159 任务）

## 最终状态

```
TASK=T154
DESIGN_STATUS=done
FILES_CREATED=docs/stage8-monitor-verify-report-architecture.md, reports/dev/T154-dev-report.md
FILES_MODIFIED=docs/tasks.md
BUSINESS_CODE_CHANGED=no
FRAMEWORK_CODE_CHANGED=no
REAL_EXECUTION_CHANGED=no
RUNNER_CHANGED=no
TOOLS_CHANGED=no
CLAUDE_AGENT_SDK_INTEGRATED=no
CHECK_RESULT=pass
NEXT_PENDING=T155
NEXT_STAGE=Stage 8
```
