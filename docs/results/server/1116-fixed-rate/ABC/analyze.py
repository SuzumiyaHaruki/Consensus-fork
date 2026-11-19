"""Recompute fixed-rate A/B/C measurements from the supplied archives."""
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
import csv
import json
import os
import tarfile

ROOT = Path(__file__).resolve().parent
VERSIONS = ('baseline', 'v000', 'v003')
CPUS = ('1c1t-g1', '2c2t-g2', '2c4t-g4')
METRICS = ('window_ops_s', 'batch_ops_s', 'mean_ms', 'p99_ms', 'issued_mean_ms', 'issued_p99_ms', 'tail_s', 'actual_rate',
           'completion_pct', 'send_lag_p99_ms', 'cpu_sum_pct', 'rss_sum_mib', 'allocated_mib_s')


def key(d):
    return d['case']['name'], d['cpu_layout'], d['version'], d['repeat']


def analyze(shard):
    with tarfile.open(ROOT / f'server-{shard}-results.tar.gz') as archive:
        data = {str(Path(*Path(m.name).parts[1:])): json.load(archive.extractfile(m))
                for m in archive.getmembers() if m.isfile() and m.name.endswith('.json')}
    plan = data['plan.json']
    assert plan['method'] == 'fixed-rate-1115' and plan['shard'] == shard
    expected = {key(j): j for j in plan['jobs']}
    assert len(expected) == len(plan['jobs'])
    topology = {cpu: (t['package'], t['core']) for t in data['environment.json']['cpu_topology']
                for cpu in t['logical_cpus']}
    rows, groups = [], defaultdict(list)
    for path, d in sorted(data.items()):
        if not (path.startswith('jobs/') and path.count('/') == 2 and path.endswith('/result.json')):
            continue
        assert key(d) in expected and d['case'] == expected[key(d)]['case']
        job = str(Path(path).parent)
        p = data[job + '/processes.json']
        cores, threads, go_p = {'1c1t-g1': (1, 1, 1), '2c2t-g2': (2, 2, 2), '2c4t-g4': (2, 4, 4)}[d['cpu_layout']]
        assert (p['physical_cores_per_replica'], p['hardware_threads_per_replica'], p['gomaxprocs']) == (cores, threads, go_p)
        assert p['observed_gomaxprocs'] == [go_p] * 7 and p['workers'] == 4
        owned = set()
        for assigned, actual in zip(p['replica_cpu_affinity'], p['observed_cpu_affinity']):
            physical = {topology[c] for c in actual}
            assert sorted(assigned) == sorted(actual) and len(actual) == threads and len(physical) == cores
            assert not physical & owned
            owned |= physical
        assert not owned & {topology[c] for c in p['driver_cpu_affinity']}
        r = d['result']; lat = r.get('complete_latency_ms') or {}; counts = r['counts']
        assert sum(counts.values()) == r['planned_requests']
        assert r['issued'] + r['not_sent'] == r['planned_requests']
        assert r['completed_requests'] == sum(counts.get(s, 0) for s in ('OK', 'APPLIED', 'ALREADY_EXECUTED'))
        if r['all_completed']:
            assert r['planned_requests'] == r['issued'] == r['completed_requests'] == lat['count']
        else:
            assert not lat and r.get('batch_throughput_ops_s') is None
        issued_complete = r['issued'] > 0 and r['completed_requests'] == r['issued']
        issued_lat = (r.get('successful_latency_ms') or {}) if issued_complete else {}
        if issued_complete:
            assert issued_lat['count'] == r['issued']
        resources = r.get('resources', [])
        def resource_sum(field):
            return sum(x[field] for x in resources) if resources and all(x.get(field) is not None for x in resources) else None
        row = dict(job=job, case=d['case']['name'], cpu=d['cpu_layout'], version=d['version'], repeat=d['repeat'],
                   group=d['case']['group'], topology=d['case'].get('topology', 'balanced'), rate=d['case']['rate'],
                   seconds=r['duration_seconds'], elapsed_s=d['elapsed_seconds'], status=r['status'],
                   all_completed=r['all_completed'], planned=r['planned_requests'], issued=r['issued'],
                   completed=r['completed_requests'], rejected=counts.get('REJECTED', 0)+counts.get('OVERLOADED', 0),
                   observation_ended=counts.get('OBSERVATION_ENDED', 0), not_sent=r['not_sent'],
                   late_sent=r['issued_after_window'], counts=counts, window_ops_s=r['throughput_ops_s'],
                   batch_ops_s=r.get('batch_throughput_ops_s'), mean_ms=lat.get('mean'), p99_ms=lat.get('p99'),
                   issued_all_completed=issued_complete,
                   issued_mean_ms=issued_lat.get('mean'), issued_p99_ms=issued_lat.get('p99'),
                   tail_s=r.get('drain_seconds'), actual_rate=r['actual_send_rate'],
                   completion_pct=100*r['completed_requests']/r['planned_requests'],
                   send_lag_p99_ms=r['send_lag_ms'].get('p99'),
                   observed_mean_undecided=r.get('observed_mean_undecided'),
                   missing_decisions=r.get('missing_decisions_after_drain'),
                   observation_complete=r.get('observation_complete'), event_errors=r.get('event_transport_errors'),
                   event_gaps=r.get('event_gaps'), cpu_sum_pct=resource_sum('cpu_percent_one_core'),
                   rss_sum_mib=resource_sum('peak_rss_mib'), allocated_mib_s=resource_sum('allocated_mib_s'))
        rows.append(row); groups[key(d)[:3]].append(row)
    assert len({(r['case'], r['cpu'], r['version'], r['repeat']) for r in rows}) == len(rows)
    aggregates = []
    for k, rs in sorted(groups.items()):
        a = dict(zip(('case', 'cpu', 'version'), k))
        a.update(recorded=len(rs), complete=sum(r['all_completed'] for r in rs),
                 statuses=dict(Counter(r['status'] for r in rs)))
        a.update({f'{field}_total': sum(r[field] for r in rs) for field in
                  ('planned', 'issued', 'completed', 'rejected', 'observation_ended', 'not_sent', 'late_sent')})
        for m in METRICS:
            xs = [r[m] for r in rs if r[m] is not None]
            for name, value in [('n', len(xs)), ('median', median(xs) if xs else None),
                                ('min', min(xs) if xs else None), ('max', max(xs) if xs else None)]:
                a[f'{m}_{name}'] = value
        aggregates.append(a)
    for name, records in [('jobs', rows), ('groups', aggregates)]:
        with (ROOT / f'{shard}-{name}.csv').open('w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(records[0])); w.writeheader()
            for r in records:
                w.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, dict) else v for k, v in r.items()})
    summary = dict(planned=len(expected), recorded=len(rows), elapsed_hours=sum(r['elapsed_s'] for r in rows)/3600,
                   statuses=dict(Counter(r['status'] for r in rows)), groups=aggregates,
                   observation_issues=[r['job'] for r in rows if not r['observation_complete'] or r['event_errors'] or r['event_gaps']],
                   missing=[k for k in expected if k not in {(r['case'], r['cpu'], r['version'], r['repeat']) for r in rows}],
                   options=plan['options'], origins=data['origins.json'])
    by_version = {v: {(r['case'], r['cpu'], r['repeat']): r for r in rows
                      if r['version'] == v and r['group'] != 'calibration'} for v in VERSIONS}
    matched = set.intersection(*(set(rs) for rs in by_version.values()))
    summary['matched'] = {}
    for v, rs in by_version.items():
        selected = [rs[k] for k in sorted(matched)]
        summary['matched'][v] = dict(tasks=len(selected), complete=sum(r['all_completed'] for r in selected),
            counts=dict(sum((Counter(r['counts']) for r in selected), Counter())),
            planned=sum(r['planned'] for r in selected),
            only_driver_incomplete=sum(r['not_sent'] > 0 and r['issued'] == r['completed'] for r in selected))
    (ROOT / f'{shard}-analysis.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
    return rows, summary


def figures():
    os.environ.setdefault('MPLCONFIGDIR', '/tmp/forge-server-ABC-matplotlib')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    colors = dict(zip(VERSIONS, ('#4477aa', '#ee7733', '#228833')))
    a = json.loads((ROOT / 'A-analysis.json').read_text())
    fig, axes = plt.subplots(2, 3, figsize=(12, 6.5))
    for row, topology_name in enumerate(('single', 'balanced')):
        for col, cpu in enumerate(CPUS):
            ax = axes[row, col]
            upper = 1000 if topology_name == 'single' else (1800 if cpu == '2c4t-g4' else 1200)
            for version in VERSIONS:
                gs = sorted((g for g in a['groups'] if g['version'] == version and g['cpu'] == cpu
                             and g['case'].startswith(f'ordinary-{topology_name}-')
                             and 300 <= int(g['case'].rsplit('r', 1)[1]) <= upper), key=lambda g: int(g['case'].rsplit('r', 1)[1]))
                xs = [int(g['case'].rsplit('r', 1)[1]) for g in gs]
                ax.plot(xs, [g['window_ops_s_median'] for g in gs], 'o-', color=colors[version], label=version)
                ax.fill_between(xs, [g['window_ops_s_min'] for g in gs], [g['window_ops_s_max'] for g in gs], color=colors[version], alpha=.12)
            ax.plot([0, max(xs)], [0, max(xs)], '--', color='gray', lw=1)
            ax.set_title(f'{topology_name}; {cpu}'); ax.set_xlabel('Offered requests/s')
            ax.set_ylabel('Execution replies/s during 30 s'); ax.grid(alpha=.2)
            if row == 0 and col == 0: ax.legend()
    fig.tight_layout(); fig.savefig(ROOT / 'A-throughput.png', dpi=160); plt.close(fig)
    for shard, case, total in [('B', 'hot-balanced-r500', 15000), ('C', 'delay-1ms-r400', 12000)]:
        with tarfile.open(ROOT / f'server-{shard}-results.tar.gz') as archive:
            results = [json.load(archive.extractfile(m)) for m in archive.getmembers()
                       if m.isfile() and m.name.endswith('/result.json')]
        fig, axes = plt.subplots(1, 3, figsize=(12, 3.7))
        grid = list(range(331))
        for ax, cpu in zip(axes, CPUS):
            for version in VERSIONS:
                rs = [d['result'] for d in results if d['case']['name'] == case and d['cpu_layout'] == cpu and d['version'] == version]
                assert len(rs) == 5
                curves = []
                for r in rs:
                    counts = {b['second']+1: b['execution_replies'] for b in r['timeline']}
                    cumulative = 0; curve = []
                    for second in grid:
                        cumulative += counts.get(second, 0); curve.append(cumulative)
                    curves.append(curve)
                values = list(zip(*curves))
                ax.step(grid, [median(v) for v in values], where='post', color=colors[version], label=version)
                ax.fill_between(grid, [min(v) for v in values], [max(v) for v in values], step='post', color=colors[version], alpha=.12)
            ax.axvline(30, color='gray', linestyle='--', lw=1); ax.axhline(total, color='gray', linestyle=':', lw=1)
            ax.set_title(cpu); ax.set_xlabel('Seconds since load started'); ax.set_ylabel('Cumulative execution replies')
            ax.set_ylim(0, total*1.05); ax.grid(alpha=.2)
        axes[0].legend(); fig.tight_layout(); fig.savefig(ROOT / f'{shard}-completion.png', dpi=160); plt.close(fig)


if __name__ == '__main__':
    for shard in 'ABC':
        rows, summary = analyze(shard)
        print(shard, json.dumps({k: summary[k] for k in ('planned', 'recorded', 'statuses')}, ensure_ascii=False))
    figures()
