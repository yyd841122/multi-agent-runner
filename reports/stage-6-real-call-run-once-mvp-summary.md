# Stage 6 Real-call Run-once MVP Summary

## Goal

本小结覆盖 Stage 6 中 real-call run-once safety shell + child command parser dry-run 的 MVP 成果。

**重要说明**：当前仍然不是"真实执行 MVP"。系统可以构造调用信息、解析子命令输出，但尚未真实调用 `run_project_task_full()`。

## Completed Scope

| # | 任务 | 角色 | 说明 |
|---|------|------|------|
| T084 | 真实调用最小实现设计 | Designer | 设计 run-once 最小协议、数据结构、workspace 检测、推断逻辑 |
| T085 | real-call run-once safety shell | Developer | 实现 RealCallRunOnceResult + safety shell 函数 + CLI 参数 |
| T086 | child command parser dry-run | Developer | 实现 parse_child_command_output + workspace 辅助函数 + dry-run CLI |
| T087 | real-call-run-once 拒绝验证 | Tester | 验证 10 拒绝场景 + 1 对照场景，全部 PASS |
| T088 | simulated CHECK_RESULT=pass 验证 | Tester | CLI 样例 + 函数级验证，12 断言全部 PASS |
| T089 | simulated CHECK_RESULT=fail 验证 | Tester | CLI 样例 + 函数级验证，12 断言全部 PASS |

## Implemented Commands

```bash
# run-once safety shell（双重确认，不执行真实调用）
python runner.py run-project-loop \
  --project . \
  --max-tasks 1 \
  --execute \
  --confirm EXECUTE_PROJECT_LOOP \
  --real-call \
  --real-confirm EXECUTE_REAL_TASK_ONCE \
  --real-call-run-once

# child parser dry-run（解析内置样例）
python runner.py parse-child-output-dry-run --sample pass
python runner.py parse-child-output-dry-run --sample fail
```

## Current Capabilities

当前系统可以：

- 接收 `--real-call-run-once` 参数并通过双重确认进入 run-once safety shell
- 复用 `validate_real_call_safety()` 做前置检查（9 层级）
- 构造未来真实调用的 command 字符串
- 构造未来真实调用的 function_call 字符串
- 输出 RealCallRunOnceResult（26 字段）
- 解析 child command stdout 样例（KEY=value 格式）
- 正确解析 CHECK_RESULT=pass（TASK_STATUS=done）
- 正确解析 CHECK_RESULT=fail（TASK_STATUS=failed）
- 正确解析 REPORT_PATHS（逗号分隔为 list）
- 缺失字段时安全降级为 unknown 或 fail
- 验证拒绝场景不真实执行（10/10 PASS）
- 验证 pass 后必须停止
- 验证 fail 后必须停止

## Important Non-capabilities

当前系统仍然**不能**：

- 真实调用 `run_project_task_full()`
- 真实执行任务
- 调用 Claude Code
- 修改业务代码
- 自动进入下一任务
- 自动 Git 备份
- 自动返工
- 执行多个任务（max_tasks>1 真实执行）
- 无人值守连续推进

## Safety Guarantees

| 保证项 | 说明 |
|--------|------|
| 双重确认必须存在 | EXECUTE_PROJECT_LOOP + EXECUTE_REAL_TASK_ONCE |
| max_tasks=1 only | 不允许 max_tasks>1 |
| run-once safety shell 不执行命令 | RUN_PROJECT_TASK_FULL_CALLED=no |
| parser dry-run 只解析样例输出 | 不执行任何命令 |
| pass 后停止 | AUTO_CONTINUE_TO_NEXT_TASK=false |
| fail 后停止 | AUTO_CONTINUE_TO_NEXT_TASK=false |
| REAL_TASK_EXECUTION=no | 始终为 no |
| RUN_PROJECT_TASK_FULL_CALLED=no | 始终为 no |
| CLAUDE_CODE_CALLED=no | 始终为 no（safety shell 模式） |
| BUSINESS_CODE_CHANGED=no | 始终为 no（safety shell 模式） |
| AUTO_CONTINUE_TO_NEXT_TASK=no | 硬编码 false |
| AUTO_GIT_BACKUP=no | 硬编码 false |

## Verification Summary

| 任务 | 验证内容 | 场景数 | 结果 |
|------|----------|--------|------|
| T085 | run-once safety shell 验证 | 12 | 全部 PASS |
| T087 | real-call-run-once 拒绝验证 | 10+1 | 全部 PASS |
| T086 | child parser dry-run 验证 | 10+10 | 全部 PASS |
| T088 | simulated CHECK_RESULT=pass | CLI+函数级 | 全部 PASS |
| T089 | simulated CHECK_RESULT=fail | CLI+函数级 | 全部 PASS |

## Key Files

| 文件 | 说明 |
|------|------|
| tools/continuous_task_planner.py | RealCallRunOnceResult + safety shell + parser 函数 |
| runner.py | --real-call-run-once + parse-child-output-dry-run CLI |
| docs/run-project-task-full-real-call-minimal-design.md | T084 设计文档 |
| reports/checks/T087-real-call-run-once-rejection-check.md | 拒绝验证报告 |
| reports/checks/T088-simulated-child-check-result-pass-check.md | pass 验证报告 |
| reports/checks/T089-simulated-child-check-result-fail-check.md | fail 验证报告 |
| docs/tasks.md | 任务状态跟踪 |

## Recommended Next Step

建议下一步：

**T091：设计首次真实调用 run-project-task-full 的验收协议**

注意：下一步建议仍然先设计，不直接实现真实执行。从 safety shell + parser dry-run 到真实执行之间，需要单独设计验收协议，确认真实调用前的环境、任务选择、预期结果和回退策略。

## Stage 6 Commit Chain

```
f6ea1d8 test: verify simulated child check-result fail
3cd34ec test: verify simulated child check-result pass
5e298f5 test: verify real-call run-once rejection
64d32ae feat: add child command parser dry-run
6eed0cd feat: add real-call run-once safety shell
8c4c00b docs: design real-call run-once minimal protocol
```

## Final Status

```
REAL_CALL_RUN_ONCE_MVP_STATUS=done
REAL_TASK_EXECUTION=no
RUN_PROJECT_TASK_FULL_CALLED=no
CLAUDE_CODE_CALLED=no
BUSINESS_CODE_CHANGED=no
AUTO_CONTINUE_TO_NEXT_TASK=no
AUTO_GIT_BACKUP=no
CHECK_RESULT=pass
NEXT_PENDING=T091
NEXT_STAGE=Stage 7
```
