#!/usr/bin/env python3
"""Native delivered-server throughput investigation; no model calls or protocol edits."""
import argparse
import json
import os
import resource
from pathlib import Path
import shutil
import socket
import subprocess
import threading
import time
import urllib.request

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
SOURCE = REPO/'baseline/experiments/20261117T070206Z-sol-high-baseline-1117-01-00tot07s/workspace'
ROOT = Path('/home/nitro/Desktop/baseline-throughput-1117')
ENV = dict(os.environ, GOTOOLCHAIN='local', GOPROXY='off', GOWORK='off', GOCACHE=str(ROOT/'cache'))
HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))

def dump(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')

def rpc(address, path='/stats', body=None):
    data=None if body is None else json.dumps(body).encode()
    req=urllib.request.Request('http://'+address+path,data=data,headers={'Content-Type':'application/json'})
    with HTTP.open(req,timeout=3) as r:return json.load(r)

def cpu(pid):
    raw=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
    return dict(cpu_s=(int(raw[11])+int(raw[12]))/os.sysconf('SC_CLK_TCK'),rss=int(raw[21])*os.sysconf('SC_PAGE_SIZE'))

def prepare():
    ROOT.mkdir(exist_ok=True)
    target=ROOT/'candidate'
    if not target.exists():
        shutil.copytree(SOURCE,target,ignore=shutil.ignore_patterns('.git','.runtime','results'))
    dump(ROOT/'origin.json',dict(source=str(SOURCE),run=SOURCE.parent.name,go=subprocess.check_output(['go','version'],text=True).strip(),cpus=sorted(os.sched_getaffinity(0)),meminfo=Path('/proc/meminfo').read_text()))
    for prog in ('server','keygen'):
        subprocess.run(['go','build','-buildvcs=false','-o',str(ROOT/prog),'./cmd/'+prog],cwd=target,env=ENV,check=True)
    subprocess.run(['go','build','-o',str(ROOT/'load'),str(HERE/'load.go')],env=ENV,check=True)
    with (ROOT/'native-tests.log').open('w') as log:
        subprocess.run(['go','test','./...','-count=1','-timeout=90s'],cwd=target,env=ENV,stdout=log,stderr=subprocess.STDOUT,check=True)
    profile=target/'cmd/server/diagnostic_profile.go'
    profile.write_text((HERE/'diagnostic_profile.go.txt').read_text())
    try:
        subprocess.run(['go','build','-buildvcs=false','-o',str(ROOT/'server-profile'),'./cmd/server'],cwd=target,env=ENV,check=True)
    finally:
        profile.unlink()
    print('Prepared native binaries and passed functional tests.',flush=True)

def run_case(a, rate, repeat):
    name=f'{a.name}-n{a.n}-{a.topology}-r{rate:g}-rep{repeat}'
    out=ROOT/'jobs'/name
    if out.exists():raise RuntimeError('Refusing to overwrite '+str(out))
    out.mkdir(parents=True);procs=[];logs=[];stop=threading.Event();monitor=None
    sockets=[]
    try:
        for _ in range(2*a.n+int(a.profile)):
            s=socket.socket();s.bind(('127.0.0.1',0));sockets.append(s)
        ports=[s.getsockname()[1] for s in sockets]
        peers=[f'127.0.0.1:{p}' for p in ports[:a.n]];apis=[f'127.0.0.1:{p}' for p in ports[a.n:2*a.n]]
        for s in sockets:s.close()
        config=dict(members=[dict(id=i,address=x) for i,x in enumerate(peers)],f=4 if a.n==7 else 1,s=1 if a.n==7 else 0,e=1 if a.n==7 else 0,tick=int(a.tick_ms*1e6))
        dump(out/'config.json',config)
        subprocess.run([str(ROOT/'keygen'),'-dir',str(out/'keys'),'-n',str(a.n)],stdout=subprocess.DEVNULL,check=True)
        cpus=sorted(os.sched_getaffinity(0));p=1 if a.n==7 else 2
        if len(cpus)<a.n*p+1:raise RuntimeError('insufficient CPUs for requested layout')
        dump(out/'settings.json',dict(args=vars(a),rate=rate,repeat=repeat,per_replica_cpus=[cpus[i*p:(i+1)*p] for i in range(a.n)],driver_cpus=cpus[a.n*p:],source=str(SOURCE)))
        for i,api in enumerate(apis):
            log=(out/f'replica-{i}.log').open('w');logs.append(log)
            cmd=['taskset','-c',','.join(map(str,cpus[i*p:(i+1)*p])),str(ROOT/('server-profile' if a.profile else 'server')),'-config',str(out/'config.json'),'-keys',str(out/'keys'),'-id',str(i),'-api',api,'-workers',str(a.workers),'-gomaxprocs',str(p),'-w',f'{a.w_ms}ms','-wait',f'{a.timeout+5}s','-queue','4096','-max-active','4096']
            procs.append(subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=dict(ENV,GOMAXPROCS=str(p),FORGE_PROFILE_ADDR=(f'127.0.0.1:{ports[-1]}' if a.profile and i==0 else ''))))
        deadline=time.monotonic()+10
        for api in apis:
            while True:
                try:rpc(api);break
                except (OSError,ValueError):
                    if time.monotonic()>deadline:raise RuntimeError('startup timeout')
                    time.sleep(.05)
        def warm(i):
            return rpc(apis[i%a.n],'/request',dict(rid=dict(client='throughput-warmup-session',seq=i+1),op='put',key=f'warm/{i}',value='v'*16))
        # Warm connections with sequential requests, avoiding incidental admission rejection.
        for i in range(7*a.n):
            r=warm(i)
            if r.get('status')!='OK':raise RuntimeError('warmup '+str(r))
        deadline=time.monotonic()+8
        while True:
            stats=[rpc(x) for x in apis]
            if all(x['node']['executed']==7*a.n for x in stats):break
            if time.monotonic()>deadline:raise RuntimeError('warmup incomplete at replicas')
            time.sleep(.05)
        before_cpu=[cpu(p.pid) for p in procs];dump(out/'before.json',dict(stats=stats,cpu=before_cpu,vmstat=Path('/proc/vmstat').read_text()))
        def watch():
            with (out/'samples.jsonl').open('w') as f:
                while not stop.is_set():
                    sample=dict(time_ns=time.time_ns(),cpu=[cpu(p.pid) for p in procs])
                    try:sample['stats']=[rpc(x) for x in apis]
                    except Exception as error:sample['error']=str(error)
                    f.write(json.dumps(sample)+'\n');f.flush();stop.wait(1)
        monitor=threading.Thread(target=watch,daemon=True);monitor.start()
        cmd=['taskset','-c',','.join(map(str,cpus[a.n*p:])),str(ROOT/'load'),'-addresses',','.join(apis),'-rate',str(rate),'-seconds',str(a.seconds),'-timeout',str(a.timeout),'-topology',a.topology,'-seed',str(17+repeat),'-output',str(out)]
        if a.profile:
            def profile():
                try:
                    with HTTP.open(f'http://127.0.0.1:{ports[-1]}/debug/pprof/profile?seconds=10',timeout=20) as r:
                        (out/'cpu-0.pprof').write_bytes(r.read())
                except Exception as e:dump(out/'profile-error.json',dict(error=str(e)))
            profiler=threading.Thread(target=profile,daemon=True);profiler.start()
        usage_before=resource.getrusage(resource.RUSAGE_CHILDREN)
        with (out/'driver.log').open('w') as log:
            subprocess.run(cmd,env=dict(ENV,GOMAXPROCS=str(len(cpus[a.n*p:]))),stdout=log,stderr=subprocess.STDOUT,check=True,timeout=a.seconds+a.timeout+20)
        if a.profile:profiler.join(timeout=20)
        usage_after=resource.getrusage(resource.RUSAGE_CHILDREN)
        load=json.loads((out/'load.json').read_text())
        load['driver_cpu_seconds']=(usage_after.ru_utime+usage_after.ru_stime)-(usage_before.ru_utime+usage_before.ru_stime)
        load['driver_cpu_cores']=load['driver_cpu_seconds']/((load['observed_until_ns']-load['start_ns'])/1e9)
        after=[rpc(x) for x in apis]
        dump(out/'after.json',dict(stats=after,cpu=[cpu(p.pid) for p in procs],vmstat=Path('/proc/vmstat').read_text()))
        dump(out/'result.json',dict(name=name,rate=rate,repeat=repeat,n=a.n,topology=a.topology,seconds=a.seconds,load=load))
        print(name,'throughput',round(load['throughput_ops_s'],1),'counts',load['counts'],'lag p99',load['send_lag_ms']['p99'],flush=True)
    except Exception as e:
        dump(out/'error.json',dict(error=repr(e),traceback=__import__('traceback').format_exc()));raise
    finally:
        stop.set()
        if monitor:monitor.join(timeout=5)
        for p in procs:
            if p.poll() is None:p.terminate()
        for p in procs:
            try:p.wait(timeout=5)
            except subprocess.TimeoutExpired:p.kill();p.wait()
        for f in logs:f.close()
        for s in sockets:s.close()
        shutil.rmtree(out/'keys',ignore_errors=True)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','run'])
    p.add_argument('--name',default='scan');p.add_argument('--n',type=int,choices=[3,7],default=7)
    p.add_argument('--topology',choices=['single','balanced','random'],default='random')
    p.add_argument('--rates',default='300,800,1500,3000,6000');p.add_argument('--seconds',type=float,default=12)
    p.add_argument('--timeout',type=float,default=15);p.add_argument('--repeats',type=int,default=1)
    p.add_argument('--profile',action='store_true')
    p.add_argument('--workers',type=int,default=4);p.add_argument('--w-ms',type=int,default=200);p.add_argument('--tick-ms',type=int,default=40)
    a=p.parse_args()
    if a.action=='prepare':prepare();return
    for repeat in range(1,a.repeats+1):
        for rate in map(float,a.rates.split(',')):run_case(a,rate,repeat)
if __name__=='__main__':main()
