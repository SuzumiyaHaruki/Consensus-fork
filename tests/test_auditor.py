"""Offline checks of the fork's source capture, audit loop and execution boundaries."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from artifacts import prepare_handoff
from audit_bridge import git
from runtime import local_exec
from auditor.codex import Codex, decode, process
from auditor.config import Config, load_config, validate_selection
from auditor.runner import continuation_plan, run
from runtime.storage import sensitive_file, write_json


class ScriptedAudit:
    """Fixture events test orchestration; they are not model-generated findings."""
    def __init__(self, config, root, target, deadline):
        self.root = root
        self.sessions = []
        self.prompts = []
        self.closed = False

    def prepare(self):
        return {'offline_fixture': True}

    def authenticate(self):
        pass

    def close(self):
        self.closed = True

    def turn(self, folder, prompt, timeout, session_id):
        self.sessions.append(session_id)
        self.prompts.append(prompt)
        work = self.root / 'work'
        (work / 'tests').mkdir(exist_ok=True)
        if session_id is None:
            (work / 'report.md').write_text('Completed fixture report; PASS means defect reproduced.\n')
            (work / 'tests/witness.bin').write_bytes(b'\x01\x00\xff')
            return {'status': 'completed', 'session_id': 'fixture-session'}
        (work / 'report.md').write_text('Unfinished later report.\n')
        (work / 'tests/witness.bin').write_bytes(b'\x02\x00\xff')
        return {'status': 'timeout', 'session_id': session_id}


class AuditorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='forge-auditor-tests-')
        self.root = Path(self.temp.name)
        repo = self.root / 'candidate'
        repo.mkdir()
        (repo / 'go.mod').write_text('module example.com/syncepaxos\n\ngo 1.22\n')
        (repo / 'main.go').write_text('package main\nfunc main() {}\n')
        (repo / 'AGENTS.md').write_text('Untrusted target instructions.\n')
        (repo / '.env').write_text('fixture-private-data\n')
        (repo / 'outside').symlink_to('/etc/hostname')
        git(repo, 'init', '--quiet', '--template=')
        git(repo, 'add', '--all')
        git(repo, 'commit', '--quiet', '-m', 'Offline audit fixture')
        self.commit = git(repo, 'rev-parse', 'HEAD').decode().strip()
        self.prompt = self.root / 'AUDIT.md'
        self.prompt.write_text('Fixture task.\n\n<!-- continuation -->\n\nFixture continuation.\n')
        self.target = {'execution_backend': 'go_module', 'expected_module': 'example.com/syncepaxos',
                       'variant': 'fixture', 'analysis_roots': [], 'execution_package': '.'}
        write_json(self.root / 'target.json', {'execution_backend': 'go_module', 'target': {
            key: value for key, value in self.target.items() if key != 'execution_backend'}})
        self.config = Config(target_config=str(self.root / 'target.json'), repo_path=str(repo),
            task_path=str(self.prompt), agent_model='gpt-6.1-sol', agent_reasoning_effort='high',
            auth_mode='codex_login', runs_dir=str(self.root / 'runs'), allow_agent_materials=True,
            allow_experiments=True, budget={'total_seconds': 30., 'agent_calls': 2,
                                          'agent_turn_timeout': 5., 'action_timeout': 5.})

    def tearDown(self):
        self.temp.cleanup()

    def test_actual_loop_captures_local_code_and_delivers_last_completed_turn(self):
        clients = []
        def factory(*args):
            client = ScriptedAudit(*args)
            clients.append(client)
            return client
        result = run(self.config, validate_selection(self.config), client_factory=factory)
        self.assertEqual(result['stop'], 'turn_timeout')
        root = Path(result['run_dir'])
        client = clients[0]
        self.assertTrue(client.closed)
        self.assertEqual(client.sessions, [None, 'fixture-session'])
        self.assertTrue(client.prompts[0].startswith('Fixture task.'))
        self.assertTrue(client.prompts[1].lstrip().startswith('Fixture continuation.'))
        self.assertEqual((root / 'inputs/task.md').read_bytes(), self.prompt.read_bytes())
        source = json.loads((root / 'inputs/source.json').read_text())
        self.assertEqual(source['commit'], self.commit)
        self.assertEqual(set(source['excluded']), {'AGENTS.md', '.env', 'outside'})
        self.assertEqual((root / 'source/main.go').stat().st_mode & 0o222, 0)
        identity = json.loads((root / 'inputs/implementation.json').read_text())
        for name in ('auditor/runner.py', 'runtime/storage.py', 'runtime/tracecheck.py', 'runtime/schedule.py', 'audit_bridge.py', 'requirements.txt'):
            self.assertTrue((root / identity['retained_source'][name]['record']).is_file())
        helper = root / 'tools/tracecheck.py'
        self.assertEqual(helper.stat().st_mode & 0o222, 0)
        self.assertIn(str(helper), client.prompts[0])
        self.assertFalse((root / 'work/tracecheck.py').exists())
        schedule = root / 'tools/schedule.py'
        self.assertEqual(schedule.stat().st_mode & 0o222, 0)
        self.assertIn(str(schedule), client.prompts[0])
        self.assertFalse((root / 'work/schedule.py').exists())
        self.assertEqual({Path(path).name for path in identity['reload_inputs']}, {'local_exec.py', 'storage.py', 'replay.py'})
        feedback = self.root / 'feedback'
        handoff = prepare_handoff(root, {'path': self.config.repo_path, 'commit': self.commit}, feedback)
        self.assertEqual(handoff['last_completed_turn'], 1)
        self.assertEqual(handoff['incomplete_turns'], [2])
        self.assertEqual((feedback / 'audit-work/tests/witness.bin').read_bytes(), b'\x01\x00\xff')
        self.assertIn('Completed fixture', (feedback / handoff['report']).read_text())
        self.assertEqual((feedback / 'raw/turns/0002/changes/files/tests/witness.bin').read_bytes(), b'\x02\x00\xff')
        self.assertEqual((feedback / 'raw/tools/tracecheck.py').read_bytes(), helper.read_bytes())
        self.assertEqual((feedback / 'raw/tools/schedule.py').read_bytes(), schedule.read_bytes())
        self.assertEqual(git(Path(self.config.repo_path), 'status', '--porcelain'), b'')

    def test_review_is_finite_and_receives_readonly_context(self):
        context = self.root / 'review-context'
        context.mkdir()
        request = {'before_commit': 'before', 'after_commit': 'after', 'issue_ids': []}
        write_json(context / 'request.json', request)
        config = self.config.model_copy(update={'task_mode': 'review', 'review_context': str(context)})
        class CompleteReview(ScriptedAudit):
            def turn(self, *args):
                result = super().turn(*args)
                write_json(self.root / 'work/review.json', {**request, 'summary': 'Fixture', 'issues': []})
                return result
        result = run(config, self.target, client_factory=CompleteReview)
        self.assertEqual(result['stop'], 'review_complete')
        root = Path(result['run_dir'])
        record = json.loads((root / 'run.json').read_text())
        self.assertEqual(len(record['turns']), 1)
        self.assertEqual((root / 'context/request.json').stat().st_mode & 0o222, 0)
        self.assertIn(str(root / 'context'), (root / 'turns/0001/request.txt').read_text())

    def test_review_repairs_incomplete_delivery_in_the_same_session(self):
        for defect in ('missing_index', 'missing_issue', 'unlinked_fix', 'bad_new_issue', 'missing_report'):
            with self.subTest(defect=defect):
                context = self.root / defect
                context.mkdir()
                request = {'before_commit': 'before', 'after_commit': 'after', 'issue_ids': ['F1']}
                write_json(context / 'request.json', request)
                class CompletingReview(ScriptedAudit):
                    def turn(client, folder, prompt, timeout, session_id):
                        client.sessions.append(session_id)
                        item = {'id': 'F1', 'disposition': 'fixed', 'method': 'executed',
                                'reason': 'Fixture only', 'before_observation': 'Before', 'after_observation': 'After',
                                'evidence': ['work/report.md', 'executions/checked/result.json']}
                        write_json(client.root / 'executions/checked/result.json', {'execution_id': 'checked',
                                   'turn': folder.name, 'status': 'completed', 'exit_code': 1, 'argv': ['fixture-only'],
                                   'source_context': {'kind': 'candidate_copy', 'commit': 'after'}})
                        report = client.root / 'work/report.md'
                        report.write_text('Fixture report, no consensus claim')
                        data = {**request, 'summary': 'Fixture', 'issues': [item]}
                        if session_id is None:
                            if defect == 'missing_index':
                                return {'status': 'completed', 'session_id': 'review-session'}
                            if defect == 'missing_issue':
                                data['issues'] = []
                            if defect == 'unlinked_fix':
                                item['evidence'] = ['work/report.md']
                            if defect == 'bad_new_issue':
                                data['new_issues'] = [{'id': 'F2'}]
                            if defect == 'missing_report':
                                report.unlink()
                                item['evidence'] = ['executions/checked/result.json']
                        write_json(client.root / 'work/review.json', data)
                        return {'status': 'completed', 'session_id': 'review-session'}
                config = self.config.model_copy(update={'task_mode': 'review', 'review_context': str(context)})
                result = run(config, self.target, client_factory=CompletingReview)
                self.assertEqual(result['stop'], 'review_complete')
                root = Path(result['run_dir'])
                self.assertEqual(len(json.loads((root / 'run.json').read_text())['turns']), 2)
                self.assertIn('Review delivery is incomplete', (root / 'turns/0002/request.txt').read_text())
                bundle = self.root / f'handoff-{defect}'
                prepare_handoff(root, {'commit': self.commit}, bundle)
                from issues import review_result
                result = review_result(bundle, {'commit': 'before'}, {'commit': 'after', 'version': 1}, ['F1'])
                self.assertEqual(result['issues'][0]['disposition'], 'fixed')

    def test_unfinished_review_does_not_become_complete_when_call_budget_ends(self):
        context = self.root / 'review-context'
        context.mkdir()
        write_json(context / 'request.json', {'before_commit': 'before', 'after_commit': 'after', 'issue_ids': ['F1']})
        class UnfinishedReview(ScriptedAudit):
            def turn(client, *args):
                (client.root / 'work/report.md').write_text('Still investigating')
                return {'status': 'completed', 'session_id': 'same-session'}
        config = self.config.model_copy(update={'task_mode': 'review', 'review_context': str(context)})
        result = run(config, self.target, client_factory=UnfinishedReview)
        self.assertEqual(result['stop'], 'agent_call_limit')
        self.assertEqual(len(json.loads((Path(result['run_dir']) / 'run.json').read_text())['turns']), 2)

    def test_budget_plan_keeps_short_investigations_available_after_long_turns(self):
        self.assertEqual(continuation_plan(1200, 37, [300], True)['work_mode'], 'retain_report')
        self.assertEqual(continuation_plan(1200, 146, [300, 200, 250], True)['work_mode'], 'investigate')
        self.assertEqual(continuation_plan(1200, 146, [10, 12, 11], True)['work_mode'], 'investigate')
        self.assertEqual(continuation_plan(1200, 120, [10, 12, 11], True)['work_mode'], 'wrap_up')
        self.assertEqual(continuation_plan(1200, 11, [], False)['work_mode'], 'wrap_up')
        self.assertEqual(continuation_plan(30, 10, [.1], True)['work_mode'], 'investigate')
        self.assertEqual(continuation_plan(900, 112, [788], False)['work_mode'], 'investigate')
        self.assertEqual(continuation_plan(900, 80, [820], False)['work_mode'], 'wrap_up')
        self.assertEqual(continuation_plan(900, 20, [880], False)['work_mode'], 'wrap_up')
        self.assertEqual(continuation_plan(1800, 1012, [788], False)['work_mode'], 'investigate')
        # The observed baseline run had 622s left after a 575s first turn.
        for has_report in (True, False):
            plan = continuation_plan(1200, 622.3, [574.7], has_report)
            self.assertEqual(plan['work_mode'], 'investigate')
            self.assertAlmostEqual(plan['investigation_seconds'], 562.3)

    def test_first_timeout_wraps_up_without_promoting_an_unfinished_report(self):
        for first_duration, final_status in ((820., 'completed'), (880., 'completed'), (820., 'timeout')):
            with self.subTest(first_duration=first_duration, final_status=final_status):
                clock = [10000.0]
                class ResumableAudit(ScriptedAudit):
                    def turn(inner, folder, prompt, timeout, session_id):
                        inner.prompts.append(prompt)
                        first = len(inner.prompts) == 1
                        work = inner.root / 'work'
                        if first:
                            self.assertIsNone(session_id)
                            self.assertEqual(timeout, 600.)
                            (work / 'witness.txt').write_text('Evidence retained before timeout.')
                        else:
                            self.assertEqual(session_id, 'fixture-session')
                            self.assertEqual(timeout, 900. - first_duration)
                            self.assertIn('final planned turn', prompt)
                            record = json.loads((inner.root / 'run.json').read_text())
                            self.assertIsNone(record.get('last_completed_report'))
                        status = 'timeout' if first else final_status
                        clock[0] += first_duration if first else (timeout if status == 'timeout' else 5.)
                        (work / 'report.md').write_text(f'Fixture report {len(inner.prompts)}: {status}')
                        if status == 'completed':
                            write_json(work / 'findings.json', {'candidate_commit': self.commit,
                                'coverage': 'Fixture only', 'issues': []})
                        return {'status': status, 'session_id': 'fixture-session',
                                'continuable_timeout': status == 'timeout'}
                config = self.config.model_copy(update={'budget': self.config.budget.model_copy(
                    update={'total_seconds': 900., 'agent_turn_timeout': 600., 'agent_calls': 6})})
                with patch('auditor.runner.time.monotonic', side_effect=lambda: clock[0]):
                    result = run(config, self.target, client_factory=ResumableAudit)
                self.assertEqual(result['stop'], 'budget_wrap_up' if final_status == 'completed' else 'total_deadline')
                root = Path(result['run_dir'])
                record = json.loads((root / 'run.json').read_text())
                self.assertEqual([turn['status'] for turn in record['turns']], ['timeout', final_status])
                second = json.loads((root / 'turns/0002/result.json').read_text())
                self.assertEqual(second['budget_plan']['work_mode'], 'wrap_up')
                self.assertEqual(second['budget_plan']['recent_turn_seconds'], first_duration)
                candidate = {'path': self.config.repo_path, 'commit': self.commit}
                feedback = self.root / f'feedback-{first_duration}-{final_status}'
                if final_status == 'completed':
                    handoff = prepare_handoff(root, candidate, feedback)
                    self.assertEqual(handoff['last_completed_turn'], 2)
                    self.assertEqual((feedback / handoff['report']).read_text(), 'Fixture report 2: completed')
                    self.assertEqual((feedback / 'audit-work/witness.txt').read_text(), 'Evidence retained before timeout.')
                else:
                    self.assertIsNone(record.get('last_completed_report'))
                    self.assertTrue((root / 'turns/0002/changes/files/report.md').is_file())
                    with self.assertRaisesRegex(ValueError, 'no completed report'):
                        prepare_handoff(root, candidate, feedback)

    def test_wrap_up_finishes_once_or_retains_report_without_tiny_new_turn(self):
        for durations, expected_stop, last_completed in (([575, 102, 430, 15], 'budget_wrap_up', 4),
                ([100, 1045], 'budget_wrap_up', 2), ([1090, 110], 'total_deadline', 1)):
            with self.subTest(durations=durations):
                clock = [10000.0]
                clients = []
                class TimedAudit(ScriptedAudit):
                    def turn(inner, folder, prompt, timeout, session_id):
                        inner.prompts.append(prompt)
                        index = len(inner.prompts)
                        clock[0] += durations[index - 1]
                        (inner.root / 'work/report.md').write_text(f'Completed fixture {index}')
                        commit = json.loads((inner.root / 'inputs/source.json').read_text())['commit']
                        write_json(inner.root / 'work/findings.json', {'candidate_commit': commit,
                            'coverage': 'Fixture only', 'issues': []})
                        return {'status': 'timeout' if index > last_completed else 'completed',
                                'session_id': 'fixture-session'}
                def factory(*args):
                    client = TimedAudit(*args)
                    clients.append(client)
                    return client
                config = self.config.model_copy(update={'budget': self.config.budget.model_copy(
                    update={'total_seconds': 1200., 'agent_turn_timeout': 1200., 'agent_calls': 10})})
                with patch('auditor.runner.time.monotonic', side_effect=lambda: clock[0]):
                    result = run(config, self.target, client_factory=factory)
                self.assertEqual(result['stop'], expected_stop)
                self.assertTrue(result['ok'])
                self.assertEqual(len(clients[0].prompts), len(durations))
                for prompt in clients[0].prompts[:-1]:
                    self.assertNotIn('final planned turn', prompt)
                if durations[0] != 100:
                    self.assertIn('final planned turn', clients[0].prompts[-1])
                else:
                    self.assertNotIn('final planned turn', clients[0].prompts[-1])
                root = Path(result['run_dir'])
                if durations[0] == 575:
                    # Returning after a shorter follow-up must leave room for a
                    # third investigation, rather than ending after turn two.
                    for number in (2, 3):
                        plan = json.loads((root / f'turns/{number:04d}/result.json').read_text())['budget_plan']
                        self.assertEqual(plan['work_mode'], 'investigate')
                handoff = prepare_handoff(root, {'path': self.config.repo_path, 'commit': self.commit},
                                          self.root / f'feedback-{durations[0]}-{durations[1]}')
                self.assertEqual(handoff['last_completed_turn'], last_completed)

    def test_private_session_usage_is_retained_before_private_home_cleanup(self):
        from datetime import datetime, timedelta, timezone
        root = self.root / 'private-record-test'
        (root / 'work').mkdir(parents=True)
        client = Codex(self.config, root, self.target, time.monotonic() + 30)
        instant = datetime.now(timezone.utc) - timedelta(seconds=1)
        client.telemetry_started_at = (instant - timedelta(seconds=1)).isoformat()
        client.session_ids.add('private-root')
        path = client.client_home / 'sessions' / instant.strftime('%Y/%m/%d') / 'rollout.jsonl'
        path.parent.mkdir(parents=True)
        records = [{'type': 'session_meta', 'payload': {'id': 'private-root', 'timestamp': instant.isoformat(),
                    'cwd': str(client.work), 'account_id': 'private-account'}},
                   {'type': 'token_usage_record', 'payload': {'thread_id': 'private-root', 'response_id': 'r',
                    'usage': {'input_tokens': 10, 'output_tokens': 3},
                    'thread_token_usage': {'input_tokens': 10, 'output_tokens': 3}}}]
        path.write_text(''.join(json.dumps(row) + '\n' for row in records))
        result = client.close()
        self.assertFalse(client.home.exists())
        self.assertTrue(result['usage_complete'])
        self.assertEqual(result['usage']['total_tokens'], 13)
        self.assertTrue((root / 'agent-records/private-root.json').is_file())
        self.assertNotIn('private-account', (root / 'agents.json').read_text())

    def test_next_turn_gets_concrete_feedback_without_repeating_same_question(self):
        clients = []
        class RepeatingAudit(ScriptedAudit):
            def turn(self, folder, prompt, timeout, session_id):
                self.prompts.append(prompt)
                (self.root/'work/report.md').write_text('Fixture claim, not a consensus result.')
                (self.root/'work/observation.txt').write_text('Fixture only.')
                commit = json.loads((self.root/'inputs/source.json').read_text())['commit']
                write_json(self.root/'work/findings.json', {'candidate_commit': commit, 'issues': [
                    {'id': 'F1', 'method': 'executed', 'evidence': ['work/observation.txt']}]})
                return {'status': 'completed', 'session_id': 'fixture-session'}
        def factory(*args):
            client = RepeatingAudit(*args)
            clients.append(client)
            return client
        config = self.config.model_copy(update={'budget': self.config.budget.model_copy(update={'agent_calls': 3})})
        result = run(config, self.target, client_factory=factory)
        self.assertEqual(result['stop'], 'agent_call_limit')
        self.assertNotIn('execution_not_linked', clients[0].prompts[0])
        self.assertIn('execution_not_linked', clients[0].prompts[1])
        self.assertNotIn('execution_not_linked', clients[0].prompts[2])
        self.assertNotIn('No substantive description', clients[0].prompts[1])
        root = Path(result['run_dir'])
        self.assertTrue((root/'turns/0001/evidence-feedback.json').is_file())

    def test_dirty_source_is_rejected_before_client_or_login(self):
        (Path(self.config.repo_path) / 'main.go').write_text('dirty\n')
        with patch('auditor.runner.Codex') as factory:
            result = run(self.config, self.target, client_factory=factory)
            factory.assert_not_called()
        self.assertEqual(result['stop'], 'preflight_or_runtime_error')
        self.assertIn('clean Git commit', result['reason'])

    def test_model_requires_authorization_and_valid_prompt(self):
        self.config.allow_experiments = False
        with self.assertRaisesRegex(ValueError, 'authorized'):
            run(self.config, self.target)
        self.config.allow_experiments = True
        self.prompt.write_text('Missing continuation delimiter.')
        with self.assertRaisesRegex(ValueError, 'Audit prompt'):
            run(self.config, self.target)
        self.assertFalse(Path(self.config.runs_dir).exists())

    def test_execution_reload_change_stops_before_native_invocation(self):
        root = self.root / 'reload-test'
        (root / 'work').mkdir(parents=True)
        runtime_file = self.root / 'runtime.py'
        runtime_file.write_text('# changed fixture\n')
        write_json(root / 'inputs/implementation.json', {'reload_inputs': {str(runtime_file): 'earlier-bytes'}})
        client = Codex(self.config, root, self.target, time.monotonic() + 30)
        try:
            with patch('auditor.codex.process') as invoke:
                with self.assertRaisesRegex(ValueError, 'implementation changed'):
                    client.turn(root / 'turns/0001', 'fixture', 5, None)
                invoke.assert_not_called()
        finally:
            home = client.home
            client.close()
        self.assertFalse(home.exists())

    def test_config_duplicate_keys_and_credential_variable_are_rejected(self):
        path = self.root / 'bad.yaml'
        path.write_text('agent_model: first\nagent_model: second\n')
        with self.assertRaisesRegex(ValueError, 'Duplicate configuration key'):
            load_config(path)
        data = self.config.model_dump() | {'auth_mode': 'api_key', 'api_key_env': 'HOME'}
        with self.assertRaisesRegex(ValueError, 'dedicated credential variable'):
            Config.model_validate(data)


class ExecutionBoundaryTests(unittest.TestCase):
    def test_tool_rejects_escaping_paths_and_has_no_host_fallback(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'link').symlink_to('/etc', target_is_directory=True)
            for directory in ('../outside', '/etc', 'link'):
                with self.subTest(directory=directory), self.assertRaises(ValueError):
                    local_exec.validate_directory(root, directory)
            with patch('runtime.local_exec.shutil.which', return_value=None):
                with self.assertRaisesRegex(FileNotFoundError, 'no host execution fallback'):
                    local_exec.isolated_command(['/bin/true'], root, root, root / 'hosts')
        with self.assertRaises(ValueError):
            local_exec.Arguments(argv=['true'], timeout_seconds=float('nan'))

    def test_isolated_service_bootstrap_imports_only_local_source_and_dependencies(self):
        with tempfile.TemporaryDirectory() as temp:
            settings = local_exec.server_settings(Path(temp) / 'control.json', 5)
            args = settings['args']
            code = args[args.index('-c') + 1].split(';runpy.run_path(')[0]
            code += ';import runtime, mcp; print(runtime.__file__)'
            result = subprocess.run([sys.executable, '-I', '-S', '-c', code], cwd=temp,
                                    capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(Path(result.stdout.strip()).resolve(), Path(local_exec.__file__).with_name('__init__.py'))
            self.assertNotIn('consensus-assurance', str(settings))

    def test_native_session_and_completion_evidence_are_distinct_from_tool_success(self):
        cases = [
            ([{'type': 'thread.started', 'thread_id': 'same'}, {'type': 'turn.completed'}], None, 'completed'),
            ([{'type': 'thread.started', 'thread_id': 'different'}, {'type': 'turn.completed'}], 'same', 'session_mismatch'),
            ([{'type': 'thread.started', 'thread_id': 'same'}, {'type': 'item.completed',
              'item': {'type': 'command_execution', 'exit_code': 0}}], None, 'external_blocker_needs_review'),
            ([{'type': 'thread.started', 'thread_id': 'same'}, {'type': 'turn.failed',
              'error': {'message': 'Permission denied'}}], None, 'external_error'),
        ]
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / 'stderr.log').touch()
            for events, session, expected in cases:
                (folder / 'stdout.jsonl').write_text('\n'.join(json.dumps(event) for event in events))
                result = decode(folder, {'status': 'completed', 'exit_code': 0}, session)
                self.assertEqual(result['status'], expected)
                self.assertFalse(result['final_present'])

    def test_process_redacts_supplied_secret_and_reports_timeout(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            secret = 'fixture-sensitive-value'
            result = process([sys.executable, '-c', 'import os; print(os.environ["FIXTURE_VALUE"])'],
                             root, root / 'output', 5, env={'FIXTURE_VALUE': secret}, secrets=[secret])
            self.assertEqual(result['status'], 'completed')
            self.assertEqual((root / 'output/stdout.jsonl').read_text(), '[REDACTED_CREDENTIAL]\n')
            result = process([sys.executable, '-c', 'import time; time.sleep(20)'],
                             root, root / 'timeout', .1, env={})
            self.assertEqual(result['status'], 'timeout')

    def test_java_credential_screening_keeps_original_parser_dependency(self):
        self.assertFalse(sensitive_file('Token.java', b'public class Token {}'))
        self.assertTrue(sensitive_file('config.txt', b'password = "fixture-sensitive-value"'))


if __name__ == '__main__':
    unittest.main()
