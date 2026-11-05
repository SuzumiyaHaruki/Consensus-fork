"""One run-scoped STDIO tool; commands execute only in an isolated filesystem."""
import asyncio
from contextlib import asynccontextmanager
import fcntl
import importlib.metadata
import json
import os
import signal
import shutil
import sys
import sysconfig
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import anyio
from mcp import types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from pydantic import BaseModel, ConfigDict, Field

from runtime.storage import write_json
from runtime import replay


DESCRIPTION = ('Run an ordinary local test in a private network and PID namespace. The ordinary shell retains its current restrictions. '
               'Use this tool for TCP or a bounded isolated run; start all communicating processes within the same invocation. '
               'Returns execution output, not an audit verdict. cwd is relative to this run working copy. '
               'Execution remains bounded by action and active run/phase deadlines; only the auditor pauses its Agent turn timer. '
               'No background service survives an invocation. Complete raw logs are retained read-only. '
               'Calls in the same run serialize across tool processes, including native subagents; queue waiting consumes the run budget. '
               'Optionally select source from the captured sources listed in the run brief and overlays of relative test/helper files from work. '
               'This starts from a private candidate copy; overlays and the starting commit are retained. Without source, work is mutable and no exact candidate binding is claimed. '
               'Use outputs to retain selected relative files/directories from the execution workspace before cleanup, including on test failure/timeout. '
               'Read result.artifacts for saved files and exclusions; unselected files in a source copy are deleted. '
               'Output collection excludes links, credentials, executables and private/cache directories; limits are 16 MB per file, 64 MiB total and 1024 entries.')


class Arguments(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, allow_inf_nan=False)
    argv: list[str] = Field(min_length=1)
    cwd: str = '.'
    timeout_seconds: float | None = Field(default=None, gt=0)
    source: str | None = None
    overlays: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)


def tool():
    return types.Tool(name='isolated_exec', description=DESCRIPTION, inputSchema=Arguments.model_json_schema())


def server_settings(control, action_timeout, run_deadline=None):
    script = Path(__file__).resolve()
    # -S excludes site hooks/.pth; only explicitly selected installed packages and trusted source load.
    code = 'import sys,runpy;sys.path[:0]=' + repr([str(script.parents[1]), sysconfig.get_path('purelib')])
    code += ';runpy.run_path(' + repr(str(script)) + ',run_name="__main__")'
    # A queued call can wait behind another agent's execution. The service still enforces
    # the action limit after acquiring the run lock and the shared total deadline.
    tool_timeout = max(action_timeout, run_deadline - time.monotonic()) if run_deadline is not None else action_timeout
    return {'command': '/usr/bin/env', 'args': ['-i', 'PATH=/usr/bin:/bin', 'LANG=C.UTF-8',
            sys.executable, '-I', '-S', '-c', code, str(control)], 'cwd': str(script.parent),
            'env_vars': [], 'enabled_tools': ['isolated_exec'], 'required': True,
            'startup_timeout_sec': 15, 'tool_timeout_sec': tool_timeout + 5,
            'default_tools_approval_mode': 'approve'}


def identity(settings, control):
    return {'server': settings, 'tool': tool().model_dump(mode='json', exclude_none=True),
            'protocol_package': {'name': 'mcp', 'version': importlib.metadata.version('mcp')},
            'permissions': {key: control[key] for key in ('work','records','tool_roots','read_only_roots','environment','action_timeout')},
            'isolation': 'allowlisted files; private network/PID/IPC; clean environment; calls serialized across processes per run'}


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def remaining(control, requested):
    limits = {'requested': requested if requested is not None else control['action_timeout'],
              'action_timeout': control['action_timeout'],
              control.get('deadline_kind', 'total_seconds'): control['run_deadline'] - time.monotonic()}
    key = min(limits, key=limits.get)
    return max(0, limits[key]), key


def execution_seconds(clock, now):
    """Only the trusted serial execution service can pause the Agent timer."""
    active = clock.get('active')
    # A dead service cannot keep granting time after its last action deadline.
    return clock['elapsed_seconds'] + (max(0, min(now, active[1]) - active[0]) if active else 0)


def validate_directory(work, relative):
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('cwd must remain relative to this run working copy')
    resolved = (work/path).resolve(strict=True)
    if not resolved.is_relative_to(work) or not resolved.is_dir():
        raise ValueError('cwd escapes this run working copy or is not a directory')
    return resolved


def isolated_command(command, workspace, directory, hosts, tool_roots=(), read_only_roots=()):
    """Allowlisted filesystem for caller-selected commands; roots are trusted inputs."""
    executable = shutil.which('bwrap')
    if not executable:
        raise FileNotFoundError('Bubblewrap is required; no host execution fallback')
    args = [executable, '--die-with-parent', '--new-session', '--unshare-net', '--unshare-pid',
            '--unshare-ipc', '--unshare-uts', '--hostname', 'audit-local', '--cap-drop', 'ALL']
    for name in ('/usr/bin', '/usr/lib', '/usr/lib64', '/usr/libexec', '/usr/include', '/usr/share', '/etc/alternatives'):
        if Path(name).is_dir():args += ['--ro-bind', name, name]
    for name in ('/bin', '/sbin', '/lib', '/lib64'):
        path = Path(name)
        if path.is_symlink():args += ['--symlink', os.readlink(path), name]
        elif path.is_dir():args += ['--ro-bind', name, name]
    if Path('/etc/ld.so.cache').is_file():args += ['--ro-bind', '/etc/ld.so.cache', '/etc/ld.so.cache']
    # Establish private temporary filesystems first; explicit read-only roots may live under /tmp.
    args += ['--tmpfs', '/tmp', '--tmpfs', '/run', '--dir', '/var', '--symlink', '/run', '/var/run',
             '--dev', '/dev', '--proc', '/proc']
    for path in (*tool_roots, *read_only_roots):
        args += ['--ro-bind', str(path), str(path)]
    args += ['--ro-bind', str(hosts), '/etc/hosts',
             '--bind', str(workspace), str(workspace),
             '--chdir', str(directory), '--', *command]
    return args


@asynccontextmanager
async def execution_lock(records, deadline):
    """Coordinate separate MCP servers sharing mutable work and the execution clock."""
    records = Path(records)
    records.mkdir(parents=True, exist_ok=True)
    # This directory is outside the candidate's writable execution filesystem.
    # flock releases on process exit, so a dead subagent cannot strand the run.
    with (records / '.execution.lock').open('a') as lock:
        while True:
            if time.monotonic() >= deadline:
                raise TimeoutError('Run deadline reached while waiting for local execution')
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                await asyncio.sleep(min(.05, max(0, deadline - time.monotonic())))
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


async def execute(control, arguments, request_id):
    async with execution_lock(control['records'], control['run_deadline']):
        return await execute_locked(control, arguments, request_id)


async def execute_locked(control, arguments, request_id):
    args = Arguments.model_validate(arguments)
    if not args.argv[0] or any('\0' in value for value in args.argv):
        raise ValueError('argv needs a nonempty executable and must not contain NUL')
    if not control['allow_experiments']:
        raise ValueError('Local execution is not authorized')
    work = Path(control['work'])
    # The selected source may have a different directory layout from mutable work.
    execution_id = uuid4().hex
    folder = Path(control['records'])/execution_id
    folder.mkdir(parents=True)
    limit, basis = remaining(control, args.timeout_seconds)
    record = {'execution_id': execution_id, 'turn': control['turn'], 'mcp_request_id': request_id,
              'argv': args.argv, 'cwd': str(work / args.cwd), 'requested_source': args.source,
              'requested_overlays': args.overlays, 'requested_timeout_seconds': args.timeout_seconds,
              'requested_outputs': args.outputs,
              'timeout_seconds': limit, 'timeout_limit': basis, 'started_at': timestamp(),
              'status': 'running', 'exit_code': None, 'service_pid': os.getpid()}
    started = time.monotonic()
    write_json(folder/'result.json', record)
    child = None
    execution_work = None
    pumps = []
    clock_path = Path(control['execution_clock_path']) if control.get('execution_clock_path') else None
    clock = None
    try:
        execution_work, environment, context = replay.prepare(control, args.source, args.overlays, folder)
        cwd = validate_directory(execution_work, args.cwd)
        record.update(cwd=str(cwd), cwd_relative=str(cwd.relative_to(execution_work)), source_context=context)
        write_json(folder/'result.json', record)
        if clock_path:
            clock = json.loads(clock_path.read_text())
            # A previous server may have died without clearing its bounded active interval.
            clock['elapsed_seconds'] = execution_seconds(clock, started)
            clock['active'] = [started, started + limit]
            write_json(clock_path, clock)
        if limit <= 0:
            record['status'] = 'timeout'
        else:
            hosts = folder/'hosts'
            hosts.write_text('127.0.0.1 localhost audit-local\n::1 localhost audit-local\n')
            command = isolated_command(args.argv, execution_work, cwd, hosts, control['tool_roots'], control['read_only_roots'])
            record['command'] = command
            write_json(folder/'result.json', record)
            async def capture(stream, path):
                with path.open('wb') as output:
                    while data := await stream.read(65536):
                        output.write(data); output.flush()
            if started + limit <= time.monotonic():
                record['status'] = 'timeout'
            else:
                child = await asyncio.create_subprocess_exec(*command, cwd='/', env=environment,
                    stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE, start_new_session=True)
                pumps = [asyncio.create_task(capture(stream, folder/(name+'.txt')))
                         for name, stream in (('stdout', child.stdout), ('stderr', child.stderr))]
                record['process_id'] = child.pid
                write_json(folder/'result.json', record)
                try:
                    await asyncio.wait_for(child.wait(), max(0, started + limit - time.monotonic()))
                    record.update(status='completed', exit_code=child.returncode)
                except asyncio.TimeoutError:
                    record['status'] = 'timeout'
    except asyncio.CancelledError:
        record.update(status='cancelled', reason=control.get('cancellation_reason', 'request_cancelled'))
        raise
    except (OSError, ValueError) as exc:
        record.update(status='launch_error', reason=str(exc))
    finally:
        with anyio.CancelScope(shield=True):
            if child:
                try: os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError: pass
                await asyncio.wait_for(child.wait(), 3)
                record['exit_code'] = child.returncode
                await asyncio.wait_for(asyncio.gather(*pumps), 3)
            record.update(ended_at=timestamp(), elapsed_seconds=time.monotonic()-started)
            for name in ('stdout', 'stderr'):
                path = folder/(name+'.txt'); path.touch(exist_ok=True)
                with path.open('rb') as stream: preview = stream.read(8192)
                record[name] = {'path': str(path), 'preview': preview.decode(errors='replace'),
                                'truncated': path.stat().st_size > len(preview), 'bytes': path.stat().st_size}
            if record['status'] == 'completed' and record['exit_code'] and record['stderr']['preview'].startswith('bwrap:'):
                record['status'] = 'launch_error'
            try:
                if args.outputs and execution_work is not None:
                    record['artifacts'] = replay.retain_outputs(execution_work, args.outputs, folder)
            except (OSError, ValueError) as exc:
                record['artifacts'] = {'files': [], 'excluded': [{'path': '.', 'reason': str(exc)}]}
            try:
                replay.cleanup(folder)
            except OSError as exc:
                record['cleanup_error'] = str(exc)
            write_json(folder/'result.json', record)
            if clock is not None:
                clock['elapsed_seconds'] += record['elapsed_seconds']
                clock.pop('active', None)
                write_json(clock_path, clock)
    return record


async def serve(path, parent_fd):
    control = json.loads(path.read_text())
    server = Server('audit_local')
    lock = anyio.Lock()
    @server.list_tools()
    async def list_tools():
        return [tool()]
    @server.call_tool()
    async def call_tool(name, arguments):
        if name != 'isolated_exec':raise ValueError('Unknown tool')
        async with lock:
            return await execute(control, arguments, server.request_context.request_id)
    # STDIO EOF and termination cancel in-flight work rather than waiting for its requested time.
    with anyio.CancelScope() as scope:
        loop = asyncio.get_running_loop()
        def stop(reason):
            control.setdefault('cancellation_reason', reason)
            scope.cancel()
        for sig in (signal.SIGTERM, signal.SIGINT):loop.add_signal_handler(sig, stop, sig.name)
        # A pidfd tracks the parent process, not the transient thread that spawned us.
        loop.add_reader(parent_fd, stop, 'parent_exit')
        reader = asyncio.StreamReader(limit=sys.maxsize)
        transport = None
        class Input:
            def __aiter__(self):return self
            async def __anext__(self):
                line = await reader.readline()
                if not line:
                    stop('stdio_eof')
                    raise StopAsyncIteration
                return line.decode('utf-8')
        try:
            transport, _ = await loop.connect_read_pipe(lambda: asyncio.StreamReaderProtocol(reader), sys.stdin.buffer)
            async with stdio_server(stdin=Input()) as streams:
                await server.run(*streams, server.create_initialization_options())
        finally:
            loop.remove_reader(parent_fd)
            if transport:transport.close()


def reconcile(records, turn, reason):
    """Preserve abruptly interrupted executions without inventing completion receipts."""
    for path in Path(records).glob('*/result.json'):
        record = json.loads(path.read_text())
        if record['turn'] == turn and record['status'] == 'running':
            record.update(status='interrupted', reason=reason, observed_at=timestamp())
            write_json(path, record)


if __name__ == '__main__':
    parent = os.getppid()
    parent_fd = os.pidfd_open(parent)
    try:
        if os.getppid() != parent:sys.exit(1)
        anyio.run(serve, Path(sys.argv[1]), parent_fd)
    finally:
        os.close(parent_fd)
