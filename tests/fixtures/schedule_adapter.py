"""Small queue fixture for runner tests; deliberately contains no consensus."""
import json
import os
import sys
import time

now, pending, delivered = 0, [], []
for line in sys.stdin:
    request = json.loads(line)
    op = request['op']
    events = []
    if op == 'init':
        setup = request['setup']
        if setup.get('pid_file'):
            with open(setup['pid_file'], 'w') as stream:
                stream.write(str(os.getpid()))
        if setup.get('hang'):
            time.sleep(20)
        pending = setup.get('pending', [])
    elif op == 'deliver':
        selected = next(p for p in pending if p['id'] == request['id'])
        pending.remove(selected)
        delivered.append(selected['id'])
        events = [{'kind': 'deliver', 'at_ns': now, 'id': selected['id']}]
    elif op == 'advance':
        now = request['now_ns']
    elif op == 'record':
        events = request['events']
        now = request['now_ns']
    elif op == 'bad_json':
        print('ordinary stdout is not a response', flush=True)
        continue
    elif op == 'fail':
        print(json.dumps({'error': 'candidate rejected action'}), flush=True)
        continue
    elif op == 'exit':
        sys.exit(0)
    frame = {'now_ns': now, 'pending': pending, 'events': events,
             'observations': {'delivered': delivered, 'marker': sys.argv[1:]}}
    if op == 'init':
        frame['scope'] = 'Fixture queue, not a protocol implementation'
        if 'trace_model' in setup:
            frame['trace_model'] = setup['trace_model']
    print(json.dumps(frame), flush=True)
