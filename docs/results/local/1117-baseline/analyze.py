#!/usr/bin/env python3
"""Summarize preserved observations; do not rewrite original workload outcomes."""
import csv
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=Path('/home/nitro/Desktop/baseline-throughput-1117')
validation_path=ROOT/'validation.json'
validation=json.loads(validation_path.read_text()) if validation_path.exists() else {}
rows=[]
for p in sorted((ROOT/'jobs').glob('*/result.json')):
    r=json.loads(p.read_text());v=r['load'];settings=json.loads((p.parent/'settings.json').read_text());a=settings['args']
    before=json.loads((p.parent/'before.json').read_text());after=json.loads((p.parent/'after.json').read_text())
    ss=[json.loads(x) for x in (p.parent/'samples.jsonl').read_text().splitlines()]
    ss=[s for s in ss if v['start_ns']<=s['time_ns']<=v['end_ns'] and 'stats' in s]
    dt=(ss[-1]['time_ns']-ss[0]['time_ns'])/1e9
    cores=sum(y['cpu_s']-x['cpu_s'] for x,y in zip(ss[0]['cpu'],ss[-1]['cpu']))/dt
    delta=lambda field:sum(x[field] for x in after['stats'])-sum(x[field] for x in before['stats'])
    node_delta=lambda field:sum(x['node'][field] for x in after['stats'])-sum(x['node'][field] for x in before['stats'])
    all_issued=v['issued']>0 and v['completed']==v['issued']
    counts=v['counts'];latency=v['completed_subset_latency_ms'] if all_issued else None
    row=dict(name=r['name'],n=r['n'],topology=r['topology'],rate=r['rate'],seconds=r['seconds'],repeat=r['repeat'],tick_ms=a['tick_ms'],w_ms=a['w_ms'],profile=a.get('profile',False),throughput_ops_s=v['throughput_ops_s'],issued=v['issued'],completed=v['completed'],reply_fraction=v['completed']/v['issued'],not_sent=v['planned']-v['issued'],rejected=counts.get('REJECTED',0),transport_errors=counts.get('TRANSPORT_ERROR',0),driver_limited=counts.get('DRIVER_LIMIT',0),full_mean_ms=latency['mean'] if latency else None,full_p99_ms=latency['p99'] if latency else None,cpu_cores=cores,driver_cpu_cores=v.get('driver_cpu_cores'),wire_per_reply=delta('wire_messages')/v['completed'],fast=node_delta('fast'),slow=node_delta('slow'),recoveries=node_delta('recoveries'),fetches=node_delta('fetches'),drops=node_delta('dropped'),window_misses=node_delta('window_misses'),heap_mb=sum(x['heap_bytes'] for x in after['stats'])/1e6,unexecuted_end=sum(x['node']['unexecuted'] for x in after['stats']),send_lag_p99_ms=v['send_lag_ms']['p99'],five_second_tps={k:n/5 for k,n in v['five_second_completions'].items()},errors=v['errors'])
    row['sent_after_window']=validation.get(r['name'],{}).get('late_sent')
    rows.append(row)
(ROOT/'analysis.json').write_text(json.dumps(rows,indent=2)+'\n')
(HERE/'analysis.json').write_text(json.dumps(rows,indent=2)+'\n')
keys=[k for k in rows[0] if k not in ('five_second_tps','errors')]
with (HERE/'analysis.csv').open('w') as f:
    w=csv.DictWriter(f,fieldnames=keys,extrasaction='ignore');w.writeheader();w.writerows(rows)
for r in rows:
    print(r['name'],f"{r['throughput_ops_s']:.1f}/s",f"{r['reply_fraction']:.3%}",'reject',r['rejected'],'transport',r['transport_errors'],'CPU',round(r['cpu_cores'],2),'lag',round(r['send_lag_p99_ms'],2))
