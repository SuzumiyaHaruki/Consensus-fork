"""Export candidates and invoke the locally maintained auditor."""
import argparse
import json
import os
from pathlib import Path
import stat
import subprocess
import sys


def git(root, *args):
    return subprocess.check_output([
        'git', '-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false',
        '-c', 'user.name=Consensus Forge', '-c', 'user.email=consensus-forge@localhost',
        '-c', 'commit.gpgsign=false', '-C', str(root), *args,
    ], stderr=subprocess.PIPE, timeout=30)


def export(workspace, destination):
    from runtime.storage import EXCLUDED_DIRS
    excluded_dirs = EXCLUDED_DIRS | {'.forge', '.runtime', '.execution', '.pytest_cache', '.cache'}
    names = git(workspace, 'ls-files', '--cached', '--others', '--exclude-standard', '-z').decode().split('\0')
    destination.mkdir(parents=True, exist_ok=False)
    files, excluded = [], {}
    for name in sorted(set(filter(None, names))):
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Unsafe candidate path')
        path = workspace / relative
        if (set(relative.parts) & excluded_dirs or path.name in {'AGENTS.md', 'SKILL.md', 'TASK.md'}
                or path.suffix in {'.test', '.pyc'} or path.name == 'coverage.out'):
            excluded[name] = 'instructions, feedback, or transient output'
            continue
        if any(p.is_symlink() for p in (path, *path.parents) if p.is_relative_to(workspace)):
            excluded[name] = 'symbolic link'
            continue
        if not path.exists():
            continue
        if not stat.S_ISREG(path.stat().st_mode):
            excluded[name] = 'not a regular file'
            continue
        if path.stat().st_size > 16_000_000:
            excluded[name] = 'oversized artifact; inspect original generation output'
            continue
        data = path.read_bytes()
        if data.startswith(b'\x7fELF'):
            excluded[name] = 'compiled executable'
            continue
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        target.chmod(0o755 if os.access(path, os.X_OK) else 0o644)
        files.append(name)
    module = destination / 'go.mod'
    if not module.is_file() or not any(line.split() == ['module', 'example.com/mixepaxos'] for line in module.read_text().splitlines()):
        raise ValueError('Candidate must provide module example.com/mixepaxos')
    git(destination, 'init', '--quiet', '--template=')
    git(destination, 'add', '--force', '--', *files)
    git(destination, 'commit', '--quiet', '--no-verify', '-m', 'Capture generated candidate')
    return {'path': str(destination), 'commit': git(destination, 'rev-parse', 'HEAD').decode().strip(),
            'files': files, 'excluded': excluded}


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='operation', required=True)
    sub.add_parser('probe')
    capture = sub.add_parser('export')
    capture.add_argument('workspace', type=Path)
    capture.add_argument('destination', type=Path)
    for command in ('audit', 'check-env'):
        child = sub.add_parser(command)
        child.add_argument('config', type=Path)
    args = parser.parse_args()
    from auditor.config import load_config, validate_selection
    if args.operation == 'probe':
        from auditor.runner import run  # Import dependencies without logging in or calling a model.
        result = {'available': True, 'audit_root': str(Path(__file__).resolve().parent / 'auditor'), 'python': sys.executable}
    elif args.operation == 'export':
        result = export(args.workspace.resolve(), args.destination.absolute())
    else:
        from auditor.runner import run
        config = load_config(args.config)
        target = validate_selection(config)
        result = run(config, target, environment_only=args.operation == 'check-env')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get('ok', True) else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f'Audit bridge: {exc}', file=sys.stderr)
        raise SystemExit(2)
