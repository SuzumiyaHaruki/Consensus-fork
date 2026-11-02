"""Check a supplied bounded-delivery, crash-stop event ledger, not consensus correctness.

Usage: python3 tracecheck.py trace.json

Example (integer nanoseconds on ONE controlled or observer monotonic clock):
{"clock":"controlled", "members":["A","B","C"], "fault_limit":1,
 "delivery_bound_ns":100, "end_ns":110, "events":[
   {"at_ns":0, "kind":"send", "id":"tx1", "src":"A", "dst":"B"},
   {"at_ns":10, "kind":"send_complete", "id":"tx1"},
   {"at_ns":110, "kind":"deliver", "id":"tx1"}]}

Allowed clocks: controlled, single_observer. Never merge unsynchronized host clocks.
Events are actual observations, ordered by at_ns; equal-time order is list order.
send means an actual issued attempt, not enqueue; id identifies one transmission
attempt, not a command. send_complete is per recipient, not full-broadcast completion.
deliver may precede a completion callback. Once completed, at least one delivery is
due within delivery_bound_ns unless the recipient crashes by that deadline. A sender
crash does not cancel that obligation. Duplicate deliveries of an issued attempt
are allowed; this does not check payloads. crash has a node field and is permanent.
observe is an uninterpreted annotation (e.g. a decision, timer or client outcome);
its optional node field identifies the subject, not necessarily a running observer.
Other event kinds are rejected. Metadata fields may accompany any event.

end_ns closes only a finite prefix. At exactly a deadline an undelivered send is
pending, since another event at that instant may follow. An incomplete send has no
delivery deadline here. The checker cannot detect omitted or fabricated events,
wrong completion instrumentation, wrong bounds, or an unrecorded process restart.
It does not check processing time, timer priority, quorum rules, client semantics,
production reachability, safety or liveness. A violation may expose an illegal test
schedule OR an implementation/transport defect; do not automatically dismiss it.
Exit 0 means consistent_prefix only; 1 means violations; 2 means invalid_trace.
"""
import argparse
import heapq
import json
from pathlib import Path

MAX_BYTES = 16 * 1024 * 1024
SCOPE = 'Supplied finite event ledger only; no authenticity, completeness, reachability or consensus verdict.'


def integer(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f'{name} must be an integer >= {minimum}')
    return value


def validate(data):
    if not isinstance(data, dict):
        raise ValueError('trace must be an object')
    if data.get('clock') not in ('controlled', 'single_observer'):
        raise ValueError('clock must be controlled or single_observer')
    members = data.get('members')
    if (not isinstance(members, list) or not members
            or any(not isinstance(m, str) or not m.strip() for m in members)
            or len(set(members)) != len(members)):
        raise ValueError('members must contain unique nonempty strings')
    if integer(data.get('fault_limit'), 'fault_limit') > len(members):
        raise ValueError('fault_limit exceeds membership')
    integer(data.get('delivery_bound_ns'), 'delivery_bound_ns', 1)
    end = integer(data.get('end_ns'), 'end_ns')
    events = data.get('events')
    if not isinstance(events, list):
        raise ValueError('events must be a list')
    previous = 0
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            raise ValueError(f'event {index} must be an object')
        at = integer(event.get('at_ns'), f'event {index}.at_ns')
        if not previous <= at <= end:
            raise ValueError(f'event {index} is out of order or beyond end_ns')
        previous = at
        kind = event.get('kind')
        if kind not in ('send', 'send_complete', 'deliver', 'crash', 'observe'):
            raise ValueError(f'event {index} has unsupported kind')
        if kind in ('send', 'send_complete', 'deliver'):
            if not isinstance(event.get('id'), str) or not event['id'].strip():
                raise ValueError(f'event {index} needs a transmission id')
        fields = ('src', 'dst') if kind == 'send' else ('node',) if kind == 'crash' else ()
        if kind == 'observe' and 'node' in event:
            fields = ('node',)
        for field in fields:
            if event.get(field) not in members:
                raise ValueError(f'event {index}.{field} is not a member')


def check_trace(data):
    try:
        validate(data)
    except ValueError as exc:
        return {'status': 'invalid_trace', 'scope': SCOPE, 'errors': [str(exc)]}
    sends, dead, deadlines, violations = {}, set(), [], []

    def fail(code, index, **details):
        violations.append({'code': code, 'event': index, **details})

    def expire(at, index):
        # Strict inequality leaves equal-time delivery/crash events available.
        while deadlines and deadlines[0][0] < at:
            deadline, ident = heapq.heappop(deadlines)
            send = sends[ident]
            if send['delivered'] is None and send['dst'] not in dead:
                fail('delivery_deadline_missed', index, id=ident, deadline_ns=deadline)
                send['missed'] = True

    for index, event in enumerate(data['events']):
        at, kind = event['at_ns'], event['kind']
        expire(at, index)
        if kind == 'observe':
            continue
        if kind == 'crash':
            node = event['node']
            if node in dead:
                fail('repeated_crash', index, node=node)
            dead.add(node)
            if len(dead) > data['fault_limit']:
                fail('fault_limit_exceeded', index, crashes=len(dead))
            continue
        ident = event['id']
        if kind == 'send':
            if ident in sends:
                fail('reused_transmission_id', index, id=ident)
                continue
            if event['src'] in dead:
                fail('send_after_crash', index, id=ident)
            sends[ident] = {**event, 'complete': None, 'delivered': None, 'missed': False}
            continue
        if ident not in sends:
            fail('unknown_transmission', index, id=ident)
            continue
        send = sends[ident]
        if kind == 'send_complete':
            if send['complete'] is not None:
                fail('repeated_completion', index, id=ident)
                continue
            if send['src'] in dead:
                fail('completion_after_crash', index, id=ident)
            send['complete'] = at
            heapq.heappush(deadlines, (at + data['delivery_bound_ns'], ident))
        elif kind == 'deliver':
            if send['dst'] in dead:
                fail('delivery_after_crash', index, id=ident)
            if send['delivered'] is None:
                send['delivered'] = at
    expire(data['end_ns'], len(data['events']))
    pending = []
    for ident, send in sends.items():
        if send['complete'] is None:
            pending.append({'id': ident, 'reason': 'no_completion_recorded',
                            'delivered': send['delivered'] is not None})
        elif send['delivered'] is None and send['dst'] not in dead and not send['missed']:
            pending.append({'id': ident, 'reason': 'delivery_deadline_not_passed',
                            'deadline_ns': send['complete'] + data['delivery_bound_ns']})
    return {'status': 'violations' if violations else 'consistent_prefix', 'scope': SCOPE,
            'events_checked': len(data['events']), 'violations': violations, 'pending': pending}


def check_file(path):
    try:
        with Path(path).open('rb') as stream:
            raw = stream.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError(f'trace exceeds {MAX_BYTES} bytes')
        return check_trace(json.loads(raw))
    except (OSError, ValueError, RecursionError) as exc:
        return {'status': 'invalid_trace', 'scope': SCOPE, 'errors': [str(exc)]}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('trace', type=Path)
    result = check_file(parser.parse_args().trace)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return {'consistent_prefix': 0, 'violations': 1, 'invalid_trace': 2}[result['status']]


if __name__ == '__main__':
    raise SystemExit(main())
