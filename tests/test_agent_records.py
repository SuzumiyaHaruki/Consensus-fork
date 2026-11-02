"""Offline native-session fixtures: ownership, partial usage, privacy and cleanup."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest

from runtime.agent_records import collect


class AgentRecordsTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.home, self.work, self.out = (self.root / name for name in ('codex', 'work', 'out'))
        self.base = datetime.now(timezone.utc) - timedelta(minutes=10)

    def at(self, seconds=0):
        return (self.base + timedelta(seconds=seconds)).isoformat()

    def event(self, kind, payload, seconds=2):
        return {'type': kind, 'timestamp': self.at(seconds), 'payload': payload}

    def tokens(self, thread, response, count, total, turn=None):
        def counts(value):
            return {'input_tokens': value, 'cached_input_tokens': value // 2,
                    'output_tokens': value, 'reasoning_output_tokens': value // 2,
                    'total_tokens': value * 2}
        return self.event('token_usage_record', {'thread_id': thread, 'response_id': response,
            'turn_id': turn or thread + '-turn', 'usage': counts(count), 'thread_token_usage': counts(total)})

    def session(self, ident, events, parent=None, agent_path=None, cwd=None):
        path = self.home / 'sessions' / self.base.strftime('%Y/%m/%d') / f'{ident}.jsonl'
        path.parent.mkdir(parents=True, exist_ok=True)
        meta = self.event('session_meta', {'id': ident, 'session_id': 'root',
            'parent_thread_id': parent, 'agent_path': agent_path, 'timestamp': self.at(),
            'cwd': str(cwd or self.work), 'cli_version': 'fixture',
            'base_instructions': 'PRIVATE_INSTRUCTIONS', 'account_id': 'PRIVATE_ACCOUNT'}, 0)
        path.write_text(''.join(json.dumps(row) + '\n' for row in [meta, *events]))
        return path

    def run_collect(self, **kwargs):
        result = collect(self.home, ['root'], self.work, self.at(-1), self.out, **kwargs)
        return result, json.loads((self.out / 'agents.json').read_text())

    def test_descendants_resume_and_fork_history_are_counted_once_without_messages(self):
        context = self.event('turn_context', {'turn_id': 'root-turn', 'model': 'gpt-6.1-sol', 'effort': 'high'})
        spawn = self.event('response_item', {'type': 'function_call', 'name': 'collaboration.spawn_agent',
            'call_id': 'call1', 'arguments': json.dumps({'task_name': 'transport', 'message': 'PRIVATE_PROMPT'})})
        result = self.event('response_item', {'type': 'function_call_output', 'call_id': 'call1',
            'output': json.dumps({'task_name': '/root/transport'})})
        first = self.tokens('root', 'response1', 10, 10)
        self.session('root', [context, spawn, result, first, first,
            self.event('event_msg', {'type': 'token_count', 'info': {'total_token_usage': {'input_tokens': 99999}}}),
            self.tokens('root', 'response2', 20, 30, 'resumed-turn')])
        self.session('child', [context, first,
            self.event('event_msg', {'type': 'task_started', 'turn_id': 'root-turn'}),
            self.event('turn_context', {'turn_id': 'child-turn', 'model': 'child-model', 'effort': 'high'}),
            self.event('event_msg', {'type': 'task_started', 'turn_id': 'child-turn'}),
            self.tokens('child', 'response1', 6, 6),
            self.event('event_msg', {'type': 'task_complete', 'turn_id': 'child-turn', 'duration_ms': 123}, 3)],
            parent='root', agent_path='/root/transport')
        self.session('grandchild', [self.tokens('grandchild', 'response1', 4, 4)], parent='child')
        self.session('unrelated', [self.tokens('unrelated', 'response1', 1000, 1000)])
        summary, data = self.run_collect()
        self.assertTrue(summary['usage_complete'])
        self.assertEqual(summary['thread_count'], 3)
        self.assertEqual(data['usage']['input_tokens'], 40)
        self.assertEqual(data['usage']['total_tokens'], 80)
        child = next(item for item in data['agents'] if item['thread_id'] == 'child')
        self.assertEqual(child['turns'], [{'turn_id': 'child-turn', 'model': 'child-model',
            'reasoning_effort': 'high', 'status': 'completed', 'started_at': self.at(2),
            'ended_at': self.at(3), 'duration_ms': 123}])
        records = ''.join(path.read_text() for path in self.out.rglob('*.json'))
        for private in ('PRIVATE_PROMPT', 'PRIVATE_INSTRUCTIONS', 'PRIVATE_ACCOUNT', 'unrelated', '99999'):
            self.assertNotIn(private, records)

    def test_missing_child_keeps_observed_usage_explicitly_partial(self):
        self.session('root', [self.tokens('root', 'response1', 10, 10),
            self.event('response_item', {'type': 'function_call', 'name': 'spawn_agent', 'call_id': 'c'}),
            self.event('response_item', {'type': 'function_call_output', 'call_id': 'c',
                'output': '{"agent_id":"missing-child", "task_name":"/root/missing"}'})])
        summary, data = self.run_collect()
        self.assertFalse(summary['usage_complete'])
        self.assertEqual(data['usage']['input_tokens'], 10)
        self.assertEqual(data['missing_threads'], ['missing-child'])
        self.assertEqual(data['missing_agent_paths'], ['/root/missing'])

    def test_missing_or_unsupported_usage_is_unknown_not_zero(self):
        self.session('root', [self.event('event_msg', {'type': 'token_count', 'tokens': 300})])
        summary, data = self.run_collect()
        self.assertIsNone(summary['usage'])
        self.assertFalse(summary['usage_complete'])
        self.assertIn('no_per_response_usage', data['agents'][0]['warnings'])

    def test_truncated_aborted_or_mismatched_records_preserve_partial_usage(self):
        path = self.session('root', [self.tokens('root', 'response1', 10, 30),
            self.event('event_msg', {'type': 'task_started', 'turn_id': 'root-turn'}),
            self.event('response_item', {'type': 'function_call', 'name': {'invalid': 'name'}}),
            {'payload': {}}])
        with path.open('a') as stream:
            stream.write('{unfinished')
        summary, data = self.run_collect()
        self.assertFalse(summary['usage_complete'])
        self.assertEqual(summary['usage']['input_tokens'], 10)
        self.assertEqual(set(data['agents'][0]['warnings']), {'invalid_native_record',
            'unfinished_or_aborted_turn', 'response_usage_not_reconciled_with_thread_counter'})

    def test_root_workspace_and_symlinks_are_not_bypassed(self):
        path = self.session('root', [self.tokens('root', 'r', 2, 2)], cwd=self.root / 'another-run')
        summary, data = self.run_collect()
        self.assertEqual(data['missing_threads'], ['root'])
        self.assertIsNone(summary['usage'])
        saved = self.root / 'outside.jsonl'
        path.rename(saved)
        path.symlink_to(saved)
        summary, data = self.run_collect()
        self.assertEqual(summary['thread_count'], 0)

    def test_allowlisted_values_still_get_credential_redaction(self):
        self.session('root', [self.tokens('root', 'response1', 10, 10),
            self.event('turn_context', {'turn_id': 't', 'model': 'secret-model-name', 'effort': 'high'})])
        self.run_collect(secrets=['secret-model-name'])
        records = ''.join(path.read_text() for path in self.out.rglob('*.json'))
        self.assertNotIn('secret-model-name', records)
        self.assertIn('[REDACTED_CREDENTIAL]', records)

    def test_local_date_directory_can_differ_from_utc_stage_date(self):
        path = self.session('root', [self.tokens('root', 'r', 2, 2)])
        local = self.home / 'sessions' / (self.base + timedelta(days=1)).strftime('%Y/%m/%d') / path.name
        local.parent.mkdir(parents=True, exist_ok=True)
        path.rename(local)
        summary, data = self.run_collect()
        self.assertTrue(summary['usage_complete'])
        self.assertEqual(data['usage']['total_tokens'], 4)


if __name__ == '__main__':
    unittest.main()
