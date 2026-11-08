"""Attach the auditor's bounded local execution service to native generation."""
import json
from pathlib import Path
import subprocess
import sys
import time

from runtime.storage import read_json, write_json

ROOT = Path(__file__).resolve().parents[1]


def prepare(settings, stage, deadline):
    # The controller remains stdlib-only; installed MCP dependencies live in this Python.
    bootstrap = 'import sys;sys.path.insert(0, ' + repr(str(ROOT)) + ');from generator.execution import main;main()'
    try:
        result = subprocess.run([settings.execution_python, '-I', '-c', bootstrap,
                                 str(stage), json.dumps(deadline), str(settings.action_seconds)],
                                capture_output=True, text=True, timeout=max(0.01, min(45, deadline - time.monotonic())) if deadline is not None else 45)
    except subprocess.TimeoutExpired as exc:
        errors = exc.stderr or b''
        if isinstance(errors, bytes):
            errors = errors.decode(errors='replace')
        (stage / 'execution-setup.stderr').write_text(errors + '\nLocal execution setup timed out.\n')
        raise
    (stage / 'execution-setup.stderr').write_text(result.stderr)
    if result.returncode:
        raise ValueError('Isolated execution preflight failed; see execution-setup.stderr. No model started.')
    return json.loads(result.stdout)


def reconcile(stage):
    # Called after the entire Codex process group has terminated, including the MCP server.
    from .runner import utc_now
    for path in (stage / 'executions').glob('*/result.json'):
        record = read_json(path)
        if record['status'] == 'running':
            record.update(status='interrupted', ended_at=utc_now(), reason='Generation process group ended')
            write_json(path, record)


def configure(stage, deadline, action_seconds):
    from runtime import local_exec
    from runtime.codex_support import codex_options
    from runtime.toolchains import go_environment
    stage = stage.resolve()
    work = stage / 'workspace'
    scratch = work / '.runtime'
    for name in ('home', 'tmp', 'go-build', 'go-mod'):
        (scratch / name).mkdir(parents=True, exist_ok=True)
    goroot = Path(subprocess.check_output(['go', 'env', 'GOROOT'], text=True, timeout=10).strip()).resolve()
    environment = {'PATH': str(goroot / 'bin') + ':/usr/bin:/bin', 'HOME': str(scratch / 'home'),
                   'TMPDIR': str(scratch / 'tmp'), 'LANG': 'C.UTF-8', **go_environment(work),
                   'GOCACHE': str(scratch / 'go-build'), 'GOMODCACHE': str(scratch / 'go-mod')}
    control = {'work': str(work), 'records': str(stage / 'executions'), 'tool_roots': [str(goroot)],
               'read_only_roots': [str(stage / 'inputs')], 'environment': environment,
               'action_timeout': action_seconds, 'run_deadline': deadline,
               'turn': 'generation-or-repair', 'allow_experiments': True}
    metadata = json.loads((stage / 'run.json').read_text()) if (stage / 'run.json').is_file() else {}
    control['source_context'] = {'phase': metadata.get('workflow_role', 'generation'),
                                 'base_commit': metadata.get('candidate_commit')}
    control['replay_sources'] = ({'candidate': {'path': metadata['candidate_path'], 'commit': metadata['candidate_commit']}}
                                 if metadata.get('candidate_path') and metadata.get('candidate_commit') else {})
    path = stage / 'execution-control.json'
    write_json(path, control)
    server = local_exec.server_settings(path, action_seconds, deadline)
    return {'options': codex_options({'mcp_servers.forge_local': server}),
            'identity': local_exec.identity(server, control), 'server': server}


async def probe(server, stage):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    # Real STDIO registration and private TCP; never loads authentication or contacts a model.
    program = ('import socket,threading; s=socket.socket(); s.bind(("127.0.0.1",0)); s.listen(); '
               't=threading.Thread(target=lambda:s.accept()[0].sendall(b"forge-tcp-ok")); t.start(); '
               'c=socket.create_connection(s.getsockname()); assert c.recv(32)==b"forge-tcp-ok"; '
               'c.close();t.join();s.close();print("forge-tcp-ok")')
    params = StdioServerParameters(command=server['command'], args=server['args'], cwd=server['cwd'], env={})
    with (stage / 'execution-probe.stderr').open('w') as errors:
        async with stdio_client(params, errlog=errors) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                listed = await session.list_tools()
                if [tool.name for tool in listed.tools] != ['isolated_exec']:
                    raise ValueError('Unexpected local execution tools')
                result = await session.call_tool('isolated_exec', {'argv': ['/usr/bin/python3', '-I', '-c', program],
                                                                  'timeout_seconds': 10.0})
                (stage / 'execution-probe.json').write_text(result.model_dump_json(indent=2) + '\n')
                if result.isError:
                    raise ValueError('Local TCP probe returned a tool error')
    records = [json.loads(path.read_text()) for path in (stage / 'executions').glob('*/result.json')]
    if not records or records[-1]['status'] != 'completed' or records[-1]['exit_code'] != 0:
        raise ValueError('Private TCP execution failed; see executions/ and execution-probe.json')
    return 'verified_via_stdio'


def main():
    import asyncio
    stage, deadline, action = Path(sys.argv[1]), json.loads(sys.argv[2]), float(sys.argv[3])
    prepared = configure(stage, deadline, action)
    prepared['probe'] = asyncio.run(asyncio.wait_for(probe(prepared['server'], stage),
                                                   max(0.01, min(30, deadline - time.monotonic())) if deadline is not None else 30))
    print(json.dumps(prepared))
