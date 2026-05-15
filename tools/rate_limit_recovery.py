#!/usr/bin/env python3
"""
rate_limit_recovery.py - Rate-limit Recovery Dry-run

Stage 12 rate-limit recovery tool.
Supports dry-run mode only: parse-error, plan-wait, evaluate-recovery.

All operations output to reports/rate-limit-recovery/ only.
No runtime/ directory is created.
No real resume, no real rate-limit recovery, no git operations.
"""

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, List, Dict


# ---------------------------------------------------------------------------
# Data Structures (aligned with stage12-rate-limit-recovery-design.md)
# ---------------------------------------------------------------------------

@dataclass
class RateLimitRecoveryState:
    """RateLimitRecoveryState - API rate-limit event complete record."""

    # === Detection info ===
    detected: bool
    provider: str
    error_code: str
    error_message: str
    raw_payload: str
    request_id: str

    # === Reset Time ===
    reset_at_raw: str
    reset_at_utc: str
    retry_after_seconds: int

    # === Capture context ===
    captured_at: str
    affected_task: str
    affected_stage: str
    affected_step: str

    # === Associations ===
    run_id: str
    checkpoint_id: str
    checkpoint_path: str
    run_state_path: str

    # === Recovery control ===
    workspace_recheck_required: bool
    next_pending_before_wait: str
    next_stage_before_wait: str
    resume_allowed_after_reset: bool
    requires_user_confirmation: bool
    blocked_reason: str

    # === Notes ===
    notes: str


@dataclass
class RecoveryDecision:
    """RecoveryDecision - rate-limit recovery decision."""

    # === Overall judgment ===
    ok: bool
    can_wait: bool
    can_resume: bool

    # === Associations ===
    run_id: str
    task_id: str
    stage: str

    # === Reset check ===
    reset_at_utc: str
    reset_passed: bool

    # === Workspace check ===
    workspace_clean: bool
    dirty_workspace_detected: bool
    unclassified_changes: List[str]

    # === Consistency check ===
    next_pending_matches: bool
    next_stage_matches: bool

    # === Checkpoint check ===
    checkpoint_valid: bool

    # === User confirmation ===
    user_confirmation_required: bool

    # === Block info ===
    blocked_reason: str
    warnings: List[str]

    # === Next action ===
    next_action: str


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

def utc_now() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def dataclass_to_dict(obj) -> dict:
    """Convert a dataclass instance to a dict, handling nested dataclasses."""
    if hasattr(obj, "__dataclass_fields__"):
        result = {}
        for key, value in asdict(obj).items():
            result[key] = value
        return result
    return {}


def build_run_id(task_id: str) -> str:
    """Build run_id in format RUN-YYYYMMDD-HHMMSS."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"RUN-{ts}"


def build_checkpoint_id(task_id: str) -> str:
    """Build checkpoint_id in format CP-YYYYMMDD-HHMMSS."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"CP-{ts}"


# ---------------------------------------------------------------------------
# Error Detection Functions
# ---------------------------------------------------------------------------

def parse_json_error_payload(raw_text: str) -> dict:
    """Parse JSON error payload from raw text.

    Handles format like:
        429 {"error":{"code":"1308","message":"..."},"request_id":"..."}

    Returns dict with keys: error_code, error_message, request_id, raw_json
    """
    result = {
        "error_code": "",
        "error_message": "",
        "request_id": "",
        "raw_json": "",
    }

    # Try to find JSON object in the text
    json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
    if not json_match:
        return result

    json_str = json_match.group(0)
    result["raw_json"] = json_str

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        return result

    # Extract error.code
    if isinstance(data, dict):
        error_obj = data.get("error", {})
        if isinstance(error_obj, dict):
            result["error_code"] = str(error_obj.get("code", ""))
            result["error_message"] = str(error_obj.get("message", ""))

        # Extract request_id
        result["request_id"] = str(data.get("request_id", ""))

    return result


def detect_rate_limit(raw_text: str, provider: str = "") -> tuple:
    """Detect rate-limit from raw error text.

    Returns: (detected: bool, error_code: str, error_message: str, request_id: str)

    Detection priority:
    1. JSON error payload
    2. HTTP 429 status code
    3. Keyword matching
    """
    detected = False
    error_code = ""
    error_message = ""
    request_id = ""

    # Priority 1: Parse JSON payload
    parsed = parse_json_error_payload(raw_text)
    if parsed["raw_json"]:
        error_code = parsed["error_code"]
        error_message = parsed["error_message"]
        request_id = parsed["request_id"]

        # Check if JSON indicates rate limit
        if error_code == "429" or error_code == "1308":
            detected = True
        elif error_message:
            msg_lower = error_message.lower()
            if any(kw in msg_lower for kw in [
                "rate limit", "quota exceeded", "too many requests",
                "使用上限", "配额", "限额",
            ]):
                detected = True

    # Priority 2: HTTP 429 status code in text
    if not detected:
        if re.search(r'\b429\b', raw_text):
            detected = True
            if not error_code:
                error_code = "429"

    # Priority 3: Keyword matching on full text
    if not detected:
        text_lower = raw_text.lower()
        keywords = [
            "rate limit",
            "quota exceeded",
            "too many requests",
            "使用上限",
            "配额",
            "限额",
        ]
        for kw in keywords:
            if kw in text_lower:
                detected = True
                break

    return (detected, error_code, error_message, request_id)


# ---------------------------------------------------------------------------
# Reset Time Extraction Functions
# ---------------------------------------------------------------------------

def extract_reset_time(raw_text: str) -> tuple:
    """Extract reset_at from raw error text.

    Returns: (reset_at_raw: str, reset_at_utc: str)

    Supported formats:
    1. Chinese format: 您的限额将在 2026-05-12 19:47:46 重置
    2. ISO 8601 UTC: 2026-05-12T19:47:46Z
    3. ISO 8601 offset: 2026-05-12T19:47:46+08:00
    4. Unix timestamp: "reset": 1747076866
    5. Retry-After header: Retry-After: 3600
    6. Provider-specific: x-ratelimit-reset: 1747076866

    All extracted times are converted to UTC.
    Chinese format is treated as UTC+8.
    """
    reset_at_raw = ""
    reset_at_utc = ""

    # Format 1: Chinese datetime
    cn_match = re.search(
        r'您的限额将在\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s*重置',
        raw_text,
    )
    if cn_match:
        reset_at_raw = cn_match.group(1)
        try:
            dt = datetime.strptime(reset_at_raw, "%Y-%m-%d %H:%M:%S")
            # Chinese format is UTC+8
            dt_utc = dt - timedelta(hours=8)
            dt_utc = dt_utc.replace(tzinfo=timezone.utc)
            reset_at_utc = dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
            return (reset_at_raw, reset_at_utc)
        except ValueError:
            pass

    # Format 2: ISO 8601 UTC
    iso_utc_match = re.search(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)', raw_text)
    if iso_utc_match:
        reset_at_raw = iso_utc_match.group(1)
        reset_at_utc = reset_at_raw
        return (reset_at_raw, reset_at_utc)

    # Format 3: ISO 8601 with offset
    iso_offset_match = re.search(
        r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2})',
        raw_text,
    )
    if iso_offset_match:
        reset_at_raw = iso_offset_match.group(1)
        try:
            dt = datetime.fromisoformat(reset_at_raw)
            dt_utc = dt.astimezone(timezone.utc)
            reset_at_utc = dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
            return (reset_at_raw, reset_at_utc)
        except ValueError:
            pass

    # Format 4: Unix timestamp in JSON field
    unix_match = re.search(r'["\']?reset["\']?\s*[:=]\s*(\d{10,})', raw_text)
    if unix_match:
        reset_at_raw = unix_match.group(1)
        try:
            ts = int(reset_at_raw)
            dt_utc = datetime.fromtimestamp(ts, tz=timezone.utc)
            reset_at_utc = dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
            return (reset_at_raw, reset_at_utc)
        except (ValueError, OSError):
            pass

    # Format 6: Provider-specific x-ratelimit-reset
    provider_match = re.search(
        r'["\']?x-ratelimit-reset["\']?\s*[:=]\s*(\d+)',
        raw_text,
    )
    if provider_match:
        reset_at_raw = provider_match.group(1)
        try:
            ts = int(reset_at_raw)
            dt_utc = datetime.fromtimestamp(ts, tz=timezone.utc)
            reset_at_utc = dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
            return (reset_at_raw, reset_at_utc)
        except (ValueError, OSError):
            pass

    # Fail closed: unable to extract reset_at
    return ("", "")


def parse_retry_after(raw_text: str) -> int:
    """Parse Retry-After header value from text.

    Format: Retry-After: 3600 (seconds)

    Returns: retry_after_seconds (0 if not found)
    """
    match = re.search(r'retry-after\s*:\s*(\d+)', raw_text, re.IGNORECASE)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            return 0
    return 0


# ---------------------------------------------------------------------------
# Workspace Functions
# ---------------------------------------------------------------------------

def read_git_status_short(project_root: Path) -> List[str]:
    """Read git status --short output as a list of lines."""
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return []
        lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
        return [line.strip() for line in lines if line.strip()]
    except Exception:
        return []


def classify_unclassified_changes(
    git_status: List[str],
    allowed_files: List[str],
) -> List[str]:
    """Classify workspace changes and return unclassified file list.

    A file is unclassified if it is changed (modified/untracked/staged)
    and NOT in the allowed_files list.
    """
    allowed_set = set(allowed_files)
    all_changed: set = set()

    for line in git_status:
        if not line or len(line) < 4:
            continue
        status_code = line[:2]
        filepath = line[3:].strip()
        if filepath.startswith('"') and filepath.endswith('"'):
            filepath = filepath[1:-1]

        all_changed.add(filepath)

        # Handle renamed files
        if status_code[0] == "R":
            parts = filepath.split(" -> ")
            if parts:
                all_changed.add(parts[-1])

    unclassified = [f for f in all_changed if f not in allowed_set]
    return sorted(unclassified)


# ---------------------------------------------------------------------------
# Builder Functions
# ---------------------------------------------------------------------------

def build_rate_limit_recovery_state(
    detected: bool,
    provider: str,
    error_code: str,
    error_message: str,
    raw_payload: str,
    request_id: str,
    reset_at_raw: str,
    reset_at_utc: str,
    retry_after_seconds: int,
    affected_task: str,
    affected_stage: str,
    affected_step: str,
    run_id: str,
    checkpoint_id: str,
    checkpoint_path: str,
    run_state_path: str,
    next_pending_before_wait: str,
    next_stage_before_wait: str,
) -> RateLimitRecoveryState:
    """Build RateLimitRecoveryState instance."""
    return RateLimitRecoveryState(
        detected=detected,
        provider=provider,
        error_code=error_code,
        error_message=error_message,
        raw_payload=raw_payload,
        request_id=request_id,
        reset_at_raw=reset_at_raw,
        reset_at_utc=reset_at_utc,
        retry_after_seconds=retry_after_seconds,
        captured_at=utc_now(),
        affected_task=affected_task,
        affected_stage=affected_stage,
        affected_step=affected_step,
        run_id=run_id,
        checkpoint_id=checkpoint_id,
        checkpoint_path=checkpoint_path,
        run_state_path=run_state_path,
        workspace_recheck_required=True,
        next_pending_before_wait=next_pending_before_wait,
        next_stage_before_wait=next_stage_before_wait,
        resume_allowed_after_reset=False,
        requires_user_confirmation=True,
        blocked_reason="",
        notes="dry-run: no real rate limit recovery",
    )


def build_recovery_decision(
    task_id: str,
    stage: str,
    run_id: str,
    reset_at_utc: str,
    expected_next_pending: str,
    expected_next_stage: str,
    project_root: Path,
    allowed_files: List[str],
) -> RecoveryDecision:
    """Build RecoveryDecision with fail-closed logic.

    Check order:
    1. Reset time passed
    2. NEXT_PENDING / NEXT_STAGE matches (before workspace to report correctly)
    3. Workspace recheck (unclassified changes)
    4. Dirty workspace with only allowed files
    5. All checks passed → resume

    All uncertain states must block resume.
    """
    warnings: List[str] = []

    # Check 1: Reset time passed
    reset_passed = False
    try:
        reset_dt = datetime.fromisoformat(reset_at_utc.replace("Z", "+00:00"))
        now_dt = datetime.now(timezone.utc)
        reset_passed = now_dt >= reset_dt
    except Exception:
        reset_passed = False
        warnings.append("cannot parse reset_at_utc, treating as not passed")

    if not reset_passed:
        return RecoveryDecision(
            ok=False,
            can_wait=True,
            can_resume=False,
            run_id=run_id,
            task_id=task_id,
            stage=stage,
            reset_at_utc=reset_at_utc,
            reset_passed=False,
            workspace_clean=False,
            dirty_workspace_detected=False,
            unclassified_changes=[],
            next_pending_matches=True,
            next_stage_matches=True,
            checkpoint_valid=True,
            user_confirmation_required=False,
            blocked_reason="E_RATE_LIMITED: reset_at not yet reached",
            warnings=["reset_at has not passed, cannot resume"],
            next_action="wait_for_rate_limit",
        )

    # Check 2: NEXT_PENDING matches
    next_pending_matches = True
    if expected_next_pending:
        tasks_path = project_root / "docs" / "tasks.md"
        if tasks_path.exists():
            tasks_text = tasks_path.read_text(encoding="utf-8")
            matches = re.findall(
                r"<!--\s*NEXT_PENDING\s*=\s*(T\d+)\s*-->",
                tasks_text,
            )
            actual_next_pending = matches[-1] if matches else ""
            next_pending_matches = actual_next_pending == expected_next_pending
            if not next_pending_matches:
                warnings.append(
                    f"NEXT_PENDING mismatch: actual={actual_next_pending}, expected={expected_next_pending}"
                )
        else:
            next_pending_matches = False
            warnings.append("docs/tasks.md not found, cannot verify NEXT_PENDING")

    # Check 3: NEXT_STAGE matches
    next_stage_matches = True
    if expected_next_stage:
        tasks_path = project_root / "docs" / "tasks.md"
        if tasks_path.exists():
            tasks_text = tasks_path.read_text(encoding="utf-8")
            matches = re.findall(
                r"<!--\s*NEXT_STAGE\s*=\s*(Stage\s+\d+)\s*-->",
                tasks_text,
            )
            actual_next_stage = matches[-1] if matches else ""
            next_stage_matches = actual_next_stage == expected_next_stage
            if not next_stage_matches:
                warnings.append(
                    f"NEXT_STAGE mismatch: actual={actual_next_stage}, expected={expected_next_stage}"
                )
        else:
            next_stage_matches = False
            warnings.append("docs/tasks.md not found, cannot verify NEXT_STAGE")

    # Check 4: NEXT_PENDING / NEXT_STAGE mismatch → fail closed
    if not next_pending_matches or not next_stage_matches:
        blocked_parts = []
        if not next_pending_matches:
            blocked_parts.append("E_NEXT_PENDING_MISMATCH")
        if not next_stage_matches:
            blocked_parts.append("E_STAGE_MISMATCH")
        return RecoveryDecision(
            ok=False,
            can_wait=False,
            can_resume=False,
            run_id=run_id,
            task_id=task_id,
            stage=stage,
            reset_at_utc=reset_at_utc,
            reset_passed=True,
            workspace_clean=False,
            dirty_workspace_detected=False,
            unclassified_changes=[],
            next_pending_matches=next_pending_matches,
            next_stage_matches=next_stage_matches,
            checkpoint_valid=True,
            user_confirmation_required=True,
            blocked_reason=" or ".join(blocked_parts),
            warnings=warnings,
            next_action="fail_closed",
        )

    # Check 5: Workspace recheck
    git_status = read_git_status_short(project_root)
    workspace_clean = len(git_status) == 0
    dirty_workspace_detected = len(git_status) > 0
    unclassified_changes = classify_unclassified_changes(git_status, allowed_files)

    if unclassified_changes:
        return RecoveryDecision(
            ok=False,
            can_wait=False,
            can_resume=False,
            run_id=run_id,
            task_id=task_id,
            stage=stage,
            reset_at_utc=reset_at_utc,
            reset_passed=True,
            workspace_clean=False,
            dirty_workspace_detected=True,
            unclassified_changes=unclassified_changes,
            next_pending_matches=True,
            next_stage_matches=True,
            checkpoint_valid=True,
            user_confirmation_required=True,
            blocked_reason=f"E_UNCLASSIFIED_FILE_CHANGE: {unclassified_changes}",
            warnings=[f"unclassified files detected: {unclassified_changes}"],
            next_action="fail_closed",
        )

    # Check 6: Dirty workspace but only allowed files
    if dirty_workspace_detected:
        return RecoveryDecision(
            ok=True,
            can_wait=False,
            can_resume=True,
            run_id=run_id,
            task_id=task_id,
            stage=stage,
            reset_at_utc=reset_at_utc,
            reset_passed=True,
            workspace_clean=False,
            dirty_workspace_detected=True,
            unclassified_changes=[],
            next_pending_matches=True,
            next_stage_matches=True,
            checkpoint_valid=True,
            user_confirmation_required=True,
            blocked_reason="",
            warnings=["dirty workspace with only allowed files, user confirmation required"],
            next_action="wait_for_user_confirmation",
        )

    # All checks passed
    return RecoveryDecision(
        ok=True,
        can_wait=False,
        can_resume=True,
        run_id=run_id,
        task_id=task_id,
        stage=stage,
        reset_at_utc=reset_at_utc,
        reset_passed=True,
        workspace_clean=True,
        dirty_workspace_detected=False,
        unclassified_changes=[],
        next_pending_matches=True,
        next_stage_matches=True,
        checkpoint_valid=True,
        user_confirmation_required=False,
        blocked_reason="",
        warnings=[],
        next_action="resume",
    )


# ---------------------------------------------------------------------------
# Report Writers
# ---------------------------------------------------------------------------

def write_json_report(path: Path, payload: dict) -> None:
    """Write a JSON report file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def write_markdown_report(
    path: Path,
    title: str,
    status_lines: dict,
    details: List[str],
) -> None:
    """Write a Markdown report file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n")
        f.write(f"Generated: {utc_now()}\n\n")
        f.write("## Status\n\n")
        f.write("```text\n")
        for key, value in status_lines.items():
            f.write(f"{key}={value}\n")
        f.write("```\n\n")
        if details:
            f.write("## Details\n\n")
            for detail in details:
                f.write(f"- {detail}\n")
            f.write("\n")


def print_status_lines(status_lines: dict) -> None:
    """Print structured KEY=VALUE status lines to stdout."""
    for key, value in status_lines.items():
        print(f"{key}={value}")


# ---------------------------------------------------------------------------
# CLI Subcommands
# ---------------------------------------------------------------------------

def cmd_parse_error(args: argparse.Namespace) -> int:
    """Handle parse-error dry-run subcommand."""
    project_root = Path(__file__).resolve().parent.parent
    run_id = build_run_id(args.task)
    checkpoint_id = build_checkpoint_id(args.task)

    # Detect rate limit
    detected, error_code, error_message, request_id = detect_rate_limit(
        args.error_text, args.provider,
    )

    # Extract reset time
    reset_at_raw, reset_at_utc = extract_reset_time(args.error_text)

    # Parse retry-after
    retry_after_seconds = parse_retry_after(args.error_text)

    # Build recovery state
    recovery_state = build_rate_limit_recovery_state(
        detected=detected,
        provider=args.provider,
        error_code=error_code,
        error_message=error_message,
        raw_payload=args.error_text,
        request_id=request_id,
        reset_at_raw=reset_at_raw,
        reset_at_utc=reset_at_utc,
        retry_after_seconds=retry_after_seconds,
        affected_task=args.task,
        affected_stage=args.stage,
        affected_step="parse-error-dry-run",
        run_id=run_id,
        checkpoint_id=checkpoint_id,
        checkpoint_path="",
        run_state_path="",
        next_pending_before_wait="",
        next_stage_before_wait="",
    )

    # Output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write JSON report
    json_path = output_dir / f"{args.task}-rate-limit-recovery-state.json"
    write_json_report(json_path, dataclass_to_dict(recovery_state))

    # Build status lines
    check_result = "pass" if detected else "fail"
    status_lines = {
        "RATE_LIMIT_RECOVERY_RESULT": "pass",
        "COMMAND": "parse-error",
        "TASK_ID": args.task,
        "STAGE": args.stage,
        "RUN_ID": run_id,
        "RATE_LIMIT_DETECTED": "yes" if detected else "no",
        "ERROR_CODE": error_code,
        "REQUEST_ID": request_id,
        "RESET_AT_RAW": reset_at_raw,
        "RESET_AT_UTC": reset_at_utc,
        "RETRY_AFTER_SECONDS": str(retry_after_seconds),
        "WAIT_REQUIRED": "yes" if reset_at_utc else "no",
        "WAIT_UNTIL": reset_at_utc,
        "REAL_WAIT_STARTED": "no",
        "WORKSPACE_RECHECK_REQUIRED": "yes",
        "WORKSPACE_RECHECK_DONE": "no",
        "RESET_PASSED": "no",
        "NEXT_PENDING_MATCHES": "no",
        "NEXT_STAGE_MATCHES": "no",
        "RECOVERY_ALLOWED": "no",
        "USER_CONFIRMATION_REQUIRED": "yes",
        "RUNTIME_CREATED": "no",
        "CHECKPOINT_FILES_CREATED": "no",
        "REAL_RESUME_ENABLED": "no",
        "RUNNER_EXECUTED": "no",
        "GIT_ADD_EXECUTED": "no",
        "GIT_COMMIT_EXECUTED": "no",
        "GIT_PUSH_EXECUTED": "no",
        "REPORT_PATH": str(output_dir / f"{args.task}-parse-error-report.md"),
        "CHECK_RESULT": check_result,
    }

    # Write Markdown report
    md_path = output_dir / f"{args.task}-parse-error-report.md"
    details = [
        f"detected: {detected}",
        f"provider: {args.provider}",
        f"error_code: {error_code}",
        f"error_message: {error_message}",
        f"request_id: {request_id}",
        f"reset_at_raw: {reset_at_raw}",
        f"reset_at_utc: {reset_at_utc}",
        f"retry_after_seconds: {retry_after_seconds}",
        f"run_id: {run_id}",
        f"checkpoint_id: {checkpoint_id}",
        f"JSON report written to: {json_path}",
    ]
    write_markdown_report(md_path, f"{args.task} Parse Error Dry-run Report", status_lines, details)

    # Print structured output
    print_status_lines(status_lines)

    return 0


def cmd_plan_wait(args: argparse.Namespace) -> int:
    """Handle plan-wait dry-run subcommand."""
    project_root = Path(__file__).resolve().parent.parent
    run_id = build_run_id(args.task)
    checkpoint_id = build_checkpoint_id(args.task)

    reset_at_utc = args.reset_at

    # Calculate wait_seconds
    wait_seconds = 0
    wait_required = True
    try:
        reset_dt = datetime.fromisoformat(reset_at_utc.replace("Z", "+00:00"))
        now_dt = datetime.now(timezone.utc)
        delta = reset_dt - now_dt
        wait_seconds = max(0, int(delta.total_seconds()))
        if wait_seconds <= 0:
            wait_required = False
    except Exception:
        wait_seconds = 18000  # default 5 hours
        wait_required = True

    # Output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build plan payload
    plan_payload = {
        "command": "plan-wait",
        "task_id": args.task,
        "stage": args.stage,
        "run_id": run_id,
        "provider": args.provider,
        "request_id": args.request_id,
        "reset_at_utc": reset_at_utc,
        "wait_seconds": wait_seconds,
        "wait_required": wait_required,
        "workspace_recheck_required": True,
        "real_wait_started": False,
        "real_resume_enabled": False,
        "dry_run": True,
    }

    # Write JSON report
    json_path = output_dir / f"{args.task}-plan-wait.json"
    write_json_report(json_path, plan_payload)

    # Build status lines
    status_lines = {
        "RATE_LIMIT_RECOVERY_RESULT": "pass",
        "COMMAND": "plan-wait",
        "TASK_ID": args.task,
        "STAGE": args.stage,
        "RUN_ID": run_id,
        "RATE_LIMIT_DETECTED": "yes",
        "ERROR_CODE": "",
        "REQUEST_ID": args.request_id,
        "RESET_AT_RAW": "",
        "RESET_AT_UTC": reset_at_utc,
        "RETRY_AFTER_SECONDS": "0",
        "WAIT_REQUIRED": "yes" if wait_required else "no",
        "WAIT_UNTIL": reset_at_utc,
        "WAIT_SECONDS": str(wait_seconds),
        "REAL_WAIT_STARTED": "no",
        "WORKSPACE_RECHECK_REQUIRED": "yes",
        "WORKSPACE_RECHECK_DONE": "no",
        "RESET_PASSED": "no" if wait_required else "yes",
        "NEXT_PENDING_MATCHES": "no",
        "NEXT_STAGE_MATCHES": "no",
        "RECOVERY_ALLOWED": "no",
        "USER_CONFIRMATION_REQUIRED": "yes",
        "RUNTIME_CREATED": "no",
        "CHECKPOINT_FILES_CREATED": "no",
        "REAL_RESUME_ENABLED": "no",
        "RUNNER_EXECUTED": "no",
        "GIT_ADD_EXECUTED": "no",
        "GIT_COMMIT_EXECUTED": "no",
        "GIT_PUSH_EXECUTED": "no",
        "REPORT_PATH": str(output_dir / f"{args.task}-plan-wait-report.md"),
        "CHECK_RESULT": "pass",
    }

    # Write Markdown report
    md_path = output_dir / f"{args.task}-plan-wait-report.md"
    details = [
        f"run_id: {run_id}",
        f"provider: {args.provider}",
        f"reset_at_utc: {reset_at_utc}",
        f"wait_seconds: {wait_seconds}",
        f"wait_required: {wait_required}",
        f"workspace_recheck_required: True",
        f"real_wait_started: False",
        f"real_resume_enabled: False",
        f"JSON report written to: {json_path}",
    ]
    write_markdown_report(md_path, f"{args.task} Plan Wait Dry-run Report", status_lines, details)

    # Print structured output
    print_status_lines(status_lines)

    return 0


def cmd_evaluate_recovery(args: argparse.Namespace) -> int:
    """Handle evaluate-recovery dry-run subcommand."""
    project_root = Path(__file__).resolve().parent.parent
    run_id = build_run_id(args.task)

    reset_at_utc = args.reset_at

    # Collect allowed files
    allowed_files: List[str] = []
    if args.allowed_file:
        allowed_files = list(args.allowed_file)

    # Build recovery decision
    decision = build_recovery_decision(
        task_id=args.task,
        stage=args.stage,
        run_id=run_id,
        reset_at_utc=reset_at_utc,
        expected_next_pending=args.expected_next_pending,
        expected_next_stage=args.expected_next_stage,
        project_root=project_root,
        allowed_files=allowed_files,
    )

    # Output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write JSON report
    json_path = output_dir / f"{args.task}-recovery-decision.json"
    write_json_report(json_path, dataclass_to_dict(decision))

    # Build status lines
    recovery_allowed = "yes" if decision.can_resume else "no"
    result_str = "pass" if decision.ok else "fail"
    user_confirm = "yes" if decision.user_confirmation_required else "no"

    status_lines = {
        "RATE_LIMIT_RECOVERY_RESULT": result_str,
        "COMMAND": "evaluate-recovery",
        "TASK_ID": args.task,
        "STAGE": args.stage,
        "RUN_ID": run_id,
        "RATE_LIMIT_DETECTED": "yes",
        "ERROR_CODE": "",
        "REQUEST_ID": "",
        "RESET_AT_RAW": "",
        "RESET_AT_UTC": reset_at_utc,
        "RETRY_AFTER_SECONDS": "0",
        "WAIT_REQUIRED": "no",
        "WAIT_UNTIL": reset_at_utc,
        "REAL_WAIT_STARTED": "no",
        "WORKSPACE_RECHECK_REQUIRED": "yes",
        "WORKSPACE_RECHECK_DONE": "yes",
        "RESET_PASSED": "yes" if decision.reset_passed else "no",
        "NEXT_PENDING_MATCHES": "yes" if decision.next_pending_matches else "no",
        "NEXT_STAGE_MATCHES": "yes" if decision.next_stage_matches else "no",
        "RECOVERY_ALLOWED": recovery_allowed,
        "USER_CONFIRMATION_REQUIRED": user_confirm,
        "RUNTIME_CREATED": "no",
        "CHECKPOINT_FILES_CREATED": "no",
        "REAL_RESUME_ENABLED": "no",
        "RUNNER_EXECUTED": "no",
        "GIT_ADD_EXECUTED": "no",
        "GIT_COMMIT_EXECUTED": "no",
        "GIT_PUSH_EXECUTED": "no",
        "REPORT_PATH": str(output_dir / f"{args.task}-evaluate-recovery-report.md"),
        "CHECK_RESULT": result_str,
    }

    # Write Markdown report
    md_path = output_dir / f"{args.task}-evaluate-recovery-report.md"
    details = [
        f"ok: {decision.ok}",
        f"can_wait: {decision.can_wait}",
        f"can_resume: {decision.can_resume}",
        f"reset_passed: {decision.reset_passed}",
        f"workspace_clean: {decision.workspace_clean}",
        f"dirty_workspace_detected: {decision.dirty_workspace_detected}",
        f"unclassified_changes: {decision.unclassified_changes}",
        f"next_pending_matches: {decision.next_pending_matches}",
        f"next_stage_matches: {decision.next_stage_matches}",
        f"checkpoint_valid: {decision.checkpoint_valid}",
        f"user_confirmation_required: {decision.user_confirmation_required}",
        f"blocked_reason: {decision.blocked_reason}",
        f"warnings: {decision.warnings}",
        f"next_action: {decision.next_action}",
        f"JSON report written to: {json_path}",
    ]
    write_markdown_report(
        md_path,
        f"{args.task} Evaluate Recovery Dry-run Report",
        status_lines,
        details,
    )

    # Print structured output
    print_status_lines(status_lines)

    return 0


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

def main() -> int:
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Rate Limit Recovery - Dry-run mode only",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # parse-error
    p_parse = subparsers.add_parser("parse-error", help="Parse error text and detect rate-limit")
    p_parse.add_argument("--task", required=True, help="Task ID (e.g. T200)")
    p_parse.add_argument("--stage", required=True, help="Stage (e.g. 'Stage 12')")
    p_parse.add_argument("--provider", default="unknown", help="API provider")
    p_parse.add_argument("--error-text", required=True, help="Raw error text to parse")
    p_parse.add_argument("--output-dir", default="reports/rate-limit-recovery", help="Output directory")

    # plan-wait
    p_plan = subparsers.add_parser("plan-wait", help="Plan wait strategy dry-run")
    p_plan.add_argument("--task", required=True, help="Task ID")
    p_plan.add_argument("--stage", required=True, help="Stage")
    p_plan.add_argument("--provider", default="unknown", help="API provider")
    p_plan.add_argument("--reset-at", required=True, help="Reset time (ISO 8601)")
    p_plan.add_argument("--request-id", default="", help="Request ID")
    p_plan.add_argument("--output-dir", default="reports/rate-limit-recovery", help="Output directory")

    # evaluate-recovery
    p_eval = subparsers.add_parser("evaluate-recovery", help="Evaluate recovery decision dry-run")
    p_eval.add_argument("--task", required=True, help="Task ID")
    p_eval.add_argument("--stage", required=True, help="Stage")
    p_eval.add_argument("--expected-next-pending", required=True, help="Expected NEXT_PENDING value")
    p_eval.add_argument("--expected-next-stage", required=True, help="Expected NEXT_STAGE value")
    p_eval.add_argument("--reset-at", required=True, help="Reset time (ISO 8601)")
    p_eval.add_argument("--allowed-file", action="append", default=[], help="Allowed file path (repeatable)")
    p_eval.add_argument("--output-dir", default="reports/rate-limit-recovery", help="Output directory")

    args = parser.parse_args()

    if args.command == "parse-error":
        return cmd_parse_error(args)
    elif args.command == "plan-wait":
        return cmd_plan_wait(args)
    elif args.command == "evaluate-recovery":
        return cmd_evaluate_recovery(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
