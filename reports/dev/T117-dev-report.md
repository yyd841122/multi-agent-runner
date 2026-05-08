# T117 Dev Report

## Task

实现 proposal parser dry-run。

## Scope

本轮只实现 parser dry-run，不实现 validator，不应用 patch，不执行 command，不真实执行任务。

## Background

- T115 设计了 no-tool-use safe execution fallback strategy
- T116 设计了 no-tool-use execution proposal schema（22 required fields, 5 proposal types, 30 validation rules, 20 failure cases）
- T113 Layer 1 text-only validation: 6/6 pass
- T114 Layer 2 tool-use validation: 0/3 pass (timeout)
- Model role shifted from "direct executor" to "structured output provider"
- Runner takes over actual execution control

## Changed Files

| File | Change Type | Description |
|------|-------------|-------------|
| tools/continuous_task_planner.py | modified | Added parser dataclass, parser function, and 7 dry-run samples |
| runner.py | modified | Added no-tool-use-parse-proposal CLI command |
| docs/tasks.md | modified | T117 status update |
| reports/checks/T117-proposal-parser-dry-run-check.md | new | Check report for 7 scenarios |
| reports/dev/T117-dev-report.md | new | This file |
| memory/lessons.md | modified | Parser dry-run lesson |
| memory/pitfalls.md | modified | Parser implementation pitfall |

## Implementation

### NoToolUseProposalParseResult

Dataclass with 17 fields tracking parser result:

- Core fields: proposal_version, execution_mode, task_id, task_title, change_type, target_files, proposed_commands, expected_reports
- Safety fields (parser reads, doesn't validate): safety_declarations_present, human_review_required, auto_continue_to_next_task, auto_git_backup
- Parse metadata: next_action, required_fields_missing, yaml_parse_error, parse_status, check_result, message

### parse_no_tool_use_execution_proposal()

Four-step parsing process:

1. Extract YAML from text: supports ```proposal, ```yaml fenced blocks, and raw YAML text
2. Parse YAML using PyYAML safe_load
3. Check 9 top-level required fields + 2 task sub-fields + 7 safety sub-fields
4. Check execution_mode equals "no_tool_use_single_task_proposal"

Returns one of four parse_status values:
- `parsed`: all fields present and execution_mode correct
- `failed_to_parse`: YAML syntax error or no YAML found
- `missing_required_fields`: required fields missing
- `invalid_execution_mode`: execution_mode doesn't match

### run_no_tool_use_proposal_parser_dry_run()

Built-in sample text for 7 scenarios:

| Sample | Description | Expected CHECK_RESULT |
|--------|-------------|----------------------|
| pass | Complete valid proposal | pass |
| missing-required-field | Missing scope section | fail |
| invalid-yaml | Malformed YAML syntax | fail |
| invalid-execution-mode | execution_mode="direct_tool_use_execution" | fail |
| missing-safety | Safety section completely missing | fail |
| auto-continue-requested | auto_continue_to_next_task="yes" | fail |
| auto-git-backup-requested | auto_git_backup="yes" | fail |

### runner.py CLI

New command: `python runner.py no-tool-use-parse-proposal [--sample <name>]`

Output includes all key fields as KEY=VALUE pairs for machine parsing.

## Behavior

### YAML Extraction

- First tries ```proposal fenced block (matching T116 schema recommendation)
- Falls back to ```yaml fenced block
- Finally assumes entire text is YAML (strips markdown headings)

### Field Parsing

- Uses PyYAML safe_load for YAML parsing
- Extracts target_files from changes.target_files[].path
- Extracts commands from commands.proposed[].command
- Extracts reports from reports.expected[].path

### Missing Required Fields

- Reports all missing field names in required_fields_missing list
- Still extracts as many fields as possible from the partial data
- Returns parse_status="missing_required_fields" with check_result="fail"

### Invalid YAML

- Catches yaml.YAMLError and returns parse_status="failed_to_parse"
- Includes original error message in yaml_parse_error field

### Safety Violations

- auto-continue-requested: parser succeeds but check_result=fail because auto_continue_to_next_task="yes" violates safety constraint
- auto-git-backup-requested: parser succeeds but check_result=fail because auto_git_backup="yes" violates safety constraint
- Full validation of all 7 safety fields is deferred to T118 validator

## Safety Rules

| Check | Result |
|-------|--------|
| no validator | yes |
| no patch apply | yes |
| no command execution | yes |
| no run-project-task-full call | yes |
| no Claude Code call | yes |
| no business code modification | yes |
| no real task execution | yes |
| no auto-continue | yes |
| no auto Git backup | yes |
| human review required | yes |
| no bypass permissions | yes |

## Verification

7 scenarios verified in `reports/checks/T117-proposal-parser-dry-run-check.md`:

| Scenario | PARSE_STATUS | CHECK_RESULT |
|----------|-------------|-------------|
| pass | parsed | pass |
| missing-required-field | missing_required_fields | fail |
| invalid-yaml | failed_to_parse | fail |
| invalid-execution-mode | invalid_execution_mode | fail |
| missing-safety | missing_required_fields | fail |
| auto-continue-requested | parsed | fail |
| auto-git-backup-requested | parsed | fail |

7/7 PASS.

## Next

T118: 实现 allowed scope validator dry-run
