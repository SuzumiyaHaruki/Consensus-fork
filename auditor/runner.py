"""Fixed input capture, bounded same-session turns, and append-only handoffs."""
import json
import hashlib
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import time
from statistics import median
from datetime import datetime, timezone
from pathlib import Path

from runtime.storage import EXCLUDED_DIRS, digest, file_digest, fixed_submodules, write_json

from .codex import Codex
from runtime.evidence import report_feedback


EXCLUDED = EXCLUDED_DIRS | {".execution", ".pytest_cache", ".mypy_cache"}
WORK_EXCLUDED = EXCLUDED | {".runtime"}


def implementation_identity(root):
    """Retain the local audit source; record Git identity when available."""
    project = Path(__file__).resolve().parents[1]
    paths = ('auditor', 'runtime', 'audit_bridge.py', 'requirements.txt')
    sources = {str(path.relative_to(project)): path for name in paths[:2] for path in (project/name).glob('*.py')}
    sources.update({name: project/name for name in paths[2:]})
    commit, dirty = None, None
    try:
        if Path(git(project, 'rev-parse', '--show-toplevel').decode().strip()).resolve() == project:
            commit = git(project, 'rev-parse', 'HEAD').decode().strip()
            dirty = git(project, 'status', '--porcelain', '--untracked-files=all', '--', *paths).decode()
    except (ValueError, OSError, subprocess.SubprocessError):
        pass  # A source checkout need not have been initialized as a Git repository.
    retained = {}
    for name, path in sources.items():
        if path.is_symlink() or set(Path(name).parts) & EXCLUDED:
            retained[name] = {'source': str(path), 'record': None, 'reason': 'private or excluded file'}
            continue
        data = path.read_bytes()
        destination = root/'inputs/implementation-source'/name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        retained[name] = {'source': str(path), 'record': str(destination.relative_to(root))}
    # Execution modules reload when each MCP subprocess starts, after this capture.
    from runtime import local_exec
    from runtime import storage
    from runtime import replay
    reload_inputs = {str(Path(module.__file__).resolve()): digest(Path(module.__file__).read_bytes())
                     for module in (local_exec, storage, replay)}
    return {'framework_commit': commit,
            'execution_input_changes': dirty.splitlines() if dirty is not None else None,
            'execution_inputs_dirty': bool(dirty) if dirty is not None else None,
            'retained_source': retained, 'reload_inputs': reload_inputs, 'python': sys.executable,
            'catalog_record': 'inputs/models.json', 'server_model_revision': 'unknown',
            'execution_service_record': 'inputs/local-exec.json'}


def executable_identity(client):
    path = getattr(client, "executable", None)
    if not path:
        return {"status": "not measured: test double"}
    path = Path(path)
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return {"path": str(path), "version": client.version, "sha256": hasher.hexdigest()}


def now():
    return datetime.now(timezone.utc).isoformat()


def git(repo, *args, deadline=None, stdin=None):
    timeout = min(30, deadline - time.monotonic()) if deadline else 30
    if timeout <= 0:
        raise TimeoutError("Total deadline reached during source capture")
    result = subprocess.run(["git", "--no-optional-locks", "-c", "core.fsmonitor=false",
                             "-c", "core.hooksPath=/dev/null", "-C", str(repo), *args], input=stdin,
                            capture_output=True, timeout=timeout)
    if result.returncode:
        raise ValueError("Git input capture failed: " + result.stderr.decode(errors="replace"))
    return result.stdout


def capture_source(repo, destination, deadline):
    repo = Path(repo)
    submodules = fixed_submodules(repo)
    if git(repo, "status", "--porcelain", "--untracked-files=all", deadline=deadline).strip():
        raise ValueError("Target must be a clean Git commit; dirty files are never cleaned automatically")
    commit = git(repo, "rev-parse", "HEAD", deadline=deadline).decode().strip()
    tree = git(repo, "ls-tree", "-rz", "--full-tree", commit, deadline=deadline)
    entries, excluded, files = [], {}, {}
    for record in tree.split(b"\0"):
        if not record:
            continue
        meta, raw_name = record.split(b"\t", 1)
        mode, kind, oid = meta.decode().split()
        name = raw_name.decode("utf-8")
        path = Path(name)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Unsafe Git tree path")
        if (mode == '160000' and not (set(path.parts) & EXCLUDED)
                and path.name not in {'AGENTS.md', 'SKILL.md'}):
            nested = capture_source(repo/path, destination/path, deadline)
            files.update({str(path/key):value for key,value in nested['files'].items()})
            excluded.update({str(path/key):value for key,value in nested['excluded'].items()})
            continue
        if (set(path.parts) & EXCLUDED or path.name in {"AGENTS.md", "SKILL.md"}
                or mode not in {"100644", "100755"} or kind != "blob"):
            excluded[name] = "instruction, private, excluded directory, link, or submodule"
        else:
            entries.append((name, mode, oid))
    payload = git(repo, "cat-file", "--batch", deadline=deadline,
                  stdin="".join(oid + "\n" for _, _, oid in entries).encode()) if entries else b""
    offset = 0
    destination.mkdir(parents=True, exist_ok=True)
    for name, mode, oid in entries:
        if time.monotonic() >= deadline:
            raise TimeoutError("Total deadline reached during source capture")
        end = payload.index(b"\n", offset)
        header = payload[offset:end].decode().split()
        if header[:2] != [oid, "blob"]:
            raise ValueError("Unexpected Git object response")
        size = int(header[2])
        data = payload[end + 1:end + 1 + size]
        offset = end + size + 2
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        path.chmod(int(mode, 8) & 0o777)
        files[name] = {"git_blob": oid, "mode": mode, "size": size}
    if not files:
        raise ValueError("No authorized regular source files remain")
    return {"commit": commit, "files": files, "submodules":submodules, "excluded": excluded, "capture": "committed Git blobs, no history"}


def file_inventory(root, *, exclude=WORK_EXCLUDED):
    """Hash mutable output bytes only, never follow links or archive special files."""
    files, excluded = {}, {}
    for folder, dirs, names in os.walk(root, followlinks=False):
        for name in list(dirs):
            path = Path(folder) / name
            if name in exclude or path.is_symlink():
                dirs.remove(name)
                excluded[str(path.relative_to(root))] = "excluded directory or symlink"
        for name in names:
            path = Path(folder) / name
            rel = str(path.relative_to(root))
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                excluded[rel] = "symlink, hardlink, or nonregular file"
                continue
            if name.endswith(".lock.tmp"):
                excluded[rel] = "transient file"
                continue
            checksum, size = file_digest(path)
            files[rel] = {"digest": checksum, "mode": stat.S_IMODE(info.st_mode), "size": size}
    return files, excluded


def save_changes(work, folder, previous):
    actual, excluded = file_inventory(work)
    changed = {name: info for name, info in actual.items() if previous.get(name) != info}
    for name in changed:
        destination = folder / "files" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        source = work / name
        info = source.stat()
        # Retain exact bytes without expanding preallocated test logs onto disk.
        if info.st_blocks * 512 < info.st_size:
            subprocess.run(["cp", "--sparse=always", "--", str(source), str(destination)], check=True)
        else:
            shutil.copyfile(source, destination)
        destination.chmod(actual[name]["mode"])
    write_json(folder / "manifest.json", {"changed": changed, "deleted": sorted(previous.keys() - actual.keys()),
                                          "excluded": excluded, "basis": "previous retained turn, initially source",
                                          "timing": "end of turn, not input at each command start"})
    return actual


def freeze(root):
    for folder, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if not (Path(folder) / d).is_symlink()]
        for name in names:
            path = Path(folder) / name
            if not path.is_symlink() and stat.S_ISREG(path.lstat().st_mode):
                path.chmod(path.stat().st_mode & ~0o222)
        Path(folder).chmod(0o555)


def scrub_work(root):
    """Remove runtime directories, links and transient files, not candidate or evidence content."""
    work = root / "work"
    _, excluded = file_inventory(work)
    write_json(root / "inputs/work-exclusions.json", excluded)
    for relative in sorted(excluded, key=lambda x: len(Path(x).parts), reverse=True):
        path = work / relative
        if path.is_symlink() or path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()


def brief(root, source, target, deadline, timeout, calls_left):
    remaining = max(0, deadline - time.monotonic())
    return "\n\nRun brief (host facts):\n" + json.dumps({
        "working_directory": str(root / "work"), "read_only_source": str(root / "source"),
        "source_identity": source.get("commit") or source.get("kind"), "scope": target,
        "report_path": str(root / "work/report.md"), "retained_logs": str(root / "turns"),
        "review_context": str(root / 'context') if (root / 'context').is_dir() else None,
        "schedule_helper": {"path": str(root / 'tools/schedule.py'),
                            "usage": "python3 -I PATH --help; optional adapter-driven event scheduling and strict JSONL replay inside isolated_exec; retain adapter/plan as overlays and cite stdout"},
        "execution_sources": (['candidate', 'before'] if (root/'context/before').is_dir() else ['candidate']) if target['execution_backend'] == 'go_module' else [],
        "execution_evidence": "isolated_exec optionally accepts source and overlays (relative helper/test files). Cite executions/<id>/result.json or its logs. Source selects captured starting bytes, not proof of what an arbitrary command actually tests.",
        "permissions": "Source/logs read only; work writable; ordinary shell has no network. isolated_exec supports private local TCP; no host or external network.",
        "tool_environment": f"Offline {target['execution_backend']}. work/.runtime is disposable, excluded from retained artifacts and removed at cleanup. Keep reproduction source, scripts, notes and outputs needed for review elsewhere under work.",
        "remaining_total_seconds": remaining, "turn_timeout_seconds": timeout, "remaining_agent_calls": calls_left,
        "generated_at": now(),
        "deadline_basis": "Host monotonic clock; preparation, tool work and model waiting all consume total time. "
                          "Only isolated_exec execution pauses the Agent turn timer, never the investigation/reporting wall deadline; ordinary shell and model waiting count against both."}, indent=2)


def continuation_plan(total_seconds, remaining, durations, has_report):
    """Reserve a short final window; earlier turns do not set an investigation minimum."""
    reserve = min(60.0, total_seconds * .05)
    recent = median(durations[-3:]) if durations else None
    mode = 'investigate'
    if has_report and remaining < reserve:
        mode = 'retain_report'
    elif remaining <= 2 * reserve:
        mode = 'wrap_up'
    return {'work_mode': mode, 'remaining_seconds': max(0.0, remaining),
            'reporting_reserve_seconds': reserve, 'recent_turn_seconds': recent,
            'investigation_seconds': max(0.0, remaining - reserve) if mode == 'investigate' else 0.0}


def loop(config, root, source, target, client, deadline, record):
    task, continuation = (root / "inputs/task.md").read_text().split("<!-- continuation -->")
    previous, _ = file_inventory(root / "work")
    session = None
    feedback, delivered = None, set()
    report_version = "source/report.md" if "report.md" in previous else None
    start = deadline - config.budget.total_seconds
    durations = []
    for number in range(1, config.budget.agent_calls + 1):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            record["stop"] = "total_deadline"
            break
        plan = continuation_plan(config.budget.total_seconds, remaining, durations,
                                 bool(record.get('last_completed_report')) and
                                 record['turns'][-1]['status'] == 'completed')
        if plan['work_mode'] == 'retain_report':
            record.update(stop='budget_wrap_up', budget_plan=plan,
                          reason='Remaining budget is too short for another invocation; retaining the completed report.')
            break
        turn_deadline = deadline - (plan['reporting_reserve_seconds'] if plan['work_mode'] == 'investigate' else 0)
        timeout = min(config.budget.agent_turn_timeout, turn_deadline - time.monotonic())
        folder = root / "turns" / f"{number:04d}"
        folder.mkdir()
        prompt = task if number == 1 else continuation
        if plan['work_mode'] == 'wrap_up':
            prompt += ('\n\nThis is the final planned turn within this audit budget. Prioritize consolidating '
                       'existing evidence, updating the report/index and finishing delegated work. You may '
                       'complete a small bounded check if useful; do not start a broad investigation merely '
                       'to consume the remaining time. State unfinished work and uncertainty explicitly.')
        else:
            prompt += ('\n\nChoose investigations that fit the remaining investigation time, allowing for reporting. '
                       'The investigation wall deadline also bounds isolated_exec; a resumable timeout leaves '
                       'the reporting reserve for consolidation in the same session. '
                       'A follow-up investigation may be shorter than earlier turns; their duration is context, '
                       'not a minimum required to continue.')
        prompt += '\n\nBudget guidance (time planning, not a required test plan):\n' + json.dumps(plan)
        if feedback:
            errors = feedback['delivery_errors'] if config.task_mode == 'review' else []
            if errors:
                prompt += '\n\nReview delivery is incomplete; correct these record errors or retain unchecked issues as unresolved:\n' + json.dumps(errors, ensure_ascii=False, indent=2)
            fresh = [item for item in feedback['observations'] if item not in errors and json.dumps(item, sort_keys=True) not in delivered][:12]
            if fresh:
                prompt += '\n\nEvidence follow-up (observations, not verdicts or mandatory extra tests):\n' + json.dumps(fresh, ensure_ascii=False, indent=2)
                delivered.update(json.dumps(item, sort_keys=True) for item in fresh)
        prompt += brief(root, source, target, deadline, timeout, config.budget.agent_calls - number + 1)
        (folder / "request.txt").write_text(prompt)
        remaining = max(0, turn_deadline - time.monotonic())
        turn_start = time.monotonic()
        try:
            result = client.turn(folder, prompt, min(timeout, remaining), session, deadline=turn_deadline)
        except KeyboardInterrupt:
            result = {"status": "cancelled", "session_id": session}
        except (ValueError, OSError) as exc:
            result = {"status": "external_blocker_needs_review", "session_id": session, "reason": str(exc)}
        result.setdefault('timeout_limit', ('reporting_reserve' if turn_deadline < deadline else 'total_seconds')
                          if remaining <= config.budget.agent_turn_timeout else 'agent_turn_timeout')
        result["ended_at"] = now()
        result['budget_plan'] = plan
        result["run_elapsed_seconds"] = time.monotonic() - start
        write_json(folder / "result.json", result)
        record["turns"].append({"number": number, "status": result["status"], "session_id": result.get("session_id"),
                                "tool_events": result.get("tool_events", 0), "path": str(folder.relative_to(root))})
        write_json(root / "run.json", record)
        archive_start = time.monotonic()
        actual = save_changes(root / "work", folder / "changes", previous)
        result["archive_seconds"] = time.monotonic() - archive_start
        if 'report.md' not in actual:
            report_version = None
        elif actual['report.md'] != previous.get('report.md'):
            report_version = str((folder/'changes/files/report.md').relative_to(root))
        if result['status'] == 'completed' and report_version:
            record['last_completed_report'] = report_version
        if result['status'] == 'completed':
            expected = {'candidate_commit': source['commit']}
            expected_ids = None
            if config.task_mode == 'review':
                request = json.loads((root/'context/request.json').read_text())
                expected = {key: request[key] for key in ('before_commit', 'after_commit')}
                expected_ids = request['issue_ids']
            feedback = report_feedback(root, 'review.json' if config.task_mode == 'review' else 'findings.json', expected, expected_ids)
            write_json(folder/'evidence-feedback.json', feedback)
        previous = actual
        # A resumable timeout still consumed wall time, including tool execution.
        # Use it for planning without treating its draft as a completed report.
        if result['status'] == 'completed' or result.get('continuable_timeout'):
            durations.append(time.monotonic() - turn_start)
        write_json(folder / "result.json", result)
        session = result.get("session_id")
        write_json(root / "run.json", record)
        if config.task_mode == 'review' and result['status'] == 'completed' and not feedback['delivery_errors']:
            # Complete delivery is distinct from an agent turn ending or a correctness verdict.
            record['stop'] = 'review_complete'
            break
        if result['status'] == 'completed' and plan['work_mode'] == 'wrap_up':
            record.update(stop='budget_wrap_up', budget_plan=plan,
                          reason='Completed the final planned consolidation turn.')
            break
        if result.get("continuable_timeout") and result["timeout_limit"] in {'agent_turn_timeout', 'reporting_reserve'}:
            continue
        if result["status"] != "completed":
            record["stop"] = ("total_deadline" if result["status"] == "timeout" and result["timeout_limit"] == "total_seconds"
                              else "turn_timeout" if result["status"] == "timeout" else result["status"])
            record["reason"] = result.get("reason")
            break
    else:
        record["stop"] = "agent_call_limit"


def index(root, record):
    lines = ["# 运行索引", "", f"类型：{record['kind']}；停止原因：`{record['stop']}`。", "",
             "模型自述未经裁决；每轮变更仅表示回合结束状态。", "", "[完整运行记录](run.json)", ""]
    report = record.get("last_completed_report")
    lines += [f"[最近完成回合的报告]({report})" if report else "未交付完成回合报告；不能据此解释为没有缺陷。", ""]
    for turn in record["turns"]:
        path = turn["path"]
        links = [f"[{label}]({path}/{name})" for label, name in (
            ('记录', 'result.json'), ('原始输出', 'stdout.jsonl'), ('错误输出', 'stderr.log'),
            ('最终回答', 'final.txt'), ('变更', 'changes/manifest.json')) if (root/path/name).is_file()]
        lines.append(f"- 回合 {turn['number']}：{turn['status']}；" + '、'.join(links))
    executions = sorted((root/'executions').glob('*/result.json'))
    if executions:
        lines += ['', '隔离执行记录（不代表缺陷确认）：', '']
        for path in executions:
            execution = json.loads(path.read_text())
            lines.append(f"- {execution['turn']} / {execution['execution_id']}：{execution['status']}；[原始记录]({path.relative_to(root)})")
    (root / "index.md").write_text("\n".join(lines) + "\n")


def run(config, target, *, client_factory=Codex, environment_only=False):
    if not environment_only and not (config.allow_agent_materials and config.allow_experiments):
        raise ValueError("Model transmission and local experiments must both be authorized")
    task = Path(config.task_path).read_bytes()
    parts = task.decode('utf-8').split('<!-- continuation -->')
    if len(parts) != 2 or not all(part.strip() for part in parts):
        raise ValueError('Audit prompt needs task and continuation separated by one <!-- continuation -->')
    start = time.monotonic()
    target_name = re.sub(r"[^A-Za-z0-9_-]+", "-", target.get("variant") or target["execution_backend"]).strip("-_")[:80] or "target"
    deadline = start + config.budget.total_seconds
    kind = "check-env" if environment_only else config.task_mode
    suffix = kind
    name = datetime.now().astimezone().strftime("%Y-%m-%d_%H-%M-%S") + f"-{target_name}-{suffix}"
    attempt = 1
    while True:
        root = Path(config.runs_dir) / (name if attempt == 1 else f"{name}-{attempt}")
        try:
            root.mkdir(parents=True, mode=0o700)
            break
        except FileExistsError:
            attempt += 1
    for name in ("inputs", "source", "work", "turns"):
        (root / name).mkdir()
    record = {"kind": kind, "started_at": now(), "config": config.model_dump(),
              "turns": [], "stop": "preparing", "usage_semantics": "raw per event; no automatic sum",
              "last_completed_report": None, "archive_exclusions": sorted(WORK_EXCLUDED)}
    write_json(root / "run.json", record)
    print(f"运行目录：{root}", file=sys.stderr, flush=True)
    def phase(name, message):
        record["phase"] = name
        record.setdefault("phase_times", {})[name] = {"at": now(), "elapsed_seconds": time.monotonic() - start}
        write_json(root / "run.json", record)
        print(message, file=sys.stderr, flush=True)
    client = identity = None
    old_handler = signal.getsignal(signal.SIGTERM)
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    try:
        phase("source_capture", "正在捕获源码；尚未调用模型。")
        (root / "inputs/task.md").write_bytes(task)
        write_json(root / "inputs/config.json", config.model_dump())
        write_json(root / "inputs/target.json", target)
        identity = implementation_identity(root)
        record["implementation"] = "inputs/implementation.json"
        write_json(root / record["implementation"], identity)
        source = capture_source(
            config.repo_path, root / "source", deadline)
        if target.get("expected_module"):
            if not (root / "source/go.mod").is_file() or not any(
                    line.split() == ["module", target["expected_module"]] for line in (root / "source/go.mod").read_text().splitlines()):
                raise ValueError("Captured Go module differs from target.expected_module")
        write_json(root / "inputs/source.json", source)
        shutil.copytree(root / "source", root / "work", dirs_exist_ok=True)
        # A fresh empty Git boundary prevents configuration discovery in framework ancestors.
        git(root / "work", "-c", "init.templateDir=", "init", deadline=deadline)
        freeze(root / "source")
        (root / 'tools').mkdir()
        shutil.copyfile(Path(__file__).resolve().parents[1] / 'runtime/schedule.py', root / 'tools/schedule.py')
        freeze(root / 'tools')
        if config.review_context:
            if config.task_mode != 'review':
                raise ValueError('Fresh discovery must not receive review context')
            context = Path(config.review_context)
            if context.is_symlink() or not context.is_dir():
                raise ValueError('Review context must be a regular directory')
            files, excluded = file_inventory(context)
            if excluded:
                raise ValueError('Review context contains excluded/private files: ' + ', '.join(excluded))
            for name in files:
                dest = root / 'context' / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(context / name, dest)
                dest.chmod(files[name]['mode'])
            freeze(root / 'context')
        client = client_factory(config, root, target, deadline)
        phase("environment_check", "正在检查本地权限和工具环境；尚未调用模型。")
        record["environment"] = client.prepare()
        identity["codex"] = executable_identity(client)
        write_json(root / record["implementation"], identity)
        if environment_only:
            phase("dependency_check", "正在检查离线依赖；尚未调用模型。")
            client.check_environment()
            record['environment']['tool_evidence']['local_registration_and_tcp'] = 'verified_via_stdio'
            key = config.credential_name
            record["credential_available"] = bool(os.environ.get(key)) if key else "not inspected; codex_login checked only on authorized model run"
            record["stop"] = "environment_checked"
        else:
            client.authenticate()
            record["stop"] = "running"
            phase("model_audit", "本地准备完成，开始调用模型。")
            loop(config, root, source, target, client, deadline, record)
    except (TimeoutError, subprocess.TimeoutExpired) as exc:
        exhausted = time.monotonic() >= deadline
        record.update(stop="total_deadline" if exhausted else "preflight_or_runtime_error",
                      reason=str(exc) or ("Total deadline reached" if exhausted else "Local operation timed out before total deadline"))
    except KeyboardInterrupt:
        record["stop"] = "cancelled"
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        record.update(stop="preflight_or_runtime_error", reason=str(exc))
    finally:
        if client:
            agents = client.close()
            if agents is not None:
                record['agents'] = agents
        signal.signal(signal.SIGTERM, old_handler)
        record["elapsed_seconds"] = time.monotonic() - start
        record["ended_at"] = now()
        scrub_work(root)
        write_json(root / "run.json", record)
        index(root, record)
    return {"ok": (record["stop"] == "environment_checked" if environment_only else
                   record["stop"] in {"agent_call_limit", "total_deadline", "review_complete", "budget_wrap_up"}),
            "run_dir": str(root), "stop": record["stop"], "reason": record.get("reason"),
            "tool_evidence": record.get('environment', {}).get('tool_evidence', {}),
            "model_compatibility": "not evaluated" if environment_only else "requires review of raw tool and session evidence"}


def check_environment(config, target):
    return run(config, target, environment_only=True)
