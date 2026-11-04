"""Run common scenarios against untouched candidate copies; no model calls."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from http_cases import run as http_cases

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MAIN = ROOT / 'experiments/20261103T104654Z-sol-high-complete-collection-02-z2hq9xag/candidates'
SOURCES = {
    'baseline': ROOT / 'baseline/experiments/20261104T042609Z-independent-audit-baseline-01-ui662dvg/candidate',
    **{name: MAIN / name for name in ('v000', 'v001', 'v002')},
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--targets', nargs='+', choices=SOURCES, default=['baseline', 'v000', 'v002'])
    parser.add_argument('--case', choices=['correctness', 'boundary', 'http', 'history', 'network'], default='correctness')
    parser.add_argument('--repeat', type=int, default=1)
    args = parser.parse_args()
    if args.repeat < 1:
        parser.error('--repeat must be positive')
    (HERE / 'runs').mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-')
    run = Path(tempfile.mkdtemp(prefix=stamp + args.case + '-', dir=HERE / 'runs'))
    records = []
    env = os.environ | {'GOCACHE': '/tmp/consensus-forge-comparison-gocache', 'GOTOOLCHAIN': 'local', 'GOPROXY': 'off'}
    for repeat in range(args.repeat):
        # Rotate order to avoid always benchmarking the same candidate first.
        order = args.targets[repeat % len(args.targets):] + args.targets[:repeat % len(args.targets)]
        for name in order:
            source = SOURCES[name]
            folder = run / f'{repeat + 1:02d}-{name}'
            workspace = folder / 'workspace'
            shutil.copytree(source, workspace, ignore=shutil.ignore_patterns('.git', '.runtime', '__pycache__', '*.test'))
            adapter = 'baseline' if name == 'baseline' else 'forge'
            for src in [HERE/'tests/common_test.go', HERE/f'tests/{adapter}_test.go']:
                shutil.copyfile(src, workspace/'tests'/('comparison_' + src.name))
            commit = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
            if args.case in ('http', 'network'):
                result = http_cases(workspace, folder, name == 'baseline', env, network=args.case == 'network')
                record = {'candidate': name, 'commit': commit, 'case': args.case, 'repeat': repeat+1, 'folder': str(folder), 'results': result}
                records.append(record)
                (run/'results.json').write_text(json.dumps(records, ensure_ascii=False, indent=2)+'\n')
                print(json.dumps(record), flush=True)
                continue
            pattern = {'correctness': 'Concurrent|Cycle|Recovery', 'boundary': 'Delta|MemberIdentity', 'history': 'History'}[args.case]
            command = ['go', 'test', '-json', './tests', '-run', '^TestComparison(' + pattern + ')$', '-count=1', '-timeout=180s']
            if args.case != 'history':
                command.insert(2, '-race')
            start = time.monotonic()
            with (folder/'go-test.jsonl').open('w') as output:
                result = subprocess.run(command, cwd=workspace, env=env, stdout=output, stderr=subprocess.STDOUT, timeout=210)
            record = {'candidate': name, 'commit': commit, 'source': str(source), 'case': args.case,
                      'repeat': repeat + 1, 'command': command, 'returncode': result.returncode,
                      'elapsed_seconds': round(time.monotonic() - start, 3), 'folder': str(folder)}
            (folder/'execution.json').write_text(json.dumps(record, indent=2) + '\n')
            records.append(record)
            (run/'results.json').write_text(json.dumps(records, indent=2) + '\n')
            print(json.dumps(record), flush=True)
    print(run, flush=True)


if __name__ == '__main__':
    main()
