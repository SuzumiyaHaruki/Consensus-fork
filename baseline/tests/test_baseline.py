"""Exercise the independent condition without model calls or outer-workflow edits."""
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from baseline import run
from generator import runner


class BaselineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='forge-baseline-tests-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(run.BASE/'inputs', self.root/'inputs')
        self.base_patch = patch.object(run, 'BASE', self.root)
        self.base_patch.start()
        self.addCleanup(self.base_patch.stop)
        self.fake = self.root/'fake-codex'
        shutil.copyfile(run.PROJECT/'tests/fake_codex.py', self.fake)
        self.fake.chmod(0o755)
        runner.write_json(self.root/'config.json', {'model': 'gpt-6.1-sol', 'reasoning_effort': 'high',
                          'codex': str(self.fake), 'timeout_seconds': 10})
        self.settings = run.load(self.root/'config.json')

    def test_prepare_delivers_only_local_materials_and_same_optional_tools(self):
        with patch.object(runner.Client, 'authenticate', side_effect=AssertionError('No authentication during prepare')):
            root = run.prepare(self.settings)
        record = run.inspect(root)
        self.assertEqual(record['condition'], run.CONDITION)
        self.assertEqual(record['input_files'], ['AGENTS.md', 'TASK.md', 'protocol.md', 'pseudocode.md'])
        self.assertEqual(set(p.name for p in (root/'workspace').glob('*.md')), set(run.INPUTS))
        for name in run.INPUTS:
            self.assertEqual((root/'inputs'/name).read_bytes(), (self.root/'inputs'/name).read_bytes())
            self.assertEqual((root/'workspace'/name).read_bytes(), (root/'inputs'/name).read_bytes())
        self.assertEqual((root/'inputs/schedule.py').read_bytes(), (run.PROJECT/'runtime/schedule.py').read_bytes())
        self.assertFalse((root/'inputs/tracecheck.py').exists())
        for name in ('protocol.md', 'pseudocode.md'):
            self.assertEqual((root/'inputs'/name).read_bytes(), (run.PROJECT/'inputs'/name).read_bytes())
        self.assertFalse((root/'events.jsonl').exists())
        self.assertTrue((root/'workspace/.git').is_dir())
        original = (root/'prompt.txt').read_bytes()
        (self.root/'inputs/TASK.md').write_text('New experiment material')
        self.assertEqual((root/'prompt.txt').read_bytes(), original)
        self.assertEqual((root/'inputs/TASK.md').read_bytes(), original)
        second = run.prepare(self.settings)
        self.assertNotEqual(root, second)
        self.assertEqual((second/'prompt.txt').read_text(), 'New experiment material')

    def test_config_cannot_redirect_inputs_or_output_into_main_workflow(self):
        self.assertEqual(Path(self.settings.inputs_dir), self.root/'inputs')
        self.assertEqual(Path(self.settings.output_root), self.root/'experiments')
        for key in ('inputs_dir', 'output_root', 'audit_model', 'profile'):
            runner.write_json(self.root/'bad.json', {key: 'outside'})
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'Unknown baseline settings'):
                run.load(self.root/'bad.json')
        with self.assertRaises(ValueError):
            run.load(self.root/'config.json', {'timeout_seconds': -1})

    def test_missing_input_fails_before_creating_output(self):
        (self.root/'inputs/protocol.md').unlink()
        with self.assertRaisesRegex(ValueError, 'Missing baseline input'):
            run.prepare(self.settings)
        self.assertFalse((self.root/'experiments').exists())

    def test_wrong_workflow_or_external_directory_cannot_be_executed(self):
        root = run.prepare(self.settings)
        record = runner.read_json(root/'run.json')
        runner.write_json(root/'run.json', record | {'condition': 'protocol-to-system-native-agent'})
        with patch.object(runner, 'execute') as execute:
            with self.assertRaisesRegex(ValueError, 'not a baseline'):
                run.execute(root)
            external = self.root/'main-experiment'
            external.mkdir()
            runner.write_json(external/'run.json', record)
            with self.assertRaisesRegex(ValueError, 'inside baseline/experiments'):
                run.execute(external)
            execute.assert_not_called()
        self.assertEqual(runner.read_json(external/'run.json'), record)

    def test_cli_prepare_is_offline_and_uses_baseline_configuration(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout), patch.object(run, 'execute', side_effect=AssertionError('No execution')):
            self.assertEqual(run.main(['prepare', '--config', str(self.root/'config.json'),
                                      '--label', 'cli', '--timeout-seconds', '123']), 0)
        root = Path(json.loads(stdout.getvalue())['run_dir'])
        self.assertEqual(run.inspect(root)['settings']['timeout_seconds'], 123)

    def test_shared_runner_executes_exact_prompt_and_keeps_failure_distinct(self):
        auth = self.root/'fixture-login'
        auth.mkdir()
        runner.write_json(auth/'auth.json', {'auth_mode': 'chatgpt', 'tokens': {}})
        def prepare_execution(settings, root, deadline):
            runner.write_json(root/'execution-control.json', {'environment': {'PATH': '/usr/bin:/bin'}})
            return {'options': []}
        with patch.dict(os.environ, {'CODEX_HOME': str(auth), 'CODEX_API_KEY': ''}), \
                patch('generator.execution.prepare', side_effect=prepare_execution):
            for mode, status in (('complete', 'agent_finished'), ('zero_exit_failure', 'agent_failed')):
                root = run.prepare(self.settings)
                (root/'workspace/FAKE_MODE').write_text(mode)
                result = run.execute(root)
                self.assertEqual(result['status'], status)
                self.assertEqual(result['condition'], run.CONDITION)
                self.assertEqual((root/'workspace/received-prompt.txt').read_bytes(), (root/'prompt.txt').read_bytes())
                args = runner.read_json(root/'run.json')['command']
                self.assertEqual(args[args.index('--model') + 1], 'gpt-6.1-sol')
                self.assertIn('features.multi_agent=true', args)
                self.assertTrue((root/'agents.json').exists())
                self.assertFalse(any((root/name).exists() for name in ('audits', 'feedback', 'reviews', 'issues.json')))
                self.assertFalse(list(root.glob('.client-*')))
                before = (root/'events.jsonl').read_bytes()
                with self.assertRaisesRegex(ValueError, 'prepare a fresh run'):
                    run.execute(root)
                self.assertEqual((root/'events.jsonl').read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
