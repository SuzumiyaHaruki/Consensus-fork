"""Check the ledger helper's bounded claims, including boundary counterexamples."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from runtime.tracecheck import check_trace, check_file


def event(at, kind, **fields):
    return {'at_ns': at, 'kind': kind, **fields}


def ledger(events, end=201, **fields):
    return {'clock': 'controlled', 'members': ['A', 'B', 'C'], 'fault_limit': 1,
            'delivery_bound_ns': 100, 'end_ns': end, 'events': events, **fields}


class TraceTests(unittest.TestCase):
    def codes(self, events, end=201):
        result = check_trace(ledger(events, end))
        self.assertEqual(result['status'], 'violations')
        return {v['code'] for v in result['violations']}

    def test_completion_not_enqueue_or_send_start_controls_deadline(self):
        events = [event(0, 'observe', name='enqueue_broadcast'),
                  event(0, 'send', id='ab', src='A', dst='B'),
                  event(0, 'send_complete', id='ab'),
                  event(0, 'send', id='ac', src='A', dst='C'),
                  event(50, 'send_complete', id='ac'),
                  event(100, 'deliver', id='ab'),
                  event(100, 'send', id='ba', src='B', dst='A'),
                  event(100, 'send_complete', id='ba'),
                  event(100, 'deliver', id='ba'),
                  event(150, 'deliver', id='ac'),
                  event(150, 'send', id='ca', src='C', dst='A'),
                  event(150, 'send_complete', id='ca'),
                  event(200, 'observe', node='A', name='incorrectly_declares_C_dead'),
                  event(230, 'deliver', id='ca')]
        result = check_trace(ledger(events, 250))
        self.assertEqual(result['status'], 'consistent_prefix')
        self.assertEqual(result['pending'], [])
        # Observed decisions are deliberately not interpreted as protocol/crash truth.
        self.assertIn('no authenticity', result['scope'])

    def test_sender_crash_cannot_cancel_completed_send(self):
        events = [event(0, 'send', id='x', src='A', dst='B'),
                  event(0, 'send_complete', id='x'), event(1, 'crash', node='A')]
        self.assertIn('delivery_deadline_missed', self.codes(events, 101))
        self.assertEqual(check_trace(ledger(events + [event(100, 'deliver', id='x')]))['status'],
                         'consistent_prefix')

    def test_receiver_crash_by_deadline_but_not_later_relieves_delivery(self):
        start = [event(0, 'send', id='x', src='A', dst='B'), event(0, 'send_complete', id='x')]
        for at in (1, 100):
            self.assertEqual(check_trace(ledger(start + [event(at, 'crash', node='B')]))['status'],
                             'consistent_prefix')
        self.assertIn('delivery_deadline_missed', self.codes(start + [event(101, 'crash', node='B')]))

    def test_partial_broadcast_early_and_duplicate_delivery(self):
        events = [event(0, 'send', id='ab', src='A', dst='B'),
                  event(1, 'deliver', id='ab'), event(2, 'send_complete', id='ab'),
                  event(3, 'send', id='ac', src='A', dst='C'), event(4, 'crash', node='A'),
                  event(5, 'deliver', id='ac'), event(200, 'deliver', id='ab')]
        result = check_trace(ledger(events))
        self.assertEqual(result['status'], 'consistent_prefix')
        self.assertEqual(result['pending'], [{'id': 'ac', 'reason': 'no_completion_recorded', 'delivered': True}])

    def test_exact_deadline_is_pending_until_time_advances(self):
        events = [event(0, 'send', id='x', src='A', dst='B'), event(0, 'send_complete', id='x')]
        result = check_trace(ledger(events, 100))
        self.assertEqual(result['status'], 'consistent_prefix')
        self.assertEqual(result['pending'][0]['deadline_ns'], 100)
        self.assertEqual(check_trace(ledger(events + [event(100, 'deliver', id='x')], 100))['pending'], [])
        self.assertIn('delivery_deadline_missed', self.codes(events + [event(101, 'deliver', id='x')]))

    def test_impossible_events_and_fault_budget(self):
        events = [event(0, 'deliver', id='unknown'), event(1, 'crash', node='A'),
                  event(2, 'send', id='x', src='A', dst='B'), event(3, 'send_complete', id='x'),
                  event(4, 'send_complete', id='x'), event(5, 'send', id='x', src='C', dst='B'),
                  event(6, 'crash', node='A'), event(7, 'crash', node='B'), event(8, 'deliver', id='x')]
        self.assertEqual(self.codes(events), {'unknown_transmission', 'send_after_crash', 'completion_after_crash',
                                             'repeated_completion', 'reused_transmission_id', 'repeated_crash',
                                             'fault_limit_exceeded', 'delivery_after_crash'})

    def test_crash_and_delivery_at_same_time_preserve_recorded_order(self):
        start = [event(0, 'send', id='x', src='A', dst='B'), event(0, 'send_complete', id='x')]
        deliver, crash = event(100, 'deliver', id='x'), event(100, 'crash', node='B')
        self.assertEqual(check_trace(ledger(start + [deliver, crash]))['status'], 'consistent_prefix')
        self.assertIn('delivery_after_crash', self.codes(start + [crash, deliver]))

    def test_bad_schema_clock_restart_or_time_is_invalid(self):
        values = [None, [], ledger([], clock='wall'), ledger([], fault_limit=True),
                  ledger([], members=['A', 'A']), ledger([], members=[{}]),
                  ledger([], delivery_bound_ns=0), ledger([], end=float('nan')),
                  ledger([event(True, 'observe')]), ledger([event(1, 'restart', node='A')]),
                  ledger([event(2, 'observe'), event(1, 'observe')]), ledger([event(202, 'observe')]),
                  ledger([event(0, 'send', id='x', src='A', dst='unknown')]), ledger([{}])]
        for value in values:
            with self.subTest(value=value):
                original = copy.deepcopy(value)
                self.assertEqual(check_trace(value)['status'], 'invalid_trace')
                self.assertEqual(repr(value), repr(original))

    def test_file_and_cli_errors_and_size_limit(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'trace.json'
            helper = Path(__file__).resolve().parents[1] / 'runtime/tracecheck.py'
            for content, status, code in [('[]', 'invalid_trace', 2), ('{bad', 'invalid_trace', 2),
                                           (json.dumps(ledger([])), 'consistent_prefix', 0),
                                           (json.dumps(ledger([event(0, 'deliver', id='missing')])), 'violations', 1)]:
                path.write_text(content)
                completed = subprocess.run([sys.executable, str(helper), str(path)], capture_output=True, text=True)
                self.assertEqual(completed.returncode, code)
                self.assertEqual(json.loads(completed.stdout)['status'], status)
            with patch('runtime.tracecheck.MAX_BYTES', 2):
                self.assertEqual(check_file(path)['status'], 'invalid_trace')
            self.assertEqual(check_file(path.with_name('missing'))['status'], 'invalid_trace')


if __name__ == '__main__':
    unittest.main()
