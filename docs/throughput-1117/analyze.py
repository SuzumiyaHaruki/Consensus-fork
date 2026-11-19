#!/usr/bin/env python3
"""Summarize measured windows, keeping incomplete replies separate from latency."""
import csv
import json
import os
from pathlib import Path
import subprocess
import sys

root=Path(sys.argv[1] if len(sys.argv)>1 else '/home/nitro/Desktop/consensus-throughput-1117')
rows=[]
for file in sorted((root/'jobs').glob('*/result.json')):
    v=json.loads(file.read_text())
    if file.parent.name.startswith(('scan7-', 'quiet7-')):
        continue  # Exclude adapter pilots and the mislabeled run without --quiet.
    if v['quiet']:
        assert v['config']['skip_events'] is True
        before=json.loads((file.parent/'before.json').read_text())['replicas']
        assert all(a['serial']==b['serial'] for a,b in zip(before,v['after']['replicas'])), file.parent
    res=v['resources']
    latency=v.get('complete_latency_ms') or {}
    conditional=v.get('successful_latency_ms') or {}
    row=dict(job=file.parent.name,label=v['job']['label'],n=v['n'],input_rate=v['job']['rate'],repeat=v['job']['repeat'],
             quiet=v['quiet'],profile=v['profile'],topology=v['topology'],seconds=v['seconds'],throughput=v['throughput_ops_s'],
             actual_send_rate=v['actual_send_rate'],issued=v['issued'],completed=v['completed_requests'],not_sent=v['not_sent'],
             complete=v['all_completed'],counts=v['counts'],complete_latency_ms=latency,conditional_latency_ms=conditional,
             sum_cpu_cores=sum(r.get('cpu_percent_one_core',0) for r in res)/100,
             allocation_mib_s=sum(r.get('allocated_mib_s',0) for r in res),
             protocol_rpc_s=sum(r.get('protocol_requests_s',0) for r in res),
             protocol_mib_s=sum(r.get('protocol_mib_s',0) for r in res),
             peak_sum_rss_mib=sum(r.get('peak_rss_mib',0) for r in res),driver_cpu=v.get('driver_cpu_percent_one_core'),
             windows=v.get('candidate_stats'),timeline=v.get('timeline'),resources=res,
             actual_mean_undecided=v.get('observed_mean_undecided'),actual_peak_undecided=v.get('observed_peak_undecided'))
    if row['throughput']:
        row['protocol_rpc_per_completed']=row['protocol_rpc_s']/row['throughput']
        row['allocation_kib_per_completed']=row['allocation_mib_s']*1024/row['throughput']
        row['cpu_ms_per_completed']=row['sum_cpu_cores']*1000/row['throughput']
    rows.append(row)
(root/'analysis.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
fields=['job','label','n','input_rate','repeat','quiet','profile','throughput','actual_send_rate','issued','completed','not_sent','complete','sum_cpu_cores','allocation_mib_s','protocol_rpc_s','protocol_mib_s','driver_cpu']
with (root/'analysis.csv').open('w') as f:
    out=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');out.writeheader();out.writerows(rows)
for r in rows:
    print(r['job'],f"{r['throughput']:.1f}",f"{r['completed']}/{r['issued']}",f"CPU={r['sum_cpu_cores']:.2f}",f"alloc={r['allocation_mib_s']:.1f}MiB/s")
(root/'pprof-cache').mkdir(exist_ok=True)
profile_env=dict(os.environ, PPROF_TMPDIR=str(root/'pprof-cache'))
pprof=[os.environ['PPROF_TOOL']] if os.environ.get('PPROF_TOOL') else ['go','tool','pprof']
for job in (root/'jobs').glob('profile*'):
    if not (job/'result.json').exists():continue
    v=json.loads((job/'result.json').read_text());binary=root/'build'/v['job']['label']/'bench'
    profiles=sorted(job.glob('node-*/cpu.pprof'))
    if not profiles:continue
    for tag,extra in [('flat',[]),('cumulative',['-cum'])]:
        target=job/f'cpu-{tag}.txt'
        if not target.exists() or 'no such tool' in target.read_text():
            with target.open('w') as out:
                subprocess.run([*pprof,'-top','-nodecount=60',*extra,str(binary),*map(str,profiles)],stdout=out,stderr=subprocess.STDOUT,check=True,env=profile_env)
    allocs=sorted(job.glob('node-*/allocs-after.pprof'))
    if allocs and not (job/'allocations.txt').exists():
        with (job/'allocations.txt').open('w') as out:
            subprocess.run([*pprof,'-top','-alloc_space','-nodecount=45',str(binary),*map(str,allocs)],stdout=out,stderr=subprocess.STDOUT,check=True,env=profile_env)
