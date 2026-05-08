# No-Tool-Use Execution Proposal Schema

## Background

Stability validation results:

| Layer | Content | Result |
|-------|---------|--------|
| Layer 1 | text-only 6 calls | 6/6 pass |
| Layer 2 | acceptEdits + tool-use 3 calls | 0/3 pass (1st timeout at 120s) |
| Layer 3 | runner-level | Not executed (stopped after Layer 2 fail) |

T115 designed the no-tool-use fallback strategy. The core decision:

- Claude Code / domestic models act as "structured output providers" only
- Runner takes over actual execution control (parse, validate, apply, test, report)
- All model outputs use text-only / default mode, no tool-use dependency

T116 defines the proposal schema that models must follow in no-tool-use mode.

## Purpose

This schema defines the structured format that models must output in no-tool-use execution mode.

Models cannot:
- Directly write files
- Run commands
- Commit / push to Git

Models can only output structured proposals. The runner is responsible for:
1. Parse the proposal
2. Validate scope (files, commands, safety)
3. Classify changes (expected / unexpected)
4. Apply patches (Python direct file operations)
5. Execute allowed commands
6. Generate execution reports
7. Stop for human review

## Design Principles

| Principle | Description |
|-----------|-------------|
| text-only output only | Model outputs are pure text, never trigger tool-use |
| deterministic structure | Proposal format is fixed and machine-parseable |
| single-task scope | Each proposal targets exactly one task |
| explicit file list | All target files must be declared upfront |
| explicit patch proposal | File changes as unified diff patches |
| explicit command proposal | Commands to run must be declared upfront |
| explicit safety declarations | Safety fields are mandatory, not optional |
| no implicit execution | Runner never executes without explicit proposal |
| no auto-continue | Each execution stops for human review |
| no auto-git-backup | Git operations are never automatic |
| human review required | Every execution result requires human confirmation |

## Proposal Format

Recommended format: YAML wrapped in Markdown fenced code block (```proposal).

Using YAML because it is more readable than JSON for human review, and easier for models to generate correctly in text-only mode.

### Full Schema

```yaml
# === Header (required) ===
proposal_version: "1.0"
execution_mode: "no_tool_use_single_task_proposal"

# === Task Identification (required) ===
task:
  id: "Txxx"                          # Must match current task ID
  title: "Task title"                 # Human-readable task title
  source: "docs/tasks.md"             # Task source file

# === Intent (required) ===
intent:
  summary: "What this proposal intends to do"
  expected_outcome: "Expected result after execution"

# === Scope (required) ===
scope:
  allowed_files:                      # Files this proposal intends to touch
    - "path/to/file1"
    - "path/to/file2"
  forbidden_files:                    # Files this proposal must NOT touch
    - "runner.py"
    - "tools/*.py"
  business_code_change: "no"          # yes/no: does this change business code?
  framework_code_change: "no"         # yes/no: does this change framework code?

# === Changes (required) ===
changes:
  type: "doc_only"                    # doc_only / report_only / patch_proposal / command_only / mixed_safe_proposal
  target_files:
    - path: "path/to/file"
      change_type: "create"           # create / modify / delete
      reason: "Why this file needs change"

# === Patches (optional, required if changes.type is patch_proposal or mixed_safe_proposal) ===
patches:
  - file: "path/to/file"
    format: "unified_diff"
    content: |
      --- a/path/to/file
      +++ b/path/to/file
      @@ -10,3 +10,8 @@
      context line
      +new line 1
      +new line 2

# === Commands (optional) ===
commands:
  proposed:
    - command: "python runner.py test-game-task Gxxx"
      purpose: "Run test for task Gxxx"
      required: true                  # true = must pass for proposal to succeed
      allowlist_category: "test"      # test / validation / status

# === Reports (optional) ===
reports:
  expected:
    - path: "reports/dev/Txxx-dev-report.md"
      purpose: "Development report for task Txxx"

# === Safety (required) ===
safety:
  real_task_execution: "no"                   # Must be "no"
  run_project_task_full_called: "no"           # Must be "no"
  claude_code_tool_use_used: "no"              # Must be "no"
  auto_continue_to_next_task: "no"             # Must be "no"
  auto_git_backup: "no"                        # Must be "no"
  bypass_permissions_used: "no"                # Must be "no"
  human_review_required: "yes"                 # Must be "yes"

# === Validation (required) ===
validation:
  expected_check_result: "pass"                # pass / fail / manual_review
  success_criteria:
    - "File X exists and contains Y"
    - "Test command returns exit code 0"

# === Failure Handling (optional) ===
failure_handling:
  stop_conditions:
    - "If patch apply fails, stop and report"
    - "If test command fails, stop and report"

# === Next Action (required) ===
next_action:
  recommendation: "human_review"               # human_review / controlled_apply / block
```

## Required Fields

The following fields are mandatory. Missing any required field causes proposal rejection.

| Field | Type | Constraint | Description |
|-------|------|------------|-------------|
| proposal_version | string | Must be "1.0" | Schema version for forward compatibility |
| execution_mode | string | Must be "no_tool_use_single_task_proposal" | Ensures correct proposal type |
| task.id | string | Non-empty, must match current task | Task identifier |
| task.title | string | Non-empty | Human-readable task title |
| intent.summary | string | Non-empty | What the proposal intends to do |
| intent.expected_outcome | string | Non-empty | Expected result |
| scope.allowed_files | list[string] | At least 1 entry | Files the proposal may touch |
| scope.forbidden_files | list[string] | At least 1 entry | Files the proposal must not touch |
| scope.business_code_change | string | "yes" or "no" | Whether business code is modified |
| scope.framework_code_change | string | "yes" or "no" | Whether framework code is modified |
| changes.type | string | Must be valid proposal type | Type of changes proposed |
| changes.target_files | list[object] | At least 1 entry if type involves files | Target file declarations |
| safety.real_task_execution | string | Must be "no" | No direct task execution |
| safety.run_project_task_full_called | string | Must be "no" | No run-project-task-full call |
| safety.claude_code_tool_use_used | string | Must be "no" | No tool-use dependency |
| safety.auto_continue_to_next_task | string | Must be "no" | No auto-continue |
| safety.auto_git_backup | string | Must be "no" | No auto Git backup |
| safety.bypass_permissions_used | string | Must be "no" | No permission bypass |
| safety.human_review_required | string | Must be "yes" | Human review mandatory |
| validation.expected_check_result | string | "pass", "fail", or "manual_review" | Expected validation result |
| next_action.recommendation | string | "human_review", "controlled_apply", or "block" | Recommended next step |

## Optional Fields

The following fields are optional but must be present when their parent type requires them.

| Field | Required When | Description |
|-------|---------------|-------------|
| patches | changes.type is patch_proposal or mixed_safe_proposal | Unified diff patches to apply |
| commands | Task involves running test/validation commands | Commands to execute |
| commands.proposed[].allowlist_category | commands is present | Category for allowlist check |
| reports | Task expects report generation | Expected report file paths |
| failure_handling | Always optional | How to handle failure scenarios |
| intent.expected_outcome | Always required | Expected result description |
| validation.success_criteria | Always recommended | List of success conditions |

## Allowed Proposal Types

| Type | Description | Patches | Commands | Scope |
|------|-------------|---------|----------|-------|
| doc_only | Documentation-only changes (docs/, memory/) | No | No | docs/ files only |
| report_only | Report generation only (reports/) | No | No | reports/ files only |
| patch_proposal | Code/patch changes with unified diff | Yes | Optional | Depends on task |
| command_only | Only commands to run, no file changes | No | Yes | No file changes |
| mixed_safe_proposal | Combination of safe types | Yes | Yes | Must pass all sub-type rules |

### Type-specific Rules

**doc_only:**
- allowed_files must only contain paths under docs/ or memory/
- patches must not contain code file changes (.py, .js, .html, .css)
- business_code_change must be "no"
- framework_code_change must be "no"

**report_only:**
- allowed_files must only contain paths under reports/
- patches must not contain code file changes
- business_code_change must be "no"
- framework_code_change must be "no"

**patch_proposal:**
- patches field is required
- Each patch must be valid unified diff format
- Target files must match scope.allowed_files

**command_only:**
- commands field is required
- Each command must belong to an allowlist_category
- No file modifications proposed

**mixed_safe_proposal:**
- Combines multiple safe types
- Must satisfy all sub-type rules simultaneously
- Highest risk among safe types, requires extra scrutiny

## Forbidden Proposal Content

The following content in a proposal causes immediate rejection.

| Forbidden Content | Reason |
|-------------------|--------|
| Request for Claude Code to directly write files | Tool-use is unstable |
| Request for Claude Code to execute Bash commands | Execution must go through runner |
| git add / git commit / git push operations | Git operations controlled by dedicated step |
| run-project-task-full invocation | Prevents infinite recursion |
| Auto-continue to next task | Each execution requires human review |
| Bypass of runner safety gates | Safety gates are non-negotiable |
| Modification of forbidden_files | Scope violation |
| Omission of safety declarations | Safety is mandatory |
| Free-form unstructured text instead of proposal | Proposal must be machine-parseable |
| Environment variable or API key output | Security risk |
| Deletion of framework or business code files | Irreversible without backup |

## Validation Rules

The runner must validate the following rules when parsing a proposal.

### Structural Validation

| Rule | Check | On Failure |
|------|-------|------------|
| proposal_version supported | version in ["1.0"] | hard reject |
| execution_mode correct | mode == "no_tool_use_single_task_proposal" | hard reject |
| task.id matches current task | id == current_task_id | hard reject |
| task.id non-empty | len(id) > 0 | hard reject |
| task.title non-empty | len(title) > 0 | hard reject |
| intent.summary non-empty | len(summary) > 0 | hard reject |

### Scope Validation

| Rule | Check | On Failure |
|------|-------|------------|
| allowed_files not empty | len(allowed_files) > 0 | hard reject |
| forbidden_files not empty | len(forbidden_files) > 0 | hard reject |
| target files inside allowed scope | all target_files in allowed_files | hard reject |
| no target file in forbidden scope | no target_file in forbidden_files | hard reject |
| no path traversal | no ".." in file paths | hard reject |
| no absolute paths | all paths are relative | hard reject |

### Patch Validation (when present)

| Rule | Check | On Failure |
|------|-------|------------|
| patch format correct | format == "unified_diff" | hard reject |
| patch parseable | unified diff can be parsed | hard reject |
| patch file matches target | patch.file in allowed_files | hard reject |
| patch hunk headers valid | @@ markers are correct | hard reject |
| patch content non-empty | at least 1 addition or deletion | hard reject |

### Command Validation (when present)

| Rule | Check | On Failure |
|------|-------|------------|
| command allowlist check | category in ["test", "validation", "status"] | hard reject |
| no forbidden commands | no git add/commit/push, rm -rf, etc. | hard reject |
| no compound commands | no && or ; in commands | hard reject |

### Safety Validation

| Rule | Check | On Failure |
|------|-------|------------|
| safety declarations complete | all 7 safety fields present | hard reject |
| real_task_execution == "no" | Must be "no" | hard reject |
| run_project_task_full_called == "no" | Must be "no" | hard reject |
| claude_code_tool_use_used == "no" | Must be "no" | hard reject |
| auto_continue_to_next_task == "no" | Must be "no" | hard reject |
| auto_git_backup == "no" | Must be "no" | hard reject |
| bypass_permissions_used == "no" | Must be "no" | hard reject |
| human_review_required == "yes" | Must be "yes" | hard reject |

### Action Validation

| Rule | Check | On Failure |
|------|-------|------------|
| expected_check_result valid | value in ["pass", "fail", "manual_review"] | hard reject |
| next_action.recommendation valid | value in ["human_review", "controlled_apply", "block"] | hard reject |

## Failure Cases

### Structural Failures

| Failure ID | Condition | Severity | Recovery |
|------------|-----------|----------|----------|
| F001 | Missing required field | hard reject | Report missing fields, wait for human |
| F002 | Invalid proposal_version | hard reject | Report version mismatch, wait for human |
| F003 | Invalid execution_mode | hard reject | Report mode mismatch, wait for human |
| F004 | task.id mismatch | hard reject | Report ID mismatch, wait for human |
| F005 | Empty allowed_files | hard reject | Report empty scope, wait for human |

### Scope Failures

| Failure ID | Condition | Severity | Recovery |
|------------|-----------|----------|----------|
| F006 | Forbidden file in target_files | hard reject | Report violation, wait for human |
| F007 | Target file outside allowed scope | hard reject | Report out-of-scope, wait for human |
| F008 | Path traversal detected ("..") | hard reject | Report security violation, wait for human |
| F009 | Absolute path detected | hard reject | Report format violation, wait for human |

### Format Failures

| Failure ID | Condition | Severity | Recovery |
|------------|-----------|----------|----------|
| F010 | Invalid unified diff format | hard reject | Report parse error, wait for human |
| F011 | Empty patch content | hard reject | Report empty patch, wait for human |
| F012 | Unsafe command detected | hard reject | Report unsafe command, wait for human |
| F013 | Compound command detected (&&/;) | hard reject | Report compound command, wait for human |

### Safety Failures

| Failure ID | Condition | Severity | Recovery |
|------------|-----------|----------|----------|
| F014 | Missing safety declaration | hard reject | Report missing declaration, wait for human |
| F015 | auto_continue_to_next_task != "no" | hard reject | Report safety violation, wait for human |
| F016 | auto_git_backup != "no" | hard reject | Report safety violation, wait for human |
| F017 | human_review_required != "yes" | hard reject | Report safety violation, wait for human |
| F018 | real_task_execution != "no" | hard reject | Report safety violation, wait for human |

### Ambiguity Failures

| Failure ID | Condition | Severity | Recovery |
|------------|-----------|----------|----------|
| F019 | Ambiguous next_action value | soft reject | Request clarification, wait for human |
| F020 | Conflicting scope declarations | soft reject | Report conflict, wait for human |

## Sample Proposal

Below is a minimal sample of a safe doc_only proposal. This does not contain real business code modifications.

```yaml
proposal_version: "1.0"
execution_mode: "no_tool_use_single_task_proposal"

task:
  id: "T116"
  title: "Design no-tool-use execution proposal schema"
  source: "docs/tasks.md"

intent:
  summary: "Create the proposal schema document for no-tool-use execution mode"
  expected_outcome: "docs/no-tool-use-execution-proposal-schema.md created with complete schema definition"

scope:
  allowed_files:
    - "docs/no-tool-use-execution-proposal-schema.md"
    - "reports/dev/T116-dev-report.md"
  forbidden_files:
    - "runner.py"
    - "tools/*.py"
    - "projects/**"
  business_code_change: "no"
  framework_code_change: "no"

changes:
  type: "doc_only"
  target_files:
    - path: "docs/no-tool-use-execution-proposal-schema.md"
      change_type: "create"
      reason: "New schema design document"

safety:
  real_task_execution: "no"
  run_project_task_full_called: "no"
  claude_code_tool_use_used: "no"
  auto_continue_to_next_task: "no"
  auto_git_backup: "no"
  bypass_permissions_used: "no"
  human_review_required: "yes"

validation:
  expected_check_result: "pass"
  success_criteria:
    - "Schema document exists at docs/no-tool-use-execution-proposal-schema.md"
    - "Schema contains all required field definitions"

next_action:
  recommendation: "human_review"
```

## Relationship to T117

T117 will implement a proposal parser dry-run based on this schema.

Key points for T117:
- Parser should first extract the YAML block from model output (between ```proposal and ```)
- Parser should validate all required fields exist
- Parser should return a structured data object (dict or dataclass)
- Parser should report specific missing/invalid fields on failure
- Parser dry-run should use the sample proposal above as test input
- Parser must not execute any real operations

T116 does not implement the parser. T116 only defines the schema that the parser must handle.

## Decision Summary

```text
NO_TOOL_USE_PROPOSAL_SCHEMA=designed
READY_FOR_PROPOSAL_PARSER_DRY_RUN=yes
READY_FOR_REAL_EXECUTION=no
HUMAN_REVIEW_REQUIRED=yes
```
