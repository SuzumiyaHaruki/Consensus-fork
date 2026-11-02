"""CLI for Consensus Forge; prepare and doctor never call a model."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

import workflow
from workflow_config import DEFAULT, load


def main(argv=None):
    parser = argparse.ArgumentParser(description='Generate, audit, repair, and re-audit a synchronous consensus system')
    sub = parser.add_subparsers(dest='action', required=True)
    for name in ('prepare', 'run', 'doctor'):
        child = sub.add_parser(name)
        child.add_argument('--config', type=Path, default=DEFAULT)
        child.add_argument('--output-root')
        child.add_argument('--total-seconds', type=float)
        child.add_argument('--max-repairs', type=int)
        if name != 'doctor':
            child.add_argument('--label', default='sol-high-system')
    for name in ('execute', 'inspect'):
        child = sub.add_parser(name)
        child.add_argument('experiment_dir', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.action in {'prepare', 'run', 'doctor'}:
            settings = load(args.config, {k: getattr(args, k) for k in ('output_root', 'total_seconds', 'max_repairs') if getattr(args, k) is not None})
            if args.action == 'doctor':
                result = workflow.doctor(settings)
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return 0 if result['ready'] else 1
            root = workflow.prepare(settings, args.label)
            print(json.dumps({'experiment_dir': str(root), 'status': 'prepared'}), flush=True)
            if args.action == 'prepare':
                return 0
        else:
            root = args.experiment_dir.resolve()
        if args.action == 'inspect':
            print(json.dumps(workflow.inspect(root), ensure_ascii=False, indent=2))
            return 0
        result = workflow.execute(root)
        print(json.dumps(workflow.inspect(root), ensure_ascii=False, indent=2))
        if result['status'] == 'cycle_complete':
            return 0
        return {'interrupted': 130, 'budget_exhausted': 124, 'stage_timed_out': 124}.get(result['status'], 1)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
