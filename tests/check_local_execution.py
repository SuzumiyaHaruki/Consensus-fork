"""Opt-in real namespaces/MCP/native configuration check; never authenticates or calls a model.

Run from the project: .venv/bin/python tests/check_local_execution.py
Requires permission to create Linux namespaces. No host execution fallback.
"""
import asyncio
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from generator.config import Settings
from generator.execution import prepare
from generator.client import Client
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

GO_TEST = r'''package checks
import ("bufio"; "io"; "net"; "os"; "os/exec"; "testing")
func TestServer(t *testing.T) {
 if os.Getenv("FORGE_CHILD") != "1" { return }
 l,e:=net.Listen("tcp","127.0.0.1:0"); if e!=nil { t.Fatal(e) }; defer l.Close()
 println(l.Addr().String())
 c,e:=l.Accept(); if e!=nil { t.Fatal(e) }; defer c.Close()
 b:=make([]byte,4); if _,e=io.ReadFull(c,b); e!=nil { t.Fatal(e) }
 if string(b)!="ping" { t.Fatal(string(b)) }; c.Write([]byte("pong"))
}
func TestProcesses(t *testing.T) {
 for i:=0;i<2;i++ {
  cmd:=exec.Command(os.Args[0],"-test.run=^TestServer$"); cmd.Env=append(os.Environ(),"FORGE_CHILD=1")
  pipe,e:=cmd.StderrPipe(); if e!=nil { t.Fatal(e) }; if e=cmd.Start(); e!=nil { t.Fatal(e) }
  scanner:=bufio.NewScanner(pipe); if !scanner.Scan() { t.Fatal("no listener address") }
  c,e:=net.Dial("tcp",scanner.Text()); if e!=nil { t.Fatal(e) }
  c.Write([]byte("ping")); b:=make([]byte,4); _,e=io.ReadFull(c,b); c.Close()
  if e!=nil || string(b)!="pong" { t.Fatal(e,string(b)) }; if e=cmd.Wait(); e!=nil { t.Fatal(e) }
 }
}
'''


async def exercise(prepared, stage, host_port):
    server = prepared['server']
    params = StdioServerParameters(command=server['command'], args=server['args'], cwd=server['cwd'], env={})
    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            async def call(argv, timeout=15.0, **options):
                output = await session.call_tool('isolated_exec', {'argv': argv, 'timeout_seconds': timeout, **options})
                if output.isError:
                    raise AssertionError(output.model_dump())
                return json.loads(output.content[0].text)
            # Native subagents may each connect a separate STDIO tool server.
            # Both servers must serialize mutable-work execution and clock updates.
            async with stdio_client(params) as (other_reader, other_writer):
                async with ClientSession(other_reader, other_writer) as other:
                    await other.initialize()
                    arguments = {'argv': ['/usr/bin/python3', '-I', '-c',
                        'import os,time; fd=os.open("execution-active",os.O_CREAT|os.O_EXCL|os.O_WRONLY); '
                        'time.sleep(.15); os.close(fd); os.unlink("execution-active")'], 'timeout_seconds': 10.0}
                    prior = json.loads((stage/'execution-clock.json').read_text())['elapsed_seconds']
                    outputs = await asyncio.gather(session.call_tool('isolated_exec', arguments),
                                                   other.call_tool('isolated_exec', arguments))
                    records = []
                    for output in outputs:
                        assert not output.isError, output
                        record = json.loads(output.content[0].text)
                        assert record['status'] == 'completed' and record['exit_code'] == 0, record
                        records.append(record)
                    clock = json.loads((stage/'execution-clock.json').read_text())
                    assert 'active' not in clock, clock
                    assert abs(clock['elapsed_seconds']-prior-sum(r['elapsed_seconds'] for r in records)) < .000001, clock
            script = ('from pathlib import Path; import socket; '
                      f'p=Path({str(stage / "inputs/material.txt")!r}); assert p.read_text()=="read-only"; '
                      f'assert not Path({str(stage / "host-only.txt")!r}).exists(); '
                      f'assert not Path({str(stage / "executions")!r}).exists(); '
                      f's=socket.socket(); s.settimeout(1); assert s.connect_ex(("127.0.0.1",{host_port}))!=0; '
                      '\ntry: p.write_text("bad")\nexcept OSError: pass\nelse: raise AssertionError("writable input")\n')
            record = await call(['/usr/bin/python3', '-I', '-c', script])
            assert record['status'] == 'completed' and record['exit_code'] == 0, record
            record = await call(['/usr/bin/python3', '-I', str(stage / 'inputs/tracecheck.py'), 'tests/trace.json'])
            assert record['status'] == 'completed' and record['exit_code'] == 0, record
            overlays = ['tests/schedule_adapter.py', 'tests/schedule.json']
            for mode, filename in [('--plan', 'schedule.json'), ('--replay', 'previous.jsonl')]:
                record = await call(['/usr/bin/python3', '-I', str(stage / 'inputs/schedule.py'), mode,
                                     'tests/' + filename, '--', '/usr/bin/python3', '-I', 'tests/schedule_adapter.py'],
                                    source='candidate', overlays=overlays)
                assert record['status'] == 'completed' and record['exit_code'] == 0, record
                assert record['source_context']['commit'] == 'new', record
                stdout = Path(record['stdout']['path'])
                rows = [json.loads(line) for line in stdout.read_text().splitlines()]
                assert rows[-1]['status'] == 'completed', rows[-1]
                assert rows[-2]['response']['observations']['delivered'] == ['a:1'], rows[-2]
                folder = stage / 'executions' / record['execution_id']
                assert not (folder / 'replay-work').exists()
                for name in overlays:
                    assert (folder / 'inputs' / name).read_bytes() == (stage / 'workspace' / name).read_bytes()
                if mode == '--plan':
                    shutil.copyfile(stdout, stage / 'workspace/tests/previous.jsonl')
                    overlays.append('tests/previous.jsonl')
                else:
                    assert rows[-1]['replay_match'] is True, rows[-1]
            for selected, expected in [('before', 'old'), ('candidate', 'new')]:
                record = await call(['/usr/bin/python3', '-I', 'replay_check.py'], source=selected,
                                    cwd='tests', overlays=['tests/replay_check.py'])
                assert record['status'] == 'completed' and record['exit_code'] == 0, record
                assert record['source_context']['commit'] == expected, record
                assert record['cwd_relative'] == 'tests', record
                assert record['stdout']['preview'].strip() == expected, record
                folder = stage/'executions'/record['execution_id']
                assert not (folder/'replay-work').exists()
                assert (folder/'inputs/tests/replay_check.py').read_bytes() == (stage/'workspace/tests/replay_check.py').read_bytes()
                assert (stage/selected/'value.txt').read_text() == expected
            record = await call(['go', 'test', '-race', '-count=1', './...'], 90.0)
            assert record['status'] == 'completed' and record['exit_code'] == 0, record
            # Selected outputs must survive disposable-source cleanup, even on failure/timeout.
            for ending, status, code in [('raise SystemExit(0)', 'completed', 0),
                                         ('raise SystemExit(7)', 'completed', 7),
                                         ('import time; time.sleep(30)', 'timeout', None)]:
                script = 'from pathlib import Path; Path("results").mkdir(); Path("results/history.json").write_text("[1,2]"); ' + ending
                record = await call(['/usr/bin/python3', '-I', '-c', script], 1.0,
                                    source='candidate', outputs=['results', 'missing'])
                assert record['status'] == status, record
                if code is not None:
                    assert record['exit_code'] == code, record
                folder = stage/'executions'/record['execution_id']
                assert not (folder/'replay-work').exists()
                assert (folder/'artifacts/results/history.json').read_text() == '[1,2]', record
                assert record['artifacts']['excluded'][0]['path'] == 'missing', record
            orphan = 'import subprocess;subprocess.Popen(["/bin/sh","-c","sleep 1; touch leaked-child"])'
            record = await call(['/usr/bin/python3', '-I', '-c', orphan])
            assert record['status'] == 'completed' and record['exit_code'] == 0, record
            await asyncio.sleep(1.5)
            assert not (stage / 'workspace/leaked-child').exists()


def main():
    with tempfile.TemporaryDirectory(prefix='forge-local-check-') as temp:
        stage = Path(temp)
        (stage / 'workspace/tests').mkdir(parents=True)
        (stage / 'inputs').mkdir()
        (stage / 'inputs/material.txt').write_text('read-only')
        project = Path(__file__).resolve().parents[1]
        for name in ('tracecheck.py', 'schedule.py'):
            shutil.copyfile(project / 'runtime' / name, stage / 'inputs' / name)
        shutil.copyfile(project / 'tests/fixtures/schedule_adapter.py', stage / 'workspace/tests/schedule_adapter.py')
        (stage / 'workspace/tests/schedule.json').write_text(json.dumps({
            'setup': {'pending': [{'id': 'a:1', 'actions': ['deliver'], 'dst': 'b'}]},
            'steps': [{'do': 'deliver', 'select': {'dst': 'b'}},
                      {'expect': {'observations': {'delivered': ['a:1']}}}]}))
        (stage / 'host-only.txt').write_text('local fixture, no credentials')
        (stage / 'workspace/go.mod').write_text('module local/check\n\ngo 1.22\n')
        (stage / 'workspace/tests/process_test.go').write_text(GO_TEST)
        (stage / 'workspace/tests/replay_check.py').write_text('from pathlib import Path\np=Path("../value.txt")\nprint(p.read_text())\np.write_text("private change")\n')
        (stage / 'workspace/tests/trace.json').write_text(json.dumps({
            'clock': 'controlled', 'members': ['A', 'B', 'C'], 'fault_limit': 1,
            'delivery_bound_ns': 10, 'end_ns': 11, 'events': [
                {'at_ns': 0, 'kind': 'send', 'id': 'tx1', 'src': 'A', 'dst': 'B'},
                {'at_ns': 0, 'kind': 'send_complete', 'id': 'tx1'},
                {'at_ns': 1, 'kind': 'crash', 'node': 'A'},
                {'at_ns': 10, 'kind': 'deliver', 'id': 'tx1'}]}))
        prepared = prepare(Settings(action_seconds=90), stage, time.monotonic() + 150)
        control = json.loads((stage/'execution-control.json').read_text())
        # Deliberately conflicting host, ancestor and project instructions must not be loaded.
        unwanted = 'FORGE_UNWANTED_LOCAL_INSTRUCTIONS'
        (stage / 'inputs/AGENTS.md').write_text('FORGE_SUPPLIED_INSTRUCTIONS')
        (stage / 'AGENTS.md').write_text(unwanted)
        (stage / 'workspace/AGENTS.md').write_text(unwanted)
        (stage / 'workspace/.codex').mkdir()
        (stage / 'workspace/.codex/config.toml').write_text('developer_instructions="' + unwanted + '"\n')
        host_config = stage / 'host-config'
        (host_config / 'skills/local').mkdir(parents=True)
        (host_config / 'AGENTS.md').write_text(unwanted)
        (host_config / 'config.toml').write_text('developer_instructions="' + unwanted + '"\n')
        (host_config / 'skills/local/SKILL.md').write_text('---\nname: local\ndescription: ' + unwanted + '\n---\n' + unwanted)
        with patch.dict(os.environ, {'CODEX_HOME': str(host_config), 'FORGE_HOST_SENTINEL': unwanted}):
            client = Client(Settings(), stage, time.monotonic() + 60)
            try:
                client.prepare(control['environment'])
                context = (stage / 'client-prompt.json').read_text()
                assert 'FORGE_SUPPLIED_INSTRUCTIONS' in context and unwanted not in context
                assert 'FORGE_HOST_SENTINEL' not in client.environment
                assert client.settings['features.multi_agent'] is True
            finally:
                client.close()
        assert not client.home.exists()
        control['execution_clock_path'] = str(stage/'execution-clock.json')
        (stage/'execution-clock.json').write_text(json.dumps({'elapsed_seconds': 0.0}))
        control['replay_sources'] = {}
        for name, version in [('before', 'old'), ('candidate', 'new')]:
            (stage/name).mkdir()
            (stage/name/'value.txt').write_text(version)
            control['replay_sources'][name] = {'path': str(stage/name), 'commit': version}
        (stage/'execution-control.json').write_text(json.dumps(control))
        private = stage / 'cli-home'
        private.mkdir()
        (private / 'codex').mkdir()
        env = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'HOME': str(private), 'CODEX_HOME': str(private / 'codex')}
        result = subprocess.run([shutil.which('codex'), '--no-daemon', *prepared['options'],
                                 'mcp', 'get', 'forge_local', '--json'], cwd=stage / 'workspace', env=env,
                                capture_output=True, text=True, timeout=20)
        assert result.returncode == 0, result.stderr
        config = json.loads(result.stdout)
        assert config['name'] == 'forge_local', config
        with socket.socket() as host:
            host.bind(('127.0.0.1', 0))
            host.listen()
            asyncio.run(asyncio.wait_for(exercise(prepared, stage, host.getsockname()[1]), 120))
        print(json.dumps({'status': 'passed', 'checks': ['native MCP configuration', 'STDIO private TCP',
                         'private generation configuration and explicit supplied instructions without host skills',
                         'separate MCP servers serialize execution and preserve the shared clock',
                         'two Go subprocesses with race detector', 'read-only materials', 'retained trace helper execution',
                         'host files/logs/network inaccessible', 'before/after source replay and retained overlays',
                         'selected output retention after success, failure and timeout',
                         'event scheduling and strict replay through the shared helper',
                         'action timeout', 'descendant cleanup'],
                         'model_calls': 0}))


if __name__ == '__main__':
    main()
