"""Prepare a generation or repair workspace and supervise native Codex execution."""

from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile
import time

from .config import Settings, settings_from_dict
from . import execution
from .client import Client
from runtime import agent_records
from runtime.codex_support import codex_options


__version__ = "0.2.0"


REQUIRED_INPUTS = (
    "AGENTS.md", "TASK.md", "protocol.md", "system.md",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, data: dict) -> None:
    # Atomic replacement avoids truncated metadata on interruption.
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def read_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return data


def version_info(executable: str, *arguments: str) -> dict:
    resolved = shutil.which(executable)
    if resolved is None:
        return {"available": False, "requested": executable}
    try:
        completed = subprocess.run(
            [resolved, *arguments], capture_output=True, text=True,
            errors="replace", timeout=10, check=False,
        )
        return {
            "available": completed.returncode == 0, "executable": resolved,
            "returncode": completed.returncode,
            "version": completed.stdout.strip(), "stderr": completed.stderr.strip(),
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "executable": resolved, "error": str(exc)}


def doctor(settings: Settings) -> dict:
    """Only local version/help checks; no login or model call."""
    result = {
        "codex": version_info(settings.codex, "--version"),
        "git": version_info("git", "--version"),
        "go": version_info("go", "version"),
        "runner_version": __version__,
    }
    required = ("--json", "--output-last-message", "--sandbox")
    codex = result["codex"]
    if codex["available"]:
        try:
            for arguments, flags in ((["exec", "--help"], required), (["--help"], ("--no-daemon", "--ask-for-approval"))):
                completed = subprocess.run(
                    [codex["executable"], *arguments], capture_output=True,
                    text=True, errors="replace", timeout=10, check=False,
                )
                missing = [flag for flag in flags if flag not in completed.stdout]
                if completed.returncode or missing:
                    codex["compatible"] = False
                    codex.setdefault("missing_flags", []).extend(missing)
            codex.setdefault("compatible", True)
        except (OSError, subprocess.TimeoutExpired) as exc:
            codex["compatible"] = False
            codex["error"] = str(exc)
    result["ready"] = all(result[name]["available"] for name in ("codex", "git", "go")) and codex.get("compatible", False)
    return result


def command_for(settings: Settings, run_dir: Path) -> list[str]:
    # Global approval/daemon options precede the subcommand. No shell invocation.
    command = [
        settings.codex, "--no-daemon", "--ask-for-approval", "never", "exec",
        "--cd", str(run_dir / "workspace"), "--sandbox", "workspace-write",
        "--json", "--color", "never",
        "--output-last-message", str(run_dir / "final.txt"),
        "--config", 'web_search=' + json.dumps(settings.web_search),
        "--config", "features.multi_agent=true",
    ]
    if settings.model:
        command.extend(["--model", settings.model])
    if settings.reasoning_effort:
        command.extend(["--config", "model_reasoning_effort=" + json.dumps(settings.reasoning_effort)])
    command.append("-")
    return command


def prepare(settings: Settings, label: str = "native") -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", label):
        raise ValueError("label must be 1–64 letters, digits, underscores, or hyphens")
    source = Path(settings.inputs_dir)
    for relative in REQUIRED_INPUTS:
        if not (source / relative).is_file():
            raise ValueError(f"Missing input material: {source / relative}")
    output = Path(settings.output_root)
    output.mkdir(parents=True, exist_ok=True)
    prefix = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + label + "-"
    run_dir = Path(tempfile.mkdtemp(prefix=prefix, dir=output))
    metadata = {
        "runner_version": __version__, "condition": "protocol-to-system-native-agent",
        "status": "preparing", "created_at": utc_now(), "settings": settings.to_dict(),
        "workspace": str(run_dir / "workspace"), "input_files": list(REQUIRED_INPUTS),
        "environment": {
            "mode": "host", "read_isolation": False,
            "user_config": "private", "user_instructions_and_skills": "disabled",
            "project_instructions": "explicit inputs/AGENTS.md",
            "sandbox": "workspace-write", "approval_policy": "never",
            "shared_daemon": False,
            "subagents": "native_allowed",
        },
    }
    write_json(run_dir / "run.json", metadata)
    try:
        for relative in REQUIRED_INPUTS:
            for destination in (run_dir / "inputs", run_dir / "workspace"):
                path = destination / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source / relative, path)
        for name in ('tracecheck.py', 'schedule.py'):
            helper = Path(__file__).resolve().parent.parent / 'runtime' / name
            shutil.copyfile(helper, run_dir / 'inputs' / name)
        metadata['trace_helper'] = 'inputs/tracecheck.py'
        metadata['schedule_helper'] = 'inputs/schedule.py'
        prompt = (run_dir / "inputs" / "TASK.md").read_text(encoding="utf-8")
        (run_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
        (run_dir / "workspace" / ".gitignore").write_text("*.test\ncoverage.out\n.runtime/\n", encoding="utf-8")
        subprocess.run(
            ["git", "init", "--quiet", str(run_dir / "workspace")],
            check=True, capture_output=True, text=True, timeout=10,
        )
        metadata["command"] = command_for(settings, run_dir)
        metadata["status"] = "prepared"
    except (OSError, subprocess.SubprocessError) as exc:
        metadata["status"] = "prepare_failed"
        metadata["error"] = str(exc)
        write_json(run_dir / "run.json", metadata)
        raise
    write_json(run_dir / "run.json", metadata)
    return run_dir


def summarize_events(path: Path) -> dict:
    summary = {
        "thread_ids": [], "usage_events": [], "completed_turns": 0,
        "failed_turns": 0, "error_events": 0, "invalid_json_lines": 0,
        "completed_command_items": 0, "completed_file_change_items": 0,
        "last_turn_event": None,
        "usage_semantics": "raw CLI counters; use agents.json for recorded per-response usage across threads",
    }
    if not path.exists():
        return summary
    with path.open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                summary["invalid_json_lines"] += 1
                continue
            if not isinstance(event, dict):
                summary["invalid_json_lines"] += 1
                continue
            kind = event.get("type")
            if kind == "thread.started":
                identity = event.get("thread_id")
                if isinstance(identity, str) and identity not in summary["thread_ids"]:
                    summary["thread_ids"].append(identity)
            elif kind == "turn.completed":
                summary["completed_turns"] += 1
                summary["last_turn_event"] = kind
                if isinstance(event.get("usage"), dict):
                    summary["usage_events"].append(event["usage"])
            elif kind == "turn.failed":
                summary["failed_turns"] += 1
                summary["last_turn_event"] = kind
            elif kind == "turn.started":
                summary["last_turn_event"] = kind
            elif kind == "error":
                summary["error_events"] += 1
            elif kind == "item.completed":
                item = event.get("item")
                if isinstance(item, dict):
                    if item.get("type") == "command_execution":
                        summary["completed_command_items"] += 1
                    elif item.get("type") == "file_change":
                        summary["completed_file_change_items"] += 1
    return summary


@contextmanager
def exclusive_run(run_dir: Path):
    # Prevent two invocations from writing the same workspace/logs concurrently.
    with (run_dir / ".runner.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("Another runner already owns this run directory") from exc
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


class Terminated(Exception):
    pass


def terminate_group(process: subprocess.Popen, grace_seconds: float = 2.0) -> None:
    """Stop local descendants even if the group leader has already exited."""
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        process.wait()
        return
    deadline = time.monotonic() + grace_seconds
    while time.monotonic() < deadline:
        process.poll()
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.05)
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()


def execute(run_dir: Path) -> dict:
    run_dir = run_dir.resolve()
    with exclusive_run(run_dir):
        metadata = read_json(run_dir / "run.json")
        if metadata["status"] != "prepared":
            raise ValueError(f"Run is {metadata['status']!r}; prepare a fresh run instead of overwriting it")
        settings = settings_from_dict(metadata["settings"], run_dir)
        if not settings.model:
            raise ValueError("Stage settings must specify an explicit model")
        prompt = (run_dir / "prompt.txt").read_text(encoding="utf-8")
        command = command_for(settings, run_dir)
        metadata.update({
            "status": "running", "command": command, "started_at": utc_now(),
            "tools": {
                "codex": version_info(settings.codex, "--version"),
                "git": version_info("git", "--version"),
                "go": version_info("go", "version"),
            },
        })
        write_json(run_dir / "run.json", metadata)
        started = time.monotonic()
        process = None
        client = None
        execution_ready = False
        returncode = None
        state = "launch_failed"
        old_term = signal.getsignal(signal.SIGTERM)

        def handle_term(signum, frame):
            raise Terminated("SIGTERM")

        signal.signal(signal.SIGTERM, handle_term)
        try:
            prepared = execution.prepare(settings, run_dir, started + settings.timeout_seconds)
            execution_ready = True
            client = Client(settings, run_dir, started + settings.timeout_seconds)
            tool_environment = read_json(run_dir / 'execution-control.json')['environment']
            client.prepare(tool_environment)
            client.authenticate()
            command[0] = client.executable
            command[-1:-1] = [*codex_options(client.settings), *prepared['options']]
            metadata.update(command=command, isolated_execution=prepared)
            write_json(run_dir / 'run.json', metadata)
            with (run_dir / "events.jsonl").open("w", encoding="utf-8") as events, (run_dir / "stderr.log").open("w", encoding="utf-8") as errors:
                process = subprocess.Popen(
                    command, cwd=run_dir / "workspace", stdin=subprocess.PIPE,
                    stdout=events, stderr=errors, text=True, encoding="utf-8",
                    start_new_session=True, env=client.environment,
                )
                metadata["pid"] = process.pid
                write_json(run_dir / "run.json", metadata)
                try:
                    process.communicate(input=prompt, timeout=max(0.01, started + settings.timeout_seconds - time.monotonic()))
                    returncode = process.returncode
                    state = "process_exited"
                except subprocess.TimeoutExpired:
                    state = "timed_out"
        except (KeyboardInterrupt, Terminated):
            state = "interrupted"
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            state = 'launch_failed' if execution_ready else 'environment_blocked'
            if time.monotonic() >= started + settings.timeout_seconds:
                state = 'timed_out'
            metadata["error"] = str(exc)
        finally:
            # Ignore additional cancellation while stopping descendants and saving results.
            old_int = signal.signal(signal.SIGINT, signal.SIG_IGN)
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            try:
                if process is not None:
                    terminate_group(process)
                    returncode = process.returncode
                if process is not None and process.stdin is not None:
                    process.stdin.close()
                execution.reconcile(run_dir)
                summary = summarize_events(run_dir / "events.jsonl")
                try:
                    agents = agent_records.collect(client.client_home if client else run_dir / '.unstarted-client',
                        summary['thread_ids'], run_dir / 'workspace', metadata['started_at'], run_dir,
                        secrets=client.secrets if client else ())
                except OSError as exc:
                    agents = {'record': None, 'usage': None, 'usage_complete': False,
                              'warnings': [f'{type(exc).__name__} retaining agent records']}
                if state == "process_exited":
                    final = run_dir / "final.txt"
                    has_final = final.is_file() and bool(final.read_text(encoding="utf-8", errors="replace").strip())
                    if returncode != 0 or summary["last_turn_event"] == "turn.failed":
                        state = "agent_failed"
                    elif summary["last_turn_event"] == "turn.completed" and has_final:
                        state = "agent_finished"
                    else:
                        state = "incomplete_output"
                metadata.update({
                    "status": state, "returncode": returncode, "ended_at": utc_now(),
                    "elapsed_seconds": round(time.monotonic() - started, 3),
                    "events": summary,
                    "agents": agents,
                })
                write_json(run_dir / "run.json", metadata)
            finally:
                try:
                    if client is not None:
                        client.close()
                finally:
                    signal.signal(signal.SIGTERM, old_term)
                    signal.signal(signal.SIGINT, old_int)
        return metadata
