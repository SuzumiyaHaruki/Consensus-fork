"""Independent generation condition; shared Codex execution, no audit workflow."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

PROJECT = Path(__file__).resolve().parents[1]
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT))

from generator.config import settings_from_dict
from generator import runner

INPUTS = ('AGENTS.md', 'TASK.md', 'protocol.md')
CONDITION = 'native-codex-system-generation'
OPTIONS = {'model', 'reasoning_effort', 'timeout_seconds', 'action_seconds', 'codex'}


def load(config, overrides=None):
    config = config.resolve()
    values = runner.read_json(config) | (overrides or {})
    if set(values) - OPTIONS:
        raise ValueError('Unknown baseline settings: ' + ', '.join(sorted(set(values) - OPTIONS)))
    settings = settings_from_dict(values | {'inputs_dir': str(BASE/'inputs'),
        'output_root': str(BASE/'experiments'), 'execution_python': str(PROJECT/'.venv/bin/python')}, config.parent)
    if not settings.model:
        raise ValueError('Specify the baseline model explicitly')
    return settings


def prepare(settings, label='sol-high-generation'):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', label):
        raise ValueError('label must be 1-64 letters, digits, underscores, or hyphens')
    source = Path(settings.inputs_dir)
    for name in INPUTS:
        if not (source/name).is_file():
            raise ValueError(f'Missing baseline input: {source/name}')
    output = Path(settings.output_root)
    output.mkdir(parents=True, exist_ok=True)
    prefix = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-') + label + '-'
    root = Path(tempfile.mkdtemp(prefix=prefix, dir=output))
    record = {'runner_version': runner.__version__, 'condition': CONDITION, 'status': 'preparing',
              'created_at': runner.utc_now(), 'settings': settings.to_dict(),
              'workspace': str(root/'workspace'), 'input_files': list(INPUTS),
              'environment': {'mode': 'host', 'read_isolation': False, 'user_config': 'private',
                  'user_instructions_and_skills': 'disabled', 'project_instructions': 'explicit inputs/AGENTS.md',
                  'sandbox': 'workspace-write', 'approval_policy': 'never',
                  'shared_daemon': False, 'subagents': 'native_allowed'}}
    runner.write_json(root/'run.json', record)
    try:
        for name in INPUTS:
            for target in (root/'inputs', root/'workspace'):
                target.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source/name, target/name)
        for name in ('tracecheck.py', 'schedule.py'):
            shutil.copyfile(PROJECT/'runtime'/name, root/'inputs'/name)
        record.update(trace_helper='inputs/tracecheck.py', schedule_helper='inputs/schedule.py')
        (root/'prompt.txt').write_bytes((root/'inputs/TASK.md').read_bytes())
        (root/'workspace/.gitignore').write_text('*.test\ncoverage.out\n.runtime/\n')
        subprocess.run(['git', 'init', '--quiet', '--template=', str(root/'workspace')],
                       check=True, capture_output=True, text=True, timeout=10)
        record.update(status='prepared', command=runner.command_for(settings, root))
    except (OSError, subprocess.SubprocessError) as exc:
        record.update(status='prepare_failed', error=str(exc))
        runner.write_json(root/'run.json', record)
        raise
    runner.write_json(root/'run.json', record)
    return root


def inspect(root):
    root = root.resolve()
    if not root.is_relative_to((BASE/'experiments').resolve()):
        raise ValueError('Select a run inside baseline/experiments')
    record = runner.read_json(root/'run.json')
    if record.get('condition') != CONDITION:
        raise ValueError('This is not a baseline generation run')
    return {'run_dir': str(root), **record}


def execute(root):
    inspect(root)  # Do not accidentally execute a prepared run from another workflow.
    return runner.execute(root)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Generate and self-check a system with native Codex')
    sub = parser.add_subparsers(dest='action', required=True)
    for name in ('prepare', 'run', 'doctor'):
        child = sub.add_parser(name)
        child.add_argument('--config', type=Path, default=BASE/'config.json')
        child.add_argument('--model')
        child.add_argument('--reasoning-effort')
        child.add_argument('--timeout-seconds', type=float)
        if name != 'doctor':
            child.add_argument('--label', default='sol-high-generation')
    for name in ('execute', 'inspect'):
        sub.add_parser(name).add_argument('run_dir', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.action in {'prepare', 'run', 'doctor'}:
            overrides = {name: getattr(args, name) for name in ('model', 'reasoning_effort', 'timeout_seconds')
                         if getattr(args, name) is not None}
            settings = load(args.config, overrides)
            if args.action == 'doctor':
                result = runner.doctor(settings)
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return 0 if result['ready'] else 1
            root = prepare(settings, args.label)
            print(json.dumps({'run_dir': str(root), 'status': 'prepared'}), flush=True)
            if args.action == 'prepare':
                return 0
        else:
            root = args.run_dir.resolve()
        if args.action == 'inspect':
            print(json.dumps(inspect(root), ensure_ascii=False, indent=2))
            return 0
        result = execute(root)
        print(json.dumps(inspect(root), ensure_ascii=False, indent=2))
        return {'agent_finished': 0, 'interrupted': 130, 'timed_out': 124}.get(result['status'], 1)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
