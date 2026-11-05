"""Native text turns, isolated configuration, and verified local permissions."""
import json
import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import os
import shutil
import signal
import subprocess
import tempfile
import time
from pathlib import Path

from runtime.codex_support import (
    classify_failure, codex_diagnostic, common_settings, DISABLED_FEATURES, codex_options as options,
)
from runtime.toolchains import go_environment
from runtime.toolchains import cargo_tool, cargo_environment, maven_tools, maven_environment
from runtime.storage import write_json, digest
from runtime import local_exec
from runtime import agent_records


def process(command, cwd, folder, timeout, *, env, stdin="", secrets=(), execution_control=None):
    """Keep partial bytes and terminate all descendants on every exit path."""
    folder.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    result = {"status": "completed", "exit_code": None, "timeout_seconds": timeout, "command": command,
              "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    child = None
    with (folder / "stdout.jsonl").open("wb") as out, (folder / "stderr.log").open("wb") as err:
        try:
            if timeout <= 0:
                raise subprocess.TimeoutExpired(command, timeout)
            child = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.PIPE,
                                     stdout=out, stderr=err, start_new_session=True)
            payload, remaining = stdin.encode(), timeout
            control = json.loads(execution_control.read_text()) if execution_control else None
            while True:
                if control:
                    clock = json.loads(Path(control['execution_clock_path']).read_text())
                    now = time.monotonic()
                    limits = {control.get('deadline_kind', 'total_seconds'): control['run_deadline'] - now,
                              'agent_turn_timeout': timeout - (now - started) + local_exec.execution_seconds(clock, now)}
                    basis = min(limits, key=limits.get)
                    remaining = limits[basis]
                    if remaining <= 0:
                        result['timeout_limit'] = basis
                        raise subprocess.TimeoutExpired(command, timeout)
                try:
                    child.communicate(payload, timeout=min(remaining, .2) if execution_control else remaining)
                    break
                except subprocess.TimeoutExpired:
                    if not execution_control:
                        raise
                    payload = None
            result["exit_code"] = child.returncode
        except subprocess.TimeoutExpired:
            result["status"] = "timeout"
        except KeyboardInterrupt:
            result["status"] = "cancelled"
        except OSError as exc:
            result.update(status="error", reason=str(exc))
        finally:
            if child:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                child.wait()
                result["exit_code"] = child.returncode
    result["elapsed_seconds"] = time.monotonic() - started
    # Raw CLI bytes are retained except exact credential values, which never belong in archives.
    for name in ("stdout.jsonl", "stderr.log", "final.txt"):
        path = folder / name
        if path.exists():
            data = path.read_bytes()
            for secret in secrets:
                if secret:
                    data = data.replace(secret.encode(), b"[REDACTED_CREDENTIAL]")
            path.write_bytes(data)
    return result


def read_events(folder):
    events, invalid = [], 0
    for line in (folder / "stdout.jsonl").read_text(errors="replace").splitlines():
        try:
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError("Nonobject event")
            events.append(value)
        except ValueError:
            invalid += 1
    return events, invalid


def decode(folder, result, session_id=None):
    events, invalid = read_events(folder)
    identities = [e.get("thread_id") for e in events if e.get("type") == "thread.started"]
    identity = identities[-1] if identities else session_id
    completed = [e for e in events if e.get("type") == "turn.completed"]
    diagnostic = codex_diagnostic(events)
    # Baseline results are file-backed; a completed turn need not include final text.
    final_path = folder / "final.txt"
    final = final_path.read_text(errors="replace") if final_path.is_file() else ""
    tools = [e["item"] for e in events if e.get("type") == "item.completed"
             and isinstance(e.get("item"), dict) and e["item"].get("type") in
             {"command_execution", "file_change", "mcp_tool_call", "web_search"}]
    result.update(session_id=identity, native_completed=bool(completed), diagnostic=diagnostic,
                  usage=[e.get("usage") for e in completed], usage_semantics="raw CLI counters; not additive across turns or children",
                  tool_events=len(tools), invalid_jsonl_lines=invalid, final_present=bool(final))
    same_session = (isinstance(identity, str) and bool(identity.strip())
                    and all(x == identity for x in identities)
                    and (session_id is None or identity == session_id))
    refusal = any(e.get("type") == "refusal" or e.get("item", {}).get("type") == "refusal"
                  for e in events if isinstance(e.get("item", {}), dict))
    result["continuable_timeout"] = bool(result["status"] == "timeout" and same_session
        and not diagnostic["message"] and not refusal and not final.lstrip().startswith("RUN_BLOCKED:")
        and not any(e.get("type") in {"turn.failed", "error"} for e in events))
    if result["status"] != "completed":
        return result
    # Match src: native retries can emit error notifications before successful completion.
    if (result["exit_code"] != 0 or any(e.get("type") == "turn.failed" for e in events)
            or (not completed and any(e.get("type") == "error" for e in events))):
        failure = diagnostic["message"] or (folder / "stderr.log").read_text(errors="replace")
        result.update(status="external_error", failure_kind=classify_failure(failure),
                      reason=failure or "Native turn failed; inspect retained output")
        return result
    if not isinstance(identity, str) or not identity.strip():
        result.update(status="external_blocker_needs_review", reason="Missing native session identity")
        return result
    if any(x != identity for x in identities) or session_id and identity != session_id:
        result.update(status="session_mismatch", reason="Exact session changed; no replacement session allowed")
    elif not completed:
        result.update(status="external_blocker_needs_review", reason="Incomplete or unrecognized native completion")
    elif final.lstrip().startswith("RUN_BLOCKED:"):
        result.update(status="run_blocked", reason=final)
    elif refusal:
        result.update(status="external_blocker_needs_review", reason="Native refusal event; inspect retained output")
    return result


class Codex:
    def __init__(self, config, root, target, deadline):
        self.config, self.root, self.target, self.deadline = config, Path(root), target, deadline
        self.work = self.root / "work"
        private_parent = self.root
        private_parent.mkdir(exist_ok=True)
        self.private = tempfile.TemporaryDirectory(prefix=".client-", dir=private_parent)
        self.home = Path(self.private.name)
        self.client_home = self.home / "codex"
        self.client_home.mkdir()
        self.executable = shutil.which("codex")
        if not self.executable:
            raise ValueError("Codex CLI is unavailable")
        self.executable = str(Path(self.executable).resolve())
        self.helpers = self.home / "helpers"
        self.helpers.mkdir()
        for name in ("codex-linux-sandbox", "apply_patch"):
            (self.helpers / name).symlink_to(self.executable)
        self.environment = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": str(self.home),
                            "CODEX_HOME": str(self.client_home), "LANG": "C.UTF-8"}
        self.environment.update({key: os.environ[key] for key in (
            "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "all_proxy", "no_proxy",
            "SSL_CERT_FILE", "SSL_CERT_DIR") if key in os.environ})
        self.secrets = []
        self.read_roots = [str(Path(self.executable).parent), str(self.client_home / "tmp" / "arg0"), str(self.helpers)]
        self.tool_environment = {"PATH": "/usr/bin:/bin", "HOME": str(self.work / ".runtime/home"),
                                 "TMPDIR": str(self.work / ".runtime/tmp"), "LANG": "C.UTF-8"}
        for name in ("home", "tmp"):
            (self.work / ".runtime" / name).mkdir(parents=True, exist_ok=True)
        self.settings = {}
        self.session_ids = set()
        self.telemetry_started_at = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

    def close(self):
        try:
            if hasattr(self, 'execution_control'):
                local_exec.reconcile(self.root/'executions', self.execution_control['turn'], 'Client lifecycle ended without a completion record')
            try:
                return agent_records.collect(self.client_home, self.session_ids, self.work,
                                             self.telemetry_started_at, self.root, secrets=self.secrets)
            except OSError as exc:
                return {'record': None, 'usage': None, 'usage_complete': False,
                        'warnings': [f'{type(exc).__name__} retaining agent records']}
        finally:
            self.private.cleanup()

    def limit(self, maximum=30):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Total deadline reached during preparation")
        return min(maximum, remaining)

    def prefix(self, *, offline=False):
        # The outer mount namespace also normalizes non-path nsfs mounts for this CLI build.
        bwrap = shutil.which("bwrap")
        if not bwrap:
            raise ValueError("Bubblewrap is required for this Linux execution profile")
        return [bwrap, "--die-with-parent", "--ro-bind", "/", "/", "--bind", "/tmp", "/tmp", "--bind", str(self.root), str(self.root),
                "--bind", str(self.home), str(self.home), "--proc", "/proc", "--dev", "/dev",
                *(["--unshare-net"] if offline else []), "--", self.executable]

    def local(self, args, name, *, stdin="", offline=True, maximum=30, env=None):
        folder = self.root / "inputs" / name
        result = process([*self.prefix(offline=offline), *args], self.work, folder, self.limit(maximum),
                         env=env or self.environment, stdin=stdin)
        write_json(folder / "result.json", result)
        if result["status"] == "cancelled":
            raise KeyboardInterrupt
        if result["status"] == "timeout" and time.monotonic() >= self.deadline:
            raise TimeoutError("Total deadline reached during local preparation")
        return result, (folder / "stdout.jsonl").read_text(errors="replace")

    def authenticate(self):
        key = self.config.credential_name
        if self.config.auth_mode == "api_key":
            value = os.environ.get(key)
            if not value:
                raise ValueError(f"Missing credential environment variable: {key}; no model request sent")
            self.environment[key if self.config.codex_provider else "CODEX_API_KEY"] = value
            self.secrets = [value]
        else:
            original = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "auth.json"
            if not original.is_file() or original.is_symlink():
                raise ValueError("codex_login requires existing file-backed authentication; no automatic login")
            data = original.read_bytes()
            auth = json.loads(data)
            if auth.get("auth_mode") != "chatgpt":
                raise ValueError("codex_login requires ChatGPT auth; select api_key explicitly for API auth")
            (self.client_home / "auth.json").write_bytes(data)
            (self.client_home / "auth.json").chmod(0o600)
            self.secrets = [value for key, value in auth.get("tokens", {}).items()
                            if key in {"access_token", "refresh_token", "id_token"} and isinstance(value, str)]

    def prepare(self):
        result, text = self.local(['--version'], 'cli-version')
        if result['status'] != 'completed' or result['exit_code'] or 'codex' not in text:
            raise ValueError('Codex CLI version unavailable')
        self.version = text.strip()
        backend = self.target["execution_backend"]
        scratch = self.work / '.runtime'
        if backend == 'go_module':
            discovered = subprocess.run(['go', 'env', 'GOROOT'], capture_output=True, text=True,
                                        timeout=self.limit(), check=True)
            tool_roots = [Path(discovered.stdout.strip()).resolve()]
            cache = Path(self.config.go_mod_cache_dir) if self.config.go_mod_cache_dir else scratch / 'go-mod'
            self.tool_environment.update(go_environment(self.work))
            self.tool_environment.update(GOCACHE=str(scratch/'go-build'), GOMODCACHE=str(cache),
                                         GOFLAGS='-mod=readonly -count=1')
            for name in ('go-build', 'go-mod'):(scratch/name).mkdir(exist_ok=True)
            commands = {'go': ['go', 'version'], 'go_environment':
                ['go', 'env', 'GOOS', 'GOARCH', 'GOVERSION', 'GOROOT', 'GOMODCACHE', 'GOCACHE', 'GOFLAGS', 'GOWORK']}
            dependencies = [cache] if self.config.go_mod_cache_dir else []
        elif backend == 'cargo':
            cargo = cargo_tool()
            tool_roots = [cargo.parent.parent]
            cache = Path(self.config.cargo_dependency_cache_dir or Path.home()/'.cargo')
            if not any((cache/name).is_dir() for name in ('registry', 'git')):
                raise ValueError('cargo_dependency_cache_dir needs registry/ or git/; a compiled seed directory is not a dependency cache')
            self.tool_environment.update(cargo_environment(scratch, cargo, cache))
            dependencies = [cache/name for name in ('registry', 'git') if (cache/name).is_dir()]
            commands = {'cargo': ['cargo', '--version', '--verbose'], 'rustc': ['rustc', '--version', '--verbose']}
        elif backend == 'maven':
            maven, java_home = maven_tools()
            tool_roots = [java_home, maven.parent.parent]
            cache = Path(self.config.maven_dependency_cache_dir or Path.home()/'.m2/repository')
            self.tool_environment.update(maven_environment(scratch, maven, java_home, cache))
            dependencies = [cache]
            commands = {'maven': ['mvn', '--version'], 'java': ['java', '-version']}
        else:
            raise ValueError('Unsupported toolchain: ' + backend)
        for cache in dependencies:
            if not cache.is_dir() or cache.is_symlink() or self.root.is_relative_to(cache) or cache.is_relative_to(self.root):
                raise ValueError('Dependency cache must be a separate existing directory')
        if (self.root / 'context').is_dir():
            dependencies.append(self.root / 'context')
        if (self.root / 'tools').is_dir():
            dependencies.append(self.root / 'tools')
        self.read_roots.extend(str(path) for path in [*tool_roots, *dependencies])
        tool_path = ':'.join(str(path/'bin') for path in tool_roots)
        self.tool_environment["PATH"] = tool_path + ':' + str(self.helpers) + ':/usr/bin:/bin'
        self.execution_control = {'work': str(self.work), 'records': str(self.root/'executions'),
            'tool_roots': list(map(str, tool_roots)),
            'read_only_roots': [str(self.root/'source'), *map(str, dependencies)],
            'environment': {**self.tool_environment, 'PATH': tool_path + ':/usr/bin:/bin'},
            'action_timeout': self.config.budget.action_timeout, 'run_deadline': self.deadline,
            'turn': 'environment-check',
            'allow_experiments': True}
        source = json.loads((self.root / 'inputs/source.json').read_text())
        self.execution_control['source_context'] = {'phase': self.config.task_mode, 'base_commit': source['commit']}
        self.execution_control['replay_sources'] = {}
        if backend == 'go_module':
            self.execution_control['replay_sources']['candidate'] = {'path': str(self.root/'source'), 'commit': source['commit']}
            if (self.root / 'context/request.json').is_file():
                request = json.loads((self.root / 'context/request.json').read_text())
                self.execution_control['replay_sources']['before'] = {'path': str(self.root/'context/before'), 'commit': request['before_commit']}
        # check-env authorizes only the fixed local probe. Real calls require both original switches.
        self.control_path = self.home/'local-exec.json'
        write_json(self.control_path, self.execution_control)
        (self.root/'executions').mkdir(exist_ok=True)
        self.mcp_settings = local_exec.server_settings(self.control_path, max(self.config.budget.action_timeout, self.config.budget.agent_turn_timeout), self.deadline)
        filesystem = {":root": "deny", ":minimal": "read",
                      str(self.root / "source"): "read", str(self.work): "write",
                      str(self.root / "turns"): "read", str(self.root / "inputs/task.md"): "read",
                      str(self.root / "executions"): "read",
                      **{path: "read" for path in self.read_roots}}
        self.settings = {"default_permissions": "codex_plain", "permissions.codex_plain.filesystem": filesystem,
                         "permissions.codex_plain.network.enabled": False, "approval_policy": "never",
                         "shell_environment_policy.inherit": "none",
                         "shell_environment_policy.set": self.tool_environment,
                         "shell_environment_policy.ignore_default_excludes": False,
                         "shell_environment_policy.experimental_use_profile": False,
                         **common_settings(self.config.codex_provider),
                         "projects": {str(self.work): {"trust_level": "untrusted"}},
                         "model": self.config.agent_model}
        self.settings['mcp_servers'] = {'audit_local': self.mcp_settings}
        if self.config.agent_reasoning_effort is not None:
            self.settings["model_reasoning_effort"] = self.config.agent_reasoning_effort
        provider = self.config.codex_provider
        if provider:
            self.settings["model_provider"] = provider.id
            for key, value in {"name": provider.id, "base_url": provider.base_url, "env_key": provider.env_key,
                               "wire_api": "responses", "requires_openai_auth": False, "supports_websockets": False}.items():
                self.settings[f"model_providers.{provider.id}.{key}"] = value
        else:
            self.settings["forced_login_method"] = "api" if self.config.auth_mode == "api_key" else "chatgpt"
        if provider and provider.model_catalog_path:
            raw = Path(provider.model_catalog_path).read_bytes()
            catalog = json.loads(raw)
            models = catalog.get("models", [])
            if len(models) != 1 or models[0].get("slug") != self.config.agent_model:
                raise ValueError("Catalog must contain exactly the selected model")
            supported = {x["effort"] for x in models[0].get("supported_reasoning_levels", [])}
            if self.config.agent_reasoning_effort is not None and self.config.agent_reasoning_effort not in supported:
                raise ValueError("Catalog does not support the requested reasoning effort")
            if self.config.agent_reasoning_effort is None and (supported or models[0].get("default_reasoning_level")):
                raise ValueError("null cannot omit reasoning with this catalog's defaults; select an explicit effort")
        elif provider or self.config.agent_reasoning_effort is None:
            raise ValueError("Custom models and omitted reasoning require an explicitly verified model catalog")
        else:
            result, _ = self.local(["debug", "models", "--bundled"], "bundled-catalog")
            if result["exit_code"]:
                raise ValueError("Cannot capture the native bundled model catalog without network")
            raw = (self.root / "inputs/bundled-catalog/stdout.jsonl").read_bytes()
            selected = [m for m in json.loads(raw)["models"] if m.get("slug") == self.config.agent_model]
            if len(selected) != 1 or self.config.agent_reasoning_effort not in {
                    x["effort"] for x in selected[0].get("supported_reasoning_levels", [])}:
                raise ValueError("Native model or effort is not advertised by this installed CLI catalog")
        (self.root / "inputs/models.json").write_bytes(raw)
        self.settings["model_catalog_json"] = str(self.root / "inputs/models.json")
        self.permission_probe()
        write_json(self.root/'inputs/local-exec.json', local_exec.identity(self.mcp_settings, self.execution_control))
        self.execution_control['allow_experiments'] = self.config.allow_agent_materials and self.config.allow_experiments
        write_json(self.control_path, self.execution_control)
        # The selected CLI materializes bundled skills only on prompt initialization.
        result, _ = self.local(["debug", "prompt-input", *options(self.settings),
                               "Local configuration initialization only."], "prompt-bootstrap")
        if result["status"] != "completed" or result["exit_code"]:
            raise ValueError("Cannot initialize bundled skill suppression")
        self.settings["skills.config"] = [{"path": str(path), "enabled": False}
                                          for path in sorted(self.client_home.glob("skills/**/SKILL.md"))]
        versions = {}
        commands['platform'] = ['uname', '-sm']
        for name, command in commands.items():
            result, text = self.local(["sandbox", "--include-managed-config", "-P", "codex_plain", *options(self.settings),
                                      "-C", str(self.work), *command], "tool-" + name)
            if result["status"] != "completed" or result["exit_code"]:
                raise ValueError("Cannot record the actual sandbox tool version: " + name)
            versions[name] = text.strip() or (self.root / 'inputs' / ('tool-' + name) / 'stderr.log').read_text(errors='replace').strip()
        write_json(self.root / "inputs/cli-settings.json", self.settings)
        return {"cli": self.version, "tool_roots": list(map(str, tool_roots)), "tool_environment": self.tool_environment, "versions": versions,
                "network": "ordinary shell: disabled; isolated_exec: private loopback; model client: selected provider",
                "subagents": True, "cache_policy": "private cold builds; optional read-only shared dependencies",
                "native_retries": {"request_max_retries": 4, "stream_max_retries": 5} if provider else
                    {"policy": "bundled provider defaults, tied to recorded CLI version; reserved provider cannot be overridden"},
                "unbounded_connection_retries": False, "outer_retries": 0,
                "tool_evidence": {"local_registration_and_tcp": "not_checked_in_ordinary_run",
                                  "model_request_tool_surface": "not_inspected",
                                  "real_model_tool_use": "not_evaluated"},
                "reasoning": self.config.agent_reasoning_effort, "permission_probe": "verified"}

    async def mcp_probe(self):
        settings = self.mcp_settings
        server = StdioServerParameters(command=settings['command'], args=settings['args'], cwd=settings['cwd'], env={})
        with (self.root/'inputs/local-exec-probe.stderr').open('w') as errors:
            async with stdio_client(server, errlog=errors) as streams, ClientSession(*streams) as session:
                await session.initialize()
                inventory = await session.list_tools()
                if inventory.tools != [local_exec.tool()]:
                    raise ValueError('MCP inventory differs from the configured tool')
                result = await session.call_tool('isolated_exec', {'argv': ['python3', '-c',
                    "import socket; s=socket.socket();s.bind(('127.0.0.1',0));s.listen();c=socket.create_connection(s.getsockname());a,_=s.accept();c.sendall(b'ping');assert a.recv(4)==b'ping';a.sendall(b'pong');assert c.recv(4)==b'pong';print('ISOLATED_TCP_VERIFIED')"], 'timeout_seconds': 10.0})
                write_json(self.root/'inputs/local-exec-probe.json', {'inventory': inventory.model_dump(mode='json'),
                                                                    'call': result.model_dump(mode='json')})
                observed = result.structuredContent or {}
                if result.isError or observed.get('status') != 'completed' or observed.get('exit_code') != 0 or 'ISOLATED_TCP_VERIFIED' not in observed.get('stdout', {}).get('preview', ''):
                    raise ValueError('Isolated execution MCP probe failed; no model request sent')

    def permission_probe(self):
        canary = self.home / "credential-canary"
        canary.write_text("private canary")
        protected = self.root / "turns/permission-canary"
        protected.write_text("retained canary")
        old_result = self.root / "old-results-canary"
        old_result.write_text("old result canary")
        source = next(p for p in (self.root / "source").rglob("*") if p.is_file())
        framework = Path(__file__).resolve().parent.parent
        denied = [canary, old_result, framework / "AGENTS.md", framework / "auditor", framework / "inputs",
                  framework / "README.md", self.client_home / "auth.json"]
        script = """import errno, os, pathlib, socket, subprocess, threading
def blocked(fn):
    try: fn()
    except OSError as exc:
        assert exc.errno in (errno.EPERM, errno.EACCES, errno.EROFS, errno.ENOENT), exc
    else: raise AssertionError('Forbidden operation succeeded')
"""
        script += f"for name in {list(map(str, denied))!r}:\n    blocked(lambda: pathlib.Path(name).read_bytes())\n"
        script += f"for name in {[str(source), str(protected)]!r}:\n    assert pathlib.Path(name).read_bytes()\n    blocked(lambda: pathlib.Path(name).open('a'))\n    blocked(lambda: os.chmod(name, 0o600))\n"
        names = ["OPENAI_API_KEY", "CODEX_API_KEY", self.config.credential_name or "BASELINE_SECRET"]
        script += f"assert not set({names!r}) & set(os.environ)\n"
        script += "for entry in pathlib.Path('/proc').glob('[0-9]*/environ'):\n    try: data = entry.read_bytes()\n    except OSError: continue\n    assert b'baseline-credential-canary' not in data, 'Credential visible through procfs'\n"
        script += """pathlib.Path('permission-write.txt').write_text('allowed')
assert subprocess.check_output(['/bin/sh', '-c', 'printf pipe | cat']) == b'pipe'
t = threading.Thread(target=lambda: None); t.start(); t.join()
blocked(lambda: socket.socket().bind(('127.0.0.1', 0)))
blocked(lambda: socket.socket().connect(('192.0.2.1', 9)))
print('PERMISSIONS_VERIFIED')
"""
        probe_environment = {**self.environment, **{name: "baseline-credential-canary" for name in names}}
        result, text = self.local(["sandbox", "--include-managed-config", "-P", "codex_plain",
                                  *options(self.settings), "-C", str(self.work), "/usr/bin/python3", "-c", script],
                                 "permission-probe", env=probe_environment)
        (self.work / "permission-write.txt").unlink(missing_ok=True)
        if result["status"] != "completed" or result["exit_code"] != 0 or "PERMISSIONS_VERIFIED" not in text:
            raise ValueError("Permission probe failed; no source may be sent to a model; inspect inputs/permission-probe")

    def prompt_probe(self):
        # Explicit compatibility diagnostics, never a model turn.
        result, text = self.local(["debug", "prompt-input", *options(self.settings),
                                   "Local configuration inspection only."], "prompt-input")
        if result["status"] != "completed" or result["exit_code"]:
            raise ValueError("Native prompt isolation probe failed")
        items = json.loads(text)
        kinds = [kind for item in items for kind in item.get("internal_chat_message_metadata_passthrough", {}).get("content_item_kinds", [])]
        if any(kind in {"host_skills.instructions", "agents_md.instructions"} or "memory" in kind or "plugin" in kind for kind in kinds):
            raise ValueError("Unexpected automatic instructions in native prompt; inspect inputs/prompt-input")
        result, text = self.local(["features", "list", *options(self.settings)], "features")
        features = {line.split()[0]: line.split()[-1] for line in text.splitlines() if len(line.split()) >= 3}
        if (result["exit_code"] or features.get('multi_agent') != 'true'
                or any(features.get(name) != "false" for name in DISABLED_FEATURES)):
            raise ValueError("Native subagent setting or required disabled capability could not be verified")

    def dependency_probe(self):
        command = {'go_module': ['go', 'list', '-m', 'all'],
                   'cargo': ['cargo', 'metadata', '--offline', '--format-version', '1'],
                   'maven': ['mvn', '-o', '-B', '-ntp', '-pl', self.target['execution_package'], '-am', '-DskipTests', 'test-compile']}[self.target['execution_backend']]
        result, _ = self.local(["sandbox", "--include-managed-config", "-P", "codex_plain", *options(self.settings),
                                "-C", str(self.work), *command], "dependency-probe", maximum=60)
        if result["status"] != "completed" or result["exit_code"]:
            raise ValueError("Offline dependency resolution failed; inspect inputs/dependency-probe")

    def check_environment(self):
        self.prompt_probe()
        self.dependency_probe()
        self.execution_control.update(allow_experiments=True)
        write_json(self.control_path, self.execution_control)
        try:
            asyncio.run(asyncio.wait_for(self.mcp_probe(), self.limit()))
        except (asyncio.TimeoutError, TimeoutError) as exc:
            raise TimeoutError('MCP compatibility check timed out') from exc
        except Exception as exc:
            raise ValueError('MCP compatibility check failed; inspect inputs/local-exec-probe.stderr: ' + repr(exc)) from exc
        finally:
            self.execution_control['allow_experiments'] = self.config.allow_agent_materials and self.config.allow_experiments
            write_json(self.control_path, self.execution_control)

    def turn(self, folder, prompt, timeout, session_id, *, deadline=None):
        # rmdir removes only real empty sandbox residue; it never follows links.
        for name in (".codex", ".agents"):
            path = self.work / name
            try:
                path.rmdir()
            except FileNotFoundError:
                pass
            except OSError as exc:
                raise ValueError(f"Pre-invocation reserved path {path}: {exc}") from exc
        if not (self.config.allow_agent_materials and self.config.allow_experiments):
            raise ValueError('Model transmission and local execution must both be authorized')
        implementation = json.loads((self.root/'inputs/implementation.json').read_text())
        for path, expected in implementation['reload_inputs'].items():
            if digest(Path(path).read_bytes()) != expected:
                raise ValueError('Isolated execution implementation changed; start a new run')
        # Late cleanup from a previous service can only update that turn's private clock.
        clock_path = self.home / ('execution-clock-' + folder.name + '.json')
        write_json(clock_path, {'elapsed_seconds': 0.0})
        turn_deadline = min(self.deadline, deadline if deadline is not None else self.deadline)
        self.execution_control.update(run_deadline=turn_deadline,
                                      deadline_kind='reporting_reserve' if turn_deadline < self.deadline else 'total_seconds',
                                      turn=folder.name, execution_clock_path=str(clock_path),
                                      allow_experiments=True)
        write_json(self.control_path, self.execution_control)
        command = [*self.prefix(), "exec", *(["resume"] if session_id else []), "--strict-config",
                   "--skip-git-repo-check", "--ignore-user-config", "--json",
                   "--output-last-message", str(folder / "final.txt"), *options(self.settings)]
        command += [session_id, "-"] if session_id else ["-"]
        result = process(command, self.work, folder, timeout, env=self.environment, stdin=prompt, secrets=self.secrets,
                         execution_control=self.control_path)
        local_exec.reconcile(self.root/'executions', folder.name, 'Codex turn ended: '+result['status'])
        result = decode(folder, result, session_id)
        if result.get('session_id'):
            self.session_ids.add(result['session_id'])
        return result
