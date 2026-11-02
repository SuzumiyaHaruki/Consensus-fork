"""Link retained execution facts and ask concrete follow-up questions; no verdicts."""
import json
from pathlib import Path

from .tracecheck import check_file


def inside(root, relative):
    root, relative = Path(root), Path(relative)
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError(f'Unsafe artifact path: {relative}')
    path = root / relative
    if any(p.is_symlink() for p in (path, *path.parents) if p.is_relative_to(root)):
        raise ValueError(f'Artifact link is not allowed: {relative}')
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f'Artifact escapes its root: {relative}')
    return path


def retained_path(root, ref, work_name='work', raw_name='.'):
    if not isinstance(ref, str) or not ref.strip():
        raise ValueError('Evidence path must be a nonempty string')
    parts = Path(ref).parts
    if not parts or parts[0] not in {'work', 'executions', 'turns'}:
        raise ValueError('Evidence must be relative to work/, executions/, or turns/')
    relative = Path(work_name, *parts[1:]) if parts[0] == 'work' else Path(raw_name, *parts)
    path = inside(root, relative)
    if not path.is_file():
        raise ValueError(f'Evidence file missing: {ref}')
    return str(relative)


def inspect_item(item, root, *, work_name='work', raw_name='.', expected_commits=()):
    """Only execution-service records under executions/ establish a tool link.

    A missing link does not imply no execution, and execution does not prove a claim.
    Agent-written copies in work/ are ordinary evidence, never trusted tool receipts.
    """
    feedback, traces, executions = [], [], []

    def ask(code, observation, request):
        feedback.append({'code': code, 'observation': observation, 'request': request})

    refs = item.get('evidence', [])
    if not isinstance(refs, list):
        raise ValueError('Evidence must be a list')
    linked = set()
    for ref in refs:
        retained_path(root, ref, work_name, raw_name)
        parts = Path(ref).parts
        if parts[0] != 'executions' or len(parts) < 3 or parts[1] in linked:
            continue
        linked.add(parts[1])
        record_path = str(Path(raw_name, 'executions', parts[1], 'result.json'))
        try:
            record = json.loads(inside(root, record_path).read_text())
            if not isinstance(record, dict) or record.get('execution_id') != parts[1]:
                raise ValueError('Execution ID does not match its retained directory')
        except (OSError, ValueError) as exc:
            ask('execution_record_unavailable', f'{record_path}: {exc}',
                'Locate the original execution-service record or explain the available evidence without claiming a verified tool link.')
            continue
        context = record.get('source_context', {})
        if not isinstance(context, dict):
            context = {}
        inputs = [str(Path(raw_name, 'executions', parts[1], entry['retained_path']))
                  for entry in context.get('overlays', []) if isinstance(entry, dict) and 'retained_path' in entry]
        for path in inputs:
            if not inside(root, path).is_file():
                ask('replay_input_missing', f'Retained replay input is missing: {path}',
                    'Locate the test/helper bytes used by this invocation before relying on its replayability.')
        executions.append({'path': record_path, 'execution_id': parts[1], 'argv': record.get('argv'),
                           'status': record.get('status'), 'exit_code': record.get('exit_code'),
                           'source_context': context, 'inputs': inputs})
        if record.get('status') != 'completed':
            ask('execution_incomplete', f"{record_path} ended as {record.get('status')!r}.",
                'Explain what the partial output establishes; rerun if useful or retain the limitation. A timeout alone is not a protocol failure.')
        if context.get('kind') != 'candidate_copy':
            ask('version_not_bound', f'{record_path} does not establish captured starting source; it may use mutable work.',
                'Explain the tested source and diagnostic edits, or replay with a captured source and retained overlays if useful.')
        elif expected_commits and context.get('commit') not in expected_commits:
            ask('different_source_version', f"{record_path} starts from commit {context.get('commit')!r}.",
                'Relate this version to the supplied candidate(s); do not attribute its observations to a different version.')
        if any(entry.get('replaces_source') for entry in context.get('overlays', []) if isinstance(entry, dict)):
            ask('source_overlay', f'{record_path} replaces files from the captured source.',
                'Explain the changes and whether they alter production behavior or only the test apparatus; preserve an unchanged-source reproduction where feasible.')
    if not executions and item.get('method') not in ('source_review', 'blocked'):
        ask('execution_not_linked', 'This item has no linked isolated execution-service record; ordinary-shell evidence may still exist.',
            'If executed, cite the relevant retained command/output and explain its version; otherwise state the source-only or blocked basis. No extra test is mandatory.')
    trace_refs = item.get('trace_files', [])
    if not isinstance(trace_refs, list):
        raise ValueError('trace_files must be a list')
    for ref in trace_refs:
        path = retained_path(root, ref, work_name, raw_name)
        check = {'path': path, **check_file(inside(root, path))}
        traces.append(check)
        if check['status'] != 'consistent_prefix':
            detail = check.get('errors') or check.get('violations', [])[:3]
            ask('trace_inconsistent', f"{path}: {check['status']}; {json.dumps(detail, ensure_ascii=False)}",
                'Determine whether the cause is instrumentation, the external schedule, assumptions or implementation. Correct the evidence or narrow the claim; do not silently correct implementation behavior.')
    return {'trace_files': [entry['path'] for entry in traces], 'trace_checks': traces,
            'execution_records': executions, 'evidence_feedback': feedback,
            'evidence_notes': [entry['observation'] + ' ' + entry['request'] for entry in feedback]}


def report_feedback(root, filename, expected):
    """Read-only advice for the next turn, including repairable delivery errors."""
    observations = []
    try:
        data = json.loads(inside(root, 'work/' + filename).read_text())
        if not isinstance(data, dict) or not isinstance(data.get('issues'), list):
            raise ValueError('Expected an object with an explicit issues list')
        for key, value in expected.items():
            if data.get(key) != value:
                observations.append({'code': 'version_reference', 'observation': f'{key} differs from the supplied version.',
                                     'request': f'Check the source identity and use {key}={value!r} for this report.'})
        for item in data['issues']:
            if not isinstance(item, dict):
                raise ValueError('Each issue must be an object')
            try:
                detail = inspect_item(item, root, expected_commits=tuple(expected.values()))
                observations.extend({'issue_id': item.get('id'), **entry} for entry in detail['evidence_feedback'])
            except (OSError, ValueError) as exc:
                observations.append({'issue_id': item.get('id'), 'code': 'evidence_reference', 'observation': str(exc),
                                     'request': 'Check the retained path and intended evidence. Preserve the original observation and explain anything unavailable.'})
    except (OSError, ValueError) as exc:
        observations.append({'code': 'index_unavailable', 'observation': f'{filename}: {exc}',
                             'request': 'Preserve the report and supply a readable index; an unavailable index does not mean no findings.'})
    return {'scope': 'Concrete record observations, not a quality score or correctness verdict. Address, explain or narrow claims as appropriate.',
            'observations': observations}
