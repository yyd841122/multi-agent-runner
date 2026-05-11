# T156 Dev Report：实现 continuous_verifier.py

## 基本信息

- TASK=T156
- ROLE=Dev Agent + Stage 8 Verification Module Implementer
- DATE=2026-05-11
- PROJECT_ROOT=E:/github_project/multi-agent-runner
- LAST_COMMIT=f6f070f feat: add stage 8 task monitor

## 实现目标

实现 Stage 8 执行后结果确定性验证模块 tools/continuous_verifier.py。

## 实现内容

### 新增文件

1. tools/continuous_verifier.py

### 模块功能

| 函数 | 职责 |
|------|------|
| read_text_file(path) | 读取文本文件，不存在返回空字符串 |
| parse_next_pending(tasks_text) | 从 tasks.md 识别最后一个 NEXT_PENDING=Txxx |
| parse_next_stage(tasks_text) | 从 tasks.md 识别最后一个 NEXT_STAGE=Stage N |
| is_task_marked_done(tasks_text, task_id) | 判断指定任务是否标记为 done |
| report_contains_check_result_pass(report_text) | 检查报告是否包含 CHECK_RESULT=pass |
| report_confirms_max_tasks_one(report_text) | 检查报告是否确认 MAX_TASKS=1 |
| report_confirms_no_unlimited_continuation(report_text) | 检查报告是否确认无无限连续执行 |
| report_confirms_no_next_task_executed(report_text) | 检查报告是否确认无 next task executed |
| report_confirms_no_auto_commit_push(report_text) | 检查报告是否确认无 auto commit/push |
| get_git_changed_files(repo_root) | 通过 git status --short 获取变更文件列表 |
| classify_changed_files(changed_files, allowed_paths) | 判断变更文件是否全部在允许范围内 |
| verify_continuous_result(repo_root, task_id, ...) | 核心验证函数，输出 ContinuousVerifyResult |

### ContinuousVerifyResult 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| project_root | str | 项目根路径 |
| verify_timestamp | str | 验证时间戳 |
| task_id | str | 验证的任务编号 |
| expected_next_pending | str | 预期 NEXT_PENDING |
| actual_next_pending | str \| None | 实际 NEXT_PENDING |
| expected_next_stage | str | 预期 NEXT_STAGE |
| actual_next_stage | str \| None | 实际 NEXT_STAGE |
| task_marked_done | bool | 任务是否标记为 done |
| report_exists | bool | 报告文件是否存在 |
| check_result_pass | bool | 报告中 CHECK_RESULT 是否为 pass |
| max_tasks_one_confirmed | bool | 报告是否确认 MAX_TASKS=1 |
| unlimited_continuation | bool | 是否检测到无限连续执行 |
| next_task_executed | bool | 是否检测到 next task executed |
| auto_commit_triggered | bool | 是否检测到 auto commit |
| auto_push_triggered | bool | 是否检测到 auto push |
| forbidden_files_changed | bool | 是否出现 forbidden path 修改 |
| unclassified_changes | bool | 是否出现 unclassified changes |
| unclassified_files | list[str] | 未分类变更文件列表 |
| ok | bool | 验证是否通过 |
| fail_reason | str \| None | 失败原因 |
| next_action | str | continue_to_report_writer / stop |
| verifier_modified_files | bool | 始终 False，只读不写 |

### Fail-closed 规则

| 场景 | fail_reason 片段 | 行为 |
|------|------------------|------|
| docs/tasks.md 不存在 | tasks_md_not_found | stop |
| report_path 不存在 | missing_report | stop |
| task_id 未标记 done | task_not_done:xxx | stop |
| NEXT_PENDING 不匹配 | next_pending_mismatch | stop |
| NEXT_STAGE 不匹配 | next_stage_mismatch | stop |
| 报告无 CHECK_RESULT=pass | check_result_not_pass | stop |
| 报告无 MAX_TASKS=1 | max_tasks_not_one | stop |
| 报告有无限连续执行 | unlimited_continuation_detected | stop |
| 报告有 next_task_executed | next_task_executed_detected | stop |
| 报告有 auto commit | auto_commit_detected | stop |
| 报告有 auto push | auto_push_detected | stop |
| forbidden files changed | forbidden_files_changed | stop |
| unclassified changes | unclassified_changes | stop |

### Forbidden Paths

- runner.py
- .git/
- .github/
- pyproject.toml
- requirements.txt
- package.json

### CLI 参数

```
python tools/continuous_verifier.py --task Txxx --expected-next Tyyy --expected-stage "Stage N" --report path/to/report.md --allowed path1 --allowed path2
```

## 运行验证

执行了自检命令，使用 T153 验证报告：

```
python tools/continuous_verifier.py --task T153 --expected-next T156 --expected-stage "Stage 8" --report reports/checks/T153-max-tasks-1-real-controlled-single-step-validation.md --allowed docs/tasks.md --allowed reports/checks/T153-max-tasks-1-real-controlled-single-step-validation.md --allowed reports/stage8/stage8-real-controlled-single-step-trial-approval-record.md --allowed reports/stage8/stage8-real-controlled-single-step-trial-checkpoint.md --allowed reports/stage8/stage8-real-controlled-single-step-trial-report.md --allowed tools/continuous_verifier.py
```

结果：

```
VERIFY_RESULT=pass
TASK=T153
EXPECTED_NEXT_PENDING=T156
ACTUAL_NEXT_PENDING=T156
EXPECTED_NEXT_STAGE=Stage 8
ACTUAL_NEXT_STAGE=Stage 8
TASK_MARKED_DONE=yes
REPORT_EXISTS=yes
CHECK_RESULT_PASS=yes
MAX_TASKS_ONE_CONFIRMED=yes
UNLIMITED_CONTINUATION=no
NEXT_TASK_EXECUTED=no
AUTO_COMMIT_TRIGGERED=no
AUTO_PUSH_TRIGGERED=no
FORBIDDEN_FILES_CHANGED=no
UNCLASSIFIED_CHANGES=no
NEXT_ACTION=continue_to_report_writer
```

自检通过，所有验证项正确。

## 开发过程中修复的问题

1. parse_next_pending/parse_next_stage 初始实现使用 re.search（匹配第一个），但 tasks.md 中有多个 NEXT_PENDING/NEXT_STAGE（每个任务完成时记录）。修改为 re.findall 取最后一个。
2. is_task_marked_done 初始实现使用正则块匹配，对多行 DOTALL 模式处理不稳定。修改为逐行扫描方式，更可靠。

## 未修改文件

- runner.py — 未修改
- execution_report_writer.py — 未实现
- auto_mending_planner.py — 未实现
- run_state_manager.py — 未实现

## 安全保证

- TASK=T156
- IMPLEMENTATION_STATUS=done
- BUSINESS_CODE_CHANGED=no
- FRAMEWORK_CODE_CHANGED=yes
- RUNNER_CHANGED=no
- TOOLS_CHANGED=yes
- REAL_EXECUTION_CHANGED=no
- CLAUDE_AGENT_SDK_INTEGRATED=no
- VERIFIER_MODULE_CREATED=yes
- MAX_TASKS_EXCEEDED_1=no
- REAL_CONTINUOUS_EXECUTION_STARTED=no
- AUTO_COMMIT_TRIGGERED=no
- AUTO_PUSH_TRIGGERED=no
- STAGE9_ENTERED=no

## 文件清单

### 本次新增文件

- tools/continuous_verifier.py
- reports/dev/T156-dev-report.md

### 本次修改文件

- docs/tasks.md（T156 状态更新为 done，NEXT_PENDING 改为 T157）

## 最终状态

```
TASK=T156
IMPLEMENTATION_STATUS=done
FILES_CREATED=tools/continuous_verifier.py, reports/dev/T156-dev-report.md
FILES_MODIFIED=docs/tasks.md
BUSINESS_CODE_CHANGED=no
FRAMEWORK_CODE_CHANGED=yes
RUNNER_CHANGED=no
TOOLS_CHANGED=yes
REAL_EXECUTION_CHANGED=no
CLAUDE_AGENT_SDK_INTEGRATED=no
VERIFIER_MODULE_CREATED=yes
VERIFIER_SELF_CHECK=pass
WORKTREE_STATUS=dirty
CHECK_RESULT=pass
NEXT_PENDING=T157
NEXT_STAGE=Stage 8
```
