"""Small, ordinary JSON issue records linking versions, reports and review evidence."""
import json
from pathlib import Path

from artifacts import inside, copy_tree, require_description
from generator.runner import read_json, write_json
from runtime.evidence import (CLOSED, inspect_item, retained_path, validate_findings,
                              validate_review, require_fix_execution)

def evidence(bundle, refs):
    """Map agent paths to the reconstructed completed turn, not its mutable worktree."""
    if not isinstance(refs, list) or not refs:
        raise ValueError('Evidence must contain retained file references')
    return [retained_path(bundle, ref, 'audit-work', 'raw') for ref in refs]


def rebase_evidence(item, prefix):
    return {**item, 'evidence_bundle': str(prefix),
            'evidence': [str(prefix / name) for name in item.get('evidence', [])],
            'trace_files': [str(prefix / name) for name in item.get('trace_files', [])],
            'trace_checks': [{**check, 'path': str(prefix / check['path'])}
                             for check in item.get('trace_checks', [])],
            'execution_records': [{**entry, 'path': str(prefix / entry['path']),
                                   'inputs': [str(prefix / path) for path in entry.get('inputs', [])],
                                   **{field: {name: str(prefix / path) for name, path in entry.get(field, {}).items()}
                                      for field in ('restore', 'outputs')}}
                                  for entry in item.get('execution_records', [])]}


def short_description(value, limit=360):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    text = ' '.join(text.split())
    return text if len(text) <= limit else text[:limit] + '… (see full record)'


def feedback_overview(candidate, issues, history, catalog=()):
    lines = ['# Repair evidence overview', '',
             'Navigation only. Descriptions below are copied from retained records, not independently established facts. Read the original reports, traces, commands and outputs. PASS can mean a defect was observed.', '',
             'For each execution record, restore maps workspace destinations to retained input files; outputs points to original logs. cwd_relative is the execution directory within the selected source, or null if not recorded. argv and original cwd are unchanged: inspect absolute paths, rebuild temporary binaries and adapt only with an explanation. Use isolated_exec; no command is automatically run by this handoff.', '',
             f"Current candidate: `{candidate['commit']}`. Full issue and review records: [issues.json](issues.json).", '']
    if history:
        lines.extend(['Closed history and review-added evidence are in `history.json`. Select relevant regression checks; historical closure does not verify the current candidate.', '',
                      '| Issue | Agent disposition | Version supporting closure |', '| --- | --- | --- |'])
        for item in history:
            lines.append(f"| {item['id']} | {item['state']} | {item['reviews'][-1]['after_commit']} |")
        lines.append('')
    for issue in issues:
        lines.extend([f"## {issue['id']}", '',
                      f"State: `{issue['state']}`; origin: `{issue['source_commit']}`; original bundle: `{issue['evidence_bundle']}`.", ''])
        for field in ('summary', 'property', 'reproduction', 'polarity'):
            if field in issue:
                lines.extend([f'{field}: {short_description(issue[field])}', ''])
        records = [('Original evidence', issue)]
        if issue.get('reviews'):
            review = issue['reviews'][-1]
            lines.extend([f"Latest review: `{review['disposition']}` on `{review['after_commit']}`. {short_description(review['reason'])}", ''])
            records.append(('Latest review evidence', review))
        for label, record in records:
            lines.append(label + ':')
            lines.append('')
            for execution in record.get('execution_records', []):
                version = execution['source_context'].get('commit', 'source not captured')
                command = execution.get('argv', execution.get('command'))
                lines.append(f"- [{execution['execution_id']}]({execution['path']}): `{version}`, {execution['status']}, exit {execution.get('exit_code')}; {short_description(command, 180)}")
            for ref in dict.fromkeys(record.get('evidence', []) + record.get('trace_files', [])):
                lines.append(f'- [Retained evidence]({ref})')
            lines.append('')
    if catalog:
        lines.extend(['Reusable cases and open questions: [evidence-index.json](evidence-index.json). These are agent observations for recorded versions, not current-version verification or extra repair assignments.', ''])
        for entry in catalog:
            lines.append(f"- [{entry['id']}]({entry['report']}), recorded for `{entry['candidate_commit']}`: {len(entry['cases'])} cases; open questions {'present' if entry['open_questions'] else 'none'}.")
        lines.append('')
    return '\n'.join(lines)


def catalog_entry(bundle, candidate, name, filename):
    """Optional agent-selected cases/questions; malformed notes never close or block issues."""
    data = read_json(inside(bundle, 'audit-work/' + filename))
    entry = {'id': name, 'candidate_commit': candidate['commit'], 'evidence_bundle': str(bundle),
             'report': 'audit-work/report.md', 'cases': [], 'open_questions': [], 'warnings': []}
    questions = data.get('open_questions', [])
    if questions:
        try:
            entry['open_questions'] = require_description(questions, 'open_questions')
        except ValueError as exc:
            entry['warnings'].append(str(exc))
    cases = data.get('cases', [])
    if not isinstance(cases, list):
        entry['warnings'].append('Optional cases must be a list; original field remains in the source index')
        cases = []
    for number, case in enumerate(cases):
        try:
            if not isinstance(case, dict):
                raise ValueError('Case must be an object')
            require_description(case.get('summary'), 'case summary')
            require_description(case.get('reproduction'), 'case reproduction')
            refs = evidence(bundle, case.get('evidence'))
            details = inspect_item(case, bundle, work_name='audit-work', raw_name='raw',
                                   expected_commits=(candidate['commit'],))
            entry['cases'].append({**case, 'id': f'{name}-c{number:03d}', 'local_id': case.get('id'),
                                   'recorded_for_commit': candidate['commit'], 'evidence_bundle': str(bundle),
                                   'evidence': refs, **details})
        except (OSError, ValueError, KeyError, TypeError) as exc:
            entry['warnings'].append(f'Case {number}: {exc}; original entry remains in the source index')
    return entry if entry['cases'] or entry['open_questions'] or entry['warnings'] else None


def findings(bundle, candidate, number):
    data = read_json(inside(bundle, 'audit-work/findings.json'))
    if data.get('candidate_commit') != candidate['commit']:
        raise ValueError('Finding index refers to a different candidate')
    require_description(data.get('coverage'), 'coverage')
    return data['coverage'], index_findings(data.get('issues'), bundle, candidate, f'a{number:03d}')


def index_findings(items, bundle, candidate, prefix):
    """Use the same evidence and identity handling for discovery and review findings."""
    validate_findings(items)
    result = []
    for issue in items:
        ident = issue['id']
        result.append({**issue, 'id': f'{prefix}-{ident}', 'local_id': ident,
                       'source_commit': candidate['commit'], 'candidate_version': candidate['version'],
                       'evidence_bundle': str(bundle), 'evidence': evidence(bundle, issue.get('evidence')),
                       **inspect_item(issue, bundle, work_name='audit-work', raw_name='raw', expected_commits=(candidate['commit'],)),
                       'state': 'open', 'reviews': []})
    return result


def pending(issues):
    return [issue for issue in issues if issue['state'] not in CLOSED]


def repairable(issues):
    # Only apply_review assigns this deferred state; a repairer's claim cannot.
    return [issue for issue in pending(issues) if issue['state'] != 'needs_specification']


def feedback_bundle(destination, latest, candidate, issues, catalog=()):
    copy_tree(latest, destination)
    brief = read_json(destination / 'handoff.json')
    delivered, history, origins = [], [], {}

    def retain(item, *, catalog=False):
        origin = item['evidence_bundle']
        if origin == str(latest):
            prefix = Path('.')
        else:
            if origin not in origins:
                origins[origin] = Path('previous') / f'{len(origins):03d}'
                copy_tree(Path(origin), destination / origins[origin])
            prefix = origins[origin]
        retained = rebase_evidence(item, prefix)
        if catalog:
            retained.update(report=str(prefix / item['report']),
                            cases=[rebase_evidence(case, prefix) for case in item['cases']])
        return retained

    for issue in issues:
        item = retain(issue)
        item['reviews'] = [retain(review) for review in issue['reviews']]
        (history if issue['state'] in CLOSED else delivered).append(item)
    write_json(destination / 'issues.json', {'candidate_commit': candidate['commit'], 'issues': delivered})
    write_json(destination / 'history.json', {'candidate_commit': candidate['commit'], 'issues': history})
    notes = [retain(entry, catalog=True) for entry in catalog]
    write_json(destination / 'evidence-index.json', {'current_candidate_commit': candidate['commit'], 'entries': notes,
               'scope': 'Agent-selected cases and questions. Recorded versions and actual execution source contexts remain separate; no automatic current-version verdict.'})
    (destination / 'overview.md').write_text(feedback_overview(candidate, delivered, history, notes), encoding='utf-8')
    brief.update(issues_file='issues.json', candidate_commit=candidate['commit'],
                 overview_file='overview.md', history_file='history.json',
                 evidence_index_file='evidence-index.json',
                 repair_issue_ids=[issue['id'] for issue in repairable(issues)],
                 note='Repair only repair_issue_ids. Other pending issues are specification context. Closed history is available for selective regression checks, not new repair assignments or current-version verification.')
    write_json(destination / 'handoff.json', brief)


def review_result(bundle, before, after, expected_ids):
    result = read_json(inside(bundle, 'audit-work/review.json'))
    validate_review(result, {'before_commit': before['commit'], 'after_commit': after['commit']}, expected_ids)
    for issue in result['issues']:
        details = inspect_item(issue, bundle, work_name='audit-work', raw_name='raw',
                               expected_commits=(before['commit'], after['commit']))
        require_fix_execution(issue, details, after['commit'])
        issue['evidence'] = evidence(bundle, issue.get('evidence'))
        issue.update(details)
    # Validate new observations before applying any closures. Missing field remains compatible.
    result['new_issues'] = index_findings(result.get('new_issues', []), bundle, after,
                                         f"r{after['version']:03d}")
    return result


def apply_review(issues, result, bundle, after):
    by_id = {issue['id']: issue for issue in issues}
    for item in result['issues']:
        issue = by_id[item['id']]
        issue['state'] = item['disposition']
        issue['reviews'].append({**item, 'before_commit': result['before_commit'],
                                 'after_commit': after['commit'], 'evidence_bundle': str(bundle)})
    issues.extend(result.get('new_issues', []))
