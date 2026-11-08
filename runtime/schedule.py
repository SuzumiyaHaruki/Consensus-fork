"""Execute a bounded event schedule against a caller-supplied adapter.

Run INSIDE isolated_exec, not as a host-side service. The adapter is an ordinary
executable speaking one JSON response per JSON request on stdin/stdout; stderr
is reserved for diagnostics. It must call the candidate, not implement consensus.

  python3 -I PATH/schedule.py --plan tests/scenario.json -- ./tests/adapter
  python3 -I PATH/schedule.py --replay tests/previous.jsonl -- ./tests/adapter

The first request is {"op":"init","setup":PLAN.setup}. Every response supplies
now_ns (monotonic integer), pending (enabled actions), and optional incremental
events/observations. Init also supplies scope: what code runs and what is bypassed.
Pending entries have unique string id, actions:[string,...], and arbitrary JSON
metadata for selection. Events must be actual observations, not planned actions.
Events and extra adapter fields are retained without a protocol-specific timing
verdict. This helper does not validate the supplied protocol assumptions.

Plan steps:
  {"do":"submit","args":{"node":"A","command":{...}}}
  {"do":"deliver","select":{"src":"A","dst":"B","command":"x"}}
  {"expect":{"observations":{"executed":{"B":1}}}}
  {"drive":{"choices":[{"do":"deliver","select":{}}, ...],
            "until":{"observations":{"done":true}},"limit":100}}

select matches a recursive JSON subset, with exact list/scalar matching. An
explicit selection must match exactly one enabled event. drive selects the first
matching event in adapter order from the first matching choice; this is an
explicit scheduling policy, not a fairness guarantee. No match, ambiguity, an
unmet expectation and adapter errors have distinct statuses. No action is invented
to satisfy an expectation. Drive is bounded and never silently advances time.

stdout is a flushed JSONL record of the plan, requests, responses and summary;
isolated_exec retains it even when a private source copy is removed. --replay
requires a complete previous record and compares exact requests/responses and
terminal status. Use --plan again for cross-version semantic scenarios; changed
tokens/order may legitimately prevent strict replay. Retain plans, adapter source
and checker source as overlays; the execution service associates candidate Git
versions. This tool neither authenticates adapter observations nor judges bugs.
Exit 0: completed schedule; 1: observation/selection/limit/divergence; 2: tool or
adapter failure. An expectation is caller-selected and may describe a defect.
"""
import argparse
import asyncio
import json
import math
import os
from pathlib import Path
import signal
import time

MAX_LINE = 4 * 1024 * 1024
MAX_INPUT = 64 * 1024 * 1024
REPLAYABLE = {'completed', 'expectation_failed', 'not_reached', 'ambiguous', 'step_limit'}


class Stop(Exception):
    def __init__(self, status, reason):
        self.status, self.reason = status, reason
        super().__init__(reason)


def decode(text):
    def invalid(value):
        raise ValueError('Non-finite JSON number: ' + value)
    def number(value):
        parsed = float(value)
        return parsed if math.isfinite(parsed) else invalid(value)
    return json.loads(text, parse_constant=invalid, parse_float=number)


def subset(expected, actual):
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(k in actual and subset(v, actual[k]) for k, v in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(expected) == len(actual) and all(subset(a, b) and subset(b, a) for a, b in zip(expected, actual))
    return type(expected) is type(actual) and expected == actual


def equal(left, right):
    return subset(left, right) and subset(right, left)


def action(step):
    if not isinstance(step, dict) or not isinstance(step.get('do'), str) or not step['do']:
        raise ValueError('Action needs a nonempty do string')
    if not isinstance(step.get('args', {}), dict) or set(step.get('args', {})) & {'op', 'id'}:
        raise ValueError('args must be an object without reserved op/id fields')
    if 'select' in step and not isinstance(step['select'], dict):
        raise ValueError('select must be an object')


def validate(plan):
    if not isinstance(plan, dict) or not isinstance(plan.get('steps'), list) or not isinstance(plan.get('setup', {}), dict):
        raise ValueError('Plan needs steps list and optional setup object')
    for step in plan['steps']:
        if not isinstance(step, dict) or len(set(step) & {'do', 'expect', 'drive'}) != 1:
            raise ValueError('Each step needs exactly one of do, expect, drive')
        if 'do' in step:
            action(step)
        elif 'expect' in step:
            if not isinstance(step['expect'], dict) or not step['expect']:
                raise ValueError('expect must be a nonempty object')
        else:
            drive = step['drive']
            if (not isinstance(drive, dict) or type(drive.get('limit')) is not int or drive['limit'] <= 0
                    or not isinstance(drive.get('until'), dict) or not drive['until']
                    or not isinstance(drive.get('choices'), list) or not drive['choices']):
                raise ValueError('drive needs positive limit, nonempty until object and choices list')
            for choice in drive['choices']:
                action(choice)
                if 'select' not in choice:
                    raise ValueError('drive choices must select actual pending events')


def select(step, frame, first=False):
    if 'select' not in step:
        return None
    matches = [p for p in frame['pending'] if step['do'] in p['actions'] and subset(step['select'], p)]
    if not matches:
        if first:
            return None
        raise Stop('not_reached', 'No enabled event matches ' + json.dumps(step))
    if len(matches) > 1 and not first:
        raise Stop('ambiguous', 'Multiple enabled events match ' + json.dumps(step))
    return matches[0]


def validate_frame(frame, previous_time):
    if not isinstance(frame, dict):
        raise ValueError('Adapter response must be an object')
    if frame.get('error'):
        raise ValueError('Adapter reported: ' + str(frame['error']))
    now, pending = frame.get('now_ns'), frame.get('pending')
    if type(now) is not int or now < previous_time or not isinstance(pending, list):
        raise ValueError('Response needs monotonic now_ns and pending list')
    seen = set()
    for item in pending:
        if (not isinstance(item, dict) or not isinstance(item.get('id'), str) or not item['id']
                or item['id'] in seen or not isinstance(item.get('actions'), list)
                or not item['actions'] or not all(isinstance(a, str) and a for a in item['actions'])):
            raise ValueError('Pending events need unique IDs and nonempty actions')
        seen.add(item['id'])
    if not isinstance(frame.get('events', []), list):
        raise ValueError('events must be a list of incremental observations')


def read_input(path):
    with Path(path).open('rb') as stream:
        data = stream.read(MAX_INPUT + 1)
    if len(data) > MAX_INPUT:
        raise ValueError('Input exceeds 64 MiB')
    return data


def read_replay(path):
    rows = [decode(line) for line in read_input(path).splitlines() if line.strip()]
    if (len(rows) < 4 or not all(isinstance(row, dict) for row in rows)
            or rows[0].get('kind') != 'schedule' or rows[-1].get('kind') != 'summary'
            or rows[-1].get('status') not in REPLAYABLE or (len(rows) - 2) % 2):
        raise ValueError('Replay needs a complete schedule record with a reproducible terminal status')
    exchanges = []
    for index in range(1, len(rows) - 1, 2):
        request, response = rows[index:index + 2]
        number = len(exchanges)
        if (request.get('kind') != 'request' or response.get('kind') != 'response'
                or request.get('index') != number or response.get('index') != number
                or 'request' not in request or 'response' not in response):
            raise ValueError('Incomplete or out-of-order replay exchange')
        exchanges.append((request['request'], response['response']))
    return rows[0]['plan'], exchanges, rows[-1]['status']


async def run(plan, argv, timeout, emit, replay=None):
    validate(plan)
    deadline = time.monotonic() + timeout
    emit({'kind': 'schedule', 'plan': plan, 'adapter_argv': argv, 'strict_replay': replay is not None})
    process, count, frame = None, 0, {'now_ns': 0, 'pending': []}
    step_index, status, reason = -1, 'completed', None

    async def exchange(request, selected=None):
        nonlocal count, frame
        emit({'kind': 'request', 'index': count, 'step': step_index, 'request': request, 'selected': selected})
        if replay and (count >= len(replay[0]) or not equal(request, replay[0][count][0])):
            raise Stop('replay_diverged', f'Request {count} differs from recorded execution')
        data = (json.dumps(request, allow_nan=False) + '\n').encode()
        if len(data) > MAX_LINE:
            raise ValueError('Adapter request exceeds 4 MiB')
        async def communicate():
            process.stdin.write(data)
            await process.stdin.drain()
            return await process.stdout.readline()
        raw = await asyncio.wait_for(communicate(), max(0, deadline - time.monotonic()))
        if not raw:
            raise ValueError('Adapter exited without a response')
        try:
            response = decode(raw)
        except ValueError as exc:
            emit({'kind': 'adapter_output', 'index': count, 'text': raw.decode(errors='replace')})
            raise ValueError('Adapter stdout must contain JSON responses only') from exc
        emit({'kind': 'response', 'index': count, 'response': response})
        validate_frame(response, frame['now_ns'])
        if count == 0:
            if not isinstance(response.get('scope'), str) or not response['scope'].strip():
                raise ValueError('Init must state the exercised implementation and its limits in scope')
        frame = response
        if replay and not equal(response, replay[0][count][1]):
            raise Stop('replay_diverged', f'Response {count} differs from recorded execution')
        count += 1

    async def perform(step, selected=None):
        request = {'op': step['do'], **step.get('args', {})}
        if selected is not None:
            request['id'] = selected['id']
        await exchange(request, selected)

    try:
        process = await asyncio.create_subprocess_exec(*argv, stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE, stderr=None, limit=MAX_LINE, start_new_session=True)
        await exchange({'op': 'init', 'setup': plan.get('setup', {})})
        for step_index, step in enumerate(plan['steps']):
            if 'expect' in step:
                if not subset(step['expect'], frame):
                    raise Stop('expectation_failed', 'Observation does not match ' + json.dumps(step['expect']))
            elif 'do' in step:
                await perform(step, select(step, frame))
            else:
                drive = step['drive']
                for _ in range(drive['limit']):
                    if subset(drive['until'], frame):
                        break
                    for choice in drive['choices']:
                        selected = select(choice, frame, first=True)
                        if selected is not None:
                            await perform(choice, selected)
                            break
                    else:
                        raise Stop('not_reached', 'Drive condition unmet with no matching enabled action')
                if not subset(drive['until'], frame):
                    raise Stop('step_limit', 'Drive exhausted its action limit')
    except Stop as exc:
        status, reason = exc.status, exc.reason
    except asyncio.TimeoutError:
        status, reason = 'timed_out', 'Adapter response exceeded the schedule wall-time budget'
    except asyncio.CancelledError:
        status, reason = 'interrupted', 'Schedule interrupted; partial observations retained'
    except (OSError, ValueError, RecursionError) as exc:
        status, reason = 'adapter_error', str(exc)
    finally:
        if process:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            # Drain/close pipes as well as reaping: a bad adapter can leave a
            # paused stdout reader even after SIGKILL. Cleanup is bounded too.
            async def reap():
                process.stdin.close()
                # Do not rely on an exit waiter being notified after pipe closure
                # on every supported Python patch version. The child watcher
                # reaps the process and publishes returncode independently.
                while process.returncode is None:
                    await asyncio.sleep(.01)
                await process.communicate()
            try:
                await asyncio.wait_for(reap(), 2.0)
            except asyncio.TimeoutError:
                status, reason = 'adapter_error', 'Adapter cleanup did not finish within two seconds'
    if replay and status in REPLAYABLE and (count != len(replay[0]) or status != replay[1]):
        status, reason = 'replay_diverged', 'Exchange count or terminal status differs from recorded execution'
    result = {'kind': 'summary', 'status': status, 'reason': reason, 'step': step_index, 'exchanges': count,
              'replay_match': None if replay is None else status == replay[1] and count == len(replay[0]),
              'scope': 'Adapter-reported execution only; schedule completion is not a consensus verdict.'}
    emit(result)
    return result


async def interruptible_run(*args):
    loop, task = asyncio.get_running_loop(), asyncio.current_task()
    loop.add_signal_handler(signal.SIGTERM, task.cancel)
    try:
        return await run(*args)
    finally:
        loop.remove_signal_handler(signal.SIGTERM)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--plan', type=Path)
    source.add_argument('--replay', type=Path)
    parser.add_argument('--timeout', type=float, default=30.0)
    parser.add_argument('adapter', nargs=argparse.REMAINDER, help='-- executable [arguments]; no shell')
    args = parser.parse_args()
    emit = lambda record: print(json.dumps(record, ensure_ascii=False, allow_nan=False), flush=True)
    try:
        argv = args.adapter[1:] if args.adapter[:1] == ['--'] else args.adapter
        if not argv or not math.isfinite(args.timeout) or args.timeout <= 0:
            raise ValueError('An adapter command and positive finite timeout are required')
        replay = None
        if args.replay:
            plan, exchanges, terminal = read_replay(args.replay)
            replay = exchanges, terminal
        else:
            plan = decode(read_input(args.plan))
        result = asyncio.run(interruptible_run(plan, argv, args.timeout, emit, replay))
    except (OSError, ValueError, KeyError, RecursionError) as exc:
        emit({'kind': 'summary', 'status': 'invalid_input', 'reason': str(exc)})
        return 2
    return 0 if result['status'] == 'completed' else 1 if result['status'] in REPLAYABLE | {'replay_diverged'} else 2


if __name__ == '__main__':
    raise SystemExit(main())
