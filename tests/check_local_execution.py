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

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from generator.config import Settings
from generator.execution import prepare
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
            for selected, expected in [('before', 'old'), ('candidate', 'new')]:
                record = await call(['/usr/bin/python3', '-I', 'tests/replay_check.py'], source=selected,
                                    overlays=['tests/replay_check.py'])
                assert record['status'] == 'completed' and record['exit_code'] == 0, record
                assert record['source_context']['commit'] == expected, record
                assert record['stdout']['preview'].strip() == expected, record
                folder = stage/'executions'/record['execution_id']
                assert not (folder/'replay-work').exists()
                assert (folder/'inputs/tests/replay_check.py').read_bytes() == (stage/'workspace/tests/replay_check.py').read_bytes()
                assert (stage/selected/'value.txt').read_text() == expected
            record = await call(['go', 'test', '-race', '-count=1', './...'], 90.0)
            assert record['status'] == 'completed' and record['exit_code'] == 0, record
            record = await call(['/usr/bin/python3', '-I', '-c', 'import time;time.sleep(30)'], .1)
            assert record['status'] == 'timeout', record
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
        shutil.copyfile(Path(__file__).resolve().parents[1] / 'runtime/tracecheck.py', stage / 'inputs/tracecheck.py')
        (stage / 'host-only.txt').write_text('local fixture, no credentials')
        (stage / 'workspace/go.mod').write_text('module local/check\n\ngo 1.22\n')
        (stage / 'workspace/tests/process_test.go').write_text(GO_TEST)
        (stage / 'workspace/tests/replay_check.py').write_text('from pathlib import Path\np=Path("value.txt")\nprint(p.read_text())\np.write_text("private change")\n')
        (stage / 'workspace/tests/trace.json').write_text(json.dumps({
            'clock': 'controlled', 'members': ['A', 'B', 'C'], 'fault_limit': 1,
            'delivery_bound_ns': 10, 'end_ns': 11, 'events': [
                {'at_ns': 0, 'kind': 'send', 'id': 'tx1', 'src': 'A', 'dst': 'B'},
                {'at_ns': 0, 'kind': 'send_complete', 'id': 'tx1'},
                {'at_ns': 1, 'kind': 'crash', 'node': 'A'},
                {'at_ns': 10, 'kind': 'deliver', 'id': 'tx1'}]}))
        prepared = prepare(Settings(action_seconds=90), stage, time.monotonic() + 150)
        control = json.loads((stage/'execution-control.json').read_text())
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
                         'separate MCP servers serialize execution and preserve the shared clock',
                         'two Go subprocesses with race detector', 'read-only materials', 'retained trace helper execution',
                         'host files/logs/network inaccessible', 'before/after source replay and retained overlays',
                         'action timeout', 'descendant cleanup'],
                         'model_calls': 0}))


if __name__ == '__main__':
    main()
