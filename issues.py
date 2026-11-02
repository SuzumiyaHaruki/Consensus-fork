"""Small, ordinary JSON issue records linking versions, reports and review evidence."""
import json
import re
from pathlib import Path

from artifacts import inside, copy_tree, require_description
from generator.runner import read_json, write_json
from runtime.evidence import inspect_item, retained_path

CLOSED = {'fixed', 'not_substantiated'}
DISPOSITIONS = CLOSED | {'unresolved', 'needs_specification', 'environment_blocked'}
FINDING_DETAILS = ('legality', 'reachability', 'impact', 'causal_explanation', 'variants')


def nonempty(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{name} must be a nonempty string')
    return value


def evidence(bundle, refs):
    """Map agent paths to the reconstructed completed turn, not its mutable worktree."""
    if not isinstance(refs, list) or not refs:
        raise ValueError('Evidence must contain retained file references')
    return [retained_path(bundle, ref, 'audit-work', 'raw') for ref in refs]


def rebase_evidence(item, prefix):
    return {**item, 'evidence_bundle': str(prefix),
            'evidence': [str(prefix / name) for name in item['evidence']],
            'trace_files': [str(prefix / name) for name in item.get('trace_files', [])],
            'trace_checks': [{**check, 'path': str(prefix / check['path'])}
                             for check in item.get('trace_checks', [])],
            'execution_records': [{**entry, 'path': str(prefix / entry['path']),
                                   'inputs': [str(prefix / path) for path in entry.get('inputs', [])],
                                   **{field: {name: str(prefix / path) for name, path in entry.get(field, {}).items()}
                                      for field in ('restore', 'outputs')}}
                                  for entry in item.get('execution_records', [])]}


def feedback_overview(candidate, issues):
    lines = ['# Repair evidence overview', '',
             'Navigation only. Descriptions below are copied from retained records, not independently established facts. Read the original reports, traces, commands and outputs. PASS can mean a defect was observed.', '',
             'For each execution record, restore maps workspace destinations to retained input files; outputs points to original logs. cwd_relative is the execution directory within the selected source, or null if not recorded. argv and original cwd are unchanged: inspect absolute paths, rebuild temporary binaries and adapt only with an explanation. Use isolated_exec; no command is automatically run by this handoff.', '',
             f"Current candidate: `{candidate['commit']}`. Full issue and review records: `issues.json`.", '']
    for issue in issues:
        lines.extend([f"## {issue['id']}", '',
                      f"State: `{issue['state']}`; origin: `{issue['source_commit']}`; original bundle: `{issue['evidence_bundle']}`.", ''])
        fields = ('summary', 'property', 'assumptions', *FINDING_DETAILS, 'reproduction', 'polarity',
                  'evidence', 'trace_files', 'execution_records', 'evidence_feedback', 'reviews')
        for field in fields:
            if field in issue:
                # JSON preserves nested values and line breaks without a lossy prose summary.
                lines.extend([f'**{field}**', '', '```json',
                              json.dumps(issue[field], ensure_ascii=False, indent=2), '```', ''])
    return '\n'.join(lines)


def findings(bundle, candidate, number):
    data = read_json(inside(bundle, 'audit-work/findings.json'))
    if data.get('candidate_commit') != candidate['commit']:
        raise ValueError('Finding index refers to a different candidate')
    require_description(data.get('coverage'), 'coverage')
    return data['coverage'], index_findings(data.get('issues'), bundle, candidate, f'a{number:03d}')


def index_findings(items, bundle, candidate, prefix):
    """Use the same evidence and identity handling for discovery and review findings."""
    if not isinstance(items, list):
        raise ValueError('Finding index needs an explicit issue list, including when empty')
    seen, result = set(), []
    for issue in items:
        if not isinstance(issue, dict):
            raise ValueError('Finding must be an object')
        ident = nonempty(issue.get('id'), 'issue id')
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}', ident) or ident in seen:
            raise ValueError('Duplicate or invalid finding id')
        seen.add(ident)
        for name in ('summary', 'property', 'assumptions', 'reproduction', 'polarity'):
            require_description(issue.get(name), name)
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


def feedback_bundle(destination, latest, candidate, issues):
    copy_tree(latest, destination)
    brief = read_json(destination / 'handoff.json')
    delivered = []
    origins = {}
    for issue in pending(issues):
        origin = issue['evidence_bundle']
        if origin == str(latest):
            prefix = Path('.')
        else:
            if origin not in origins:
                prefix = Path('previous') / f'{len(origins):03d}'
                copy_tree(Path(origin), destination / prefix)
                origins[origin] = prefix
            prefix = origins[origin]
        reviews = []
        for review in issue['reviews']:
            origin = review['evidence_bundle']
            if origin not in origins:
                review_prefix = Path('previous') / f'{len(origins):03d}'
                copy_tree(Path(origin), destination / review_prefix)
                origins[origin] = review_prefix
            review_prefix = origins[origin]
            reviews.append(rebase_evidence(review, review_prefix))
        delivered.append({**rebase_evidence(issue, prefix), 'reviews': reviews})
    write_json(destination / 'issues.json', {'candidate_commit': candidate['commit'], 'issues': delivered})
    (destination / 'overview.md').write_text(feedback_overview(candidate, delivered), encoding='utf-8')
    brief.update(issues_file='issues.json', candidate_commit=candidate['commit'],
                 overview_file='overview.md',
                 repair_issue_ids=[issue['id'] for issue in repairable(issues)],
                 note='Repair only repair_issue_ids. Other pending issues are retained as specification context, not closed. Original source_commit remains explicit.')
    write_json(destination / 'handoff.json', brief)


def review_result(bundle, before, after, expected_ids):
    result = read_json(inside(bundle, 'audit-work/review.json'))
    if result.get('before_commit') != before['commit'] or result.get('after_commit') != after['commit']:
        raise ValueError('Review refers to different before/after candidates')
    require_description(result.get('summary'), 'review summary')
    if not isinstance(result.get('issues'), list):
        raise ValueError('Review needs an issue list')
    seen = set()
    for issue in result['issues']:
        if not isinstance(issue, dict):
            raise ValueError('Review issue must be an object')
        ident = nonempty(issue.get('id'), 'review issue id')
        disposition = nonempty(issue.get('disposition'), 'review disposition')
        if ident in seen or disposition not in DISPOSITIONS:
            raise ValueError('Duplicate review id or invalid disposition')
        seen.add(ident)
        for name in ('reason', 'before_observation', 'after_observation'):
            require_description(issue.get(name), name)
        method = nonempty(issue.get('method'), 'review method')
        if method not in {'executed', 'source_review', 'blocked'}:
            raise ValueError('Review method must distinguish execution, source review and blocked work')
        if method == 'blocked' and disposition in CLOSED:
            raise ValueError('A blocked verification cannot close a finding; retain it unresolved or environment_blocked')
        if issue['disposition'] == 'fixed' and issue['method'] != 'executed':
            raise ValueError('Closing a fix needs independent execution; otherwise retain unresolved')
        details = inspect_item(issue, bundle, work_name='audit-work', raw_name='raw',
                               expected_commits=(before['commit'], after['commit']))
        issue['evidence'] = evidence(bundle, issue.get('evidence'))
        issue.update(details)
    if seen != set(expected_ids):
        raise ValueError('Review must cover exactly the supplied issue IDs')
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
