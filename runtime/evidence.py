"""Link retained execution facts and ask concrete follow-up questions; no verdicts."""
import json
import math
import re
from pathlib import Path

from .tracecheck import check_file

CLOSED = {'fixed', 'not_substantiated'}
DISPOSITIONS = CLOSED | {'unresolved', 'needs_specification', 'environment_blocked'}


def require_description(value, name):
    """Accept prose or structured descriptions without a fixed narrative layout."""
    def has_content(part):
        if isinstance(part, str):
            return bool(part.strip())
        if isinstance(part, list):
            return any(has_content(item) for item in part)
        if isinstance(part, dict):
            return any(has_content(item) for item in part.values())
        return isinstance(part, (bool, int)) or isinstance(part, float) and math.isfinite(part)
    if not isinstance(value, (str, list, dict)) or not has_content(value):
        raise ValueError(f'{name} must be nonempty text, a list, or an object containing descriptive content')
    return value


def validate_findings(items):
    if not isinstance(items, list):
        raise ValueError('Finding index needs an explicit issue list, including when empty')
    seen = set()
    for item in items:
        ident = item.get('id') if isinstance(item, dict) else None
        if not isinstance(ident, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}', ident) or ident in seen:
            raise ValueError('Duplicate or invalid finding id')
        seen.add(ident)
        for name in ('summary', 'property', 'assumptions', 'reproduction', 'polarity'):
            require_description(item.get(name), name)
        if not isinstance(item.get('evidence'), list) or not item['evidence']:
            raise ValueError('Evidence must contain retained file references')


def validate_review(data, expected, expected_ids):
    """Delivery structure only; shared by live feedback and handoff import."""
    if not isinstance(data, dict):
        raise ValueError('Review must be an object')
    if any(data.get(key) != value for key, value in expected.items()):
        raise ValueError('Review refers to different before/after candidates')
    require_description(data.get('summary'), 'review summary')
    if not isinstance(data.get('issues'), list):
        raise ValueError('Review needs an issue list')
    seen = set()
    for item in data['issues']:
        if not isinstance(item, dict):
            raise ValueError('Review issue must be an object')
        ident, disposition, method = (item.get(key) for key in ('id', 'disposition', 'method'))
        if not isinstance(ident, str) or not ident.strip() or ident in seen:
            raise ValueError('Duplicate or invalid review id')
        seen.add(ident)
        if not isinstance(disposition, str) or disposition not in DISPOSITIONS:
            raise ValueError('Invalid review disposition')
        for name in ('reason', 'before_observation', 'after_observation'):
            require_description(item.get(name), name)
        if not isinstance(method, str) or method not in {'executed', 'source_review', 'blocked'}:
            raise ValueError('Review method must distinguish execution, source review and blocked work')
        if method == 'blocked' and disposition in CLOSED:
            raise ValueError('A blocked verification cannot close a finding')
        if disposition == 'fixed' and method != 'executed':
            raise ValueError('Closing a fix needs independent execution; otherwise retain unresolved')
        if not isinstance(item.get('evidence'), list) or not item['evidence']:
            raise ValueError('Evidence must contain retained file references')
    if seen != set(expected_ids):
        raise ValueError('Review must cover exactly the supplied issue IDs')
    validate_findings(data.get('new_issues', []))


def require_fix_execution(item, details, after_commit):
    """A receipt establishes that a command finished, never what it proves."""
    if item['disposition'] != 'fixed':
        return
    for entry in details['execution_records']:
        context = entry['source_context']
        if (entry['status'] == 'completed' and isinstance(entry.get('exit_code'), int)
                and (context.get('kind') != 'candidate_copy' or context.get('commit') == after_commit)):
            return
    raise ValueError('fixed needs a linked completed execution from this review of the after version; '
                     'cite executions/<id>/result.json or turns/<turn>/stdout.jsonl#<item_id> for the actual command/output. '
                     'Explain mutable-work source identity; if not checked, retain unresolved or environment_blocked.')


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
    filename, separator, item_id = ref.partition('#')
    parts = Path(filename).parts
    if separator and (len(parts) != 3 or parts[0] != 'turns' or parts[2] != 'stdout.jsonl'
                      or not re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', item_id)):
        raise ValueError('An execution fragment must select one native command item in turns/<turn>/stdout.jsonl')
    if not parts or parts[0] not in {'work', 'executions', 'turns'}:
        raise ValueError('Evidence must be relative to work/, executions/, or turns/')
    relative = Path(work_name, *parts[1:]) if parts[0] == 'work' else Path(raw_name, *parts)
    path = inside(root, relative)
    if not path.is_file():
        raise ValueError(f'Evidence file missing: {ref}')
    return str(relative) + (separator + item_id if separator else '')


def inspect_item(item, root, *, work_name='work', raw_name='.', expected_commits=()):
    """Execution-service receipts and native command events establish tool links.

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
        retained = retained_path(root, ref, work_name, raw_name)
        filename, separator, item_id = ref.partition('#')
        parts = Path(filename).parts
        if len(parts) == 3 and parts[0] == 'turns' and parts[2] == 'stdout.jsonl' and ref not in linked:
            linked.add(ref)
            if not separator:
                ask('command_not_selected', f'{ref} cites a whole turn, not a particular verification command.',
                    'If this supports execution, cite turns/<turn>/stdout.jsonl#<item_id> for the relevant completed command. The full log remains contextual evidence.')
                continue
            log_path = retained.partition('#')[0]
            selected = []
            for line in inside(root, log_path).read_text(errors='replace').splitlines():
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                item_event = event.get('item', {}) if isinstance(event, dict) else {}
                if (isinstance(event, dict) and event.get('type') == 'item.completed' and isinstance(item_event, dict)
                        and item_event.get('id') == item_id and item_event.get('type') == 'command_execution'
                        and isinstance(item_event.get('exit_code'), int)):
                    selected.append({'path': retained, 'execution_id': item_id,
                                       'command': item_event.get('command'), 'status': 'completed',
                                       'exit_code': item_event['exit_code'], 'source_context': {'kind': 'native_shell'},
                                       'inputs': [], 'restore': {}, 'outputs': {'event_log': log_path}})
            if len(selected) != 1:
                raise ValueError(f'Expected one completed native command for {ref}, found {len(selected)}')
            executions.extend(selected)
            continue
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
        restore = {}
        for entry in context.get('overlays', []):
            if isinstance(entry, dict) and isinstance(entry.get('path'), str) and 'retained_path' in entry:
                inside(root / work_name, entry['path'])  # Never advertise an escaping destination.
                restore[entry['path']] = str(Path(raw_name, 'executions', parts[1], entry['retained_path']))
        outputs = {name: str(Path(raw_name, 'executions', parts[1], name + '.txt')) for name in ('stdout', 'stderr')
                   if inside(root, Path(raw_name, 'executions', parts[1], name + '.txt')).is_file()}
        artifacts = record.get('artifacts', {})
        for entry in artifacts.get('files', []):
            output = str(Path(raw_name, 'executions', parts[1], entry['retained_path']))
            if inside(root, output).is_file():
                outputs['artifact:' + entry['path']] = output
            else:
                ask('output_missing', f'Recorded output is missing: {output}', 'Locate the original file or narrow the evidence claim.')
        if artifacts.get('excluded'):
            ask('output_excluded', f'{record_path} reports excluded or missing requested outputs.',
                'Read its artifacts.excluded entries; do not cite these outputs as retained files.')
        executions.append({'path': record_path, 'execution_id': parts[1], 'argv': record.get('argv'),
                           'status': record.get('status'), 'exit_code': record.get('exit_code'),
                           'source_context': context, 'inputs': inputs, 'restore': restore, 'outputs': outputs,
                           'cwd': record.get('cwd'), 'cwd_relative': record.get('cwd_relative'),
                           'timeout_seconds': record.get('timeout_seconds')})
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
        ask('execution_not_linked', 'This item has no linked execution record; ordinary-shell evidence may still exist.',
            'If executed, cite the relevant retained command/output and explain its version; otherwise state the source-only or blocked basis. No extra test is mandatory.')
    if any(entry['source_context'].get('kind') == 'native_shell' for entry in executions):
        ask('version_not_bound', 'Native shell events record commands and outputs, not a captured starting source.',
            'Identify the relevant command event and explain which version and edits it tested. A completed command is not proof of the claim.')
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


def report_feedback(root, filename, expected, expected_ids=None):
    """Read-only advice for the next turn, including repairable delivery errors."""
    observations, delivery_errors = [], []
    try:
        data = json.loads(inside(root, 'work/' + filename).read_text())
        if not isinstance(data, dict) or not isinstance(data.get('issues'), list):
            raise ValueError('Expected an object with an explicit issues list')
        if expected_ids is not None:
            validate_review(data, expected, expected_ids)
            if not inside(root, 'work/report.md').read_text().strip():
                raise ValueError('Review report.md is empty')
        for key, value in expected.items():
            if data.get(key) != value:
                observations.append({'code': 'version_reference', 'observation': f'{key} differs from the supplied version.',
                                     'request': f'Check the source identity and use {key}={value!r} for this report.'})
        for item in data['issues'] + (data.get('new_issues', []) if expected_ids is not None else []):
            if not isinstance(item, dict):
                raise ValueError('Each issue must be an object')
            try:
                detail = inspect_item(item, root, expected_commits=tuple(expected.values()))
                observations.extend({'issue_id': item.get('id'), **entry} for entry in detail['evidence_feedback'])
                if expected_ids is not None and item in data['issues']:
                    require_fix_execution(item, detail, expected['after_commit'])
            except (OSError, ValueError) as exc:
                entry = {'issue_id': item.get('id'), 'code': 'evidence_reference', 'observation': str(exc),
                         'request': 'Check the retained path and intended evidence. Preserve the original observation and explain anything unavailable.'}
                observations.append(entry)
                delivery_errors.append(entry)
    except (OSError, ValueError) as exc:
        entry = {'code': 'index_unavailable', 'observation': f'{filename}: {exc}',
                 'request': 'Complete or correct the report/index; retain uncertainty for unchecked issues. An unavailable index does not mean no findings.'}
        observations.append(entry)
        delivery_errors.append(entry)
    return {'scope': 'Concrete record observations, not a quality score or correctness verdict. Address, explain or narrow claims as appropriate.',
            'observations': observations, 'delivery_errors': delivery_errors}
