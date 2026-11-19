#!/usr/bin/env python3
"""Reuse the server evaluator for a local, unbatched admission-window sweep."""
import argparse
import csv
import json
from pathlib import Path
import platform
import random
import shutil
import statistics
import subprocess
import sys


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def lifecycle(directory, result, entry, k):
    start, end = result['start_ns'], result['end_ns']
    admissions, decisions, executions, transitions = {}, {}, {}, []
    serial, invalid_lines = 0, 0
    for line in (directory / f'node-{entry}/events.jsonl').open():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            invalid_lines += 1
            continue
        serial = max(serial,event.get('serial',0))
        if event['id']['replica'] != entry:
            continue
        x, at, kind = event['id']['index'], event['at_ns'], event['kind']
        if kind == 'admitted':
            admissions.setdefault(x, at)
        elif kind == 'decided':
            decisions.setdefault(x, at)
        elif kind == 'executed':
            executions.setdefault(x, at)
    address = result.get('config',{}).get('addresses',[None]*(entry+1))[entry]
    required = result.get('observation_cursors',{}).get(address,0)
    evidence = dict(slot_observation_complete=serial>=required and not invalid_lines,
                    saved_event_serial=serial, required_event_serial=required,
                    invalid_event_lines=invalid_lines)
    if not evidence['slot_observation_complete']:
        return evidence
    for x, at in admissions.items():
        if at <= end:
            transitions.append((at, 1))
            if x in executions and executions[x] <= end:
                transitions.append((executions[x], -1))
    active = peak = area = full = above = 0
    previous = start
    for at, change in sorted(transitions):
        if at >= start:
            area += active * (at - previous)
            full += (at - previous) if active >= k else 0
            above += (at - previous) if active > k else 0
            previous = at
        active += change
        if at >= start:
            peak = max(peak, active)
    area += active * (end - previous)
    full += (end - previous) if active >= k else 0
    above += (end - previous) if active > k else 0
    selected = {x: at for x, at in admissions.items() if start <= at <= end}
    out = dict(**evidence, mean_slots=area / (end-start), peak_slots=peak,
               full_slots_fraction=full / (end-start), slots_at_send_end=active,
               event_count_above_k_fraction=above / (end-start),
               admitted_in_send_window=len(selected),
               locally_unexecuted_at_observation_end=sum(x not in executions for x in selected))
    pairs = {'admit_decide': (selected, decisions), 'admit_execute': (selected, executions),
             'decide_execute': ({x: decisions[x] for x in selected if x in decisions}, executions)}
    for name, (begins, ends) in pairs.items():
        values = [(ends[x]-at)/1e6 for x, at in begins.items() if x in ends]
        out[name+'_samples'] = len(values)
        out[name+'_mean_ms'] = statistics.mean(values) if values else None
    return out


def analyze(output):
    rows = []
    for file in sorted((output / 'jobs').glob('*/result.json')):
        job = json.loads(file.read_text())
        result, case = job['result'], job['case']
        row = dict(job=file.parent.name, version=job['version'], scenario=case['scenario_label'],
                   k=case['k'], repeat=job['repeat'], status=result['status'])
        for key in ('actual_send_rate','throughput_ops_s','issued','not_sent','completed_requests',
                    'all_completed','batch_throughput_ops_s','drain_seconds','event_gaps',
                    'observation_complete','driver_cpu_percent_one_core','resources'):
            row[key] = result.get(key)
        if 'start_ns' in result:
            row.update(lifecycle(file.parent, result, case['entries'][0], case['k']))
            row['counts'] = result['counts']
            row['complete_latency_ms'] = result['complete_latency_ms']
            row['send_lag_ms'] = result['send_lag_ms']
            row['coordinator_stats'] = result.get('post_stats',{}).get(str(case['entries'][0]),{})
            row['coordinator_resources'] = next((r for r in result.get('resources',[])
                                                 if r['replica']==case['entries'][0]),{})
            row['slot_observation_scope'] = ('Execution event occurs after slot release and unlock; '
                'event-derived occupancy can temporarily exceed actual slots.' if job['version']=='baseline'
                else 'Admission and execution events are emitted while the slot registry remains locked.')
        rows.append(row)
    save(output / 'analysis.json', rows)
    groups = []
    for scenario in sorted({r['scenario'] for r in rows}):
        for version in ('baseline','v000','v003'):
            for k in (64,128,256,512):
                selected = [r for r in rows if (r['scenario'],r['version'],r['k']) == (scenario,version,k)]
                if not selected:
                    continue
                group = dict(scenario=scenario, version=version, k=k, runs=len(selected),
                             complete_runs=sum(bool(r.get('all_completed')) for r in selected))
                for field in ('throughput_ops_s','actual_send_rate','mean_slots','peak_slots','full_slots_fraction',
                              'admit_decide_mean_ms','admit_execute_mean_ms','decide_execute_mean_ms'):
                    values = [r[field] for r in selected if r.get(field) is not None]
                    group[field] = statistics.median(values) if values else None
                    group[field+'_range'] = [min(values),max(values)] if values else None
                group['completion_fraction'] = sum(r.get('completed_requests') or 0 for r in selected) / max(1,sum(r.get('issued') or 0 for r in selected))
                groups.append(group)
    save(output / 'groups.json', groups)
    if groups:
        with (output/'groups.csv').open('w') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(groups[0]))
            writer.writeheader()
            writer.writerows(groups)
    print(json.dumps(groups, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('run','analyze'))
    parser.add_argument('--suite', type=Path, default=Path('/home/nitro/Desktop/consensus-server-evaluation-1111'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--versions', default='baseline,v000,v003')
    parser.add_argument('--ks', default='64,128,256,512')
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--seconds', type=float, default=15)
    parser.add_argument('--drain-seconds', type=float, default=30)
    parser.add_argument('--rate', type=float, default=800)
    args = parser.parse_args()
    output, suite = args.output.resolve(), args.suite.resolve()
    if args.action == 'analyze':
        analyze(output)
        return
    output.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(suite/'scripts'))
    from hardware import topology, allocation
    options = dict(seconds_override=args.seconds, idle_seconds=10, cpu_per_replica=1,
                   threads_per_core=1, replica_gomaxprocs=1, native_gomaxprocs=8,
                   driver_cpus=1, pin=True, drain_seconds=args.drain_seconds,
                   history_drain_seconds=30, preparation_seconds=30, observation_seconds=2)
    allocation(7, options)
    rng, jobs = random.Random(20261116), []
    for repeat in range(1,args.repeats+1):
        block = []
        for label, crashes in [('ordinary',0),('two-crashed',2)]:
            for k in map(int,args.ks.split(',')):
                for version in args.versions.split(','):
                    case = dict(name=f'{label}-k{k}-r{args.rate:g}', shard='K', group='performance',
                                scenario_label=label, k=k, crashes=crashes, entries=[2],
                                workers=4, rate=args.rate, topology='single', payload=64)
                    block.append(dict(version=version, case=case, repeat=repeat,
                                      cpu=dict(cpu_per_replica=1,threads_per_core=1), cpu_layout='1vcpu-g1'))
        rng.shuffle(block)
        jobs.extend(block)
    save(output/'plan.json',dict(method='fixed-rate-1115',shard='K',versions=args.versions.split(','),options=options,jobs=jobs))
    shutil.copy2(suite/'origins.json',output/'origins.json')
    save(output/'environment.json',dict(platform=platform.platform(),cpu_topology=topology(),
         cpuinfo=Path('/proc/cpuinfo').read_text(),meminfo=Path('/proc/meminfo').read_text(),
         go=subprocess.check_output(['go','version'],text=True).strip(),options=options,
         scope='VM-local sensitivity test; one pinned vCPU and Go P=1 per replica, one vCPU for driver. No batching or candidate changes.'))
    subprocess.run([sys.executable,str(suite/'scripts/run.py'),'run','--resume',str(output)],check=True)
    analyze(output)


if __name__ == '__main__':
    main()
