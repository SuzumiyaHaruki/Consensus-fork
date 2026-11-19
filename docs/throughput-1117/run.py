#!/usr/bin/env python3
"""Four delivered candidates, one fixed-rate HTTP load generator; no model calls."""
import argparse
import difflib
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import threading
import time

DESKTOP = Path('/home/nitro/Desktop')
LABELS = ['1111-baseline', '1111-v000', '1113-baseline', '1113-v000']

def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def prepare(root):
    root.mkdir(parents=True, exist_ok=True)
    template = DESKTOP/'consensus-server-evaluation-1111'
    shutil.copytree(template/'scripts', root/'scripts', dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__'))
    # One loopback address per member preserves the 1113 baseline's source-IP identity checks.
    common_path=root/'scripts/common.py'
    common_text=common_path.read_text()
    common_text=common_text.replace("for sock in ports:\n                sock.bind(('127.0.0.1', 0))", "for i, sock in enumerate(ports):\n                sock.bind((f'127.0.0.{i+1}', 0))")
    common_text=common_text.replace("addresses = [f'127.0.0.1:{s.getsockname()[1]}' for s in ports]", "addresses = [f'127.0.0.{i+1}:{s.getsockname()[1]}' for i, s in enumerate(ports)]")
    common_path.write_text(common_text)
    origins = {}
    for label in LABELS:
        date, version = label.split('-')
        suite = DESKTOP/f'consensus-server-evaluation-{date}'
        work = root/'build'/label
        work.mkdir(parents=True, exist_ok=True)
        candidate = work/'candidate'
        if candidate.exists():
            raise RuntimeError(f'Build copy already exists: {candidate}')
        shutil.copytree(suite/'implementations'/version, candidate)
        origins[label] = json.loads((suite/'origins.json').read_text())['implementations'][version]
        for name in ('main.go','load.go','faults.go','load_test.go'):
            shutil.copy2(template/'harness'/name, work/name)
        shutil.copy2(suite/'harness'/f'adapter_{"baseline" if version=="baseline" else "forge"}.go', work/'adapter.go')
        patches = []
        if label == '1113-baseline':
            for name, counter, event in [('node.go','Admitted','admitted'),('data.go','Decided','decided'),('execution.go','Executed','executed')]:
                path=candidate/name; old=path.read_text(); needle=f'n.stats.{counter}++'
                assert old.count(needle)==1
                new=old.replace(needle, needle+f'\n\tn.event(Event{{Type: "{event}", X: x}})')
                path.write_text(new)
                patches.extend(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='original/'+name,tofile='observed/'+name))
        (work/'candidate-observation.patch').write_text(''.join(patches))
        main=(work/'main.go').read_text().replace('"sync"','"sync"\n "sync/atomic"')
        main=main.replace('type Recorder struct {','type Recorder struct {\n disabled atomic.Bool')
        main=main.replace('func (r *Recorder) observe(e Event) {','func (r *Recorder) observe(e Event) {\n if r.disabled.Load() { return }')
        main=main.replace('mux.HandleFunc("/bench/events", rec.events)', 'mux.HandleFunc("/bench/recording", func(w http.ResponseWriter, r *http.Request) { rec.disabled.Store(r.URL.Query().Get("enabled")=="0"); respond(w, map[string]bool{"disabled":rec.disabled.Load()}) })\n mux.HandleFunc("/bench/events", rec.events)')
        (work/'main.go').write_text(main)
        load=(work/'load.go').read_text().replace('type LoadConfig struct {','type LoadConfig struct {\n SkipEvents bool `json:"skip_events"`')
        load=load.replace('if len(c.Observers) == 0 {','if c.SkipEvents { c.Observers = nil }\n if len(c.Observers) == 0 && !c.SkipEvents {')
        (work/'load.go').write_text(load)
        (work/'go.mod').write_text('module local/consensusbench\n\ngo 1.25\n\nrequire example.com/mixepaxos v0.0.0\nreplace example.com/mixepaxos => ./candidate\n')
        env=dict(os.environ,GOTOOLCHAIN='local',GOPROXY='off',GOWORK='off',GOCACHE=str(template/'.cache/go-build'),GOMAXPROCS='4')
        with (work/'build.log').open('w') as log:
            subprocess.run(['go','build','-buildvcs=false','-tags','baseline' if version=='baseline' else 'forge','-o','bench','.'],cwd=work,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        print('built',label,flush=True)
    dump(root/'origins.json',origins)


def run(root, args):
    sys.path.insert(0,str(root/'scripts'))
    import common
    from checks import resources_for_window
    from hardware import topology
    common.ROOT=root
    options=dict(cpu_per_replica=1 if args.n==7 else 2,threads_per_core=1,
                 replica_gomaxprocs=1 if args.n==7 else 2,driver_cpus=1 if args.n==7 else 2,
                 pin=True,drain_seconds=args.drain,observation_seconds=2)
    env=dict(cpu_topology=topology(),meminfo=Path('/proc/meminfo').read_text(),
             vmstat=Path('/proc/vmstat').read_text(),go=subprocess.check_output(['go','version'],text=True).strip(),
             options=options,n=args.n,seconds=args.seconds,drain=args.drain,rate_list=args.rates,
             source='Delivered pre-K-removal candidates; unbatched independent-key PUT, 16-byte value.')
    dump(root/f'environment-{args.name}.json',env)
    jobs=[]
    for repeat in range(1,args.repeats+1):
        for rate in map(float,args.rates.split(',')):
            block=[dict(label=label,rate=rate,repeat=repeat) for label in args.versions.split(',')]
            random.Random(20261117+repeat+int(rate)).shuffle(block)
            jobs.extend(block)
    dump(root/f'plan-{args.name}.json',dict(jobs=jobs,args=vars(args)))
    for index,job in enumerate(jobs,1):
        label,rate,repeat=job['label'],job['rate'],job['repeat']
        name=f'{args.name}-{label}-n{args.n}-r{rate:g}-rep{repeat}'
        directory=root/'jobs'/name
        if directory.exists():
            print('skip existing',name,flush=True);continue
        print(f'[{index}/{len(jobs)}] {name}',flush=True)
        started=time.monotonic();c=None;errors=[];profiler=None
        try:
            case=dict(n=args.n,f=4 if args.n==7 else 1,s=1 if args.n==7 else 0,e=1 if args.n==7 else 0,
                      k=64,workers=4,queue=4096,window_ms=200)
            c=common.Cluster(label,directory,case,options)
            for i in range(args.n):
                response=c.request(i,common.command('warmup-session-01',i+1,key=f'warm/{i}',value='x'*16),wait_ms=3000)
                if response['result'].get('status') not in ('OK','APPLIED'):
                    raise RuntimeError(f'warmup: {response}')
            drain=c.wait_executed(args.n,timeout=5)
            if not drain['complete']:raise RuntimeError('warmup not executed at all replicas')
            before=c.metrics();dump(directory/'before.json',before)
            if args.quiet:
                for a in c.addresses:common.rpc(a,'/bench/recording?enabled=0')
            if args.profile:
                for a in c.addresses:common.rpc(a,'/bench/profile?kind=cpu&action=start')
                def stop_profiles():
                    try:
                        deadline=time.monotonic()+15
                        while not (directory/'load/started.json').exists():
                            if time.monotonic()>deadline:raise TimeoutError('load not started')
                            time.sleep(.02)
                        start=json.loads((directory/'load/started.json').read_text())['start_ns']/1e9
                        time.sleep(max(0,start+args.seconds-time.time()))
                        for a in c.addresses:
                            common.rpc(a,'/bench/profile?kind=cpu&action=stop',timeout=10)
                            common.rpc(a,'/bench/profile?kind=allocs&action=after',timeout=10)
                    except Exception as error:errors.append(str(error))
                profiler=threading.Thread(target=stop_profiles,daemon=True);profiler.start()
            c.start_monitor()
            result=c.load('load',duration_seconds=args.seconds,rate=rate,payload_bytes=16,
                          topology=args.topology,entries=[0] if args.topology=='single' else list(range(args.n)),
                          key_prefix='k',session='throughput-test-01',skip_events=args.quiet,seed=17+repeat,max_http=65536)
            result['resources']=resources_for_window(c.samples,result['start_ns'],result['end_ns'])
            result['after']=c.metrics()
            result['candidate_stats']={}
            for i,a in enumerate(c.addresses):
                try: result['candidate_stats'][str(i)]=common.rpc(a,'/bench/stats',timeout=1)[1]
                except (OSError,TimeoutError) as error: result['candidate_stats'][str(i)]={'observation_error':str(error)}
            result['status']='measured'
            if profiler:profiler.join(timeout=20)
            result['profile_errors']=errors
            result.update(job=job,n=args.n,seconds=args.seconds,quiet=args.quiet,profile=args.profile,topology=args.topology)
            dump(directory/'result.json',result)
            print(f"  throughput={result['throughput_ops_s']:.1f} issued={result['issued']} completed={result['completed_requests']} counts={result['counts']} elapsed={time.monotonic()-started:.1f}s",flush=True)
        except Exception as error:
            dump(directory/'error.json',dict(error=repr(error),job=job,traceback=__import__('traceback').format_exc()))
            print('ERROR',repr(error),flush=True)
        finally:
            if profiler:profiler.join(timeout=20)
            if c:c.close()
        time.sleep(.3)
    summarize(root)


def summarize(root):
    rows=[]
    for f in sorted((root/'jobs').glob('*/result.json')):
        v=json.loads(f.read_text());r=dict(name=f.parent.name,**v['job'],n=v['n'],quiet=v['quiet'],profile=v['profile'],topology=v['topology'])
        for k in ('throughput_ops_s','actual_send_rate','completed_requests','issued','all_completed','counts','not_sent','mean_inflight','peak_inflight','complete_latency_ms','observed_completed_latency_ms','send_lag_ms','driver_cpu_percent_one_core','resources'):
            r[k]=v.get(k)
        rows.append(r)
    dump(root/'summary.json',rows)
    for r in rows:
        print(r['name'],round(r['throughput_ops_s'],1),r['counts'])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['prepare','run','summary'])
    p.add_argument('--root',default=str(DESKTOP/'consensus-throughput-1117'))
    p.add_argument('--name',default='scan');p.add_argument('--versions',default=','.join(LABELS))
    p.add_argument('--n',type=int,choices=[3,7],default=7);p.add_argument('--rates',default='300,1500,5000')
    p.add_argument('--seconds',type=float,default=8);p.add_argument('--drain',type=float,default=8)
    p.add_argument('--repeats',type=int,default=1);p.add_argument('--quiet',action='store_true');p.add_argument('--profile',action='store_true')
    p.add_argument('--topology',choices=['random','single','balanced'],default='random')
    a=p.parse_args();root=Path(a.root)
    if a.action=='prepare':prepare(root)
    elif a.action=='run':run(root,a)
    else:summarize(root)
