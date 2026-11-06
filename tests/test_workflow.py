"""Offline workflow tests; fixture programs never implement or audit consensus."""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from artifacts import candidate_commit, copy_regular, copy_tree, inside, prepare_handoff
from audit_bridge import git
from generator.runner import execute as execute_agent, read_json, write_json
import workflow
from workflow_config import ROOT, WorkflowSettings, from_dict, load


def put(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content if isinstance(content, bytes) else content.encode())


def fixture_audit(folder, candidate, *, incomplete=False, empty=False):
    folder.mkdir(parents=True)
    copy_tree(Path(candidate['path']), folder / 'source', excluded={'.git'})
    (folder / 'inputs').mkdir()
    write_json(folder / 'inputs/source.json', {'commit': candidate['commit']})
    turns = []
    for number, status, report in ((1, 'completed', 'F1: fixture defect; PASS reproduces the defect.\n'),
                                    (2, 'timeout', 'An unfinished draft must not replace the completed report.\n')):
        path = folder / 'turns' / f'{number:04d}'
        put(path / 'changes/files/report.md', report)
        put(path / 'changes/files/tests/witness.bin', bytes([number, 0, 255]))
        write_json(path / 'changes/files/tests/trace.json', {'clock': 'controlled', 'members': ['A'],
                   'fault_limit': 0, 'delivery_bound_ns': 10, 'end_ns': 0, 'events': []})
        write_json(path / 'changes/files/findings.json', {'candidate_commit': candidate['commit'],
                   'coverage': 'Offline fixture coverage only.', 'issues': [] if empty else [{
                   'id': 'F1', 'summary': 'Fixture defect', 'property': 'Fixture required behavior',
                   'assumptions': 'Fixture legal conditions', 'reproduction': 'Fixture, no real execution claim',
                   'polarity': 'PASS reproduces defect', 'evidence': ['work/tests/witness.bin'],
                   'legality': 'Empty fixture ledger only', 'reachability': 'No real execution claim',
                   'impact': 'Fixture only', 'causal_explanation': {'fixture': 'No protocol cause'},
                   'variants': ['No variants executed'], 'trace_files': ['work/tests/trace.json']}]})
        write_json(path / 'changes/manifest.json', {'changed': {'report.md': {}, 'findings.json': {},
                   'tests/witness.bin': {}, 'tests/trace.json': {}}, 'deleted': []})
        turns.append({'number': number, 'status': 'timeout' if incomplete else status,
                      'path': str(path.relative_to(folder))})
    write_json(folder / 'run.json', {'stop': 'total_deadline', 'turns': turns,
               'last_completed_report': None if incomplete else 'turns/0001/changes/files/report.md'})
    put(folder / 'work/report.md', 'This mutable work tree contains the unfinished draft.\n')
    return folder


class OfflineRuntime(workflow.Runtime):
    def __init__(self, action='repaired', *, incomplete=False, wrong_commit=False, change_material=False, failure=None):
        self.action = action
        self.incomplete = incomplete
        self.wrong_commit = wrong_commit
        self.change_material = change_material
        self.failure = failure
        self.calls = []
        self.empty_after = None
        self.review_disposition = 'fixed'
        self.repair_dispositions = {}
        self.review_dispositions = {}
        self.review_invalid = False
        self.budgets = []

    def check(self, settings):
        return {'ready': True, 'offline_fixture': True}

    def agent(self, stage):
        role = read_json(stage / 'run.json')['workflow_role']
        self.calls.append(role)
        workspace = stage / 'workspace'
        write_json(stage / 'execution-control.json', {'environment': {'PATH': '/usr/bin:/bin'}})
        # Exercise the actual native runner, stdin delivery, model arguments, and final-event validation.
        with patch('generator.execution.prepare', return_value={'options': []}):
            result = execute_agent(stage)
        if self.failure:
            return result | {'status': self.failure}
        if role == 'generation':
            put(workspace / 'go.mod', 'module example.com/mixepaxos\n\ngo 1.22\n')
            put(workspace / 'server.go', 'package mixepaxos\nconst Version = 0\n')
            put(workspace / 'README.md', 'Generated service documentation.\n')
            if self.change_material:
                put(workspace / 'protocol.md', 'The fixture changed the protocol.\n')
        else:
            handoff = read_json(workspace / '.forge/feedback/handoff.json')
            put(stage / 'executions/fixture/result.json', json.dumps({'execution_id': 'fixture',
                'status': 'completed', 'exit_code': 0, 'argv': ['fixture-only'],
                'source_context': {'kind': 'mutable_workspace', 'base_commit': handoff['candidate_commit']}}))
            self.delivered_report = (workspace / '.forge/feedback' / handoff['report']).read_text()
            write_json(workspace / '.forge/repair-result.json', {
                'input_commit': 'wrong-commit' if self.wrong_commit else handoff['candidate_commit'],
                'action': self.action, 'summary': 'Offline fixture repair result.',
                'issues': [{'id': issue['id'], 'disposition': self.repair_dispositions.get(
                            issue['id'], 'addressed' if self.action == 'repaired' else 'unresolved'),
                            'reason': 'Fixture only; no consensus claim.',
                            'before_check': {'fixture': 'Not a consensus replay'},
                            'checks': ['No real consensus checks']}
                           for issue in read_json(workspace / '.forge/feedback/issues.json')['issues']
                           if issue['id'] in handoff['repair_issue_ids']],
            })
            if self.action == 'repaired':
                put(workspace / 'server.go', f'package mixepaxos\nconst Version = {self.calls.count("repair")}\n')
                put(workspace / 'tests/regression_test.go', 'package tests\n')
        return result

    def export(self, settings, workspace, destination, logs, timeout):
        # A small fixture export keeps state-machine tests independent of audit dependencies.
        destination.mkdir(parents=True)
        names = ['go.mod', 'server.go', 'README.md', 'protocol.md', 'pseudocode.md', 'system.md']
        if (workspace / 'tests/regression_test.go').exists():
            names.append('tests/regression_test.go')
        for name in names:
            copy_regular(workspace / name, destination / name)
        git(destination, 'init', '--quiet', '--template=')
        git(destination, 'add', '--all')
        git(destination, 'commit', '--quiet', '-m', 'Offline fixture')
        return {'path': str(destination), 'commit': candidate_commit(destination), 'files': names, 'excluded': {}}

    def audit(self, settings, candidate, folder, seconds, timeout):
        self.calls.append('audit')
        self.audit_prompt = Path(settings.audit_prompt).read_text()
        self.budgets.append(('audit', seconds))
        return fixture_audit(folder / 'runs/fixture', candidate, incomplete=self.incomplete,
                             empty=self.empty_after is not None and candidate['version'] >= self.empty_after)

    def verify(self, settings, candidate, folder, context, seconds, timeout):
        self.calls.append('verify')
        self.budgets.append(('verify', seconds))
        self.review_prompt = Path(settings.review_prompt).read_text()
        request = read_json(context / 'request.json')
        audit = fixture_audit(folder / 'runs/fixture', candidate)
        path = audit / 'turns/0001/changes'
        (audit / 'executions/checked').mkdir(parents=True)
        write_json(audit / 'executions/checked/result.json', {'execution_id': 'checked',
                   'argv': ['fixture-only'], 'status': 'completed', 'exit_code': 0,
                   'source_context': {'kind': 'candidate_copy', 'commit': candidate['commit']}})
        result = {'before_commit': request['before_commit'], 'after_commit': candidate['commit'],
                  'summary': 'Offline verification fixture.', 'issues': [
                      {'id': ident, 'disposition': self.review_dispositions.get(ident, self.review_disposition), 'reason': 'Fixture observation',
                       'method': 'executed', 'before_observation': 'Fixture before', 'after_observation': 'Fixture after',
                       'variant_checks': ['Fixture only'], 'trace_files': ['work/tests/trace.json'],
                       'evidence': ['work/tests/witness.bin', 'executions/checked/result.json']} for ident in request['issue_ids']]}
        if self.review_invalid:
            result['issues'] = []
        write_json(path / 'files/review.json', result)
        manifest = read_json(path / 'manifest.json')
        manifest['changed']['review.json'] = {}
        write_json(path / 'manifest.json', manifest)
        return audit


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='forge-tests-')
        self.root = Path(self.temp.name)
        home = patch.dict(os.environ, {'CODEX_HOME': str(self.root / 'codex-home')})
        home.start()
        self.addCleanup(home.stop)
        put(self.root / 'codex-home/auth.json', json.dumps({'auth_mode': 'chatgpt', 'tokens': {}}))
        fake = self.root / 'fake codex'
        shutil.copyfile(ROOT / 'tests/fake_codex.py', fake)
        fake.chmod(0o755)
        self.settings = from_dict({'codex': str(fake), 'output_root': str(self.root / 'experiments'), 'max_repairs': 1}, ROOT)

    def tearDown(self):
        self.temp.cleanup()

    def run_fixture(self, runtime=None, **changes):
        settings = from_dict(self.settings.to_dict() | changes, ROOT)
        root = workflow.prepare(settings, 'offline')
        result = workflow.execute(root, runtime or OfflineRuntime())
        return root, result

    def test_review_discovery_reaches_next_repair_despite_empty_fresh_audit(self):
        class ReviewDiscovery(OfflineRuntime):
            def audit(self, settings, candidate, folder, seconds, timeout):
                audit = super().audit(settings, candidate, folder, seconds, timeout)
                if candidate['version'] == 0:
                    path = audit / 'turns/0001/changes/files/findings.json'
                    result = read_json(path)
                    result['cases'] = [{'summary': 'Original bounded check without a finding',
                        'reproduction': 'Fixture only', 'evidence': ['work/tests/witness.bin']}]
                    result['open_questions'] = 'An unresolved interpretation; not a repair assignment'
                    write_json(path, result)
                return audit

            def verify(self, settings, candidate, folder, context, seconds, timeout):
                audit = super().verify(settings, candidate, folder, context, seconds, timeout)
                if candidate['version'] == 1:
                    path = audit / 'turns/0001/changes/files/review.json'
                    result = read_json(path)
                    result['new_issues'] = [{'id': 'REGRESSION', 'summary': 'Separate fixture defect',
                        'property': 'Original promise', 'assumptions': 'Fixture conditions',
                        'reproduction': 'Fixture only', 'polarity': 'PASS observes defect',
                        'evidence': ['work/tests/witness.bin']}]
                    result['cases'] = [{'summary': 'Review-added reusable check', 'reproduction': 'Fixture only',
                        'evidence': ['executions/checked/result.json']}]
                    write_json(path, result)
                return audit
        runtime = ReviewDiscovery()
        runtime.empty_after = 1
        root, result = self.run_fixture(runtime, max_repairs=2)
        self.assertEqual(result['stop_reason'], 'repair_limit')
        self.assertEqual(runtime.calls, ['generation', 'audit', 'repair', 'verify', 'audit', 'repair', 'verify'])
        delivered = read_json(root / 'feedback/001/issues.json')['issues']
        self.assertEqual([item['id'] for item in delivered], ['r001-REGRESSION'])
        self.assertEqual(delivered[0]['source_commit'], result['candidates'][1]['commit'])
        self.assertTrue((root / 'feedback/001' / delivered[0]['evidence'][0]).is_file())
        index = read_json(root / 'issues.json')
        self.assertNotIn('assessment', index)
        self.assertEqual([item['state'] for item in index['issues']], ['fixed', 'fixed'])
        evidence = read_json(root/'feedback/001/evidence-index.json')
        self.assertEqual([entry['id'] for entry in evidence['entries']], ['a000', 'r001', 'a001'])
        self.assertEqual([entry['candidate_commit'] for entry in evidence['entries']],
                         [result['candidates'][i]['commit'] for i in (0, 1, 1)])
        self.assertEqual(evidence['entries'][-1]['cases'], [])
        self.assertEqual(evidence['entries'][-1]['supplemental_turns'][0]['status'], 'timeout')
        for entry in evidence['entries']:
            self.assertTrue((root/'feedback/001'/entry['report']).is_file())
            for case in entry['cases']:
                self.assertTrue(all((root/'feedback/001'/ref).is_file() for ref in case['evidence']))
        self.assertIn('not a repair assignment', evidence['entries'][0]['open_questions'])
        self.assertEqual(read_json(root/'evidence-index.json')['current_candidate_commit'], result['candidates'][2]['commit'])
        self.assertEqual(workflow.inspect(root)['evidence_index'], str(root/'evidence-index.json'))
        # Fresh discovery gets only the candidate, not the accumulated context.
        self.assertFalse((root/'audits/001/feedback').exists())
        # A new finding in the last allowed review remains open at shutdown.
        runtime = ReviewDiscovery()
        root, result = self.run_fixture(runtime, max_repairs=1)
        self.assertEqual(runtime.calls, ['generation', 'audit', 'repair', 'verify'])
        self.assertEqual(result['open_issues'], ['r001-REGRESSION'])
        self.assertEqual(read_json(root / 'issues.json')['issues'][0]['state'], 'fixed')

    def test_inspect_omits_legacy_assessment_without_rewriting_archive(self):
        root = workflow.prepare(self.settings, 'legacy')
        path = root / 'experiment.json'
        data = read_json(path) | {'assessment': 'not_performed'}
        write_json(path, data)
        before = path.read_bytes()
        self.assertNotIn('assessment', workflow.inspect(root))
        self.assertEqual(path.read_bytes(), before)

    def test_full_cycle_versions_exact_feedback_models_and_final_review(self):
        runtime = OfflineRuntime()
        root, result = self.run_fixture(runtime)
        self.assertEqual(result['status'], 'cycle_complete')
        self.assertNotIn('assessment', result)
        self.assertEqual((root / 'inputs/REPAIR.md').read_bytes(), Path(self.settings.repair_prompt).read_bytes())
        self.assertEqual((root / 'inputs/AUDIT.md').read_bytes(), Path(self.settings.audit_prompt).read_bytes())
        self.assertFalse((root / 'prompts').exists())
        self.assertEqual(runtime.calls, ['generation', 'audit', 'repair', 'verify'])
        old, new = result['candidates']
        self.assertNotEqual(old['commit'], new['commit'])
        self.assertEqual(new['changes'], {'added': ['tests/regression_test.go'], 'deleted': [], 'modified': ['server.go']})
        self.assertIn('F1: fixture defect', runtime.delivered_report)
        self.assertNotIn('unfinished', runtime.delivered_report)
        self.assertFalse((Path(new['path']) / '.forge').exists())
        delivered = read_json(root / 'feedback/000/issues.json')['issues'][0]
        self.assertEqual(delivered['trace_checks'], [])
        self.assertEqual(delivered['causal_explanation'], {'fixture': 'No protocol cause'})
        self.assertTrue((root / 'feedback/000' / delivered['trace_files'][0]).is_file())
        self.assertIn(delivered['id'], (root / 'feedback/000/overview.md').read_text())
        reviewed = read_json(root / 'issues.json')['issues'][0]['reviews'][0]
        self.assertEqual(reviewed['trace_checks'], [])
        self.assertEqual(reviewed['variant_checks'], ['Fixture only'])
        request = read_json(root / 'reviews/001/context/request.json')
        self.assertEqual(request['repair_claim']['issues'][0]['before_check'], {'fixture': 'Not a consensus replay'})
        self.assertEqual(request['repair_executions'], 'repair-executions/')
        receipt = read_json(root / 'reviews/001/context/repair-executions/fixture/result.json')
        self.assertEqual(receipt['source_context']['base_commit'], old['commit'])
        self.assertEqual(read_json(root / 'reviews/001/handoff/handoff.json')['candidate_commit'], new['commit'])
        for stage in result['stages']:
            if stage['kind'] in {'generation', 'repair'}:
                args = json.loads((Path(stage['path']) / 'workspace/received-args.json').read_text())
                self.assertEqual(args[args.index('--model') + 1], 'gpt-6.1-sol')
                self.assertIn('model_reasoning_effort="high"', args)
                stage_path = Path(stage['path'])
                self.assertFalse((stage_path / 'inputs/tracecheck.py').exists())
                self.assertEqual((stage_path / 'workspace/pseudocode.md').read_bytes(), (root / 'inputs/pseudocode.md').read_bytes())
                self.assertFalse((stage_path / 'workspace/AUDIT.md').exists())
                if stage['kind'] == 'generation':
                    self.assertFalse((stage_path / 'workspace/REPAIR.md').exists())
                    self.assertEqual((stage_path / 'prompt.txt').read_bytes(), (root / 'inputs/TASK.md').read_bytes())
                else:
                    self.assertEqual((stage_path / 'prompt.txt').read_bytes(), (root / 'inputs/REPAIR.md').read_bytes())
        self.assertEqual(result['settings']['audit_model'], 'gpt-6.1-sol')
        before = (root / 'experiment.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'already started'):
            workflow.execute(root, runtime)
        self.assertEqual(before, (root / 'experiment.json').read_bytes())

    def test_real_finding_shape_completes_repair_and_final_review(self):
        runtime = OfflineRuntime()
        runtime.empty_after = 1
        original_audit, original_agent, original_verify = runtime.audit, runtime.agent, runtime.verify
        def audit(settings, candidate, folder, seconds, timeout):
            run = original_audit(settings, candidate, folder, seconds, timeout)
            if candidate['version'] == 0:
                data = read_json(ROOT / 'tests/fixtures/audit-findings.json')
                # Replay the observed representation against this offline fixture's own commit.
                data['candidate_commit'] = candidate['commit']
                changes = run / 'turns/0001/changes'
                write_json(changes / 'files/findings.json', data)
                manifest = read_json(changes / 'manifest.json')
                for ref in data['issues'][0]['evidence']:
                    name = str(Path(ref).relative_to('work'))
                    put(changes / 'files' / name, 'Retained-path fixture; no execution claim.')
                    manifest['changed'][name] = {}
                write_json(changes / 'manifest.json', manifest)
            return run
        def agent(stage):
            result = original_agent(stage)
            if read_json(stage / 'run.json')['workflow_role'] == 'repair':
                path = stage / 'workspace/.forge/repair-result.json'
                claim = read_json(path)
                claim['summary'] = {'changes': ['Offline fixture repair']}
                claim['issues'][0]['reason'] = ['Fixture reason']
                claim['test_results'] = [{'command': 'fixture', 'exit_code': 0}]
                write_json(path, claim)
            return result
        def verify(settings, candidate, folder, context, seconds, timeout):
            run = original_verify(settings, candidate, folder, context, seconds, timeout)
            path = run / 'turns/0001/changes/files/review.json'
            result = read_json(path)
            result['summary'] = {'checked': ['All supplied issues']}
            result['issues'][0].update(reason=['Fixture verification'],
                                       before_observation={'premature_deaths': 2},
                                       after_observation={'premature_deaths': 0, 'decided': False})
            write_json(path, result)
            return run
        with patch.object(runtime, 'audit', side_effect=audit), patch.object(runtime, 'agent', side_effect=agent), \
             patch.object(runtime, 'verify', side_effect=verify):
            root, result = self.run_fixture(runtime)
        self.assertEqual(result['status'], 'cycle_complete')
        self.assertEqual(result['stop_reason'], 'repair_limit')
        self.assertEqual(runtime.calls, ['generation', 'audit', 'repair', 'verify'])
        index = read_json(root / 'issues.json')
        self.assertEqual(index['import_status'], 'imported')
        self.assertEqual([item['issue_count'] for item in index['imports']], [1])
        self.assertEqual(index['issues'][0]['id'], 'a000-F-001')
        self.assertEqual(index['issues'][0]['state'], 'fixed')
        self.assertIsInstance(index['issues'][0]['assumptions'], list)
        self.assertIsInstance(index['issues'][0]['reproduction'], dict)
        self.assertEqual(index['issues'][0]['reviews'][0]['after_observation']['premature_deaths'], 0)

    def test_no_change_ends_after_review_without_using_all_repair_rounds(self):
        runtime = OfflineRuntime(action='no_change')
        _, result = self.run_fixture(runtime, max_repairs=3)
        self.assertEqual(result['status'], 'cycle_complete')
        self.assertEqual(runtime.calls, ['generation', 'audit', 'repair', 'verify'])
        self.assertEqual(result['candidates'][-1]['changes'], {'added': [], 'deleted': [], 'modified': []})

    def test_three_repairs_end_with_review_instead_of_another_search(self):
        runtime = OfflineRuntime()
        root, result = self.run_fixture(runtime, max_repairs=3)
        self.assertEqual(result['status'], 'cycle_complete')
        self.assertEqual(result['stop_reason'], 'repair_limit')
        self.assertEqual(runtime.calls, ['generation'] + ['audit', 'repair', 'verify'] * 3)
        self.assertEqual(runtime.budgets, [('audit', 3600), ('verify', 900)] + [('audit', 1800), ('verify', 900)] * 2)
        self.assertEqual(len(result['candidates']), 4)
        self.assertEqual(result['open_issues'], [])
        issues = read_json(root / 'issues.json')['issues']
        self.assertEqual([x['state'] for x in issues], ['fixed'] * 3)
        self.assertTrue(all(x['reviews'][0]['before_commit'] == result['candidates'][n]['commit']
                            for n, x in enumerate(issues)))
        history = read_json(root / 'feedback/002/history.json')['issues']
        self.assertEqual([item['id'] for item in history], ['a000-F1', 'a001-F1'])
        self.assertTrue(all((root / 'feedback/002' / item['reviews'][-1]['evidence'][-1]).is_file()
                            for item in history))

    def test_actual_changes_override_repair_action_in_both_directions(self):
        for actual_action, claim in (('repaired', 'no_change'), ('no_change', 'repaired')):
            runtime = OfflineRuntime(action=actual_action)
            runtime.review_disposition, runtime.empty_after = 'unresolved', 1
            original = runtime.agent
            def misreport(stage):
                result = original(stage)
                path = stage / 'workspace/.forge/repair-result.json'
                if path.exists():
                    write_json(path, read_json(path) | {'action': claim})
                return result
            with self.subTest(claim=claim), patch.object(runtime, 'agent', side_effect=misreport):
                root, result = self.run_fixture(runtime, max_repairs=2)
                self.assertEqual(runtime.calls.count('repair'), 2 if actual_action == 'repaired' else 1)
                stage = next(item for item in result['stages'] if item['kind'] == 'repair')
                self.assertIn('action_mismatch', stage)
                request = read_json(root / 'reviews/001/context/request.json')
                self.assertEqual(request['repair_claim']['action'], claim)
                self.assertEqual(request['actual_changes'], stage['actual_changes'])

    def test_empty_discovery_only_stops_when_no_pending_issues(self):
        runtime = OfflineRuntime()
        runtime.empty_after = 0
        _, result = self.run_fixture(runtime, max_repairs=3)
        self.assertEqual(runtime.calls, ['generation', 'audit'])
        self.assertEqual(result['stop_reason'], 'no_open_findings')
        self.assertEqual(result['issue_index_status'], 'imported')
        self.assertEqual(result['stages'][-1]['finding_import']['issue_count'], 0)
        runtime = OfflineRuntime()
        runtime.empty_after = 1
        runtime.review_disposition = 'unresolved'
        root, result = self.run_fixture(runtime, max_repairs=3)
        self.assertEqual(runtime.calls.count('repair'), 3)
        self.assertEqual(result['open_issues'], ['a000-F1'])
        later = read_json(root / 'feedback/001/issues.json')['issues'][0]
        self.assertEqual(later['id'], 'a000-F1')
        self.assertTrue((root / 'feedback/001' / later['reviews'][0]['evidence'][0]).is_file())

    def test_malformed_review_never_closes_issue_or_launches_another_search(self):
        runtime = OfflineRuntime()
        runtime.review_invalid = True
        runtime.empty_after = 1
        root, result = self.run_fixture(runtime, max_repairs=3)
        self.assertEqual(result['status'], 'verification_incomplete')
        self.assertEqual(result['open_issues'], ['a000-F1'])
        self.assertEqual(runtime.calls, ['generation', 'audit', 'repair', 'verify'])
        self.assertEqual(read_json(root / 'issues.json')['issues'][0]['state'], 'open')

    def test_review_worker_timeout_stops_and_preserves_open_issue(self):
        runtime = OfflineRuntime()
        runtime.empty_after = 1
        with patch.object(runtime, 'verify', side_effect=workflow.StopWorkflow('budget_exhausted', 'review worker timeout')):
            _, result = self.run_fixture(runtime, max_repairs=3)
        self.assertEqual(result['status'], 'verification_incomplete')
        self.assertEqual(result['open_issues'], ['a000-F1'])
        self.assertEqual(runtime.calls[-1], 'repair')
        self.assertEqual(result['stages'][-1]['kind'], 'repair_verification')
        self.assertEqual(runtime.calls.count('repair'), 1)

    def test_missing_findings_is_incomplete_not_empty(self):
        runtime = OfflineRuntime()
        original = runtime.audit
        def missing(*args):
            path = original(*args)
            for manifest in path.glob('turns/*/changes/manifest.json'):
                value = read_json(manifest)
                del value['changed']['findings.json']
                write_json(manifest, value)
            return path
        with patch.object(runtime, 'audit', side_effect=missing):
            root, result = self.run_fixture(runtime)
        self.assertEqual(result['status'], 'audit_incomplete')
        index = read_json(root / 'issues.json')
        self.assertEqual(index['import_status'], 'incomplete')
        self.assertEqual(index['imports'][0]['status'], 'failed')
        self.assertIsNone(index['imports'][0]['issue_count'])
        self.assertTrue(Path(index['imports'][0]['findings_path']).parent.is_dir())
        self.assertEqual(workflow.inspect(root)['issue_index_status'], 'incomplete')
        self.assertEqual(runtime.calls, ['generation', 'audit'])

    def test_failed_audit_keeps_drafts_visible_without_importing_and_inspects_old_runs(self):
        runtime = OfflineRuntime(incomplete=True)
        original = runtime.audit
        def fail(*args):
            audit = original(*args)
            data = read_json(audit / 'run.json')
            data.update(stop='external_error', reason='Fixture service refusal',
                        agents={'record': 'agents.json', 'thread_count': 2, 'usage': {'output_tokens': 17}})
            write_json(audit / 'run.json', data)
            put(audit / 'work/report.md', 'Evidence for a new defect, not yet in the index.\n')
            write_json(audit / 'work/findings.json', {'candidate_commit': args[1]['commit'], 'issues': []})
            raise workflow.StopWorkflow('audit_failed', 'Fixture service refusal')
        with patch.object(runtime, 'audit', side_effect=fail):
            root, result = self.run_fixture(runtime)
        self.assertEqual(result['status'], 'audit_failed')
        self.assertEqual(runtime.calls, ['generation', 'audit'])
        index = read_json(root / 'issues.json')
        self.assertEqual(index['import_status'], 'incomplete')
        self.assertEqual(index['issues'], [])
        self.assertIsNone(index['imports'][0]['issue_count'])
        draft, = index['pending_reports']
        self.assertEqual(draft['status'], 'needs_review')
        self.assertEqual(draft['candidate_commit'], result['current_candidate']['commit'])
        self.assertIn('new defect', Path(draft['report']).read_text())
        self.assertEqual(read_json(Path(draft['index']))['issues'], [])
        self.assertEqual(result['pending_audit_reports'], [draft])
        stage = result['stages'][-1]
        self.assertEqual(stage['agents']['usage']['output_tokens'], 17)
        self.assertEqual(stage['audit_reason'], 'Fixture service refusal')

        # Older archives have no top-level draft or failed-stage usage pointers.
        for key in ('pending_report', 'audit_run', 'audit_stop', 'audit_reason', 'agents'):
            stage.pop(key, None)
        result.pop('pending_audit_reports')
        write_json(root / 'experiment.json', result)
        before = {p: p.read_bytes() for p in root.rglob('*') if p.is_file() and '.git' not in p.parts}
        inspected = workflow.inspect(root)
        self.assertEqual(inspected['pending_audit_reports'], [draft])
        self.assertEqual(inspected['stages'][-1]['agents']['thread_count'], 2)
        self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_failed_review_draft_cannot_close_issue_and_damaged_index_stays_visible(self):
        runtime = OfflineRuntime()
        runtime.empty_after = 1
        original = runtime.verify
        def fail(*args):
            audit = original(*args)
            put(audit / 'work/review.json', '{"issues": [{"disposition": "fixed"')
            data = read_json(audit / 'run.json')
            data.update(stop='external_error', last_completed_report=None)
            write_json(audit / 'run.json', data)
            raise workflow.StopWorkflow('audit_failed', 'Fixture interrupted review')
        with patch.object(runtime, 'verify', side_effect=fail):
            root, result = self.run_fixture(runtime)
        self.assertEqual(result['status'], 'verification_failed')
        self.assertEqual(runtime.calls, ['generation', 'audit', 'repair', 'verify'])
        self.assertEqual(result['open_issues'], ['a000-F1'])
        self.assertEqual(read_json(root / 'issues.json')['issues'][0]['state'], 'open')
        draft, = [item for item in result['pending_audit_reports']
                  if item.get('index', '').endswith('/work/review.json')]
        self.assertTrue(draft['index'].endswith('/work/review.json'))
        self.assertEqual(Path(draft['index']).read_text(), '{"issues": [{"disposition": "fixed"')

    def test_final_audit_can_be_repaired_with_review_reserved(self):
        runtime = OfflineRuntime()
        clock = [100.0]
        agent, audit, verify = runtime.agent, runtime.audit, runtime.verify
        def timed_agent(stage):
            result = agent(stage)
            meta = read_json(stage / 'run.json')
            clock[0] += 100 if meta['workflow_role'] == 'generation' else meta['settings']['timeout_seconds']
            return result
        def timed(call, *args):
            result = call(*args)
            clock[0] += args[-2]
            return result
        with patch.object(runtime, 'agent', side_effect=timed_agent), \
             patch.object(runtime, 'audit', side_effect=lambda *args: timed(audit, *args)), \
             patch.object(runtime, 'verify', side_effect=lambda *args: timed(verify, *args)), \
             patch('workflow.time.monotonic', side_effect=lambda: clock[0]):
            _, result = self.run_fixture(runtime, total_seconds=5000, max_repairs=3)
        self.assertEqual(result['stop_reason'], 'final_review_complete')
        self.assertEqual(runtime.calls, ['generation', 'audit', 'repair', 'verify'])
        self.assertEqual([s['kind'] for s in result['stages']],
                         ['generation', 'final_audit', 'repair', 'repair_verification'])
        self.assertEqual(result['stages'][2]['allocated_seconds'], 340)
        self.assertEqual(runtime.budgets, [('audit', 3600), ('verify', 900)])
        self.assertEqual(result['elapsed_seconds'], 4940)

    def test_slow_feedback_copy_rechecks_minimum_repair_budget(self):
        runtime = OfflineRuntime()
        clock = [100.0]
        original = workflow.copy_tree
        def slow_copy(source, destination, *args, **kwargs):
            original(source, destination, *args, **kwargs)
            if destination.name == 'feedback' and destination.parent.name == '.forge':
                # Leave 200 s for repair after reserving independent review and capture.
                reserve = self.settings.repair_verification_seconds + 60
                clock[0] = 100.0 + self.settings.total_seconds - reserve - 200
        with patch('workflow.copy_tree', side_effect=slow_copy), \
             patch('workflow.time.monotonic', side_effect=lambda: clock[0]):
            _, result = self.run_fixture(runtime, max_repairs=3)
        self.assertEqual(runtime.calls.count('repair'), 0)
        self.assertEqual(result['stop_reason'], 'insufficient_repair_budget')
        self.assertEqual(runtime.budgets, [('audit', 3600)])
        skipped = [stage for stage in result['stages'] if stage['kind'] == 'repair']
        self.assertEqual(skipped[0]['status'], 'not_started')

    def test_early_generation_finish_leaves_time_for_repairs_and_ends_at_review(self):
        runtime = OfflineRuntime()
        clock = [100.0]
        original_agent, original_audit, original_verify = runtime.agent, runtime.audit, runtime.verify
        def agent(stage):
            result = original_agent(stage)
            clock[0] += 1800
            return result
        def audit(settings, candidate, folder, seconds, timeout):
            result = original_audit(settings, candidate, folder, seconds, timeout)
            clock[0] += seconds
            return result
        def verify(settings, candidate, folder, context, seconds, timeout):
            result = original_verify(settings, candidate, folder, context, seconds, timeout)
            clock[0] += seconds
            return result
        with patch.object(runtime, 'agent', side_effect=agent), patch.object(runtime, 'audit', side_effect=audit), \
             patch.object(runtime, 'verify', side_effect=verify), patch('workflow.time.monotonic', side_effect=lambda: clock[0]):
            _, result = self.run_fixture(runtime, max_repairs=3)
        self.assertEqual(runtime.calls.count('repair'), 2)
        self.assertEqual(result['stop_reason'], 'final_review_complete')
        self.assertEqual(runtime.budgets[-1], ('verify', 900))
        self.assertLessEqual(result['elapsed_seconds'], self.settings.total_seconds)

    def test_zero_repairs_still_audits_generation(self):
        runtime = OfflineRuntime()
        _, result = self.run_fixture(runtime, max_repairs=0)
        self.assertEqual(result['status'], 'cycle_complete')
        self.assertEqual(runtime.calls, ['generation', 'audit'])
        self.assertEqual(runtime.budgets, [('audit', 3600)])

    def test_specification_claim_requires_review_even_without_code_changes(self):
        for action in ('needs_specification', 'no_change'):
            with self.subTest(action=action):
                runtime = OfflineRuntime(action=action)
                if action == 'no_change':
                    runtime.repair_dispositions = {'a000-F1': 'needs_specification'}
                runtime.review_disposition, runtime.empty_after = 'needs_specification', 1
                root, result = self.run_fixture(runtime, max_repairs=3)
                self.assertEqual(result['status'], 'needs_specification')
                self.assertEqual(result['open_issues'], ['a000-F1'])
                self.assertEqual(workflow.inspect(root)['awaiting_specification'], ['a000-F1'])
                self.assertEqual(runtime.calls, ['generation', 'audit', 'repair', 'verify'])
                self.assertEqual(result['candidates'][-1]['changes'], {'added': [], 'deleted': [], 'modified': []})
                self.assertEqual(read_json(root / 'issues.json')['issues'][0]['reviews'][0]['disposition'], 'needs_specification')

    def test_mixed_issues_keep_repairs_moving_with_deferred_evidence_as_context(self):
        runtime = OfflineRuntime()
        runtime.empty_after = 1
        runtime.repair_dispositions = {'a000-F2': 'needs_specification'}
        runtime.review_dispositions = {'a000-F2': 'needs_specification', 'a000-F3': 'unresolved'}
        audit, verify = runtime.audit, runtime.verify
        def with_three_issues(*args):
            run = audit(*args)
            path = run / 'turns/0001/changes/files/findings.json'
            data = read_json(path)
            if data['issues']:
                data['issues'] += [data['issues'][0] | {'id': name} for name in ('F2', 'F3')]
                write_json(path, data)
            return run
        def review_next(settings, candidate, *args):
            if candidate['version'] == 2:
                runtime.review_dispositions['a000-F3'] = 'fixed'
            return verify(settings, candidate, *args)
        with patch.object(runtime, 'audit', side_effect=with_three_issues), patch.object(runtime, 'verify', side_effect=review_next):
            root, result = self.run_fixture(runtime, max_repairs=3)
        self.assertEqual(runtime.calls.count('repair'), 2)
        self.assertEqual(result['status'], 'needs_specification')
        self.assertEqual(result['awaiting_specification'], ['a000-F2'])
        self.assertEqual(result['open_issues'], ['a000-F2'])
        issues = read_json(root / 'issues.json')['issues']
        self.assertEqual([item['state'] for item in issues], ['fixed', 'needs_specification', 'fixed'])
        self.assertEqual(len(issues[1]['reviews']), 1)
        feedback = root / 'feedback/001'
        self.assertEqual(read_json(feedback / 'handoff.json')['repair_issue_ids'], ['a000-F3'])
        delivered = read_json(feedback / 'issues.json')['issues']
        self.assertEqual([item['id'] for item in delivered], ['a000-F2', 'a000-F3'])
        self.assertTrue((feedback / delivered[0]['reviews'][0]['evidence'][0]).is_file())
        self.assertEqual(read_json(root / 'reviews/002/context/request.json')['issue_ids'], ['a000-F3'])

    def test_rejected_specification_claim_returns_to_repair(self):
        runtime = OfflineRuntime(action='no_change')
        runtime.repair_dispositions = {'a000-F1': 'needs_specification'}
        runtime.review_disposition, runtime.empty_after = 'unresolved', 1
        verify = runtime.verify
        def review_next(settings, candidate, *args):
            if candidate['version'] == 2:
                runtime.review_disposition = 'not_substantiated'
            return verify(settings, candidate, *args)
        with patch.object(runtime, 'verify', side_effect=review_next):
            root, result = self.run_fixture(runtime, max_repairs=3)
        self.assertEqual(runtime.calls.count('repair'), 2)
        self.assertEqual(result['stop_reason'], 'no_open_findings')
        self.assertEqual(result['awaiting_specification'], [])
        self.assertEqual(read_json(root / 'feedback/001/handoff.json')['repair_issue_ids'], ['a000-F1'])
        item = read_json(root / 'issues.json')['issues'][0]
        self.assertEqual([review['disposition'] for review in item['reviews']], ['unresolved', 'not_substantiated'])

    def test_specification_claim_cannot_deliver_changed_materials(self):
        runtime = OfflineRuntime(action='needs_specification')
        agent = runtime.agent
        def change_input(stage):
            result = agent(stage)
            if read_json(stage / 'run.json')['workflow_role'] == 'repair':
                put(stage / 'workspace/protocol.md', 'The repair silently changes supplied semantics.')
            return result
        with patch.object(runtime, 'agent', side_effect=change_input):
            _, result = self.run_fixture(runtime)
        self.assertEqual(result['status'], 'needs_specification')
        self.assertEqual(len(result['candidates']), 1)
        self.assertEqual(result['awaiting_specification'], [])  # No independent confirmation.
        self.assertEqual(runtime.calls[-1], 'repair')

    def test_wrong_repair_version_does_not_produce_next_candidate(self):
        _, result = self.run_fixture(OfflineRuntime(wrong_commit=True))
        self.assertEqual(result['status'], 'controller_step_failed')
        self.assertIn('different candidate', result['reason'])
        self.assertEqual(len(result['candidates']), 1)

    def test_material_edit_and_missing_completed_report_are_separate_failures(self):
        for runtime, expected, calls in (
            (OfflineRuntime(change_material=True), 'needs_specification', ['generation']),
            (OfflineRuntime(incomplete=True), 'audit_incomplete', ['generation', 'audit']),
            (OfflineRuntime(failure='timed_out'), 'stage_timed_out', ['generation']),
        ):
            with self.subTest(expected=expected):
                _, result = self.run_fixture(runtime)
                self.assertEqual(result['status'], expected)
                self.assertEqual(runtime.calls, calls)

    def test_budget_and_environment_failures_do_not_launch_generation(self):
        runtime = OfflineRuntime()
        root = workflow.prepare(self.settings)
        with patch('workflow.time.monotonic', side_effect=[10, 10 + self.settings.total_seconds + 1, 10 + self.settings.total_seconds + 2]):
            result = workflow.execute(root, runtime)
        self.assertEqual(result['status'], 'budget_exhausted')
        self.assertEqual(runtime.calls, [])
        with patch.object(runtime, 'check', return_value={'ready': False}):
            _, result = self.run_fixture(runtime)
        self.assertEqual(result['status'], 'environment_blocked')
        self.assertEqual(runtime.calls, [])

    def test_sigterm_between_children_retains_interrupted_state_and_restores_handler(self):
        runtime = OfflineRuntime()
        previous = signal.getsignal(signal.SIGTERM)
        with patch.object(runtime, 'check', side_effect=lambda _: os.kill(os.getpid(), signal.SIGTERM)):
            root, result = self.run_fixture(runtime)
        self.assertEqual(result['status'], 'interrupted')
        self.assertEqual(read_json(root / 'experiment.json')['status'], 'interrupted')
        self.assertEqual(signal.getsignal(signal.SIGTERM), previous)

    def test_configuration_is_strict_and_preserves_virtualenv_path(self):
        for values in ({'total_seconds': True}, {'audit_seconds': float('nan')}, {'initial_audit_seconds': 0}, {'max_repairs': -1},
                       {'audit_calls': 1.2}, {'extra': 1}, {'audit_reasoning_effort': 'typo'}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                from_dict(values, self.root)
        virtual = self.root / 'venv/python'
        virtual.parent.mkdir()
        virtual.symlink_to(sys.executable)
        settings = from_dict({'audit_python': 'venv/python'}, self.root)
        self.assertEqual(settings.audit_python, str(virtual))
        config = self.root / 'settings.json'
        config.write_text('{"output_root":"relative-output"}')
        self.assertEqual(load(config).output_root, str(self.root / 'relative-output'))

        self.assertEqual(from_dict({'audit_seconds': 1200}, self.root).initial_audit_seconds, 1200)
        self.assertEqual(load().initial_audit_seconds, 3600)

    def test_prepared_audit_prompt_survives_later_edits(self):
        prompt = self.root / 'AUDIT.md'
        original = 'Original task\n\n<!-- continuation -->\n\nOriginal continuation\n'
        put(prompt, original)
        settings = from_dict(self.settings.to_dict() | {'audit_prompt': str(prompt)}, ROOT)
        root = workflow.prepare(settings, 'prompt-copy')
        prompt.write_text('Changed task\n\n<!-- continuation -->\n\nChanged continuation\n')
        runtime = OfflineRuntime()
        result = workflow.execute(root, runtime)
        self.assertEqual(result['status'], 'cycle_complete')
        self.assertEqual(runtime.audit_prompt, original)

    def test_malformed_audit_prompt_fails_before_preparing_experiment(self):
        prompt = self.root / 'AUDIT.md'
        settings = from_dict(self.settings.to_dict() | {'audit_prompt': str(prompt)}, ROOT)
        for content in ('no continuation', '<!-- continuation --> next',
                        'task <!-- continuation --> next <!-- continuation --> last'):
            put(prompt, content)
            with self.subTest(content=content), self.assertRaisesRegex(ValueError, 'Audit/review prompt'):
                workflow.prepare(settings, 'bad-prompt')
        self.assertFalse(Path(settings.output_root).exists())

    def test_audit_exit_and_response_must_agree(self):
        for number, (response, code, exception) in enumerate((
            ({'stop': 'agent_call_limit'}, 0, ValueError),
            ({'stop': 'agent_call_limit'}, 7, workflow.StopWorkflow),
            ({'stop': 'turn_timeout'}, 1, None),
            ({'stop': 'cancelled'}, 1, workflow.StopWorkflow),
        )):
            folder = self.root / f'audit-{number}'
            if number:
                response['run_dir'] = str(folder / 'runs/fixture')
            def fake_invoke(argv, logs, timeout, cwd):
                logs.mkdir(parents=True)
                write_json(logs / 'stdout.log', response)
                return {'status': 'completed', 'returncode': code}
            with self.subTest(number=number), patch('workflow.invoke', side_effect=fake_invoke):
                if exception:
                    with self.assertRaises(exception):
                        workflow.Runtime().audit(self.settings, {'path': '/unused'}, folder, 30, 40)
                else:
                    result = workflow.Runtime().audit(self.settings, {'path': '/unused'}, folder, 30, 40)
                    self.assertEqual(result, folder / 'runs/fixture')


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='forge-handoff-')
        self.root = Path(self.temp.name)
        put(self.root / 'candidate/go.mod', 'module example.com/mixepaxos\n')
        self.candidate = {'path': str(self.root / 'candidate'), 'commit': 'fixture-commit'}
        self.audit = fixture_audit(self.root / 'audit/runs/fixture', self.candidate)

    def tearDown(self):
        self.temp.cleanup()

    def test_partial_draft_is_retained_but_not_delivered_as_completed_work(self):
        destination = self.root / 'feedback'
        result = prepare_handoff(self.audit, self.candidate, destination)
        self.assertEqual(result['last_completed_turn'], 1)
        self.assertEqual(result['incomplete_turns'], [2])
        self.assertEqual(result['supplemental_turns'], [
            {'number': 2, 'status': 'timeout', 'path': 'raw/turns/0002'}])
        self.assertEqual((destination / 'audit-work/tests/witness.bin').read_bytes(), b'\x01\x00\xff')
        self.assertEqual((destination / 'raw/turns/0002/changes/files/tests/witness.bin').read_bytes(), b'\x02\x00\xff')
        self.assertIn('PASS may mean', result['test_polarity'])

        entry = {'kind': 'audit', 'status': 'returned', 'path': str(self.root / 'audit')}
        workflow.record_audit_progress(self.root, entry)
        self.assertEqual(entry['pending_report']['status'], 'needs_review')
        self.assertEqual(entry['pending_report']['last_completed_turn'], 1)
        self.assertEqual(entry['pending_report']['report'], str(self.audit / 'work/report.md'))
        self.assertNotIn('finding_import', entry)
        data = read_json(self.audit / 'run.json')
        data['turns'][1]['status'] = 'completed'
        write_json(self.audit / 'run.json', data)
        fresh = {'kind': 'audit', 'status': 'returned', 'path': str(self.root / 'audit')}
        workflow.record_audit_progress(self.root, fresh)
        self.assertNotIn('pending_report', fresh)

    def test_failed_output_navigation_rejects_links_without_masking_stage_failure(self):
        folder = self.root / 'failed'
        (folder / 'runs').mkdir(parents=True)
        (folder / 'runs/linked').symlink_to(self.audit, target_is_directory=True)
        entry = {'kind': 'audit', 'status': 'audit_failed', 'path': str(folder)}
        workflow.record_audit_progress(self.root, entry)
        self.assertEqual(entry['status'], 'audit_failed')
        self.assertIn('link is not allowed', entry['retained_output_error'])
        self.assertNotIn('pending_report', entry)

    def test_archive_reconstructs_directory_replaced_by_file(self):
        first = self.audit / 'turns/0001/changes'
        put(first / 'files/diagnostic/notes.txt', 'Old diagnostic directory')
        manifest = read_json(first / 'manifest.json')
        manifest['changed']['diagnostic/notes.txt'] = {}
        write_json(first / 'manifest.json', manifest)
        second = self.audit / 'turns/0002/changes'
        put(second / 'files/diagnostic', 'Now a single diagnostic file')
        write_json(second / 'manifest.json', {'changed': {'diagnostic': {}}, 'deleted': ['diagnostic/notes.txt']})
        record = read_json(self.audit / 'run.json')
        record['turns'][1]['status'] = 'completed'
        write_json(self.audit / 'run.json', record)
        prepare_handoff(self.audit, self.candidate, self.root / 'feedback')
        self.assertEqual((self.root / 'feedback/audit-work/diagnostic').read_text(), 'Now a single diagnostic file')

    def test_wrong_commit_and_escaping_archive_paths_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'commit does not match'):
            prepare_handoff(self.audit, self.candidate | {'commit': 'another'}, self.root / 'bad')
        manifest = self.audit / 'turns/0001/changes/manifest.json'
        value = read_json(manifest)
        value['deleted'] = ['../outside']
        write_json(manifest, value)
        with self.assertRaisesRegex(ValueError, 'Unsafe artifact'):
            prepare_handoff(self.audit, self.candidate, self.root / 'escape')
        (self.root / 'link').symlink_to(self.root / 'candidate', target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'link is not allowed'):
            inside(self.root, 'link/go.mod')

    def test_deletions_and_reused_report_version_reconstruct_last_completed_turn(self):
        record = read_json(self.audit / 'run.json')
        record['turns'][1]['status'] = 'completed'
        write_json(self.audit / 'run.json', record)
        write_json(self.audit / 'turns/0002/changes/manifest.json', {'changed': {}, 'deleted': ['tests/witness.bin']})
        result = prepare_handoff(self.audit, self.candidate, self.root / 'feedback')
        self.assertEqual(result['last_completed_turn'], 2)
        self.assertFalse((self.root / 'feedback/audit-work/tests/witness.bin').exists())
        self.assertIn('F1:', (self.root / 'feedback/audit-work/report.md').read_text())


class BridgeIntegrationTests(unittest.TestCase):
    def test_real_export_preserves_candidate_materials_and_git_identity_without_model(self):
        from auditor.runner import capture_source, file_inventory
        from runtime.replay import regular_file
        settings = WorkflowSettings()
        with tempfile.TemporaryDirectory(prefix='forge-bridge-') as temp:
            root = Path(temp)
            workspace = root / 'workspace'
            put(workspace / 'go.mod', 'module example.com/mixepaxos\n\ngo 1.22\n')
            put(workspace / 'main.go', 'package main\nfunc main() {}\n')
            retained = {'protocol.md': (ROOT / 'inputs/protocol.md').read_text(),
                        'pseudocode.md': (ROOT / 'inputs/pseudocode.md').read_text(),
                        'wire/auth.go': 'package wire\nfunc Authenticate() bool { return false }\n',
                        'wire/auth.zig': '// Source language is not a capture policy.\n',
                        'docs/secret-key.md': 'Authentication implementation notes.\n',
                        'tests/token.txt': 'Ordinary parser test input.\n',
                        'auth.json': '{"access_token": "public-test-token"}\n',
                        '.env.example': 'PORT=8080\n', '.env': 'LOCAL_TEST=1\n',
                        'fixtures/credentials.json': '{"password": "test-password"}\n',
                        'wire/credentials.go': 'package wire\nvar Password = "test-password"\n',
                        'tests/tls_test.go': 'package tests\nvar Marker = "-----BEGIN PRIVATE KEY-----"\n'}
            for name, content in retained.items():
                put(workspace / name, content)
            put(workspace / '.codex/auth.json', 'Framework private directory fixture.\n')
            put(workspace / '.forge/feedback/report.md', 'Old report must not reach fresh audit.\n')
            put(workspace / 'AGENTS.md', 'Instructions must not become audit instructions.\n')
            (workspace / 'outside').symlink_to('/etc/hostname')
            git(workspace, 'init', '--quiet', '--template=')
            candidate = workflow.Runtime().export(settings, workspace, root / 'candidate', root / 'export', 20)
            self.assertEqual(candidate['files'], sorted(['go.mod', 'main.go', *retained]))
            self.assertEqual(candidate_commit(root / 'candidate'), candidate['commit'])
            self.assertEqual(set(candidate['excluded']), {'.codex/auth.json', '.forge/feedback/report.md', 'AGENTS.md', 'outside'})
            captured = capture_source(root / 'candidate', root / 'captured', time.monotonic() + 20)
            self.assertFalse(captured['excluded'])
            inventory, excluded = file_inventory(root / 'captured')
            self.assertFalse(excluded)
            for name in candidate['files']:
                self.assertIn(name, inventory)
                self.assertEqual(regular_file(root / 'captured', name)[0], (workspace / name).read_bytes())
            # Generate the actual audit config, but replace process execution before any model call.
            folder = root / 'audit'
            def fake_invoke(argv, logs, timeout, cwd):
                logs.mkdir(parents=True)
                write_json(logs / 'stdout.log', {'run_dir': str(folder / 'runs/fixture'), 'stop': 'agent_call_limit'})
                return {'status': 'completed', 'returncode': 0}
            with patch('workflow.invoke', side_effect=fake_invoke):
                workflow.Runtime().audit(settings, candidate, folder, 30, 40)
            config = read_json(folder / 'config.json')
            self.assertEqual(config['agent_model'], 'gpt-6.1-sol')
            self.assertEqual(config['agent_reasoning_effort'], 'high')
            self.assertEqual(config['task_path'], settings.audit_prompt)
            code = ('import sys; '
                    'from auditor.config import load_config,validate_selection; '
                    'c=load_config(sys.argv[1]); t=validate_selection(c); '
                    'assert t["expected_module"]=="example.com/mixepaxos"; print("config valid; no model call")')
            process = subprocess.run([settings.audit_python, '-c', code, str(folder / 'config.json')],
                                     cwd=ROOT, capture_output=True, text=True, timeout=20)
            self.assertEqual(process.returncode, 0, process.stderr)


if __name__ == '__main__':
    unittest.main()
