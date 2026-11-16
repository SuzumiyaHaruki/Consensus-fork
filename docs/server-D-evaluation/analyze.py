"""Recompute the Server D results from its compact archive; no candidate runs."""
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
METRICS = ('window_ops_s', 'batch_ops_s', 'mean_ms', 'p99_ms', 'max_ms', 'drain_s',
           'cold_read_s', 'history_drain_s', 'cpu_percent_sum', 'allocated_mib_s_sum',
           'peak_rss_sum_mib', 'send_lag_p99_ms', 'actual_send_rate')


def key(d):
    return d['case']['name'], d['cpu_layout'], d['version'], d['repeat']


def total_resource(r, field):
    resources = r.get('resources', [])
    if len(resources) != 7 or any(x.get(field) is None for x in resources):
        return None
    return sum(x[field] for x in resources)


def summarize(values):
    xs = [v for v in values if v is not None]
    return dict(n=len(xs), median=median(xs) if xs else None,
                min=min(xs) if xs else None, max=max(xs) if xs else None)


def analyze(data, prefix=''):
    plan = data['plan.json']
    expected = {key(j): j for j in plan['jobs']}
    assert len(expected) == len(plan['jobs'])
    results = [(name, d) for name, d in sorted(data.items())
               if name.startswith('jobs/') and name.count('/') == 2 and name.endswith('/result.json')]
    assert len({key(d) for _, d in results}) == len(results)
    logical_core = {cpu: (t['package'], t['core'])
                    for t in data['environment.json']['cpu_topology'] for cpu in t['logical_cpus']}
    rows = []; groups = defaultdict(list); not_reached = []; observation_notes = []
    for name, d in results:
        assert key(d) in expected and d['case'] == expected[key(d)]['case']
        job = str(Path(name).parent)
        p = data[job + '/processes.json']
        cores, threads, go_p = {'1c1t-g1': (1, 1, 1), '2c2t-g2': (2, 2, 2), '2c4t-g4': (2, 4, 4)}[d['cpu_layout']]
        assert (p['physical_cores_per_replica'], p['hardware_threads_per_replica'], p['gomaxprocs']) == (cores, threads, go_p)
        assert p['observed_gomaxprocs'] == [go_p] * 7 and p['workers'] == 4
        used = set()
        for assigned, observed in zip(p['replica_cpu_affinity'], p['observed_cpu_affinity']):
            actual = {logical_core[c] for c in observed}
            assert sorted(assigned) == sorted(observed) and len(observed) == threads and len(actual) == cores
            assert not used & actual; used |= actual
        assert not used & {logical_core[c] for c in p['driver_cpu_affinity']}
        r = d['result']; latency = r.get('complete_latency_ms') or {}
        if d['case'].get('ordered_preparation'):
            preparation = data[job + '/pending-preparation.json']
            assert r['preparation'] == preparation
            assert preparation['expected'] == preparation['observed_pending'] == d['case']['history']
            assert not preparation['invalid']
            assert r['before']['6'].get('undecided', r['before']['6'].get('active')) == d['case']['history']
            assert r['before']['6']['executed'] == 70
            assert r['recovery_measured'] is False and 'released_history' not in r
        if r.get('all_completed'):
            assert r['planned_requests'] == r['issued'] == r['completed_requests'] == latency['count']
        elif 'all_completed' in r:
            assert not latency and r.get('batch_throughput_ops_s') is None
        row = dict(case=d['case']['name'], cpu=d['cpu_layout'], version=d['version'], repeat=d['repeat'],
                   status=r['status'], job=job, elapsed_s=d['elapsed_seconds'],
                   planned_requests=r.get('planned_requests'), issued=r.get('issued'),
                   completed_requests=r.get('completed_requests'), not_sent=r.get('not_sent'),
                   completed_during_window=r.get('completed_during_window'),
                   uncompleted_requests=r.get('uncompleted_requests'),
                   all_completed=r.get('all_completed'), counts=r.get('counts'),
                   window_ops_s=r.get('throughput_ops_s') if d['case'].get('scenario') != 'cold' else None,
                   batch_ops_s=r.get('batch_throughput_ops_s') if d['case'].get('scenario') != 'cold' else None,
                   mean_ms=latency.get('mean'), p99_ms=latency.get('p99'), max_ms=latency.get('max'),
                   drain_s=r.get('drain_seconds'),
                   cold_read_s=r['completion_ms']/1000 if r.get('completion_ms') is not None else None,
                   history_drain_s=r.get('release_to_all_executed_seconds'),
                   history_complete=r.get('released_history', {}).get('complete'),
                   cpu_percent_sum=total_resource(r, 'cpu_percent_one_core'),
                   allocated_mib_s_sum=total_resource(r, 'allocated_mib_s'),
                   peak_rss_sum_mib=total_resource(r, 'peak_rss_mib'),
                   send_lag_p99_ms=r.get('send_lag_ms', {}).get('p99'), actual_send_rate=r.get('actual_send_rate'))
        rows.append(row); groups[key(d)[:3]].append(row)
        if r['status'] == 'scenario_not_reached':
            not_reached.append(dict(job=job, cpu=d['cpu_layout'], pending=r['pending'],
                                    required=r['history'], victim_before=r['before']['6']))
        if r.get('event_transport_errors') or r.get('event_gaps') or r.get('observation_complete') is False:
            observation_notes.append(dict(job=job, transport_errors=r.get('event_transport_errors'),
                                          gaps=r.get('event_gaps'), complete=r.get('observation_complete')))
    aggregates = []
    for k, rs in sorted(groups.items()):
        a = dict(zip(('case', 'cpu', 'version'), k))
        a.update(recorded=len(rs), planned=sum(key(j)[:3] == k for j in plan['jobs']),
                 statuses=dict(Counter(r['status'] for r in rs)),
                 complete_batches=sum(r['all_completed'] is True for r in rs),
                 history_complete=sum(r['history_complete'] is True for r in rs))
        a['metrics'] = {m: summarize(r[m] for r in rs) for m in METRICS}
        aggregates.append(a)
    summary = dict(planned=len(expected), recorded=len(rows), missing=[k for k in expected if k not in {key(d) for _, d in results}],
                   statuses=dict(Counter(r['status'] for r in rows)), elapsed_hours=sum(r['elapsed_s'] for r in rows)/3600,
                   not_reached=not_reached, observation_notes=observation_notes, groups=aggregates)
    (ROOT/f'{prefix}analysis.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
    with (ROOT/f'{prefix}job-metrics.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader()
        for row in rows: w.writerow({**row, 'counts': json.dumps(row['counts'])})
    with (ROOT/f'{prefix}matched-metrics.csv').open('w', newline='') as f:
        flattened = []
        for a in aggregates:
            flat = {k:v for k,v in a.items() if k != 'metrics'}; flat['statuses'] = json.dumps(flat['statuses'])
            flat.update({f'{m}_{stat}': value for m, values in a['metrics'].items() for stat, value in values.items()})
            flattened.append(flat)
        w = csv.DictWriter(f, fieldnames=list(flattened[0])); w.writeheader(); w.writerows(flattened)
    return summary, results


def plot_progress(data, results):
    os.environ.setdefault('MPLCONFIGDIR', '/tmp/forge-server-D-matplotlib')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from bisect import bisect_right
    colors = {'baseline': '#4477aa', 'v000': '#ee7733', 'v003': '#228833'}
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for ax, h in zip(axes, (1000, 10000)):
        for version in VERSIONS:
            curves = []
            for name, d in results:
                if d['case']['name'] != f'pending-h{h}-r100' or d['cpu_layout'] != '2c4t-g4' or d['version'] != version: continue
                release = d['result'].get('released_history')
                if not release: continue
                curve = data[str(Path(name).parent / release['progress_file'])]
                curves.append(curve)
            end = max(c[-1]['seconds'] for c in curves)
            grid = sorted({0., end, *range(int(end)+1)})
            def remaining(c, t):
                i = max(0, bisect_right([e['seconds'] for e in c], t)-1)
                return c[i]['remaining']['6']
            values = [[remaining(c, t) for c in curves] for t in grid]
            ax.step(grid, [median(v) for v in values], where='post', color=colors[version], label=f'{version} (n={len(curves)})')
            ax.fill_between(grid, [min(v) for v in values], [max(v) for v in values], step='post', color=colors[version], alpha=.12)
        ax.set_title(f'{h:,} pending commands'); ax.set_xlabel('Seconds after release')
        ax.set_ylabel('Commands still missing execution at replica 6'); ax.grid(alpha=.2); ax.legend()
    fig.suptitle('2 physical cores / 4 threads per replica; median and min-max of recorded runs')
    fig.tight_layout(); fig.savefig(ROOT/'history-drain.png', dpi=160); plt.close(fig)


if __name__ == '__main__':
    with tarfile.open(ROOT/'server-D-results.tar.gz') as archive:
        data = {str(Path(*Path(m.name).parts[1:])): json.load(archive.extractfile(m))
                for m in archive.getmembers() if m.isfile() and m.name.endswith('.json')}
    summary, results = analyze(data)
    plot_progress(data, results)
    print(json.dumps({k:summary[k] for k in ('planned', 'recorded', 'statuses', 'elapsed_hours')}, ensure_ascii=False))
    with tarfile.open(ROOT/'server-D-pending-latency-1116.tar.gz') as archive:
        pending = {str(Path(*Path(m.name).parts[1:])): json.load(archive.extractfile(m))
                   for m in archive.getmembers() if m.isfile() and m.name.endswith('.json')}
    assert pending['origins.json'] == data['origins.json']
    summary, _ = analyze(pending, prefix='pending-')
    print(json.dumps({k:summary[k] for k in ('planned', 'recorded', 'statuses', 'elapsed_hours')}, ensure_ascii=False))
