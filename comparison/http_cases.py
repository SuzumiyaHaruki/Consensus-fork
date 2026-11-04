"""Use unmodified server executables: HTTP boundaries and three-process service."""
from contextlib import contextmanager, ExitStack
import json
import os
from pathlib import Path
import socket
import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener


def address(ip):
    with socket.socket() as sock:
        sock.bind((ip, 0))
        return f'{ip}:{sock.getsockname()[1]}'


def stop(process):
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def original(baseline, seq, kind, key, coordinator='a'):
    if baseline:
        return {'Configuration': 'comparison', 'Coordinator': coordinator,
                'ID': {'client_id': '0'*31+'1', 'request_seq': seq},
                'Operation': {'Kind': kind.title(), 'Key': key, 'Value': 'value' if kind == 'put' else ''}}
    return {'configuration': 'comparison', 'coordinator': coordinator,
            'id': {'client': '0'*31+'1', 'seq': seq},
            'operation': {'type': kind, 'key': key, 'value': 'value' if kind == 'put' else ''}}


@contextmanager
def cluster(workspace, folder, baseline, env, count, trace):
    binary = folder/'server'
    subprocess.run(['go', 'build', '-o', str(binary), './cmd/server'], cwd=workspace, env=env, check=True, timeout=60)
    members = []
    clients = {}
    for i in range(count):
        name, ip = chr(ord('a')+i), f'127.77.1.{i+2}'
        member = {'id': name, 'address': address(ip)}
        clients[name] = address(ip) if baseline else member['address']
        if baseline:
            member['client_address'] = clients[name]
        members.append(member)
    config = {'configuration': 'comparison', 'delta': '250ms', 'members': members}
    if baseline:
        config['relay'] = address('127.77.1.250')
    (folder/'config.json').write_text(json.dumps(config))
    keys = folder/'keys.json'
    if not baseline:
        keys.write_text(json.dumps({m['id']: os.urandom(32).hex() for m in members}))
        keys.chmod(0o600)
    opener = build_opener(ProxyHandler({}))
    urls = {name: 'http://'+addr+('/v1/submit' if baseline else '/submit') for name, addr in clients.items()}

    def submit(body, coordinator='a'):
        request = Request(urls[coordinator], data=body.encode(), headers={'Content-Type': 'application/json'})
        try:
            response = opener.open(request, timeout=5)
        except HTTPError as exc:
            response = exc
        with response:
            return {'http_status': response.status, 'body': json.loads(response.read())}

    processes = []
    with ExitStack() as stack:
        def start(command, name):
            log = stack.enter_context((folder/(name+'.log')).open('w'))
            process = subprocess.Popen(command, cwd=workspace, stdout=log, stderr=subprocess.STDOUT)
            stack.callback(stop, process)
            processes.append(process)
            return process
        if baseline and count > 1:
            relay = folder/'relay'
            subprocess.run(['go', 'build', '-o', str(relay), './cmd/relay'], cwd=workspace, env=env, check=True, timeout=60)
            start([str(relay), '-config', str(folder/'config.json')], 'relay')
        for member in members:
            name = member['id']
            command = [str(binary), '-config', str(folder/'config.json'), '-id', name]
            if trace:
                command += ['-trace' if baseline else '-events', str(folder/(name+'-events.jsonl'))]
            if not baseline:
                command += ['-keys', str(keys)]
            process = start(command, name)
            deadline = time.monotonic()+5
            while True:
                try:
                    opener.open(urls[name], timeout=.2).close()
                    break
                except HTTPError:
                    break
                except URLError:
                    if process.poll() is not None or time.monotonic() > deadline:
                        raise RuntimeError('server startup failed; see '+name+'.log')
                    time.sleep(.02)
        yield submit, processes


def run(workspace, folder, baseline, env, network=False):
    with cluster(workspace, folder, baseline, env, 3 if network else 1, not network) as (submit, processes):
        if network:
            return history(folder, baseline, submit, processes)
        records = []
        field = 'request_seq' if baseline else 'seq'
        unicode_field = field.replace('s', '\u017f')
        for index, (name, alias) in enumerate([('ordinary', None), ('ascii_duplicate', field), ('unicode_alias', unicode_field)]):
            seq = index*10+1
            body = json.dumps(original(baseline, seq, 'put', name))
            if alias:
                body = body.replace(f'"{field}": {seq}', f'"{field}": {seq}, "{alias}": {seq+1}')
            result = submit(body)
            read = submit(json.dumps(original(baseline, seq+2, 'get', name)))
            records.append({'case': name, 'request': body, 'response': result, 'subsequent_read': read})
        (folder/'http-results.json').write_text(json.dumps(records, ensure_ascii=False, indent=2)+'\n')
        return records


def history(folder, baseline, submit, processes):
    records = []
    # One client, one outstanding fixed-size Put, 5ms think time; not peak throughput.
    for first in range(1, 1001, 250):
        latencies = []
        start = time.monotonic()
        for seq in range(first, first+250):
            body = json.dumps(original(baseline, seq, 'put', 'history'))
            at = time.monotonic_ns()
            response = submit(body)
            latencies.append(time.monotonic_ns()-at)
            out = response['body']
            result = out.get('outcome', out.get('result', {}))
            if out.get('status') not in ('outcome', 'executed') or result.get('Value', result.get('value')) != 'value':
                raise RuntimeError(f'command {seq}: {response}')
            time.sleep(.005)
        elapsed = time.monotonic()-start
        rss = []
        for process in processes:
            lines = Path(f'/proc/{process.pid}/status').read_text().splitlines()
            rss.append(next(int(line.split()[1]) for line in lines if line.startswith('VmRSS:')))
        latencies.sort()
        record = {'first': first, 'last': first+249, 'mean_ns': sum(latencies)//250,
                  'p50_ns': latencies[125], 'p95_ns': latencies[237], 'wall_seconds': elapsed,
                  'process_rss_kib': rss, 'sum_rss_kib': sum(rss)}
        records.append(record)
        (folder/'network-history.json').write_text(json.dumps(records, indent=2)+'\n')
        print(json.dumps({'network_history': str(folder), **record}), flush=True)
    for i, name in enumerate(('a', 'b', 'c')):
        out = submit(json.dumps(original(baseline, 1001+i, 'get', 'history', name)), name)['body']
        result = out.get('outcome', out.get('result', {}))
        if result.get('Value', result.get('value')) != 'value':
            raise RuntimeError(f'final read at {name}: {out}')
    return records
