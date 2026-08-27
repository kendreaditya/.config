#!/usr/bin/env python3
"""Run one supervised Claude Code print-mode session and preserve artifacts."""

from __future__ import annotations

import argparse
from collections import deque
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any


SCHEMA = "codex-claude-delegation.v1"
DEFAULT_TOOLS = "Read,Glob,Grep,Edit,Write,Bash"


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workdir", required=True, type=Path, help="Claude working directory")
    p.add_argument("--brief", required=True, type=Path, help="UTF-8 brief sent on stdin")
    p.add_argument("--out-dir", type=Path, help="Artifact directory outside the worktree")
    p.add_argument("--model", help="Claude model alias or full model name")
    p.add_argument("--effort", choices=("low", "medium", "high", "xhigh", "max"))
    p.add_argument("--max-budget-usd", type=float)
    resume = p.add_mutually_exclusive_group()
    resume.add_argument("--resume", metavar="SESSION_ID")
    resume.add_argument("--continue", dest="continue_session", action="store_true")
    p.add_argument("--fork-session", action="store_true")
    p.add_argument("--name", help="Claude session display name")
    p.add_argument("--permission-mode", default="acceptEdits",
                   choices=("acceptEdits", "auto", "manual", "dontAsk", "plan"))
    p.add_argument("--dangerously-skip-permissions", action="store_true",
                   help="Bypass permission checks; requires explicit human authorization")
    p.add_argument("--tools", default=DEFAULT_TOOLS,
                   help="Comma-separated built-in Claude tools; empty string disables tools")
    p.add_argument("--allow-mcp-and-skills", action="store_true",
                   help="Do not disable MCP discovery and slash commands")
    p.add_argument("--allow-dirty", action="store_true",
                   help="Allow a dirty git tree (normally only for same-session recovery)")
    p.add_argument("--timeout", type=float, help="Hard timeout in seconds")
    p.add_argument("--dry-run", action="store_true", help="Validate and print invocation metadata")
    return p


def run_capture(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)


def git_status(cwd: Path) -> list[str] | None:
    inside = run_capture(["git", "rev-parse", "--is-inside-work-tree"], cwd)
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        return None
    status = run_capture(["git", "status", "--porcelain=v1"], cwd)
    return status.stdout.splitlines() if status.returncode == 0 else None


def is_inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def terminate_process_group(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
        proc.wait(timeout=8)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        if proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass


def extract_event(event: dict[str, Any], state: dict[str, Any]) -> None:
    session_id = event.get("session_id")
    if isinstance(session_id, str):
        state["sessionId"] = session_id

    if event.get("type") == "system" and event.get("subtype") == "init":
        state["effectiveModel"] = event.get("model") or state.get("effectiveModel")
        state["permissionMode"] = event.get("permissionMode") or state.get("permissionMode")
        return

    if event.get("type") == "assistant":
        message = event.get("message") or {}
        state["effectiveModel"] = message.get("model") or state.get("effectiveModel")
        for block in message.get("content") or []:
            if isinstance(block, dict) and block.get("type") == "text":
                value = block.get("text")
                if isinstance(value, str) and value.strip():
                    print(f"[claude] {value}", file=sys.stderr, flush=True)
        return

    if event.get("type") == "result":
        state["resultSubtype"] = event.get("subtype")
        state["isError"] = event.get("is_error")
        state["finalMessage"] = event.get("result") or ""
        state["numTurns"] = event.get("num_turns")
        state["totalCostUsd"] = event.get("total_cost_usd")
        state["usage"] = event.get("usage")
        state["modelUsage"] = event.get("modelUsage") or event.get("model_usage")
        model_usage = state.get("modelUsage")
        if not state.get("effectiveModel") and isinstance(model_usage, dict) and len(model_usage) == 1:
            state["effectiveModel"] = next(iter(model_usage))


def main() -> int:
    ns = parser().parse_args()
    workdir = ns.workdir.expanduser().resolve()
    brief = ns.brief.expanduser().resolve()

    if not workdir.is_dir():
        raise SystemExit(f"workdir is not a directory: {workdir}")
    if not brief.is_file():
        raise SystemExit(f"brief is not a file: {brief}")
    if shutil.which("claude") is None:
        raise SystemExit("claude is not available on PATH")
    if ns.max_budget_usd is not None and ns.max_budget_usd <= 0:
        raise SystemExit("--max-budget-usd must be positive")
    if ns.timeout is not None and ns.timeout <= 0:
        raise SystemExit("--timeout must be positive")

    before = git_status(workdir)
    if before and not ns.allow_dirty:
        raise SystemExit("git worktree is dirty; use a clean worktree or --allow-dirty for recovery")

    auth = run_capture(["claude", "auth", "status"], workdir)
    try:
        authenticated = auth.returncode == 0 and bool(json.loads(auth.stdout).get("loggedIn"))
    except (json.JSONDecodeError, AttributeError):
        authenticated = False
    if not authenticated:
        raise SystemExit("Claude Code is not authenticated in this environment")

    version_result = run_capture(["claude", "--version"], workdir)
    version = version_result.stdout.strip() if version_result.returncode == 0 else "unknown"

    if ns.out_dir:
        out_dir = ns.out_dir.expanduser().resolve()
        if is_inside(out_dir, workdir):
            raise SystemExit("--out-dir must be outside the delegated worktree")
        out_dir.mkdir(parents=True, exist_ok=False)
    else:
        out_dir = Path(tempfile.mkdtemp(prefix="codex-claude-"))

    stored_brief = out_dir / "brief.md"
    stored_brief.write_bytes(brief.read_bytes())
    events_path = out_dir / "events.jsonl"
    stderr_path = out_dir / "stderr.txt"
    final_path = out_dir / "final.txt"
    result_path = out_dir / "result.json"

    command = ["claude", "-p", "--output-format", "stream-json", "--verbose"]
    if ns.tools is not None:
        command += ["--tools", ns.tools]
    if not ns.allow_mcp_and_skills:
        command += ["--strict-mcp-config", "--disable-slash-commands"]
    if ns.dangerously_skip_permissions:
        command.append("--dangerously-skip-permissions")
    else:
        command += ["--permission-mode", ns.permission_mode]
    if ns.model:
        command += ["--model", ns.model]
    if ns.effort:
        command += ["--effort", ns.effort]
    if ns.max_budget_usd is not None:
        command += ["--max-budget-usd", str(ns.max_budget_usd)]
    if ns.resume:
        command += ["--resume", ns.resume]
    elif ns.continue_session:
        command.append("--continue")
    if ns.fork_session:
        command.append("--fork-session")
    if ns.name:
        command += ["--name", ns.name]

    metadata = {
        "schema": SCHEMA,
        "status": "dry-run" if ns.dry_run else "running",
        "workdir": str(workdir),
        "brief": str(stored_brief),
        "outDir": str(out_dir),
        "command": command,
        "claudeVersion": version,
        "requestedModel": ns.model,
        "requestedEffort": ns.effort,
        "permissionMode": "bypassPermissions" if ns.dangerously_skip_permissions else ns.permission_mode,
        "dangerouslySkipPermissions": ns.dangerously_skip_permissions,
        "gitStatusBefore": before,
        "startedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if ns.dry_run:
        result_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(metadata, indent=2))
        return 0

    state: dict[str, Any] = {}
    stderr_chunks: deque[str] = deque(maxlen=200)
    timed_out = False
    interrupted = False

    with stored_brief.open("r", encoding="utf-8") as prompt_in, \
            events_path.open("w", encoding="utf-8") as events_out, \
            stderr_path.open("w", encoding="utf-8") as stderr_out:
        proc = subprocess.Popen(
            command,
            cwd=workdir,
            stdin=prompt_in,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            start_new_session=True,
        )

        def read_stderr() -> None:
            assert proc.stderr is not None
            for line in proc.stderr:
                stderr_out.write(line)
                stderr_out.flush()
                stderr_chunks.append(line)
                print(line, file=sys.stderr, end="", flush=True)

        stderr_thread = threading.Thread(target=read_stderr, daemon=True)
        stderr_thread.start()

        timeout_fired = threading.Event()

        def enforce_timeout() -> None:
            if proc.poll() is None:
                timeout_fired.set()
                terminate_process_group(proc)

        timer = threading.Timer(ns.timeout, enforce_timeout) if ns.timeout else None
        if timer:
            timer.daemon = True
            timer.start()

        try:
            assert proc.stdout is not None
            for line in proc.stdout:
                events_out.write(line)
                events_out.flush()
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(event, dict):
                    extract_event(event, state)
            exit_code = proc.wait()
            timed_out = timeout_fired.is_set()
        except KeyboardInterrupt:
            interrupted = True
            terminate_process_group(proc)
            exit_code = proc.returncode if proc.returncode is not None else 130
        finally:
            if timer:
                timer.cancel()
            stderr_thread.join(timeout=2)

    after = git_status(workdir)
    final_message = state.get("finalMessage") or ""
    final_path.write_text(final_message, encoding="utf-8")
    status = "timeout" if timed_out else "interrupted" if interrupted else \
        "completed" if exit_code == 0 and not state.get("isError") else "failed"
    normalized_exit = 124 if timed_out else 130 if interrupted else \
        exit_code if exit_code >= 0 else 128 + abs(exit_code)
    metadata.update(state)
    metadata.update({
        "status": status,
        "exitCode": normalized_exit,
        "processExitCode": exit_code,
        "signal": abs(exit_code) if exit_code < 0 else None,
        "gitStatusAfter": after,
        "events": str(events_path),
        "stderr": str(stderr_path),
        "final": str(final_path),
        "result": str(result_path),
        "stderrTail": "".join(stderr_chunks)[-4000:],
        "finishedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })
    result_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metadata, indent=2))
    return 0 if status == "completed" else (normalized_exit or 1)


if __name__ == "__main__":
    raise SystemExit(main())
