# T199 Dev Report: 设计 API 429 / 5 小时限额恢复机制

TASK=T199
DESIGN_STATUS=done
FILES_CREATED=docs/stage12-rate-limit-recovery-design.md, reports/dev/T199-dev-report.md
FILES_MODIFIED=docs/tasks.md
BUSINESS_CODE_CHANGED=no
FRAMEWORK_CODE_CHANGED=no
RUNNER_CHANGED=no
TOOLS_CHANGED=no
AGENTS_CHANGED=no
REAL_EXECUTION_CHANGED=no
CLAUDE_AGENT_SDK_INTEGRATED=no
RATE_LIMIT_RECOVERY_DESIGNED=yes
ERROR_DETECTION_RULES_DESIGNED=yes
RESET_TIME_EXTRACTION_DESIGNED=yes
RATE_LIMIT_RECOVERY_STATE_DESIGNED=yes
RECOVERY_DECISION_DESIGNED=yes
WORKSPACE_RECHECK_RULES_DESIGNED=yes
NEXT_PENDING_STAGE_RECHECK_DESIGNED=yes
DANGEROUS_RESUME_POINTS_DESIGNED=yes
RATE_LIMIT_RECOVERY_IMPLEMENTED=no
RUN_STATE_MANAGER_MODIFIED=no
RUNNER_CHANGED=no
RUNTIME_CREATED=no
REAL_RESUME_ENABLED=no
GIT_COMMANDS_EXECUTED=no
CHECK_RESULT=pass
NEXT_PENDING=T200
NEXT_STAGE=Stage 12

---

## 1. 本次只做设计

本任务只设计 API 429 / 5 小时限额恢复机制，不实现任何代码。

## 2. API 429 / 5 小时限额检测规则

设计了 10 种错误检测类型：HTTP 429、provider error code 1308、中文 5 小时限额、reset time 信息、rate limit 关键字、quota exceeded、too many requests、CLI stdout/stderr 429、JSON error payload。与当前 `report_manager.py:analyze_claude_output()` 的检测规则兼容并扩展。

## 3. reset_at 提取规则

设计了 6 种时间格式解析：中文格式、ISO 8601 UTC、ISO 8601 偏移、Unix timestamp、Retry-After header、provider-specific reset field。无法提取时 fail closed 使用默认 5 小时后。提取后同时保存原始字符串和标准化 UTC 字符串。

## 4. RateLimitRecoveryState 用途

24 字段 dataclass，记录 rate-limit 事件的完整上下文：检测信息（provider、error_code、error_message、raw_payload、request_id）、reset time（raw + UTC + retry_after）、捕获上下文（task、stage、step）、关联（run_id、checkpoint_id、checkpoint_path、run_state_path）、恢复控制（workspace_recheck_required、next_pending/stage_before_wait、resume_allowed、user_confirmation）。

## 5. RecoveryDecision 用途

18 字段 dataclass，综合所有检查结果生成恢复决策：总体判断（ok、can_wait、can_resume）、reset 检查（reset_at_utc、reset_passed）、workspace 检查（clean、dirty、unclassified）、一致性检查（next_pending_matches、next_stage_matches）、checkpoint 检查（valid）、人工确认（required）、阻塞信息（blocked_reason、warnings）、下一步行动（resume/fail_closed/wait_for_rate_limit/wait_for_user_confirmation）。

## 6. workspace recheck 规则

7 种 workspace 状态判断：clean → 继续、dirty+allowed → 人工确认、dirty+unclassified → fail closed、staged files → fail closed 或人工确认、deleted files → fail closed、runner/tools/agents 变化 → fail closed、tasks.md 不一致 → fail closed。与 T198 验证结果完全一致。

## 7. NEXT_PENDING / NEXT_STAGE recheck 规则

4 种不一致处理：NEXT_PENDING 不匹配 → fail closed、NEXT_STAGE 不匹配 → fail closed、任务已 done 但 checkpoint 仍 running → fail closed、tasks.md 无法解析 → fail closed。可直接调用 task_monitor.py 的 parse_next_pending/parse_next_stage。

## 8. dangerous resume points

11 种不允许自动 resume 的中断点：git add 后 commit 前、commit 后 push 前、push 中、文件写入中间态、tasks.md 修改中间态、runner 真实执行中、controlled rework 中、GitBackupGate action 中、external request apply 中、proposal apply 中、unknown step。判断依据是 checkpoint 的 step_name 和 status。

## 9. T200 实现范围

推荐创建独立 tools/rate_limit_recovery.py（而非扩展 run_state_manager.py），理由：避免影响已有工具、职责清晰、解耦、实现风险低。T200 范围：3 个 dataclass + 3 个 dry-run 子命令（parse-error、plan-wait、evaluate-recovery）+ reports/rate-limit-recovery/ 输出。不修改 runner.py、不启用真实等待/resume、不执行 Git。

## 10. 未创建 rate-limit recovery 工具

未创建 tools/rate_limit_recovery.py。

## 11. 未修改 run_state_manager.py

未修改 tools/run_state_manager.py。

## 12. 未修改 runner.py

未修改 runner.py。

## 13. 未修改 tools

未修改 tools/ 下任何文件。

## 14. 未修改 agents

未修改 agents/ 下任何文件。

## 15. 未修改业务代码

未修改业务逻辑代码。

## 16. 未启用真实恢复

未启用任何真实的 rate-limit 等待或自动恢复。

## 17. 未执行 Git

未执行 git add、git commit、git push。GIT_COMMANDS_EXECUTED=no。
