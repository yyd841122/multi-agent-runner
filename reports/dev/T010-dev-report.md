# T010 开发报告 — 多任务自动执行循环

## 任务信息

- 任务编号：T010
- 任务名称：多任务自动执行循环
- 角色：Developer
- 状态：done

## 目标

让 runner.py 可以连续执行多个 pending 任务，直到没有 pending 任务或达到最大轮数。

## 实现方案

### 修改文件

**runner.py** — 唯一修改文件，新增两个函数：

1. **`_execute_one_task(content: str) -> tuple[str, str]`**（第 384-464 行）
   - 内部函数，执行单个 pending 任务的单步闭环
   - 输入：当前 tasks.md 文件内容
   - 返回：`(status, message)` 元组
   - status 可能值：
     - `"no_pending"` — 没有 pending 任务
     - `"done"` — 执行成功且有完成证据，已标记 done
     - `"success_no_evidence"` — 执行成功但缺少完成证据
     - `"failed"` — 执行失败
   - 每轮逻辑：查找 pending → 标记 in_progress → 生成提示词 → 调用 Claude Code → 保存结果 → 判断结果 → 有证据则 done

2. **`run_loop(max_rounds: int = 10)`**（第 467-508 行）
   - 对外命令函数，循环调用 `_execute_one_task()`
   - 循环停止条件：
     - 没有 pending 任务 → 输出"所有 pending 任务已执行完毕"
     - 任务失败 → 停止循环，提示失败原因，任务保持 in_progress
     - 任务成功但缺少完成证据 → 停止循环，提示缺少文件，任务保持 in_progress
     - 达到最大轮数 → 停止循环，提示已达到限制
   - 循环结束后打印汇总：停止原因、已完成任务数、任务列表

3. **CLI 命令入口**（第 539-541 行）
   - 新增 `run-loop` 命令：`python runner.py run-loop [最大轮数]`
   - 可选参数指定最大轮数，默认 10

### 设计要点

- `_execute_one_task()` 是无副作用的纯逻辑函数（除了调用 Claude Code 和写文件），返回状态码供 `run_loop()` 判断是否继续
- `run_loop()` 不修改已有函数的行为，`run_next()` 和 `retry_current()` 保持不变
- 循环只在任务完全成功（done）时继续，任何异常情况都停止循环

## 验收标准对照

| 验收标准 | 状态 |
|---------|------|
| 可以连续查找 pending 任务 | 通过 — 每轮重新读取 tasks.md 查找 |
| 每轮可以自动生成提示词 | 通过 — `_execute_one_task` 内调用 `build_agent_prompt()` |
| 每轮可以自动标记 in_progress | 通过 — 调用 `update_task_status()` |
| 每轮可以自动调用 Claude Code | 通过 — 调用 `run_claude_code()` |
| 每轮可以自动判断执行结果 | 通过 — 调用 `analyze_claude_output()` |
| 成功时自动 done | 通过 — 有完成证据时自动标记 |
| 失败时停止循环并提示原因 | 通过 — status="failed" 时 break 并输出原因 |
| 支持最大轮数限制 | 通过 — `max_rounds` 参数，默认 10，可通过 CLI 指定 |

## 使用方式

```bash
# 默认最大 10 轮
python runner.py run-loop

# 指定最大 5 轮
python runner.py run-loop 5
```

## 注意事项

- 循环不会跳过失败任务，遇到失败即停止
- 缺少完成证据也会停止循环（可用 `retry-current` 重试单个任务后再继续）
- `_execute_one_task()` 是内部函数（下划线前缀），不直接暴露给 CLI
