#!/usr/bin/env python3
"""
run_state_manager.py - Run State Manager Dry-run

Stage 12 run state and checkpoint management tool.
Supports dry-run mode only: create-run-state, write-checkpoint,
evaluate-resume, simulate-rate-limit.

All operations output to reports/run-state/ only.
No runtime/ directory is created.
No real resume, no real rate-limit recovery, no git operations.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict


# ---------------------------------------------------------------------------
# Data Structures (aligned with stage12-run-state-and-checkpoint-design.md)
# ---------------------------------------------------------------------------

@dataclass
class RunState:
    """Run State - records the full lifecycle of a single execution."""
    run_id: str
    project_root: str
    repo_name: str
    current_task: str
    current_stage: str
    next_pending: str
    next_stage: str
    command: str
    mode: str
    status: str
    started_at: str
    updated_at: str
    current_step: str
    last_successful_step: str
    total_steps: int
    resume_allowed: bool
    resume_reason: str
    blocked_reason: str
    dirty_workspace_detected: bool
    unclassified_changes: List[str]
    rate_limit_detected: bool
    rate_limit_reset_at: str
    checkpoint_path: str
    last_error: str
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class Checkpoint:
    """Checkpoint - records a complete snapshot of a key step."""
    checkpoint_id: str
    run_id: str
    task_id: str
    stage: str
    step_name: str
    step_index: int
    created_at: str
    status: str
    command_planned: str
    command_executed: str
    output_summary: str
    files_expected: List[str]
    files_changed: List[str]
    git_status_before: List[str]
    git_status_after: List[str]
    next_pending_before: str
    next_pending_after: str
    next_stage_before: str
    next_stage_after: str
    resume_allowed_after_checkpoint: bool
    fail_closed_reason: str
    notes: str


@dataclass
class ResumeDecision:
    """ResumeDecision - judges whether resume from interruption is allowed."""
    ok: bool
    run_id: str
    task_id: str
    can_resume: bool
    resume_from_checkpoint: str
    resume_step: str
    requires_user_confirmation: bool
    dirty_workspace_detected: bool
    unclassified_changes: List[str]
    next_pending_matches: bool
    next_stage_matches: bool
    rate_limit_wait_required: bool
    rate_limit_reset_at: str
    blocked_reason: str
    warnings: List[str]
    next_action: str


@dataclass
class DirtyWorkspaceSnapshot:
    """DirtyWorkspaceSnapshot - captures workspace state at a point in time."""
    captured_at: str
    git_status_short: List[str]
    allowed_files: List[str]
    modified_files: List[str]
    untracked_files: List[str]
    staged_files: List[str]
    unclassified_files: List[str]
    safe_to_continue: bool
    safe_to_commit: bool
    fail_reason: str


@dataclass
class RateLimitState:
    """RateLimitState - records API rate limit status."""
    detected: bool
    provider: str
    error_code: str
    error_message: str
    request_id: str
    reset_at: str
    wait_seconds: int
    captured_at: str
    affected_task: str
    affected_step: str
    checkpoint_path: str
    resume_allowed_after_reset: bool
    requires_workspace_recheck: bool
    notes: str


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------

def utc_now() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_run_id(task_id: str) -> str:
    """Build run_id in format RUN-YYYYMMDD-HHMMSS."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"RUN-{ts}"


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


def classify_workspace_changes(
    git_status: List[str],
    allowed_files: List[str],
) -> DirtyWorkspaceSnapshot:
    """Classify workspace changes into allowed/modified/untracked/staged/unclassified."""
    captured_at = utc_now()
    modified_files: List[str] = []
    untracked_files: List[str] = []
    staged_files: List[str] = []
    allowed_set = set(allowed_files)

    for line in git_status:
        if not line:
            continue
        # git status --short format: XY filename
        # X = index status, Y = working tree status
        if len(line) < 4:
            continue
        status_code = line[:2]
        filepath = line[3:].strip()
        # Remove quotes if present
        if filepath.startswith('"') and filepath.endswith('"'):
            filepath = filepath[1:-1]

        # Index/staged changes
        if status_code[0] in ("A", "M", "D", "R", "C"):
            staged_files.append(filepath)

        # Modified in working tree
        if status_code[1] == "M" or status_code[0] == "M":
            modified_files.append(filepath)

        # Untracked
        if status_code in ("??", "!!"):
            untracked_files.append(filepath)

        # Renamed
        if status_code[0] == "R":
            parts = filepath.split(" -> ")
            if parts:
                staged_files.append(parts[-1])

    # Determine unclassified files
    all_changed = set(modified_files + untracked_files + staged_files)
    unclassified_files = [f for f in all_changed if f not in allowed_set]

    # Safety judgments
    safe_to_continue = len(unclassified_files) == 0
    safe_to_commit = len(unclassified_files) == 0 and len(all_changed) > 0
    fail_reason = ""
    if unclassified_files:
        fail_reason = f"E_UNCLASSIFIED_FILE_CHANGE: {len(unclassified_files)} unclassified file(s) detected"

    return DirtyWorkspaceSnapshot(
        captured_at=captured_at,
        git_status_short=git_status,
        allowed_files=sorted(allowed_set),
        modified_files=sorted(set(modified_files)),
        untracked_files=sorted(set(untracked_files)),
        staged_files=sorted(set(staged_files)),
        unclassified_files=sorted(unclassified_files),
        safe_to_continue=safe_to_continue,
        safe_to_commit=safe_to_commit,
        fail_reason=fail_reason,
    )


def create_run_state(
    task: str,
    stage: str,
    next_pending: str,
    next_stage: str,
    command: str,
    project_root: str,
) -> RunState:
    """Create a RunState instance in dry-run mode."""
    now = utc_now()
    run_id = build_run_id(task)
    repo_name = Path(project_root).name

    return RunState(
        run_id=run_id,
        project_root=project_root,
        repo_name=repo_name,
        current_task=task,
        current_stage=stage,
        next_pending=next_pending,
        next_stage=next_stage,
        command=command,
        mode="dry_run",
        status="initialized",
        started_at=now,
        updated_at=now,
        current_step="initialized",
        last_successful_step="",
        total_steps=0,
        resume_allowed=True,
        resume_reason="dry_run: initial state, resume allowed",
        blocked_reason="",
        dirty_workspace_detected=False,
        unclassified_changes=[],
        rate_limit_detected=False,
        rate_limit_reset_at="",
        checkpoint_path="",
        last_error="",
        metadata={"dry_run": "true"},
    )


def create_checkpoint(
    task: str,
    stage: str,
    step_name: str,
    step_index: int,
    run_id: str,
    project_root: str,
) -> Checkpoint:
    """Create a Checkpoint instance in dry-run mode."""
    now = utc_now()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    checkpoint_id = f"CP-{ts}-{step_index:03d}"

    return Checkpoint(
        checkpoint_id=checkpoint_id,
        run_id=run_id,
        task_id=task,
        stage=stage,
        step_name=step_name,
        step_index=step_index,
        created_at=now,
        status="success",
        command_planned=f"dry-run checkpoint for {task}",
        command_executed="",
        output_summary=f"dry-run checkpoint created for {task} step {step_name}",
        files_expected=[],
        files_changed=[],
        git_status_before=[],
        git_status_after=[],
        next_pending_before=task,
        next_pending_after=task,
        next_stage_before=stage,
        next_stage_after=stage,
        resume_allowed_after_checkpoint=True,
        fail_closed_reason="",
        notes="dry-run checkpoint, no real execution",
    )


def simulate_rate_limit_state(
    task: str,
    stage: str,
    provider: str,
    error_code: str,
    reset_at: str,
    request_id: str,
    run_id: str,
) -> RateLimitState:
    """Create a simulated RateLimitState in dry-run mode."""
    now = utc_now()
    # Calculate wait_seconds
    wait_seconds = 0
    try:
        reset_dt = datetime.fromisoformat(reset_at.replace("Z", "+00:00"))
        now_dt = datetime.now(timezone.utc)
        delta = reset_dt - now_dt
        wait_seconds = max(0, int(delta.total_seconds()))
    except Exception:
        wait_seconds = 18000  # default 5 hours

    return RateLimitState(
        detected=True,
        provider=provider,
        error_code=error_code,
        error_message=f"simulated rate limit error from {provider}",
        request_id=request_id,
        reset_at=reset_at,
        wait_seconds=wait_seconds,
        captured_at=now,
        affected_task=task,
        affected_step="dry_run",
        checkpoint_path="",
        resume_allowed_after_reset=True,
        requires_workspace_recheck=True,
        notes="dry-run simulation, no real rate limit detected, no waiting",
    )


def evaluate_resume(
    run_state: RunState,
    checkpoint: Optional[Checkpoint],
    dirty_snapshot: DirtyWorkspaceSnapshot,
    expected_next_pending: str,
    expected_next_stage: str,
) -> ResumeDecision:
    """Evaluate whether resume is allowed. Fail closed on any uncertainty."""
    warnings: List[str] = []

    # Check 1: Dirty workspace with unclassified changes
    dirty_workspace_detected = dirty_snapshot.captured_at != "" and len(dirty_snapshot.git_status_short) > 0
    unclassified_changes = dirty_snapshot.unclassified_files

    if unclassified_changes:
        return ResumeDecision(
            ok=False,
            run_id=run_state.run_id,
            task_id=run_state.current_task,
            can_resume=False,
            resume_from_checkpoint="",
            resume_step="",
            requires_user_confirmation=True,
            dirty_workspace_detected=True,
            unclassified_changes=unclassified_changes,
            next_pending_matches=False,
            next_stage_matches=False,
            rate_limit_wait_required=False,
            rate_limit_reset_at="",
            blocked_reason=f"E_UNCLASSIFIED_FILE_CHANGE: {unclassified_changes}",
            warnings=["unclassified files detected, fail closed"],
            next_action="fail_closed",
        )

    # Check 2: NEXT_PENDING matches
    next_pending_matches = run_state.next_pending == expected_next_pending
    if not next_pending_matches:
        warnings.append(
            f"NEXT_PENDING mismatch: run_state={run_state.next_pending}, expected={expected_next_pending}"
        )

    # Check 3: NEXT_STAGE matches
    next_stage_matches = run_state.next_stage == expected_next_stage
    if not next_stage_matches:
        warnings.append(
            f"NEXT_STAGE mismatch: run_state={run_state.next_stage}, expected={expected_next_stage}"
        )

    # Check 4: Rate limit
    rate_limit_wait_required = run_state.rate_limit_detected
    rate_limit_reset_at = run_state.rate_limit_reset_at
    if rate_limit_wait_required and rate_limit_reset_at:
        try:
            reset_dt = datetime.fromisoformat(rate_limit_reset_at.replace("Z", "+00:00"))
            now_dt = datetime.now(timezone.utc)
            if now_dt < reset_dt:
                return ResumeDecision(
                    ok=False,
                    run_id=run_state.run_id,
                    task_id=run_state.current_task,
                    can_resume=False,
                    resume_from_checkpoint="",
                    resume_step="",
                    requires_user_confirmation=False,
                    dirty_workspace_detected=dirty_workspace_detected,
                    unclassified_changes=[],
                    next_pending_matches=next_pending_matches,
                    next_stage_matches=next_stage_matches,
                    rate_limit_wait_required=True,
                    rate_limit_reset_at=rate_limit_reset_at,
                    blocked_reason="E_RATE_LIMITED: rate limit reset time not yet reached",
                    warnings=warnings,
                    next_action="wait_for_rate_limit",
                )
        except Exception:
            return ResumeDecision(
                ok=False,
                run_id=run_state.run_id,
                task_id=run_state.current_task,
                can_resume=False,
                resume_from_checkpoint="",
                resume_step="",
                requires_user_confirmation=True,
                dirty_workspace_detected=dirty_workspace_detected,
                unclassified_changes=[],
                next_pending_matches=next_pending_matches,
                next_stage_matches=next_stage_matches,
                rate_limit_wait_required=True,
                rate_limit_reset_at=rate_limit_reset_at,
                blocked_reason="E_RATE_LIMITED: cannot parse reset_at time",
                warnings=warnings,
                next_action="fail_closed",
            )

    # Check 5: NEXT_PENDING / NEXT_STAGE mismatch
    if not next_pending_matches or not next_stage_matches:
        return ResumeDecision(
            ok=False,
            run_id=run_state.run_id,
            task_id=run_state.current_task,
            can_resume=False,
            resume_from_checkpoint="",
            resume_step="",
            requires_user_confirmation=True,
            dirty_workspace_detected=dirty_workspace_detected,
            unclassified_changes=[],
            next_pending_matches=next_pending_matches,
            next_stage_matches=next_stage_matches,
            rate_limit_wait_required=False,
            rate_limit_reset_at="",
            blocked_reason=f"E_NEXT_PENDING_MISMATCH or E_STAGE_MISMATCH",
            warnings=warnings,
            next_action="fail_closed",
        )

    # Check 6: Dirty workspace but only allowed files
    requires_user_confirmation = dirty_workspace_detected and len(dirty_snapshot.git_status_short) > 0

    # All checks passed
    resume_from_cp = checkpoint.checkpoint_id if checkpoint else ""
    resume_step = checkpoint.step_name if checkpoint else ""

    if requires_user_confirmation:
        return ResumeDecision(
            ok=True,
            run_id=run_state.run_id,
            task_id=run_state.current_task,
            can_resume=True,
            resume_from_checkpoint=resume_from_cp,
            resume_step=resume_step,
            requires_user_confirmation=True,
            dirty_workspace_detected=True,
            unclassified_changes=[],
            next_pending_matches=True,
            next_stage_matches=True,
            rate_limit_wait_required=False,
            rate_limit_reset_at="",
            blocked_reason="",
            warnings=["dirty workspace with only allowed files, user confirmation recommended"],
            next_action="wait_for_user_confirmation",
        )

    return ResumeDecision(
        ok=True,
        run_id=run_state.run_id,
        task_id=run_state.current_task,
        can_resume=True,
        resume_from_checkpoint=resume_from_cp,
        resume_step=resume_step,
        requires_user_confirmation=False,
        dirty_workspace_detected=False,
        unclassified_changes=[],
        next_pending_matches=True,
        next_stage_matches=True,
        rate_limit_wait_required=False,
        rate_limit_reset_at="",
        blocked_reason="",
        warnings=[],
        next_action="resume",
    )


# ---------------------------------------------------------------------------
# Report Writers
# ---------------------------------------------------------------------------

def dataclass_to_dict(obj) -> dict:
    """Convert a dataclass instance to a dict, handling nested dataclasses."""
    if hasattr(obj, "__dataclass_fields__"):
        result = {}
        for key, value in asdict(obj).items():
            result[key] = value
        return result
    return {}


def write_json_report(path: Path, payload: dict) -> None:
    """Write a JSON report file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def write_markdown_report(path: Path, title: str, status_lines: Dict[str, str], details: List[str]) -> None:
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


# ---------------------------------------------------------------------------
# CLI Subcommands
# ---------------------------------------------------------------------------

def cmd_create_run_state(args: argparse.Namespace) -> int:
    """Handle create-run-state dry-run subcommand."""
    project_root = str(Path(__file__).resolve().parent.parent)
    run_state = create_run_state(
        task=args.task,
        stage=args.stage,
        next_pending=args.next_pending,
        next_stage=args.next_stage,
        command=args.run_command,
        project_root=project_root,
    )

    # Check git status for dirty workspace detection
    git_status = read_git_status_short(Path(project_root))
    if git_status:
        run_state.dirty_workspace_detected = True
        run_state.status = "running"
        run_state.updated_at = utc_now()
    else:
        run_state.status = "running"
        run_state.updated_at = utc_now()

    # Output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write JSON report
    json_path = output_dir / f"{args.task}-run-state.json"
    write_json_report(json_path, dataclass_to_dict(run_state))

    # Write Markdown report
    md_path = output_dir / f"{args.task}-run-state-report.md"
    status_lines = {
        "RUN_STATE_MANAGER_RESULT": "pass",
        "COMMAND": "create-run-state",
        "TASK_ID": args.task,
        "STAGE": args.stage,
        "RUN_ID": run_state.run_id,
        "REPORT_PATH": str(md_path),
        "RUNTIME_CREATED": "no",
        "CHECKPOINT_FILES_CREATED": "no",
        "REAL_RESUME_ENABLED": "no",
        "RUNNER_EXECUTED": "no",
        "GIT_ADD_EXECUTED": "no",
        "GIT_COMMIT_EXECUTED": "no",
        "GIT_PUSH_EXECUTED": "no",
        "CHECK_RESULT": "pass",
    }
    details = [
        f"run_id: {run_state.run_id}",
        f"mode: {run_state.mode}",
        f"status: {run_state.status}",
        f"dirty_workspace_detected: {run_state.dirty_workspace_detected}",
        f"JSON report written to: {json_path}",
    ]
    write_markdown_report(md_path, f"T{args.task} Run State Dry-run Report", status_lines, details)

    # Print structured output
    print(f"RUN_STATE_MANAGER_RESULT=pass")
    print(f"COMMAND=create-run-state")
    print(f"TASK_ID={args.task}")
    print(f"STAGE={args.stage}")
    print(f"RUN_ID={run_state.run_id}")
    print(f"REPORT_PATH={md_path}")
    print(f"RUNTIME_CREATED=no")
    print(f"CHECKPOINT_FILES_CREATED=no")
    print(f"REAL_RESUME_ENABLED=no")
    print(f"RUNNER_EXECUTED=no")
    print(f"GIT_ADD_EXECUTED=no")
    print(f"GIT_COMMIT_EXECUTED=no")
    print(f"GIT_PUSH_EXECUTED=no")
    print(f"CHECK_RESULT=pass")

    return 0


def cmd_write_checkpoint(args: argparse.Namespace) -> int:
    """Handle write-checkpoint dry-run subcommand."""
    project_root = str(Path(__file__).resolve().parent.parent)
    run_id = build_run_id(args.task)

    checkpoint = create_checkpoint(
        task=args.task,
        stage=args.stage,
        step_name=args.step_name,
        step_index=args.step_index,
        run_id=run_id,
        project_root=project_root,
    )

    # Capture git status before/after (both are same in dry-run)
    git_status = read_git_status_short(Path(project_root))
    checkpoint.git_status_before = git_status
    checkpoint.git_status_after = git_status

    # Output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write JSON report
    json_path = output_dir / f"{args.task}-checkpoint-{args.step_index:03d}.json"
    write_json_report(json_path, dataclass_to_dict(checkpoint))

    # Write Markdown report
    md_path = output_dir / f"{args.task}-checkpoint-report.md"
    status_lines = {
        "RUN_STATE_MANAGER_RESULT": "pass",
        "COMMAND": "write-checkpoint",
        "TASK_ID": args.task,
        "STAGE": args.stage,
        "RUN_ID": run_id,
        "CHECKPOINT_ID": checkpoint.checkpoint_id,
        "REPORT_PATH": str(md_path),
        "RUNTIME_CREATED": "no",
        "CHECKPOINT_FILES_CREATED": "no",
        "REAL_RESUME_ENABLED": "no",
        "RUNNER_EXECUTED": "no",
        "GIT_ADD_EXECUTED": "no",
        "GIT_COMMIT_EXECUTED": "no",
        "GIT_PUSH_EXECUTED": "no",
        "CHECK_RESULT": "pass",
    }
    details = [
        f"checkpoint_id: {checkpoint.checkpoint_id}",
        f"run_id: {run_id}",
        f"step_name: {args.step_name}",
        f"step_index: {args.step_index}",
        f"status: {checkpoint.status}",
        f"resume_allowed_after_checkpoint: {checkpoint.resume_allowed_after_checkpoint}",
        f"JSON report written to: {json_path}",
    ]
    write_markdown_report(md_path, f"T{args.task} Checkpoint Dry-run Report", status_lines, details)

    # Print structured output
    print(f"RUN_STATE_MANAGER_RESULT=pass")
    print(f"COMMAND=write-checkpoint")
    print(f"TASK_ID={args.task}")
    print(f"STAGE={args.stage}")
    print(f"RUN_ID={run_id}")
    print(f"CHECKPOINT_ID={checkpoint.checkpoint_id}")
    print(f"REPORT_PATH={md_path}")
    print(f"RUNTIME_CREATED=no")
    print(f"CHECKPOINT_FILES_CREATED=no")
    print(f"REAL_RESUME_ENABLED=no")
    print(f"RUNNER_EXECUTED=no")
    print(f"GIT_ADD_EXECUTED=no")
    print(f"GIT_COMMIT_EXECUTED=no")
    print(f"GIT_PUSH_EXECUTED=no")
    print(f"CHECK_RESULT=pass")

    return 0


def cmd_evaluate_resume(args: argparse.Namespace) -> int:
    """Handle evaluate-resume dry-run subcommand."""
    project_root = str(Path(__file__).resolve().parent.parent)

    # Create run state for evaluation
    run_state = create_run_state(
        task=args.task,
        stage=args.stage,
        next_pending=args.expected_next_pending,
        next_stage=args.expected_next_stage,
        command="evaluate-resume-dry-run",
        project_root=project_root,
    )

    # Read allowed files
    allowed_files: List[str] = []
    if args.allowed_file:
        allowed_files = args.allowed_file

    # Capture dirty workspace snapshot
    git_status = read_git_status_short(Path(project_root))
    dirty_snapshot = classify_workspace_changes(git_status, allowed_files)

    # Create a checkpoint for resume evaluation
    run_id = build_run_id(args.task)
    checkpoint = create_checkpoint(
        task=args.task,
        stage=args.stage,
        step_name="resume-evaluation",
        step_index=0,
        run_id=run_id,
        project_root=project_root,
    )

    # Evaluate resume
    decision = evaluate_resume(
        run_state=run_state,
        checkpoint=checkpoint,
        dirty_snapshot=dirty_snapshot,
        expected_next_pending=args.expected_next_pending,
        expected_next_stage=args.expected_next_stage,
    )

    # Output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write JSON report
    json_path = output_dir / f"{args.task}-resume-decision.json"
    report_payload = {
        "resume_decision": dataclass_to_dict(decision),
        "dirty_workspace_snapshot": dataclass_to_dict(dirty_snapshot),
        "run_state": dataclass_to_dict(run_state),
    }
    write_json_report(json_path, report_payload)

    # Write Markdown report
    md_path = output_dir / f"{args.task}-resume-decision-report.md"
    resume_allowed_str = "yes" if decision.can_resume else "no"
    dirty_str = "yes" if decision.dirty_workspace_detected else "no"
    unclassified_str = ",".join(decision.unclassified_changes) if decision.unclassified_changes else "none"
    np_matches = "yes" if decision.next_pending_matches else "no"
    ns_matches = "yes" if decision.next_stage_matches else "no"
    requires_confirm = "yes" if decision.requires_user_confirmation else "no"

    status_lines = {
        "RUN_STATE_MANAGER_RESULT": "pass",
        "COMMAND": "evaluate-resume",
        "TASK_ID": args.task,
        "STAGE": args.stage,
        "RUN_ID": run_state.run_id,
        "REPORT_PATH": str(md_path),
        "RESUME_ALLOWED": resume_allowed_str,
        "DIRTY_WORKSPACE_DETECTED": dirty_str,
        "UNCLASSIFIED_CHANGES": unclassified_str,
        "NEXT_PENDING_MATCHES": np_matches,
        "NEXT_STAGE_MATCHES": ns_matches,
        "REQUIRES_USER_CONFIRMATION": requires_confirm,
        "RUNTIME_CREATED": "no",
        "CHECKPOINT_FILES_CREATED": "no",
        "REAL_RESUME_ENABLED": "no",
        "RUNNER_EXECUTED": "no",
        "GIT_ADD_EXECUTED": "no",
        "GIT_COMMIT_EXECUTED": "no",
        "GIT_PUSH_EXECUTED": "no",
        "CHECK_RESULT": "pass" if decision.ok else "fail",
    }
    details = [
        f"ok: {decision.ok}",
        f"can_resume: {decision.can_resume}",
        f"next_action: {decision.next_action}",
        f"dirty_workspace_detected: {decision.dirty_workspace_detected}",
        f"unclassified_changes: {decision.unclassified_changes}",
        f"next_pending_matches: {decision.next_pending_matches}",
        f"next_stage_matches: {decision.next_stage_matches}",
        f"requires_user_confirmation: {decision.requires_user_confirmation}",
        f"blocked_reason: {decision.blocked_reason}",
        f"warnings: {decision.warnings}",
        f"dirty_snapshot.safe_to_continue: {dirty_snapshot.safe_to_continue}",
        f"dirty_snapshot.safe_to_commit: {dirty_snapshot.safe_to_commit}",
        f"JSON report written to: {json_path}",
    ]
    write_markdown_report(md_path, f"T{args.task} Resume Decision Dry-run Report", status_lines, details)

    # Print structured output
    print(f"RUN_STATE_MANAGER_RESULT=pass")
    print(f"COMMAND=evaluate-resume")
    print(f"TASK_ID={args.task}")
    print(f"STAGE={args.stage}")
    print(f"RUN_ID={run_state.run_id}")
    print(f"REPORT_PATH={md_path}")
    print(f"RESUME_ALLOWED={resume_allowed_str}")
    print(f"DIRTY_WORKSPACE_DETECTED={dirty_str}")
    print(f"UNCLASSIFIED_CHANGES={unclassified_str}")
    print(f"NEXT_PENDING_MATCHES={np_matches}")
    print(f"NEXT_STAGE_MATCHES={ns_matches}")
    print(f"REQUIRES_USER_CONFIRMATION={requires_confirm}")
    print(f"RUNTIME_CREATED=no")
    print(f"CHECKPOINT_FILES_CREATED=no")
    print(f"REAL_RESUME_ENABLED=no")
    print(f"RUNNER_EXECUTED=no")
    print(f"GIT_ADD_EXECUTED=no")
    print(f"GIT_COMMIT_EXECUTED=no")
    print(f"GIT_PUSH_EXECUTED=no")
    print(f"CHECK_RESULT={'pass' if decision.ok else 'fail'}")

    return 0


def cmd_simulate_rate_limit(args: argparse.Namespace) -> int:
    """Handle simulate-rate-limit dry-run subcommand."""
    project_root = str(Path(__file__).resolve().parent.parent)
    run_id = build_run_id(args.task)

    rate_limit_state = simulate_rate_limit_state(
        task=args.task,
        stage=args.stage,
        provider=args.provider,
        error_code=args.error_code,
        reset_at=args.reset_at,
        request_id=args.request_id,
        run_id=run_id,
    )

    # Output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write JSON report
    json_path = output_dir / f"{args.task}-rate-limit.json"
    write_json_report(json_path, dataclass_to_dict(rate_limit_state))

    # Write Markdown report
    md_path = output_dir / f"{args.task}-rate-limit-report.md"
    status_lines = {
        "RUN_STATE_MANAGER_RESULT": "pass",
        "COMMAND": "simulate-rate-limit",
        "TASK_ID": args.task,
        "STAGE": args.stage,
        "RUN_ID": run_id,
        "REPORT_PATH": str(md_path),
        "RATE_LIMIT_DETECTED": "yes",
        "RATE_LIMIT_RESET_AT": args.reset_at,
        "RESUME_ALLOWED_AFTER_RESET": "yes" if rate_limit_state.resume_allowed_after_reset else "no",
        "REQUIRES_WORKSPACE_RECHECK": "yes",
        "RUNTIME_CREATED": "no",
        "CHECKPOINT_FILES_CREATED": "no",
        "REAL_RESUME_ENABLED": "no",
        "RUNNER_EXECUTED": "no",
        "GIT_ADD_EXECUTED": "no",
        "GIT_COMMIT_EXECUTED": "no",
        "GIT_PUSH_EXECUTED": "no",
        "CHECK_RESULT": "pass",
    }
    details = [
        f"detected: {rate_limit_state.detected}",
        f"provider: {rate_limit_state.provider}",
        f"error_code: {rate_limit_state.error_code}",
        f"reset_at: {rate_limit_state.reset_at}",
        f"wait_seconds: {rate_limit_state.wait_seconds}",
        f"affected_task: {rate_limit_state.affected_task}",
        f"resume_allowed_after_reset: {rate_limit_state.resume_allowed_after_reset}",
        f"requires_workspace_recheck: {rate_limit_state.requires_workspace_recheck}",
        f"notes: {rate_limit_state.notes}",
        f"JSON report written to: {json_path}",
    ]
    write_markdown_report(md_path, f"T{args.task} Rate Limit Simulation Dry-run Report", status_lines, details)

    # Print structured output
    print(f"RUN_STATE_MANAGER_RESULT=pass")
    print(f"COMMAND=simulate-rate-limit")
    print(f"TASK_ID={args.task}")
    print(f"STAGE={args.stage}")
    print(f"RUN_ID={run_id}")
    print(f"REPORT_PATH={md_path}")
    print(f"RATE_LIMIT_DETECTED=yes")
    print(f"RATE_LIMIT_RESET_AT={args.reset_at}")
    print(f"RESUME_ALLOWED_AFTER_RESET={'yes' if rate_limit_state.resume_allowed_after_reset else 'no'}")
    print(f"REQUIRES_WORKSPACE_RECHECK=yes")
    print(f"RUNTIME_CREATED=no")
    print(f"CHECKPOINT_FILES_CREATED=no")
    print(f"REAL_RESUME_ENABLED=no")
    print(f"RUNNER_EXECUTED=no")
    print(f"GIT_ADD_EXECUTED=no")
    print(f"GIT_COMMIT_EXECUTED=no")
    print(f"GIT_PUSH_EXECUTED=no")
    print(f"CHECK_RESULT=pass")

    return 0


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

def main() -> int:
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Run State Manager - Dry-run mode only",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # create-run-state
    p_create = subparsers.add_parser("create-run-state", help="Create run state dry-run")
    p_create.add_argument("--task", required=True, help="Task ID (e.g. T197)")
    p_create.add_argument("--stage", required=True, help="Stage (e.g. 'Stage 12')")
    p_create.add_argument("--next-pending", required=True, help="NEXT_PENDING value")
    p_create.add_argument("--next-stage", required=True, help="NEXT_STAGE value")
    p_create.add_argument("--run-command", required=True, help="Command that triggers this run")
    p_create.add_argument("--output-dir", default="reports/run-state", help="Output directory")

    # write-checkpoint
    p_checkpoint = subparsers.add_parser("write-checkpoint", help="Write checkpoint dry-run")
    p_checkpoint.add_argument("--task", required=True, help="Task ID")
    p_checkpoint.add_argument("--stage", required=True, help="Stage")
    p_checkpoint.add_argument("--step-name", required=True, help="Step name")
    p_checkpoint.add_argument("--step-index", required=True, type=int, help="Step index")
    p_checkpoint.add_argument("--output-dir", default="reports/run-state", help="Output directory")

    # evaluate-resume
    p_resume = subparsers.add_parser("evaluate-resume", help="Evaluate resume dry-run")
    p_resume.add_argument("--task", required=True, help="Task ID")
    p_resume.add_argument("--stage", required=True, help="Stage")
    p_resume.add_argument("--expected-next-pending", required=True, help="Expected NEXT_PENDING")
    p_resume.add_argument("--expected-next-stage", required=True, help="Expected NEXT_STAGE")
    p_resume.add_argument("--allowed-file", action="append", default=[], help="Allowed file path (repeatable)")
    p_resume.add_argument("--output-dir", default="reports/run-state", help="Output directory")

    # simulate-rate-limit
    p_rate = subparsers.add_parser("simulate-rate-limit", help="Simulate rate limit dry-run")
    p_rate.add_argument("--task", required=True, help="Task ID")
    p_rate.add_argument("--stage", required=True, help="Stage")
    p_rate.add_argument("--provider", required=True, help="API provider")
    p_rate.add_argument("--error-code", required=True, help="Error code")
    p_rate.add_argument("--reset-at", required=True, help="Rate limit reset time (ISO 8601)")
    p_rate.add_argument("--request-id", required=True, help="Request ID")
    p_rate.add_argument("--output-dir", default="reports/run-state", help="Output directory")

    args = parser.parse_args()

    if args.command == "create-run-state":
        return cmd_create_run_state(args)
    elif args.command == "write-checkpoint":
        return cmd_write_checkpoint(args)
    elif args.command == "evaluate-resume":
        return cmd_evaluate_resume(args)
    elif args.command == "simulate-rate-limit":
        return cmd_simulate_rate_limit(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
