# T110 Dev Report

## Task

决策真实执行路线。

## Scope

本轮只做路线决策，不调用 Claude Code，不执行真实任务，不修改代码。

## Changed Files

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| docs/real-execution-route-decision.md | new | 真实执行路线决策文档 |
| reports/dev/T110-dev-report.md | new | 本文件 |
| docs/tasks.md | modified | T110 状态更新，追加 T111-T116 |
| memory/lessons.md | modified | 追加 T110 经验 |
| memory/pitfalls.md | modified | 追加 T110 避坑记录 |

## Evidence Summary

### 证据表

| Task | Scenario | Result | Meaning |
|------|----------|--------|---------|
| T100 | full run-project-task-full (框架级) | timeout (600s) | full real execution not stable |
| T102 | G008 smoke task (极小) | timeout (600s) | minimal full loop not stable |
| T103 | acceptEdits + tool-use | timeout (120s) | compatibility issue observed |
| T103 | default text-only | pass | text-only path OK |
| T103 | acceptEdits text-only | pass | text-only path OK |
| T107 | default text-only | pass | text-only path OK |
| T108 | default text-only | pass | text-only path OK |
| T108 | acceptEdits text-only | pass | text-only path OK |
| T108 | acceptEdits + tool-use | unexpected_pass | issue not deterministic |
| T109 | compatibility assessment | unstable | layered validation recommended |

### 关键发现

1. text-only 链路在 T103/T107/T108 三次验证中稳定可用
2. tool-use 兼容性不稳定：T103 超时 vs T108 通过
3. full loop 未验证成功：T100/T102 均超时
4. T108 单次 unexpected_pass 不具备统计意义

## Decision

```text
DECISION_OPTION=A
DECISION_NAME=Continue Zhipu proxy with layered stability validation
NEXT_EXECUTION_ALLOWED=no
NEXT_REAL_TASK_ALLOWED=no
NEXT_SMOKE_TEST_ALLOWED=no
```

### 选择路线 A 的理由

1. T108 unexpected_pass 说明 tool-use 不一定完全不可用
2. 但 T100/T102 真实任务仍未稳定通过
3. T103/T108 结果不一致，兼容性存在间歇性
4. 路线 A 符合当前用户实际环境，成本最低
5. 分层验证可以科学评估 tool-use 兼容性

### 后续任务路线

| Task | 目标 |
|------|------|
| T111 | 设计 layered Claude Code stability validation protocol |
| T112 | 实现 text-only stability check dry-run/report |
| T113 | 执行 Layer 1 text-only stability validation |
| T114 | 执行 Layer 2 controlled single-file tool-use stability validation |
| T115 | 执行 Layer 3 runner-level minimal Claude call validation |
| T116 | 人工决策是否恢复 G008/G009 run-project-task-full smoke test |

## Safety Result

| 检查项 | 结果 |
|--------|------|
| 是否运行 run-project-task-full | no |
| 是否调用 Claude Code | no |
| 是否执行真实任务 | no |
| 是否修改业务代码 | no |
| 是否修改框架代码 | no |
| 是否使用 bypassPermissions | no |
| 是否自动 Git backup | no |

## Next

T111：设计 layered Claude Code stability validation protocol
