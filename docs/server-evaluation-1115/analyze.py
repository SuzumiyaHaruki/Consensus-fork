"""Recompute the 1111 server summary; no candidate execution or model calls."""
import csv
from collections import Counter,defaultdict
import json
import os
from pathlib import Path
from statistics import median

ROOT=Path(__file__).resolve().parent
VERSIONS=['baseline','v000','v003']
CPUS=['1c1t-g1','2c2t-g2','2c4t-g4']
ROWS=list(csv.DictReader((ROOT/'summary.csv').open()))
PLAN=json.loads((ROOT/'plan.json').read_text())
GROUPS=defaultdict(list)
for row in ROWS:GROUPS[row['case'],row['cpu_layout'],row['version']].append(row)

def number(row,field):return float(row[field]) if row[field] else 0

def total(rows,field):return sum(number(row,field) for row in rows)

def med(case,cpu,version,field):
    values=[float(row[field]) for row in GROUPS[case,cpu,version] if row[field]]
    return median(values) if values else None

def analyze():
    actual={(r['case'],r['cpu_layout'],r['version'],int(r['repeat'])) for r in ROWS}
    expected={(r['case']['name'],r['cpu_layout'],r['version'],r['repeat']) for r in PLAN['jobs']}
    assert len(actual)==len(ROWS) and actual==expected
    for r in ROWS:
        if r['group']=='native':continue
        settings={'1c1t-g1':(1,1,1),'2c2t-g2':(2,2,2),'2c4t-g4':(2,4,4)}[r['cpu_layout']]
        assert tuple(int(r[k]) for k in ['physical_cores_per_replica','hardware_threads_per_replica','replica_gomaxprocs'])==settings
    report={'planned':len(PLAN['jobs']),'completed':len(ROWS),'job_elapsed_hours':total(ROWS,'elapsed_seconds')/3600,'versions':{}}
    for v in VERSIONS:
        perf=[r for r in ROWS if r['version']==v and r['group']=='performance']
        data={'performance_tasks':len(perf),'nonsuccess_tasks':sum(number(r,'other_replies')>0 for r in perf),
              'missing_decision_tasks':sum(number(r,'missing_decisions_after_drain')>0 for r in perf),
              **{k:total(perf,k) for k in ['issued','successful_replies','unknown','incomplete','other_replies','missing_decisions_after_drain']}}
        data['cpu']={}
        for cpu in CPUS:
            rows=[r for r in perf if r['cpu_layout']==cpu]
            data['cpu'][cpu]={'tasks':len(rows),'nonsuccess_tasks':sum(number(r,'other_replies')>0 for r in rows),
                'missing_decision_tasks':sum(number(r,'missing_decisions_after_drain')>0 for r in rows),
                **{k:total(rows,k) for k in ['unknown','incomplete','other_replies','missing_decisions_after_drain']}}
        data['groups']={g:dict(Counter(r['status'] for r in ROWS if r['version']==v and r['group']==g)) for g in ['native','correctness','performance','history']}
        data['uncompleted_history']={kind:sum(r['history_drained']=='False' for r in ROWS if r['version']==v and r['case'].startswith(kind+'-')) for kind in ['cold','pending']}
        report['versions'][v]=data
    report['failed_jobs']=[{k:r[k] for k in ['job','version','case','cpu_layout','repeat','status','path']} for r in ROWS if r['status'] not in ('passed','measured')]
    (ROOT/'analysis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    with (ROOT/'matched-metrics.csv').open('w',newline='') as f:
        writer=csv.writer(f);writer.writerow(['case','cpu','version','runs','throughput_median_ops_s','throughput_min_ops_s','throughput_max_ops_s','success_p99_median_ms','actual_concurrency_median_instances','nonsuccess_replies','missing_decisions','history_not_drained_runs'])
        for (case,cpu,v),rows in sorted(GROUPS.items()):
            rates=[float(r['throughput']) for r in rows if r['throughput']]
            writer.writerow([case,cpu,v,len(rows),median(rates) if rates else '',min(rates) if rates else '',max(rates) if rates else '',med(case,cpu,v,'p99_ms'),med(case,cpu,v,'observed_mean_undecided'),total(rows,'other_replies'),total(rows,'missing_decisions_after_drain'),sum(r['history_drained']=='False' for r in rows)])
    return report


def plots(report):
    os.environ.setdefault('MPLCONFIGDIR', '/tmp/forge-evaluation-matplotlib')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    colors={'baseline':'#4477aa','v000':'#ee7733','v003':'#228833'}
    labels={'1c1t-g1':'1 core / 1 thread / Go P=1','2c2t-g2':'2 cores / 2 threads / Go P=2','2c4t-g4':'2 cores / 4 threads / Go P=4'}
    ns=[1,4,16,64,256]
    fig,axes=plt.subplots(3,3,figsize=(12,9),sharex=True,sharey='row')
    for i,cpu in enumerate(CPUS):
        for j,topology in enumerate(['single','balanced','random']):
            ax=axes[i,j]
            for v in VERSIONS:
                samples=[[number(r,'throughput') for r in GROUPS[f'independent-{topology}-n{n}-p4',cpu,v]] for n in ns]
                ax.plot(ns,[median(s) for s in samples],label=v,color=colors[v],marker='o',markersize=3)
                ax.fill_between(ns,[min(s) for s in samples],[max(s) for s in samples],color=colors[v],alpha=.12)
            ax.set_xscale('log',base=2);ax.set_xticks(ns,ns);ax.grid(alpha=.2)
            ax.set_title(topology+' entry' if i==0 else '',fontsize=11)
            if j==0:ax.set_ylabel(labels[cpu]+'\nThroughput (ops/s)',fontsize=9)
            if i==2:ax.set_xlabel('Target undecided instances')
    handles,legend=axes[0,0].get_legend_handles_labels()
    fig.legend(handles,legend,loc='upper center',ncol=3)
    fig.suptitle('Independent keys, 4 workers per replica; median and min-max of 5 runs',y=.955,fontsize=11)
    fig.tight_layout(rect=[0,0,1,.94]);fig.savefig(ROOT/'independent-throughput.png',dpi=170);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    for ax,key,title in zip(axes,['nonsuccess_tasks','missing_decision_tasks'],['Runs with non-success replies','Runs with missing decisions after drain']):
        for i,v in enumerate(VERSIONS):
            vals=[100*report['versions'][v]['cpu'][cpu][key]/505 for cpu in CPUS]
            positions=[j+(i-1)*.24 for j in range(3)]
            ax.bar(positions,vals,width=.23,label=v,color=colors[v])
            for pos,val in zip(positions,vals):ax.text(pos,val+.25,f'{val:.1f}',ha='center',fontsize=8)
        ax.set_xticks(range(3),['1c1t / P1','2c2t / P2','2c4t / P4']);ax.set_ylabel('Share of 505 runs (%)');ax.set_title(title,fontsize=10);ax.grid(axis='y',alpha=.2)
    axes[0].legend(fontsize=8);fig.tight_layout();fig.savefig(ROOT/'progress-by-cpu.png',dpi=170);plt.close(fig)


if __name__=='__main__':
    report=analyze();plots(report);print(json.dumps({'completed':report['completed'],'job_elapsed_hours':report['job_elapsed_hours']},indent=2))
