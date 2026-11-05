"""Versioned file handoffs; no model-written summary replaces retained evidence."""
import os
from pathlib import Path
import shutil
import stat
import subprocess

from runtime.storage import read_json, write_json
from runtime.evidence import inside, require_description


def copy_regular(source, destination):
    if source.is_symlink() or not stat.S_ISREG(source.stat().st_mode):
        raise ValueError(f'Expected regular artifact: {source}')
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    destination.chmod(0o755 if source.stat().st_mode & 0o111 else 0o644)


def copy_tree(source, destination, excluded=()):
    destination.mkdir(parents=True, exist_ok=True)
    for directory, directories, files in os.walk(source, followlinks=False):
        directories[:] = sorted(d for d in directories if d not in excluded and not (Path(directory) / d).is_symlink())
        for name in sorted(files):
            path = Path(directory) / name
            if name in excluded or path.is_symlink() or not path.is_file():
                continue
            copy_regular(path, destination / path.relative_to(source))


def candidate_commit(path):
    command = ['git', '-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false', '-C', str(path)]
    if subprocess.check_output(command + ['status', '--porcelain', '--untracked-files=all'], timeout=10).strip():
        raise ValueError('Candidate repository changed after capture')
    return subprocess.check_output(command + ['rev-parse', 'HEAD'], timeout=10).decode().strip()


def check_materials(workspace, inputs, names):
    changed = [name for name in names if not inside(workspace, name).is_file()
               or inside(workspace, name).read_bytes() != inside(inputs, name).read_bytes()]
    if changed:
        raise ValueError('Supplied materials changed; retain draft and resolve specification: ' + ', '.join(changed))


def prepare_handoff(audit_run, candidate, destination):
    """Reconstruct the last completed worktree; never feed a cancelled draft as completed evidence."""
    record = read_json(audit_run / 'run.json')
    source = read_json(audit_run / 'inputs/source.json')
    if source['commit'] != candidate['commit']:
        raise ValueError('Audit source commit does not match candidate')
    completed = [turn for turn in record['turns'] if turn['status'] == 'completed']
    report_ref = record.get('last_completed_report')
    if not completed or not report_ref:
        raise ValueError('Audit has no completed report; partial work remains in the original audit run')
    last = max(turn['number'] for turn in completed)
    report = inside(audit_run, report_ref)
    destination.mkdir(parents=True, exist_ok=False)
    work = destination / 'audit-work'
    copy_tree(audit_run / 'source', work)
    for turn in sorted(record['turns'], key=lambda t: t['number']):
        if turn['number'] > last:
            continue
        folder = inside(audit_run, turn['path'])
        manifest = read_json(folder / 'changes/manifest.json')
        for name in manifest.get('deleted', []):
            path = inside(work, name)
            if path.is_file():
                path.unlink()
        for name in manifest.get('changed', {}):
            destination_file = inside(work, name)
            if destination_file.is_dir():
                # Git/file inventories omit directories. A deleted subtree may leave empty
                # directories where the next completed state has a regular file.
                for directory, _, _ in os.walk(destination_file, topdown=False):
                    Path(directory).rmdir()  # Fail on undeleted files rather than silently losing evidence.
            copy_regular(inside(folder / 'changes/files', name), destination_file)
    delivered_report = work / 'report.md'
    if not delivered_report.is_file() or delivered_report.read_bytes() != report.read_bytes():
        raise ValueError('Completed report does not match the reconstructed worktree')
    # Raw records remain separate, including any unfinished turn, with their original status.
    for name in ('turns', 'executions', 'tools', 'agent-records'):
        if (audit_run / name).is_dir():
            copy_tree(audit_run / name, destination / 'raw' / name)
    copy_regular(audit_run / 'run.json', destination / 'raw/run.json')
    copy_regular(audit_run / 'inputs/source.json', destination / 'raw/source.json')
    if (audit_run / 'agents.json').is_file():
        copy_regular(audit_run / 'agents.json', destination / 'raw/agents.json')
    handoff = {
        'candidate_commit': candidate['commit'], 'audit_run': str(audit_run),
        'audit_stop': record['stop'], 'last_completed_turn': last,
        'report': 'audit-work/report.md', 'reproductions': 'audit-work/', 'raw_records': 'raw/',
        'test_polarity': 'Read each test: PASS may mean a violating witness was observed.',
        'incomplete_turns': [t['number'] for t in record['turns'] if t['number'] > last],
        'supplemental_turns': [{'number': t['number'], 'status': t['status'],
                               'path': str(Path('raw') / inside(audit_run, t['path']).relative_to(audit_run))}
                              for t in record['turns'] if t['number'] > last],
    }
    write_json(destination / 'handoff.json', handoff)
    return handoff


def read_repair_result(workspace, expected_commit, expected_ids=None):
    result = read_json(inside(workspace, '.forge/repair-result.json'))
    if not {'input_commit', 'action', 'summary', 'issues'} <= result.keys():
        raise ValueError('Repair result must contain input_commit, action, summary, and issues')
    if result['input_commit'] != expected_commit:
        raise ValueError('Repair result refers to a different candidate commit')
    if not isinstance(result['action'], str) or result['action'] not in {'repaired', 'no_change', 'needs_specification'}:
        raise ValueError('Invalid repair action')
    require_description(result['summary'], 'repair summary')
    if not isinstance(result['issues'], list):
        raise ValueError('Repair issue list is required')
    ids = set()
    for issue in result['issues']:
        if not isinstance(issue, dict) or not {'id', 'disposition', 'reason'} <= issue.keys():
            raise ValueError('Invalid repair issue record')
        if any(not isinstance(issue[k], str) or not issue[k].strip() for k in ('id', 'disposition')):
            raise ValueError('Repair issue id and disposition must be nonempty strings')
        require_description(issue['reason'], 'repair reason')
        if issue['id'] in ids or issue['disposition'] not in {'addressed', 'not_substantiated', 'unresolved', 'needs_specification'}:
            raise ValueError('Duplicate repair issue or invalid disposition')
        ids.add(issue['id'])
    if expected_ids is not None and ids != set(expected_ids):
        raise ValueError('Repair must cover exactly the supplied issue IDs')
    return result
