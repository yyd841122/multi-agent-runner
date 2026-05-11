# T160 Dev Report：修复 task_monitor.py 解析历史 NEXT_PENDING / NEXT_STAGE 的 bug

## 基本信息

- TASK=T160
- ROLE=Bugfix Agent + Stage 8 Monitor Parser Fixer
- DATE=2026-05-11
- PROJECT_ROOT=E:/github_project/multi-agent-runner
- LAST_COMMIT=92679d6 test: validate stage 8 monitor verify report loop

## Bug 描述

task_monitor.py 的 `parse_next_pending` 和 `parse_next_stage` 使用 `re.search()` 返回第一个匹配。

`docs/tasks.md` 中随着任务逐步完成，会积累多个历史 NEXT_PENDING / NEXT_STAGE 条目（每个任务完成时在其底部记录）。

`re.search()` 返回第一个匹配，导致解析到历史值而非当前最新值。

## Bug 影响

修复前：
- NEXT_PENDING 解析为 T075（历史值，实际应为 T160）
- NEXT_STAGE 解析为 Stage 6（历史值，实际应为 Stage 8）
- 导致 stage8-monitor-verify-report pipeline 中 monitor 返回错误的任务信息

## 修复方式

将 `parse_next_pending` 和 `parse_next_stage` 从 `re.search()` 改为 `re.findall()` + `matches[-1]`，取最后一个匹配。

与 `continuous_verifier.py` 中的对应解析逻辑保持一致。

### 修复前代码（parse_next_pending）

```python
def parse_next_pending(tasks_text: str) -> str | None:
    m = re.search(r"<!--\s*NEXT_PENDING\s*=\s*(T\d+)\s*-->", tasks_text)
    if m:
        return m.group(1)
    m = re.search(r"^NEXT_PENDING\s*=\s*(T\d+)\s*$", tasks_text, re.MULTILINE)
    if m:
        return m.group(1)
    return None
```

### 修复后代码（parse_next_pending）

```python
def parse_next_pending(tasks_text: str) -> str | None:
    matches = re.findall(r"<!--\s*NEXT_PENDING\s*=\s*(T\d+)\s*-->", tasks_text)
    if matches:
        return matches[-1]
    matches = re.findall(r"^NEXT_PENDING\s*=\s*(T\d+)\s*$", tasks_text, re.MULTILINE)
    if matches:
        return matches[-1]
    return None
```

### 修复前代码（parse_next_stage）

```python
def parse_next_stage(tasks_text: str) -> str | None:
    m = re.search(r"<!--\s*NEXT_STAGE\s*=\s*(Stage\s+\d+)\s*-->", tasks_text)
    if m:
        return m.group(1)
    m = re.search(r"^NEXT_STAGE\s*=\s*(Stage\s+\d+)\s*$", tasks_text, re.MULTILINE)
    if m:
        return m.group(1)
    return None
```

### 修复后代码（parse_next_stage）

```python
def parse_next_stage(tasks_text: str) -> str | None:
    matches = re.findall(r"<!--\s*NEXT_STAGE\s*=\s*(Stage\s+\d+)\s*-->", tasks_text)
    if matches:
        return matches[-1]
    matches = re.findall(r"^NEXT_STAGE\s*=\s*(Stage\s+\d+)\s*$", tasks_text, re.MULTILINE)
    if matches:
        return matches[-1]
    return None
```

## 修复后验证

### python -m py_compile tools/task_monitor.py

通过，无错误。

### python tools/task_monitor.py

```
MONITOR_RESULT=fail
FAIL_REASON=dirty_workspace
NEXT_ACTION=stop
```

MONITOR_RESULT=fail 是因为当前工作区 dirty（已修改 task_monitor.py），属于预期行为。

直接调用解析函数验证：

```
NEXT_PENDING=T160
NEXT_STAGE=Stage 8
```

修复前这两个值分别是 T075 和 Stage 6，修复后已正确解析为 T160 和 Stage 8。

## 修复前为什么会识别历史 T075 / Stage 6

`docs/tasks.md` 中 T075 任务完成时在其底部记录了 `<!-- NEXT_PENDING=T075 -->` 和 `<!-- NEXT_STAGE=Stage 6 -->`。后续任务（T076-T159）完成时也各自记录了对应的 NEXT_PENDING / NEXT_STAGE。

`re.search()` 返回第一个匹配，即 T075 下方的历史值，而非文件中最后一个（最新的）NEXT_PENDING / NEXT_STAGE。

## 修复后为什么会识别最新 T160 / Stage 8

`re.findall()` 返回所有匹配的列表，`matches[-1]` 取列表中最后一个元素，即文件中最后出现的 NEXT_PENDING / NEXT_STAGE，也就是当前最新值。

## 未修改的文件

- runner.py：未修改
- tools/continuous_verifier.py：未修改
- tools/execution_report_writer.py：未修改
- 业务代码：未修改

## 未执行的操作

- 未执行真实 run-project-loop
- 未自动 git add
- 未自动 git commit
- 未自动 git push
- 未调用 Claude Agent SDK
- 未进入 Stage 9

## 安全保证

- TASK=T160
- BUGFIX_STATUS=done
- BUSINESS_CODE_CHANGED=no
- FRAMEWORK_CODE_CHANGED=yes
- RUNNER_CHANGED=no
- TOOLS_CHANGED=yes
- REAL_EXECUTION_CHANGED=no
- CLAUDE_AGENT_SDK_INTEGRATED=no
- BUG_FIXED=parse_next_pending_parse_next_stage_take_last_match
- TASK_MONITOR_PARSE_NEXT_PENDING_FIXED=yes
- TASK_MONITOR_PARSE_NEXT_STAGE_FIXED=yes
- SELF_CHECK_COMMAND=python tools/task_monitor.py
- SELF_CHECK_NEXT_PENDING=T160
- SELF_CHECK_NEXT_STAGE=Stage 8
- PY_COMPILE_STATUS=pass
- AUTO_COMMIT_TRIGGERED=no
- AUTO_PUSH_TRIGGERED=no
- REAL_RUN_PROJECT_LOOP_EXECUTED=no
- STAGE9_ENTERED=no

## 文件清单

### 本次新增文件

- reports/dev/T160-dev-report.md

### 本次修改文件

- tools/task_monitor.py（parse_next_pending / parse_next_stage 改为 re.findall() + matches[-1]）
- docs/tasks.md（T160 done，新增 T161 pending，NEXT_PENDING → T161）

## 最终状态

```
TASK=T160
BUGFIX_STATUS=done
FILES_CREATED=reports/dev/T160-dev-report.md
FILES_MODIFIED=tools/task_monitor.py, docs/tasks.md
BUSINESS_CODE_CHANGED=no
FRAMEWORK_CODE_CHANGED=yes
RUNNER_CHANGED=no
TOOLS_CHANGED=yes
REAL_EXECUTION_CHANGED=no
CLAUDE_AGENT_SDK_INTEGRATED=no
BUG_FIXED=parse_next_pending_parse_next_stage_take_last_match
TASK_MONITOR_PARSE_NEXT_PENDING_FIXED=yes
TASK_MONITOR_PARSE_NEXT_STAGE_FIXED=yes
SELF_CHECK_COMMAND=python tools/task_monitor.py
SELF_CHECK_NEXT_PENDING=T160
SELF_CHECK_NEXT_STAGE=Stage 8
PY_COMPILE_STATUS=pass
CHECK_RESULT=pass
NEXT_PENDING=T161
NEXT_STAGE=Stage 8
```
