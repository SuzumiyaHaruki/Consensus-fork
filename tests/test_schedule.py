import asyncio
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

from runtime import schedule

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = [sys.executable, '-I', str(ROOT / 'tests/fixtures/schedule_adapter.py')]


class ScheduleTests(unittest.TestCase):
    def exercise(self, steps=(), setup=None, replay=None, argv=ADAPTER, timeout=3):
        records = []
        result = asyncio.run(schedule.run({'setup': setup or {}, 'steps': list(steps)}, argv, timeout, records.append, replay))
        return result, records

    def transcript(self, records):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'record.jsonl'
            path.write_text(''.join(json.dumps(row) + '\n' for row in records))
            return schedule.read_replay(path)

    def pending(self):
        return [{'id': 'a:1', 'actions': ['deliver'], 'dst': 'b'},
                {'id': 'a:2', 'actions': ['deliver'], 'dst': 'c'}]

    def test_selects_actual_event_and_strictly_replays(self):
        steps = [{'do': 'deliver', 'select': {'dst': 'b'}},
                 {'expect': {'observations': {'delivered': ['a:1']}}}]
        result, rows = self.exercise(steps, {'pending': self.pending()})
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(rows[3]['request'], {'op': 'deliver', 'id': 'a:1'})
        plan, exchanges, terminal = self.transcript(rows)
        result, _ = self.exercise(plan['steps'], plan['setup'], (exchanges, terminal))
        self.assertTrue(result['replay_match'])

    def test_unreachable_ambiguous_and_failed_expectation_are_distinct(self):
        for step, status in [({'do': 'deliver', 'select': {'dst': 'absent'}}, 'not_reached'),
                             ({'do': 'deliver', 'select': {}}, 'ambiguous'),
                             ({'expect': {'observations': {'delivered': ['a:1']}}}, 'expectation_failed')]:
            with self.subTest(status=status):
                result, rows = self.exercise([step], {'pending': self.pending()})
                self.assertEqual(result['status'], status)
                self.assertEqual(result['exchanges'], 1)  # No action fabricated after init.
                plan, exchanges, terminal = self.transcript(rows)
                replay, _ = self.exercise(plan['steps'], plan['setup'], (exchanges, terminal))
                self.assertEqual(replay['status'], status)
                self.assertTrue(replay['replay_match'])

    def test_drive_is_bounded_and_respects_choice_order(self):
        step = {'drive': {'choices': [{'do': 'deliver', 'select': {'dst': 'c'}},
                                      {'do': 'deliver', 'select': {}}],
                          'until': {'pending': []}, 'limit': 1}}
        result, rows = self.exercise([step], {'pending': self.pending()})
        self.assertEqual(result['status'], 'step_limit')
        self.assertEqual(rows[3]['request']['id'], 'a:2')
        step['drive']['limit'] = 2
        result, rows = self.exercise([step], {'pending': self.pending()})
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(rows[-2]['response']['observations']['delivered'], ['a:2', 'a:1'])
        step['drive']['until'] = {'now_ns': 10}
        result, rows = self.exercise([step], {})
        self.assertEqual(result['status'], 'not_reached')
        self.assertEqual(result['exchanges'], 1)  # No implicit clock advance.

    def test_replay_checks_responses_and_does_not_run_recorded_argv(self):
        _, rows = self.exercise()
        rows[0]['adapter_argv'] = ['/path/never/to/execute']
        plan, exchanges, terminal = self.transcript(rows)
        result, _ = self.exercise(replay=(exchanges, terminal))
        self.assertTrue(result['replay_match'])
        result, rows = self.exercise(replay=(exchanges, terminal), argv=ADAPTER + ['different'])
        self.assertEqual(result['status'], 'replay_diverged')
        self.assertFalse(result['replay_match'])
        self.assertEqual(rows[-2]['response']['observations']['marker'], ['different'])

    def test_incomplete_record_is_not_replayable(self):
        _, rows = self.exercise()
        for broken in (rows[:-1], rows[:1] + rows[2:], rows + [rows[-1]]):
            with self.assertRaises(ValueError):
                self.transcript(broken)

    def test_invalid_output_candidate_error_and_clock_regression(self):
        for steps in ([{'do': 'bad_json'}], [{'do': 'fail'}], [{'do': 'exit'}],
                      [{'do': 'advance', 'args': {'now_ns': 5}}, {'do': 'advance', 'args': {'now_ns': 4}}]):
            with self.subTest(steps=steps):
                result, rows = self.exercise(steps)
                self.assertEqual(result['status'], 'adapter_error')
                self.assertTrue(result['reason'])
                self.assertEqual(rows[-1], result)

    def test_timeout_reaps_adapter_and_retains_partial_record(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'pid'
            result, rows = self.exercise(setup={'hang': True, 'pid_file': str(path)}, timeout=.3)
            self.assertEqual(result['status'], 'timed_out')
            self.assertEqual(rows[1]['request']['op'], 'init')
            self.assertTrue(path.exists())
            with self.assertRaises(ProcessLookupError):
                os.kill(int(path.read_text()), 0)

    def test_schedule_retains_events_without_applying_old_delivery_bounds(self):
        setup = {'trace_model': {'clock': 'controlled', 'members': ['a', 'b', 'c'],
                                'fault_limit': 1, 'delivery_bound_ns': 10}}
        events = [{'kind': 'send', 'at_ns': 0, 'id': 'a:1', 'src': 'a', 'dst': 'b'},
                  {'kind': 'send_complete', 'at_ns': 0, 'id': 'a:1'},
                  {'kind': 'crash', 'at_ns': 1, 'node': 'a'}]
        result, rows = self.exercise([{'do': 'record', 'args': {'now_ns': 11, 'events': events}}], setup)
        self.assertEqual(result['status'], 'completed')
        self.assertNotIn('trace_check', result)
        self.assertEqual(rows[-2]['response']['events'], events)

    def test_sigterm_preserves_partial_record_and_stops_adapter(self):
        with tempfile.TemporaryDirectory() as temp:
            pid_file, plan = Path(temp) / 'pid', Path(temp) / 'plan.json'
            plan.write_text(json.dumps({'setup': {'hang': True, 'pid_file': str(pid_file)}, 'steps': []}))
            process = subprocess.Popen([sys.executable, '-I', str(ROOT / 'runtime/schedule.py'),
                                        '--plan', str(plan), '--', *ADAPTER], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                deadline = time.monotonic() + 3
                while not pid_file.exists() and time.monotonic() < deadline:
                    time.sleep(.01)
                self.assertTrue(pid_file.exists())
                process.send_signal(signal.SIGTERM)
                output, errors = process.communicate(timeout=4)
                self.assertEqual(process.returncode, 2, errors)
                rows = [json.loads(line) for line in output.splitlines()]
                self.assertEqual(rows[1]['request']['op'], 'init')
                self.assertEqual(rows[-1]['status'], 'interrupted')
                with self.assertRaises(ProcessLookupError):
                    os.kill(int(pid_file.read_text()), 0)
            finally:
                if process.poll() is None:
                    process.kill()
                process.communicate()

    def test_json_types_and_plan_validation(self):
        self.assertFalse(schedule.subset({'a': [True]}, {'a': [1]}))
        for raw in ('NaN', 'Infinity', '1e999'):
            with self.assertRaises(ValueError):
                schedule.decode(raw)
        for step in ({'do': 'x', 'args': {'op': 'override'}},
                     {'drive': {'choices': [{'do': 'advance'}], 'until': {'now_ns': 1}, 'limit': 1}}):
            with self.assertRaises(ValueError):
                schedule.validate({'steps': [step]})

    def test_cli_runs_with_isolated_python_and_exit_codes_are_not_bug_verdicts(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'plan.json'
            path.write_text(json.dumps({'steps': [{'expect': {'now_ns': 1}}]}))
            run = subprocess.run([sys.executable, '-I', str(ROOT / 'runtime/schedule.py'),
                                  '--plan', str(path), '--', *ADAPTER], capture_output=True, text=True, timeout=5)
            self.assertEqual(run.returncode, 1, run.stderr)
            self.assertEqual(json.loads(run.stdout.splitlines()[-1])['status'], 'expectation_failed')


if __name__ == '__main__':
    unittest.main()
