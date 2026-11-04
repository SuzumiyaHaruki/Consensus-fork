"""Version, evidence and closure semantics of ordinary issue records."""
from pathlib import Path
import json
import tempfile
import unittest

from generator.runner import read_json, write_json
from artifacts import read_repair_result, require_description
from issues import findings, review_result, apply_review, pending, feedback_bundle, catalog_entry


class IssueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.bundle = Path(self.temp.name)
        (self.bundle / 'audit-work').mkdir()
        (self.bundle / 'audit-work/observation.txt').write_text('Retained fixture observation')
        self.before = {'commit': 'before', 'version': 0}
        self.after = {'commit': 'after', 'version': 1}
        (self.bundle / 'raw/executions/checked').mkdir(parents=True)
        write_json(self.bundle / 'raw/executions/checked/result.json', {
            'execution_id': 'checked', 'argv': ['fixture-only'], 'status': 'completed', 'exit_code': 1,
            'source_context': {'kind': 'candidate_copy', 'commit': 'after'}})
        self.finding = {'id': 'F1', 'summary': 'Example', 'property': 'Required property',
                        'assumptions': 'Legal conditions', 'reproduction': 'fixture only',
                        'polarity': 'PASS observes defect', 'evidence': ['work/observation.txt']}
        self.review = {'before_commit': 'before', 'after_commit': 'after', 'summary': 'Example review',
                       'issues': [{'id': 'a000-F1', 'disposition': 'fixed', 'method': 'executed',
                                   'before_observation': 'Before fixture', 'after_observation': 'After fixture',
                                   'reason': 'Example reasoning',
                                   'evidence': ['work/observation.txt', 'executions/checked/result.json']}]}

    def find(self, **changes):
        write_json(self.bundle / 'audit-work/findings.json',
                   {'candidate_commit': 'before', 'coverage': 'Fixture only', 'issues': [self.finding]} | changes)
        return findings(self.bundle, self.before, 0)[1]

    def verify(self, value=None):
        write_json(self.bundle / 'audit-work/review.json', value or self.review)
        return review_result(self.bundle, self.before, self.after, ['a000-F1'])

    def test_evidence_and_original_version_survive_independent_closure(self):
        issues = self.find()
        self.assertEqual(issues[0]['source_commit'], 'before')
        self.assertEqual(len(pending(issues)), 1)
        result = self.verify()
        apply_review(issues, result, self.bundle, self.after)
        self.assertEqual(pending(issues), [])
        self.assertEqual(issues[0]['source_commit'], 'before')
        self.assertEqual(issues[0]['reviews'][0]['after_commit'], 'after')
        self.assertNotIn('assessment', issues[0]['reviews'][0])

    def test_review_new_defect_remains_pending_with_after_version_and_evidence(self):
        items = self.find()
        self.review['new_issues'] = [self.finding | {'id': 'F2'}]
        result = self.verify()
        apply_review(items, result, self.bundle, self.after)
        self.assertEqual([item['id'] for item in pending(items)], ['r001-F2'])
        self.assertEqual(items[1]['source_commit'], 'after')
        self.assertEqual(items[1]['evidence'], ['audit-work/observation.txt'])

    def test_invalid_new_review_defect_prevents_partial_closure(self):
        for value in (None, {}, [self.finding | {'evidence': ['work/missing']}], [self.finding, self.finding]):
            items = self.find()
            with self.subTest(value=value), self.assertRaises(ValueError):
                result = self.verify(self.review | {'new_issues': value})
                apply_review(items, result, self.bundle, self.after)
            self.assertEqual(items[0]['state'], 'open')

    def test_trace_checks_are_computed_and_bad_trace_does_not_erase_finding(self):
        path = self.bundle / 'audit-work/trace.json'
        path.write_text('{bad JSON')
        self.finding.update(trace_files=['work/trace.json'], trace_checks=[{'status': 'forged'}],
                            legality={'timing': 'Argument retained verbatim'}, reachability='Source only',
                            impact='Local result only', causal_explanation=['Completion used too early'],
                            variants=['Proposed, not executed'])
        item = self.find()[0]
        self.assertEqual(item['trace_files'], ['audit-work/trace.json'])
        self.assertEqual(item['trace_checks'][0]['status'], 'invalid_trace')
        self.assertEqual(item['legality'], self.finding['legality'])
        self.assertEqual(item['state'], 'open')
        self.assertTrue(any('invalid_trace' in note for note in item['evidence_notes']))
        self.assertFalse(any('No substantive' in note for note in item['evidence_notes']))
        self.finding['trace_files'] = ['work/../trace.json']
        with self.assertRaises(ValueError):
            self.find()

    def test_legacy_record_gets_notes_not_import_failure(self):
        item = self.find()[0]
        self.assertEqual(item['trace_checks'], [])
        self.assertEqual(item['evidence_feedback'][0]['code'], 'execution_not_linked')
        self.assertFalse(any('No substantive' in note for note in item['evidence_notes']))
        self.review['issues'][0].update(disposition='unresolved', evidence=['work/observation.txt'])
        review = self.verify()['issues'][0]
        self.assertEqual(review['evidence_feedback'][0]['code'], 'execution_not_linked')

    def test_fixed_requires_execution_link_but_does_not_infer_test_polarity(self):
        original = self.review['issues'][0]['evidence']
        self.review['issues'][0]['evidence'] = ['work/observation.txt']
        with self.assertRaisesRegex(ValueError, 'linked completed execution'):
            self.verify()
        self.review['issues'][0]['evidence'] = original
        receipt = self.bundle / 'raw/executions/checked/result.json'
        good = read_json(receipt)
        for change in ({'status': 'timeout'}, {'exit_code': None},
                       {'source_context': {'kind': 'candidate_copy', 'commit': 'before'}}):
            write_json(receipt, good | change)
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'linked completed execution'):
                self.verify()
        write_json(receipt, good)
        self.assertEqual(self.verify()['issues'][0]['execution_records'][0]['exit_code'], 1)

    def test_native_shell_receipt_is_usable_but_has_no_source_binding(self):
        path = self.bundle / 'raw/turns/0001/stdout.jsonl'
        path.parent.mkdir(parents=True)
        event = {'type': 'item.completed', 'item': {'id': 'cmd1', 'type': 'command_execution',
                 'command': 'fixture-only', 'exit_code': 0, 'aggregated_output': 'Fixture, not a consensus test'}}
        unrelated = {'type': 'item.completed', 'item': {'id': 'cmd2', 'type': 'command_execution',
                     'command': 'unrelated command', 'exit_code': 0}}
        path.write_text('invalid\n[]\n' + json.dumps(event) + '\n' + json.dumps(unrelated) + '\n')
        self.review['issues'][0]['evidence'] = ['turns/0001/stdout.jsonl']
        with self.assertRaisesRegex(ValueError, 'linked completed execution'):
            self.verify()
        self.review['issues'][0]['evidence'] = ['turns/0001/stdout.jsonl#cmd1']
        item = self.verify()['issues'][0]
        self.assertEqual(len(item['execution_records']), 1)
        self.assertEqual(item['execution_records'][0]['command'], 'fixture-only')
        self.assertEqual(item['evidence'], ['raw/turns/0001/stdout.jsonl#cmd1'])
        self.assertEqual(item['evidence_feedback'][0]['code'], 'version_not_bound')
        for contents in (json.dumps(event | {'type': 'item.started'}), json.dumps(event) + '\n' + json.dumps(event)):
            path.write_text(contents)
            with self.assertRaisesRegex(ValueError, 'Expected one completed native command'):
                self.verify()

    def test_overview_is_short_navigation_and_keeps_full_original_records(self):
        long_text = 'Long investigation detail. ' * 1000
        self.finding.update(summary=long_text, reproduction={'steps': long_text})
        items = self.find()
        write_json(self.bundle/'handoff.json', {'candidate_commit': 'before'})
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp)/'feedback'
            feedback_bundle(dest, self.bundle, self.before, items)
            overview = (dest/'overview.md').read_text()
            self.assertLess(len(overview), 3000)
            self.assertIn('issues.json', overview)
            self.assertEqual(read_json(dest/'issues.json')['issues'][0]['summary'], long_text)
            self.assertEqual((dest/'audit-work/findings.json').read_bytes(),
                             (self.bundle/'audit-work/findings.json').read_bytes())

    def test_optional_cases_survive_without_issues_with_original_versions_and_artifacts(self):
        folder = self.bundle/'raw/executions/checked'
        (folder/'artifacts').mkdir()
        (folder/'artifacts/history.json').write_text('["observation"]')
        record = read_json(folder/'result.json')
        record['artifacts'] = {'files': [{'path': 'history.json', 'retained_path': 'artifacts/history.json'}], 'excluded': []}
        write_json(folder/'result.json', record)
        questions = [{'question': 'Unsettled timing interpretation', 'context': 'Report explains the alternatives'}]
        cases = [{'summary': 'No defect observed', 'reproduction': 'Run the retained command; finite scope only',
                  'evidence': ['executions/checked/result.json']}]
        self.find(issues=[], cases=cases, open_questions=questions)
        (self.bundle/'audit-work/report.md').write_text('Full case and question explanation')
        note = catalog_entry(self.bundle, self.before, 'a000', 'findings.json')
        self.assertEqual(note['cases'][0]['recorded_for_commit'], 'before')
        # The actual source context is not rewritten to the reporting candidate.
        self.assertEqual(note['cases'][0]['execution_records'][0]['source_context']['commit'], 'after')
        with tempfile.TemporaryDirectory() as temp:
            latest, dest = Path(temp)/'latest', Path(temp)/'feedback'
            latest.mkdir()
            write_json(latest/'handoff.json', {'candidate_commit': 'later'})
            feedback_bundle(dest, latest, {'commit': 'later'}, [], [note])
            brief = read_json(dest/'handoff.json')
            index = read_json(dest/brief['evidence_index_file'])
            self.assertEqual(brief['repair_issue_ids'], [])
            self.assertEqual(index['current_candidate_commit'], 'later')
            retained = index['entries'][0]
            self.assertEqual(retained['candidate_commit'], 'before')
            self.assertEqual(retained['open_questions'], questions)
            self.assertTrue((dest/retained['report']).is_file())
            execution = retained['cases'][0]['execution_records'][0]
            self.assertEqual((dest/execution['outputs']['artifact:history.json']).read_text(), '["observation"]')
            self.assertEqual(read_json(dest/'history.json')['issues'], [])

    def test_malformed_optional_cases_are_warnings_not_findings_or_closures(self):
        for cases in ('wrong type', [None], [{'summary': 'No files', 'reproduction': 'Not run', 'evidence': ['work/missing']} ]):
            items = self.find(cases=cases, open_questions=True)
            note = catalog_entry(self.bundle, self.before, 'a000', 'findings.json')
            self.assertEqual(note['cases'], [])
            self.assertEqual(note['open_questions'], [])
            self.assertGreaterEqual(len(note['warnings']), 2)
            self.assertEqual(items[0]['state'], 'open')
        self.find()
        self.assertIsNone(catalog_entry(self.bundle, self.before, 'a000', 'findings.json'))

    def test_closed_history_keeps_original_and_review_added_tests_for_next_version(self):
        items = self.find()
        (self.bundle / 'audit-work/regression.go.txt').write_text('Positive regression fixture')
        self.review['issues'][0]['evidence'].append('work/regression.go.txt')
        apply_review(items, self.verify(), self.bundle, self.after)
        with tempfile.TemporaryDirectory() as temp:
            latest, dest = Path(temp) / 'latest', Path(temp) / 'feedback'
            latest.mkdir()
            write_json(latest / 'handoff.json', {'candidate_commit': 'later'})
            feedback_bundle(dest, latest, {'commit': 'later'}, items)
            brief = read_json(dest / 'handoff.json')
            self.assertEqual(brief['repair_issue_ids'], [])
            self.assertEqual(read_json(dest / brief['issues_file'])['issues'], [])
            history = read_json(dest / brief['history_file'])['issues'][0]
            self.assertEqual(history['source_commit'], 'before')
            self.assertEqual(history['polarity'], 'PASS observes defect')
            self.assertEqual(history['reviews'][-1]['after_commit'], 'after')
            for item in (history, history['reviews'][-1]):
                self.assertTrue(all((dest / ref).is_file() for ref in item['evidence']))
            self.assertIn('Positive regression fixture', (dest / history['reviews'][-1]['evidence'][-1]).read_text())

    def test_execution_records_are_linked_and_remapped_in_feedback(self):
        folder = self.bundle / 'raw/executions/actual'
        folder.mkdir(parents=True)
        (folder / 'inputs/tests').mkdir(parents=True)
        (folder / 'inputs/tests/repro.py').write_text('print("witness")')
        (folder / 'stdout.txt').write_text('Witness observed')
        write_json(folder / 'result.json', {'execution_id': 'actual', 'argv': ['go', 'test', './...'],
                   'status': 'completed', 'exit_code': 1, 'cwd_relative': '.',
                   'source_context': {'kind': 'candidate_copy', 'commit': 'before', 'overlays': [
                       {'path': 'tests/repro.py', 'retained_path': 'inputs/tests/repro.py', 'replaces_source': False}]}})
        self.finding['evidence'].append('executions/actual/result.json')
        self.finding['execution_records'] = [{'path': 'forged'}]
        item = self.find()[0]
        self.assertEqual(item['execution_records'][0]['path'], 'raw/executions/actual/result.json')
        self.assertEqual(item['execution_records'][0]['exit_code'], 1)
        self.assertEqual(item['evidence_feedback'], [])  # Nonzero exit is not an inferred test polarity.
        self.review['issues'][0].update(disposition='unresolved', evidence=self.finding['evidence'])
        apply_review([item], self.verify(), self.bundle, self.after)
        write_json(self.bundle / 'handoff.json', {'candidate_commit': 'before'})
        with tempfile.TemporaryDirectory() as temp:
            latest = Path(temp) / 'latest'
            latest.mkdir()
            write_json(latest/'handoff.json', {'candidate_commit': 'after'})
            dest = Path(temp) / 'feedback'
            feedback_bundle(dest, latest, self.after, [item])
            delivered = read_json(dest/'issues.json')['issues'][0]['execution_records'][0]
            self.assertTrue((dest / delivered['path']).is_file())
            self.assertEqual(delivered['source_context']['commit'], 'before')
            self.assertEqual(delivered['restore'], {'tests/repro.py': 'previous/000/raw/executions/actual/inputs/tests/repro.py'})
            self.assertEqual((dest / delivered['restore']['tests/repro.py']).read_text(), 'print("witness")')
            self.assertEqual((dest / delivered['outputs']['stdout']).read_text(), 'Witness observed')
            reviewed = read_json(dest / 'issues.json')['issues'][0]['reviews'][0]['execution_records'][0]
            self.assertEqual(reviewed['restore'], delivered['restore'])
            self.assertEqual(reviewed['outputs'], delivered['outputs'])

    def test_feedback_remaps_historical_traces_and_review_without_loss(self):
        write_json(self.bundle / 'audit-work/trace.json', {
            'clock': 'controlled', 'members': ['A'], 'fault_limit': 0,
            'delivery_bound_ns': 10, 'end_ns': 0, 'events': []})
        write_json(self.bundle / 'handoff.json', {'candidate_commit': 'before'})
        self.finding.update(trace_files=['work/trace.json'], causal_explanation={'events': ['send', 'timer']})
        items = self.find()
        self.review['issues'][0].update(disposition='unresolved', trace_files=['work/trace.json'])
        apply_review(items, self.verify(), self.bundle, self.after)
        with tempfile.TemporaryDirectory() as folder:
            latest, dest = Path(folder) / 'latest', Path(folder) / 'feedback'
            latest.mkdir()
            write_json(latest / 'handoff.json', {'candidate_commit': 'after'})
            feedback_bundle(dest, latest, self.after, items)
            item = read_json(dest / 'issues.json')['issues'][0]
            for record in (item, item['reviews'][0]):
                self.assertEqual(record['trace_files'], ['previous/000/audit-work/trace.json'])
                self.assertEqual(record['trace_checks'][0]['path'], record['trace_files'][0])
                self.assertTrue((dest / record['trace_files'][0]).is_file())
            self.assertEqual(item['source_commit'], 'before')
            self.assertEqual(item['causal_explanation'], self.finding['causal_explanation'])
            self.assertEqual(read_json(dest / 'handoff.json')['overview_file'], 'overview.md')
            overview = (dest / 'overview.md').read_text()
            self.assertIn('a000-F1', overview)
            self.assertIn('previous/000/audit-work/trace.json', overview)
            self.assertIn('PASS can mean a defect', overview)
            self.assertEqual((dest / 'previous/000/audit-work/trace.json').read_bytes(),
                             (self.bundle / 'audit-work/trace.json').read_bytes())

    def test_real_audit_output_retains_structured_descriptions(self):
        # Exact findings.json from the interrupted 20261031 v2 run. Placeholder files below
        # exercise retained-path lookup only; this is not a consensus reproduction.
        raw = (Path(__file__).parent / 'fixtures/audit-findings.json').read_bytes()
        data = json.loads(raw)
        path = self.bundle / 'audit-work/findings.json'
        path.write_bytes(raw)
        for ref in data['issues'][0]['evidence']:
            dest = self.bundle / 'audit-work' / Path(ref).relative_to('work')
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text('Retained-path fixture; no execution claim.')
        coverage, found = findings(self.bundle, {'commit': data['candidate_commit'], 'version': 0}, 0)
        self.assertEqual(coverage, data['coverage'])
        self.assertEqual(found[0]['assumptions'], data['issues'][0]['assumptions'])
        self.assertEqual(found[0]['reproduction'], data['issues'][0]['reproduction'])
        self.assertEqual(found[0]['id'], 'a000-F-001')
        self.assertEqual(path.read_bytes(), raw)

    def test_repair_and_review_accept_structured_explanations_and_additional_fields(self):
        folder = self.bundle / '.forge'
        folder.mkdir()
        result = {'input_commit': 'before', 'action': 'repaired', 'summary': {'changes': ['Example fix']},
                  'tests': ['go test ./...'], 'issues': [
                      {'id': 'a000-F1', 'disposition': 'addressed', 'reason': ['Example reason'],
                       'evidence': ['tests/regression.go']}]}
        write_json(folder / 'repair-result.json', result)
        self.assertEqual(read_repair_result(self.bundle, 'before', ['a000-F1']), result)
        self.review['summary'] = ['Verification summary']
        self.review['issues'][0].update(reason={'explanation': 'Observed difference'},
                                       before_observation={'premature_deaths': 2},
                                       after_observation={'premature_deaths': 0, 'decided': False},
                                       commands=['go test ./...'])
        self.assertEqual(self.verify()['issues'][0]['after_observation'], {'premature_deaths': 0, 'decided': False})

    def test_empty_or_non_descriptive_results_still_fail(self):
        for value in (None, '', '  ', [], {}, [None, ''], {'notes': []}, 0, False):
            with self.subTest(value=value), self.assertRaises(ValueError):
                require_description(value, 'field')
        self.assertEqual(require_description({'count': 10**400}, 'large counter')['count'], 10**400)
        for change in ({'input_commit': 'other'}, {'action': ['repaired']}, {'issues': []}):
            result = {'input_commit': 'before', 'action': 'repaired', 'summary': ['Fix'],
                      'issues': [{'id': 'a000-F1', 'disposition': 'addressed', 'reason': ['Done']}]} | change
            (self.bundle / '.forge').mkdir(exist_ok=True)
            write_json(self.bundle / '.forge/repair-result.json', result)
            with self.subTest(change=change), self.assertRaises(ValueError):
                read_repair_result(self.bundle, 'before', ['a000-F1'])

    def test_blocked_verification_cannot_close_a_finding_as_refuted(self):
        self.review['issues'][0].update(method='blocked', disposition='not_substantiated')
        with self.assertRaisesRegex(ValueError, 'blocked'):
            self.verify()

    def test_wrong_version_duplicate_ids_and_missing_evidence_are_not_empty(self):
        for changes in ({'candidate_commit': 'other'}, {'issues': [self.finding, self.finding]},
                        {'issues': None}, {'coverage': ''}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.find(**changes)
        for ref in ('work/missing', 'work/../escape', '/etc/hostname', 'executions/../../etc/hostname'):
            self.finding['evidence'] = [ref]
            with self.subTest(ref=ref), self.assertRaises(ValueError):
                self.find()
        (self.bundle / 'audit-work/link').symlink_to('/etc/hostname')
        self.finding['evidence'] = ['work/link']
        with self.assertRaises(ValueError):
            self.find()

    def test_review_cannot_close_different_issues_versions_or_static_fix_claims(self):
        for value in (self.review | {'before_commit': 'other'}, self.review | {'after_commit': 'other'},
                      self.review | {'issues': []},
                      self.review | {'issues': [self.review['issues'][0] | {'id': 'unknown'}]},
                      self.review | {'issues': [self.review['issues'][0] | {'method': 'source_review'}]},
                      self.review | {'issues': [self.review['issues'][0] | {'disposition': []}]},
                      self.review | {'issues': [self.review['issues'][0] | {'method': {}}]}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.verify(value)
        self.review['issues'][0].update(method='source_review', disposition='not_substantiated')
        self.assertEqual(self.verify()['issues'][0]['disposition'], 'not_substantiated')


if __name__ == '__main__':
    unittest.main()
