"""Shared infrastructure: source association and evidence feedback, without model calls."""
import ast
import asyncio
import json
import os
from pathlib import Path
import select
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from runtime import replay
from runtime.local_exec import execution_lock
from runtime.evidence import inspect_item, report_feedback


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.work, self.source = self.root/'work', self.root/'source'
        self.work.mkdir()
        self.source.mkdir()
        (self.source/'value.txt').write_text('original')
        (self.work/'value.txt').write_text('diagnostic')
        (self.work/'test.py').write_text('print("fixture")')
        self.folder = self.root/'executions/e1'
        self.folder.mkdir(parents=True)
        self.control = {'work': str(self.work), 'source_context': {'phase': 'audit', 'base_commit': 'v0'},
                        'environment': {'HOME': str(self.work/'.runtime/home'), 'GOCACHE': str(self.work/'.runtime/cache')},
                        'replay_sources': {'candidate': {'path': str(self.source), 'commit': 'v0'}}}

    def test_private_replay_keeps_original_and_retains_exact_overlay_bytes(self):
        work, env, context = replay.prepare(self.control, 'candidate', ['test.py', 'value.txt'], self.folder)
        self.assertEqual(context['commit'], 'v0')
        self.assertFalse(context['overlays'][0]['replaces_source'])
        self.assertTrue(context['overlays'][1]['replaces_source'])
        self.assertEqual((self.folder/'inputs/test.py').read_bytes(), (self.work/'test.py').read_bytes())
        self.assertEqual((work/'value.txt').read_text(), 'diagnostic')
        (work/'value.txt').write_text('changed by command')
        self.assertEqual((self.source/'value.txt').read_text(), 'original')
        self.assertTrue(Path(env['GOCACHE']).is_relative_to(work))
        replay.cleanup(self.folder)
        self.assertFalse(work.exists())
        self.assertTrue((self.folder/'inputs/test.py').is_file())

    def test_mutable_work_does_not_claim_exact_candidate(self):
        work, _, context = replay.prepare(self.control, None, [], self.folder)
        self.assertEqual(work, self.work)
        self.assertEqual(context['kind'], 'mutable_workspace')
        self.assertNotIn('commit', context)
        for source, overlays in [(None, ['test.py']), ('unknown', [])]:
            with self.assertRaises(ValueError):
                replay.prepare(self.control, source, overlays, self.folder)

    def test_selected_outputs_survive_cleanup_and_link_to_execution(self):
        work, _, context = replay.prepare(self.control, 'candidate', [], self.folder)
        (work/'observations').mkdir()
        (work/'observations/history.json').write_text('[{"result": "observed"}]')
        (work/'discard.txt').write_text('not selected')
        artifacts = replay.retain_outputs(work, ['observations', 'observations/history.json', 'missing'], self.folder)
        replay.cleanup(self.folder)
        self.assertFalse(work.exists())
        self.assertEqual(len(artifacts['files']), 1)
        self.assertEqual(artifacts['excluded'][0]['path'], 'missing')
        self.assertFalse((self.folder/'artifacts/discard.txt').exists())
        item = self.record(source_context=context, artifacts=artifacts)
        details = inspect_item(item, self.root)
        output = details['execution_records'][0]['outputs']['artifact:observations/history.json']
        self.assertEqual((self.root/output).read_text(), '[{"result": "observed"}]')
        self.assertEqual(details['evidence_feedback'][0]['code'], 'output_excluded')
        (self.root/output).unlink()
        self.assertIn('output_missing', {entry['code'] for entry in inspect_item(item, self.root)['evidence_feedback']})

    def test_output_selection_preserves_private_file_and_link_exclusions(self):
        folder = self.work/'results'
        folder.mkdir()
        (folder/'good.txt').write_text('visible')
        (folder/'.env').write_text('private fixture')
        (folder/'binary').write_bytes(b'\x7fELFcompiled')
        (folder/'link').symlink_to(self.source/'value.txt')
        (folder/'dirlink').symlink_to(self.source, target_is_directory=True)
        (folder/'.runtime').mkdir()
        (folder/'.runtime/private.txt').write_text('private')
        os.link(self.source/'value.txt', folder/'hardlink')
        os.mkfifo(folder/'fifo')
        artifacts = replay.retain_outputs(self.work, ['results', '../source', '.', str(self.source)], self.folder)
        self.assertEqual([entry['path'] for entry in artifacts['files']], ['results/good.txt'])
        excluded = {entry['path'] for entry in artifacts['excluded']}
        self.assertTrue({'results/.env', 'results/binary', 'results/link', 'results/dirlink',
                         'results/.runtime', 'results/hardlink', 'results/fifo', '../source', '.', str(self.source)} <= excluded)

    def test_output_limits_report_partial_collection(self):
        folder = self.work/'results'
        folder.mkdir()
        for n in range(6):
            (folder/str(n)).write_text('1234')
        with patch.object(replay, 'MAX_OUTPUT_BYTES', 8):
            artifacts = replay.retain_outputs(self.work, ['results'], self.folder)
        self.assertEqual(sum(entry['bytes'] for entry in artifacts['files']), 8)
        self.assertEqual(len(artifacts['excluded']), 4)
        with patch.object(replay, 'MAX_OUTPUT_FILES', 3):
            artifacts = replay.retain_outputs(self.work, ['results'], self.folder)
        self.assertLessEqual(len(artifacts['files']), 2)
        self.assertTrue(any('partial' in entry['reason'] for entry in artifacts['excluded']))

    def test_replay_inputs_cannot_escape_or_copy_private_files(self):
        (self.work/'link').symlink_to(self.source/'value.txt')
        (self.work/'dirlink').symlink_to(self.source, target_is_directory=True)
        (self.work/'.env').write_text('private fixture')
        for name in ('', '.', '../source/value.txt', str(self.source/'value.txt'), 'link', 'dirlink/value.txt', '.env'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                replay.regular_file(self.work, name)

    def test_concurrent_parent_swap_cannot_escape_during_overlay_read(self):
        directory = self.work/'tests'
        directory.mkdir()
        (directory/'value.txt').write_text('local')
        original_open = replay.os.open
        def swap(path, flags, **kwargs):
            if path == 'tests':
                directory.rename(self.work/'old-tests')
                directory.symlink_to(self.source, target_is_directory=True)
            return original_open(path, flags, **kwargs)
        with patch('runtime.replay.os.open', side_effect=swap), self.assertRaises(OSError):
            replay.regular_file(self.work, 'tests/value.txt')

    def record(self, **changes):
        value = {'execution_id': 'e1', 'status': 'completed', 'exit_code': 0,
                 'argv': ['go', 'test', './...'], 'source_context': {'kind': 'mutable_workspace', 'base_commit': 'v0'}}
        value.update(changes)
        (self.folder/'result.json').write_text(json.dumps(value))
        return {'id': 'F1', 'evidence': ['executions/e1/result.json'], 'method': 'executed'}

    def test_feedback_targets_version_timeout_and_overlay_not_missing_headings(self):
        item = self.record(status='timeout')
        result = inspect_item(item, self.root, expected_commits=('v0',))
        self.assertEqual({entry['code'] for entry in result['evidence_feedback']}, {'execution_incomplete', 'version_not_bound'})
        self.assertEqual(result['execution_records'][0]['argv'], ['go', 'test', './...'])
        (self.folder/'inputs').mkdir()
        (self.folder/'inputs/value.txt').write_text('diagnostic')
        item = self.record(source_context={'kind': 'candidate_copy', 'commit': 'different', 'overlays': [
            {'replaces_source': True, 'retained_path': 'inputs/value.txt'}]})
        codes = {entry['code'] for entry in inspect_item(item, self.root, expected_commits=('v0',))['evidence_feedback']}
        self.assertEqual(codes, {'different_source_version', 'source_overlay'})

    def test_agent_written_receipt_is_not_a_trusted_execution_record(self):
        (self.work/'fake.json').write_text(json.dumps({'execution_id': 'fake', 'status': 'completed'}))
        result = inspect_item({'evidence': ['work/fake.json'], 'execution_records': [{'status': 'completed'}]}, self.root)
        self.assertEqual(result['execution_records'], [])
        self.assertEqual(result['evidence_feedback'][0]['code'], 'execution_not_linked')
        self.assertEqual(inspect_item({'method': 'source_review', 'evidence': ['work/fake.json']}, self.root)['evidence_feedback'], [])
        item = self.record(execution_id='wrong')
        self.assertIn('execution_record_unavailable', {entry['code'] for entry in inspect_item(item, self.root)['evidence_feedback']})

    def test_rerun_information_uses_retained_inputs_and_logs_without_rewriting_command(self):
        _, _, context = replay.prepare(self.control, 'candidate', ['test.py'], self.folder)
        (self.folder / 'stdout.txt').write_text('Original observation')
        (self.folder / 'stderr.txt').write_text('')
        argv = ['/old/work/.runtime/helper', '--script', '/old/work/test.py']
        item = self.record(argv=argv, cwd='/old/work/tests', cwd_relative='tests', timeout_seconds=30,
                           stdout={'path': '/outside/never-follow-this'}, source_context=context)
        replay.cleanup(self.folder)
        entry = inspect_item(item, self.root)['execution_records'][0]
        self.assertEqual(entry['argv'], argv)
        self.assertEqual(entry['cwd_relative'], 'tests')
        self.assertEqual(entry['cwd'], '/old/work/tests')
        self.assertEqual(entry['restore'], {'test.py': 'executions/e1/inputs/test.py'})
        self.assertEqual(entry['outputs']['stdout'], 'executions/e1/stdout.txt')
        self.assertEqual((self.root / entry['restore']['test.py']).read_text(), 'print("fixture")')
        original = self.record(cwd='/old/work/tests')
        self.assertIsNone(inspect_item(original, self.root)['execution_records'][0]['cwd_relative'])
        context['overlays'][0]['path'] = '../escape'
        with self.assertRaises(ValueError):
            inspect_item(self.record(source_context=context), self.root)

    def test_live_feedback_retains_index_and_points_to_concrete_delivery_error(self):
        path = self.work/'findings.json'
        raw = json.dumps({'candidate_commit': 'wrong', 'issues': [{'id': 'F1', 'evidence': ['work/missing']}]})
        path.write_text(raw)
        result = report_feedback(self.root, 'findings.json', {'candidate_commit': 'v0'})
        self.assertEqual({item['code'] for item in result['observations']}, {'version_reference', 'evidence_reference'})
        self.assertEqual(path.read_text(), raw)

    def test_trace_input_failure_is_not_an_inconsistent_event_ledger(self):
        ledger = {'clock': 'controlled', 'members': ['A'], 'fault_limit': 0,
                  'delivery_bound_ns': 10, 'end_ns': 0, 'events': []}
        cases = [('{}\n{}\n', 'decode', 'trace_input_error'),
                 (json.dumps({'observations': []}), 'schema', 'trace_format_unsupported'),
                 (json.dumps(ledger | {'events': [{'at_ns': 0, 'kind': 'deliver', 'id': 'missing'}]}),
                  None, 'trace_inconsistent'), (json.dumps(ledger), None, None)]
        for raw, error_kind, code in cases:
            with self.subTest(code=code):
                path = self.work / 'trace.json'
                path.write_text(raw)
                result = inspect_item({'method': 'source_review', 'evidence': ['work/trace.json'],
                                       'trace_files': ['work/trace.json']}, self.root)
                self.assertEqual(result['trace_checks'][0].get('error_kind'), error_kind)
                self.assertEqual([entry['code'] for entry in result['evidence_feedback']], [code] if code else [])
                self.assertEqual(path.read_text(), raw)

    def test_shared_modules_have_no_dependency_on_agent_roles(self):
        root = Path(__file__).resolve().parents[1]
        for path in (root/'runtime').glob('*.py'):
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.ImportFrom):
                    self.assertNotIn((node.module or '').split('.')[0], {'auditor', 'generator'}, str(path))
                elif isinstance(node, ast.Import):
                    self.assertFalse(any(name.name.split('.')[0] in {'auditor', 'generator'} for name in node.names), str(path))


class ExecutionLockTests(unittest.IsolatedAsyncioTestCase):
    async def test_separate_server_owner_blocks_waiters_and_process_exit_releases_lock(self):
        with tempfile.TemporaryDirectory() as temp:
            records = Path(temp)
            worker = '''import asyncio, sys, time
from runtime.local_exec import execution_lock
async def main():
    async with execution_lock(sys.argv[1], time.monotonic()+10):
        print("acquired", flush=True)
        await asyncio.sleep(30)
asyncio.run(main())
'''
            owner = subprocess.Popen([sys.executable, '-c', worker, str(records)],
                cwd=Path(__file__).resolve().parents[1], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                # Keep this handshake bounded without asyncio's thread wakeup socket,
                # which can be restricted by the outer test sandbox.
                ready, _, _ = select.select([owner.stdout], [], [], 5)
                self.assertTrue(ready, 'Lock owner did not become ready')
                self.assertEqual(owner.stdout.readline(), b'acquired\n')
                # A second process must honor the same lock and its own deadline.
                with self.assertRaisesRegex(TimeoutError, 'Run deadline'):
                    async with execution_lock(records, time.monotonic()+.1):
                        self.fail('Concurrent server entered the execution section')
                entered = asyncio.Event()
                async def wait_for_owner():
                    async with execution_lock(records, time.monotonic()+5):
                        entered.set()
                waiter = asyncio.create_task(wait_for_owner())
                await asyncio.sleep(.05)
                self.assertFalse(entered.is_set())
                waiter.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await waiter
                owner.kill()
                owner.wait(timeout=3)
                # No manual removal of a stale lock file is required.
                async with execution_lock(records, time.monotonic()+1):
                    pass
            finally:
                if owner.poll() is None:
                    owner.kill()
                owner.communicate(timeout=5)


if __name__ == '__main__':
    unittest.main()
