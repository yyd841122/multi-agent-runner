# T119 Controlled Patch Apply Dry-Run Check

## Command

```bash
python runner.py no-tool-use-patch-apply-dry-run --sample <name>
```

## Safety Rules

| Check | Result |
|-------|--------|
| no patch applied | yes |
| no command execution | yes |
| no Claude Code call | yes |
| no business code modification | yes |
| no framework code modification | yes |
| no real task execution | yes |
| no auto-continue | yes |
| no auto Git backup | yes |
| human review required | yes |
| no bypass permissions | yes |

## Scenarios

### 1. pass

- Command: `python runner.py no-tool-use-patch-apply-dry-run --sample pass`
- Expected: PARSE_STATUS=parsed, VALIDATION_STATUS=validated, PATCH_DRY_RUN_STATUS=ready_for_future_apply, CHECK_RESULT=pass
- Actual: PARSE_STATUS=parsed, VALIDATION_STATUS=validated, PATCH_DRY_RUN_STATUS=ready_for_future_apply, CHECK_RESULT=pass
- PATCH_APPLY_BLOCKED=yes, REAL_PATCH_APPLIED=no, READY_FOR_FUTURE_CONTROLLED_APPLY=yes
- **PASS**

### 2. no-patch

- Command: `python runner.py no-tool-use-patch-apply-dry-run --sample no-patch`
- Expected: PARSE_STATUS=parsed, VALIDATION_STATUS=validated, PATCH_DRY_RUN_STATUS=no_patch, CHECK_RESULT=fail
- Actual: PARSE_STATUS=parsed, VALIDATION_STATUS=validated, PATCH_DRY_RUN_STATUS=no_patch, CHECK_RESULT=fail
- VIOLATIONS=Proposal type 'patch_proposal' requires patches but none found
- **PASS**

### 3. empty-patch

- Command: `python runner.py no-tool-use-patch-apply-dry-run --sample empty-patch`
- Expected: PARSE_STATUS=parsed, VALIDATION_STATUS=validated, PATCH_DRY_RUN_STATUS=unsafe_patch, CHECK_RESULT=fail
- Actual: PARSE_STATUS=parsed, VALIDATION_STATUS=validated, PATCH_DRY_RUN_STATUS=unsafe_patch, CHECK_RESULT=fail
- VIOLATIONS=Patch 'docs/test.md': empty patch content
- **PASS**

### 4. patch-file-mismatch

- Command: `python runner.py no-tool-use-patch-apply-dry-run --sample patch-file-mismatch`
- Expected: PARSE_STATUS=parsed, VALIDATION_STATUS=validated, PATCH_DRY_RUN_STATUS=unsafe_patch, CHECK_RESULT=fail
- Actual: PARSE_STATUS=parsed, VALIDATION_STATUS=validated, PATCH_DRY_RUN_STATUS=unsafe_patch, CHECK_RESULT=fail
- VIOLATIONS=Patch 'docs/other.md': not in target_files list
- **PASS**

### 5. patch-outside-allowed

- Command: `python runner.py no-tool-use-patch-apply-dry-run --sample patch-outside-allowed`
- Expected: PARSE_STATUS=parsed, VALIDATION_STATUS=failed_scope, PATCH_DRY_RUN_STATUS=failed_validation, CHECK_RESULT=fail
- Actual: PARSE_STATUS=parsed, VALIDATION_STATUS=failed_scope, PATCH_DRY_RUN_STATUS=failed_validation, CHECK_RESULT=fail
- Fails at T118 validation level (target_file not in allowed scope)
- **PASS**

### 6. patch-forbidden-file

- Command: `python runner.py no-tool-use-patch-apply-dry-run --sample patch-forbidden-file`
- Expected: PARSE_STATUS=parsed, VALIDATION_STATUS=failed_scope, PATCH_DRY_RUN_STATUS=failed_validation, CHECK_RESULT=fail
- Actual: PARSE_STATUS=parsed, VALIDATION_STATUS=failed_scope, PATCH_DRY_RUN_STATUS=failed_validation, CHECK_RESULT=fail
- Fails at T118 validation level (target_file in forbidden scope)
- **PASS**

### 7. invalid-patch-format

- Command: `python runner.py no-tool-use-patch-apply-dry-run --sample invalid-patch-format`
- Expected: PARSE_STATUS=parsed, VALIDATION_STATUS=validated, PATCH_DRY_RUN_STATUS=unsafe_patch, CHECK_RESULT=fail
- Actual: PARSE_STATUS=parsed, VALIDATION_STATUS=validated, PATCH_DRY_RUN_STATUS=unsafe_patch, CHECK_RESULT=fail
- VIOLATIONS=Patch 'docs/test.md': invalid unified diff format
- **PASS**

### 8. validation-fail

- Command: `python runner.py no-tool-use-patch-apply-dry-run --sample validation-fail`
- Expected: PARSE_STATUS=parsed, VALIDATION_STATUS=failed_scope, PATCH_DRY_RUN_STATUS=failed_validation, CHECK_RESULT=fail
- Actual: PARSE_STATUS=parsed, VALIDATION_STATUS=failed_scope, PATCH_DRY_RUN_STATUS=failed_validation, CHECK_RESULT=fail
- Fails at T118 validation level (auto_continue_to_next_task must be 'no')
- **PASS**

### 9. parse-fail

- Command: `python runner.py no-tool-use-patch-apply-dry-run --sample parse-fail`
- Expected: PARSE_STATUS=failed_to_parse, VALIDATION_STATUS=failed_parse, PATCH_DRY_RUN_STATUS=failed_parse, CHECK_RESULT=fail
- Actual: PARSE_STATUS=failed_to_parse, VALIDATION_STATUS=failed_parse, PATCH_DRY_RUN_STATUS=failed_parse, CHECK_RESULT=fail
- **PASS**

## Summary

| Scenario | PARSE_STATUS | VALIDATION_STATUS | PATCH_DRY_RUN_STATUS | CHECK_RESULT |
|----------|-------------|-------------------|----------------------|-------------|
| pass | parsed | validated | ready_for_future_apply | pass |
| no-patch | parsed | validated | no_patch | fail |
| empty-patch | parsed | validated | unsafe_patch | fail |
| patch-file-mismatch | parsed | validated | unsafe_patch | fail |
| patch-outside-allowed | parsed | failed_scope | failed_validation | fail |
| patch-forbidden-file | parsed | failed_scope | failed_validation | fail |
| invalid-patch-format | parsed | validated | unsafe_patch | fail |
| validation-fail | parsed | failed_scope | failed_validation | fail |
| parse-fail | failed_to_parse | failed_parse | failed_parse | fail |

9/9 PASS.
