"""Retain selected native session metadata and response usage, never prompt/auth contents.

Codex rollout formats vary. Missing records stay missing; cumulative CLI counters
are never added to per-response usage. This module uses only the standard library.
"""
from collections import Counter
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import stat


TOKEN_FIELDS = ('input_tokens', 'cached_input_tokens', 'cache_write_input_tokens',
                'output_tokens', 'reasoning_output_tokens', 'total_tokens')
DELEGATION = {'spawn_agent', 'send_message', 'followup_task', 'wait_agent',
              'close_agent', 'interrupt_agent', 'resume_agent'}


def timestamp(value):
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc)
    except (AttributeError, TypeError, ValueError):
        return None


def identifier(value, *, thread=False):
    pattern = r'[A-Za-z0-9][A-Za-z0-9_-]{0,127}' if thread else r'[A-Za-z0-9_./:-]{1,256}'
    return value if isinstance(value, str) and re.fullmatch(pattern, value) else None


def usage(value):
    if not isinstance(value, dict):
        return None
    result = {k: v for k, v in value.items() if k in TOKEN_FIELDS and type(v) is int and v >= 0}
    if not {'input_tokens', 'output_tokens'} <= result.keys():
        return None
    result.setdefault('total_tokens', result['input_tokens'] + result['output_tokens'])
    return result


def total_usage(values):
    total = {}
    for value in values:
        for key, count in value.items():
            total[key] = total.get(key, 0) + count
    return total or None


def write_record(path, data, secrets=()):
    """Allowlisted data still gets exact-secret and common credential redaction."""
    text = json.dumps(data, ensure_ascii=False)
    for secret in secrets:
        if secret:
            text = text.replace(json.dumps(secret, ensure_ascii=False)[1:-1], '[REDACTED_CREDENTIAL]')
    text = re.sub(r'\b(?:sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9_]{16,})\b', '[REDACTED_CREDENTIAL]', text)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(text + '\n', encoding='utf-8')
    temporary.replace(path)


def native_events(path):
    """Read regular rollout files without following a final symlink or device."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, encoding='utf-8', errors='replace') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            return
        for line in stream:
            try:
                event = json.loads(line)
                if (isinstance(event, dict) and isinstance(event.get('type'), str)
                        and isinstance(event.get('payload'), dict)):
                    yield event
                else:
                    yield {'type': 'invalid_record', 'payload': {}}
            except ValueError:
                yield {'type': 'invalid_record', 'payload': {}}


def session_meta(path):
    stream = native_events(path)
    try:
        event = next(stream, {})
    finally:
        stream.close()
    if event.get('type') != 'session_meta':
        return None
    raw = event['payload']
    source = raw.get('source')
    subagent = source.get('subagent') if isinstance(source, dict) else None
    spawn = subagent.get('thread_spawn', {}) if isinstance(subagent, dict) else {}
    spawn = spawn if isinstance(spawn, dict) else {}
    return {'thread_id': identifier(raw.get('id'), thread=True),
            'session_id': identifier(raw.get('session_id'), thread=True),
            'parent_thread_id': identifier(raw.get('parent_thread_id') or spawn.get('parent_thread_id'), thread=True),
            'agent_path': identifier(raw.get('agent_path') or spawn.get('agent_path')),
            'cli_version': identifier(raw.get('cli_version')), 'created_at': raw.get('timestamp'),
            'cwd': raw.get('cwd'), 'native_file': path.name}


def read_session(path, meta, inherited_turns=()):
    ident = meta['thread_id']
    created = timestamp(meta['created_at'])
    events, responses, turns, calls = [], {}, {}, {}
    expected_children, expected_paths, warnings = set(), set(), []
    tools = Counter()
    counter = None
    last_at = created
    for event in native_events(path):
        raw, kind = event['payload'], event['type']
        at = timestamp(event.get('timestamp'))
        if at and created and at < created:
            continue  # Forked histories contain the parent's older context/lifecycle.
        if kind == 'invalid_record':
            warnings.append('invalid_native_record')
            continue
        if kind in {'turn_context', 'event_msg'} and identifier(raw.get('turn_id')) in inherited_turns:
            continue  # Fork copies can receive a new timestamp while retaining the parent's turn ID.
        row = {'type': kind, 'timestamp': at.isoformat() if at else None}
        if kind == 'token_usage_record':
            if raw.get('thread_id') != ident:
                continue  # Explicit ownership prevents inherited parent usage from being counted.
            response = identifier(raw.get('response_id'))
            counts = usage(raw.get('usage'))
            if not response or counts is None:
                warnings.append('unusable_response_usage')
                continue
            if response in responses:
                if responses[response] != counts:
                    warnings.append('conflicting_response_usage')
                continue
            responses[response] = counts
            counter = usage(raw.get('thread_token_usage')) or counter
            row.update(response_id=response, turn_id=identifier(raw.get('turn_id')), usage=counts)
        elif kind == 'turn_context':
            turn = identifier(raw.get('turn_id'))
            row.update(turn_id=turn, model=identifier(raw.get('model')),
                       reasoning_effort=identifier(raw.get('effort') or raw.get('reasoning_effort')))
            if turn:
                turns.setdefault(turn, {}).update({k: row[k] for k in ('model', 'reasoning_effort')})
        elif kind == 'event_msg' and raw.get('type') in {'task_started', 'task_complete', 'turn_aborted'}:
            turn = identifier(raw.get('turn_id'))
            row.update(type=raw['type'], turn_id=turn)
            if turn:
                state = turns.setdefault(turn, {})
                state['status'] = {'task_started': 'started', 'task_complete': 'completed', 'turn_aborted': 'aborted'}[raw['type']]
                state['started_at' if raw['type'] == 'task_started' else 'ended_at'] = row['timestamp']
                if type(raw.get('duration_ms')) is int and raw['duration_ms'] >= 0:
                    state['duration_ms'] = row['duration_ms'] = raw['duration_ms']
        elif kind == 'response_item':
            operation = (identifier(raw.get('name')) or '').rsplit('.', 1)[-1]
            call = identifier(raw.get('call_id'))
            if raw.get('type') in {'function_call', 'custom_tool_call'}:
                tools[identifier(raw.get('name')) or 'unnamed'] += 1
            if raw.get('type') == 'function_call' and operation in DELEGATION:
                try:
                    args = json.loads(raw.get('arguments', '{}'))
                except (TypeError, ValueError):
                    args = {}
                args = args if isinstance(args, dict) else {}
                details = {k: identifier(args.get(k)) for k in
                           ('task_name', 'target', 'model', 'reasoning_effort', 'fork_turns') if identifier(args.get(k))}
                row.update(type='delegation_call', call_id=call, operation=operation, arguments=details)
                if call:
                    calls[call] = operation
            elif raw.get('type') == 'function_call_output' and call in calls:
                try:
                    result = json.loads(raw.get('output', '{}'))
                except (TypeError, ValueError):
                    result = {}
                result = result if isinstance(result, dict) else {}
                row.update(type='delegation_result', call_id=call, operation=calls[call],
                           result={k: identifier(result.get(k)) for k in ('agent_id', 'task_name') if identifier(result.get(k))})
                if calls[call] == 'spawn_agent':
                    child = identifier(result.get('agent_id'), thread=True)
                    child_path = identifier(result.get('task_name'))
                    if child:
                        expected_children.add(child)
                    if child_path and child_path.startswith('/'):
                        expected_paths.add(child_path)
                    if not child and not child_path and not result.get('error'):
                        warnings.append('spawn_result_without_child_identity')
            else:
                continue
        else:
            continue
        events.append(row)
        if at:
            last_at = max(last_at, at) if last_at else at
    total = total_usage(responses.values())
    if total is None:
        warnings.append('no_per_response_usage')
    elif counter is None or any(total.get(k) != v for k, v in counter.items()):
        warnings.append('response_usage_not_reconciled_with_thread_counter')
    if any(v == 'spawn_agent' for k, v in calls.items()
           if not any(e['type'] == 'delegation_result' and e.get('call_id') == k for e in events)):
        warnings.append('unfinished_spawn_call')
    if any(turn.get('status') in {'started', 'aborted'} for turn in turns.values()):
        warnings.append('unfinished_or_aborted_turn')
    record = {k: v for k, v in meta.items() if k != 'cwd'}
    record.update(observed_until=last_at.isoformat() if last_at else None,
                  observed_span_seconds=(last_at - created).total_seconds() if created and last_at else None,
                  turns=[{'turn_id': k, **v} for k, v in turns.items()], tool_calls=dict(tools),
                  response_count=len(responses), usage=total, warnings=sorted(set(warnings)))
    return record, events, expected_children, expected_paths


def collect(codex_home, root_ids, workspace, started_at, destination, *, secrets=()):
    """Collect just this run's thread family before a private Codex home is removed."""
    destination, codex_home = Path(destination), Path(codex_home)
    roots = {value for value in root_ids if identifier(value, thread=True)}
    result = {'root_thread_ids': sorted(roots), 'agents': [], 'missing_threads': [], 'missing_agent_paths': [],
              'usage': None, 'usage_complete': False,
              'usage_basis': 'unique native (thread_id, response_id) records; cached/reasoning counts are subsets',
              'warnings': []}
    try:
        start = timestamp(started_at)
        if not start:
            raise ValueError('missing stage start')
        end = datetime.now(timezone.utc)
        sessions = codex_home / 'sessions'
        found = {}
        # Directory dates may use the host's local zone while record timestamps use UTC.
        day = start.date() - timedelta(days=1)
        while roots and day <= end.date() + timedelta(days=1):
            directory = sessions / day.strftime('%Y/%m/%d')
            if directory.is_dir() and not any(p.is_symlink() for p in (directory, directory.parent, directory.parent.parent, sessions)):
                for path in directory.glob('*.jsonl'):
                    try:
                        meta = session_meta(path)
                    except (OSError, ValueError):
                        continue
                    created = timestamp(meta.get('created_at')) if meta else None
                    if meta and meta['thread_id'] and created and start <= created <= end:
                        found[meta['thread_id']] = (path, meta)
            day += timedelta(days=1)
        selected = {k for k in roots & found.keys() if found[k][1]['cwd'] == str(Path(workspace).resolve())}
        while True:
            added = {k for k, (_, meta) in found.items() if meta['parent_thread_id'] in selected}
            if added <= selected:
                break
            selected.update(added)
        expected, paths, ancestor_turns = set(roots), set(), {}
        remaining = set(selected)
        ordered = []
        while remaining:
            ready = sorted(k for k in remaining if found[k][1]['parent_thread_id'] not in remaining)
            if not ready:
                result['warnings'].append('cyclic_thread_parent_records')
                break
            ordered.extend(ready)
            remaining.difference_update(ready)
        for ident in ordered:
            path, meta = found[ident]
            try:
                inherited = ancestor_turns.get(meta['parent_thread_id'], set())
                record, events, children, child_paths = read_session(path, meta, inherited)
                ancestor_turns[ident] = inherited | {t['turn_id'] for t in record['turns']}
            except (OSError, ValueError, TypeError) as exc:
                result['warnings'].append(f'{ident}: {type(exc).__name__} reading native records')
                continue
            expected.update(children)
            paths.update(child_paths)
            # Metadata and event allowlists intentionally omit messages, instructions and account IDs.
            relative = f'agent-records/{ident}.json'
            write_record(destination / relative, {'agent': record, 'events': events}, secrets)
            record['record'] = relative
            result['agents'].append(record)
        retained = {r['thread_id'] for r in result['agents']}
        result['missing_threads'] = sorted(expected - retained)
        result['missing_agent_paths'] = sorted(paths - {r['agent_path'] for r in result['agents']})
        result['usage'] = total_usage(r['usage'] for r in result['agents'] if r['usage'] is not None)
        result['usage_complete'] = bool(roots) and not (result['missing_threads'] or result['missing_agent_paths'] or
            result['warnings'] or any(r['warnings'] for r in result['agents']))
        if not roots:
            result['warnings'].append('no_native_root_thread_observed')
    except (OSError, ValueError, TypeError) as exc:
        result['warnings'].append(f'{type(exc).__name__} collecting native session records')
    write_record(destination / 'agents.json', result, secrets)
    return {'record': 'agents.json', 'thread_count': len(result['agents']),
            'usage': result['usage'], 'usage_complete': result['usage_complete'],
            'missing_threads': result['missing_threads'], 'warnings': result['warnings']}
