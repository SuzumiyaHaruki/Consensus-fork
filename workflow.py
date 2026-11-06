"""Finite protocol-to-system workflow using native Codex and the local auditor."""
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import signal
import subprocess
import tempfile
import time

from artifacts import (candidate_commit, check_materials, copy_regular, copy_tree, inside,
                       prepare_handoff, read_repair_result)
from generator.config import Settings
from processes import invoke
from generator.runner import (REQUIRED_INPUTS, Terminated, doctor as generation_doctor, execute as execute_agent,
                              exclusive_run, prepare as prepare_agent, utc_now)
from runtime.storage import read_json, write_json
from workflow_config import ROOT, from_dict
from issues import findings, pending, repairable, feedback_bundle, review_result, apply_review, catalog_entry


class StopWorkflow(Exception):
    def __init__(self, status, reason):
        super().__init__(reason)
        self.status = status


def bridge_command(settings, *args):
    return [settings.audit_python, str(ROOT / 'audit_bridge.py'), *map(str, args)]


def agent_settings(settings, root, seconds):
    return Settings(model=settings.generator_model, reasoning_effort=settings.generator_reasoning_effort,
                    timeout_seconds=seconds, codex=settings.codex, inputs_dir=str(root / 'inputs'),
                    output_root=str(root / 'stages'), execution_python=settings.audit_python,
                    action_seconds=settings.action_seconds)


def doctor(settings):
    result = generation_doctor(Settings(model=settings.generator_model, reasoning_effort=settings.generator_reasoning_effort,
                                        codex=settings.codex))
    try:
        process = subprocess.run(bridge_command(settings, 'probe'), cwd=ROOT,
                                 capture_output=True, text=True, timeout=20)
        result['auditor'] = json.loads(process.stdout) if process.returncode == 0 else {'available': False, 'error': process.stderr.strip()}
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        result['auditor'] = {'available': False, 'error': str(exc)}
    result['models'] = {'generation_and_repair': [settings.generator_model, settings.generator_reasoning_effort],
                        'audit': [settings.audit_model, settings.audit_reasoning_effort]}
    result['ready'] = result['ready'] and result['auditor']['available']
    result['scope'] = 'Local tools/imports only; no authentication, model call, or target execution.'
    return result


def prepare(settings, label='system'):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', label):
        raise ValueError('Invalid label: use 1-64 letters, digits, underscores, or hyphens')
    for name in REQUIRED_INPUTS:
        if not (Path(settings.inputs_dir) / name).is_file():
            raise ValueError(f'Missing input: {name}')
    if not Path(settings.repair_prompt).is_file():
        raise ValueError('Missing repair prompt')
    for prompt in (settings.audit_prompt, settings.review_prompt):
        if not Path(prompt).is_file():
            raise ValueError(f'Missing audit/review prompt: {prompt}')
        parts = Path(prompt).read_text().split('<!-- continuation -->')
        if len(parts) != 2 or not all(part.strip() for part in parts):
            raise ValueError('Audit/review prompt needs task and continuation separated by one <!-- continuation -->')
    output = Path(settings.output_root)
    output.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-') + label + '-', dir=output))
    for name in REQUIRED_INPUTS:
        copy_regular(Path(settings.inputs_dir) / name, root / 'inputs' / name)
    copy_regular(Path(settings.repair_prompt), root / 'inputs/REPAIR.md')
    copy_regular(Path(settings.audit_prompt), root / 'inputs/AUDIT.md')
    copy_regular(Path(settings.review_prompt), root / 'inputs/VERIFY.md')
    write_json(root / 'experiment.json', {
        'kind': 'consensus-forge', 'condition': 'protocol-to-system-generation-audit-repair',
        'status': 'prepared', 'created_at': utc_now(),
        'issue_index_status': 'not_started',
        'settings': settings.to_dict(), 'stages': [], 'candidates': [],
        'generation_environment': {'mode': 'host', 'read_isolation': False, 'sandbox': 'workspace-write'},
        'audit_environment': {'engine': 'auditor/codex_plain', 'isolation': 'CA-derived permission profile and Bubblewrap'},
        'verification': 'Independent agent before/after repair verification; further discovery only within remaining budget and repair rounds.',
    })
    return root


class Runtime:
    """Only these operations launch subprocesses; tests substitute offline executions."""
    def check(self, settings):
        return doctor(settings)

    def agent(self, stage):
        return execute_agent(stage)

    def export(self, settings, workspace, destination, logs, timeout):
        result = invoke(bridge_command(settings, 'export', workspace, destination), logs, timeout, ROOT)
        require_process(result, logs)
        return read_json(logs / 'stdout.log')

    def audit(self, settings, candidate, folder, seconds, timeout):
        return self._audit(settings, candidate, folder, seconds, timeout)

    def verify(self, settings, candidate, folder, context, seconds, timeout):
        return self._audit(settings, candidate, folder, seconds, timeout, context=context)

    def _audit(self, settings, candidate, folder, seconds, timeout, context=None):
        folder.mkdir(parents=True)
        write_json(folder / 'target.json', {'execution_backend': 'go_module', 'target': {
            'variant': 'mixepaxos_system', 'expected_module': 'example.com/mixepaxos',
            'analysis_roots': [], 'execution_package': '.',
        }})
        write_json(folder / 'config.json', {
            'baseline_id': 'codex_plain', 'target_config': str(folder / 'target.json'),
            'task_path': settings.review_prompt if context else settings.audit_prompt,
            'task_mode': 'review' if context else 'audit', 'review_context': str(context) if context else None,
            'repo_path': candidate['path'], 'agent_model': settings.audit_model,
            'agent_reasoning_effort': settings.audit_reasoning_effort, 'codex_provider': None,
            'auth_mode': 'codex_login', 'runs_dir': str(folder / 'runs'),
            'allow_agent_materials': True, 'allow_experiments': True,
            'budget': {'total_seconds': float(seconds), 'agent_calls': settings.audit_calls,
                       'agent_turn_timeout': float(min(settings.audit_turn_seconds, seconds)),
                       'action_timeout': float(min(settings.action_seconds, seconds))},
        })
        result = invoke(bridge_command(settings, 'audit', folder / 'config.json'), folder / 'process', timeout, ROOT)
        if result['status'] != 'completed':
            require_process(result, folder / 'process')
        response = read_json(folder / 'process/stdout.log')
        if not isinstance(response.get('run_dir'), str) or not isinstance(response.get('stop'), str):
            raise ValueError('Auditor response must contain run_dir and stop strings')
        audit_run = Path(response['run_dir']).resolve()
        if not audit_run.is_relative_to((folder / 'runs').resolve()):
            raise ValueError('Audit returned an unexpected run directory')
        if response['stop'] == 'cancelled':
            raise StopWorkflow('interrupted', 'Audit was cancelled')
        allowed = {'total_deadline', 'agent_call_limit', 'turn_timeout', 'budget_wrap_up'} | ({'review_complete'} if context else set())
        if response['stop'] not in allowed:
            raise StopWorkflow('audit_failed', f"Auditor stopped with {response['stop']}; see {audit_run}")
        # CA returns 1 for a turn timeout, which can still have earlier completed reports.
        if result.get('returncode') != 0 and not (result.get('returncode') == 1 and response['stop'] == 'turn_timeout'):
            require_process(result, folder / 'process')
        return audit_run


def require_process(record, logs):
    if record['status'] != 'completed' or record.get('returncode') != 0:
        status = {'interrupted': 'interrupted', 'timed_out': 'budget_exhausted'}.get(record['status'], 'controller_step_failed')
        raise StopWorkflow(status, f"Helper {record['status']}; see {logs}")


def delta(previous, current):
    old, new = set(previous['files']), set(current['files'])
    return {'added': sorted(new - old), 'deleted': sorted(old - new),
            'modified': sorted(name for name in old & new
                               if (Path(previous['path']) / name).read_bytes() != (Path(current['path']) / name).read_bytes())}


def record_audit_progress(root, entry):
    """Expose retained output without importing unfinished claims or changing issue states."""
    if entry['kind'] not in {'audit', 'final_audit', 'repair_verification'}:
        return
    try:
        folder = inside(root, Path(entry['path']).relative_to(root))
        runs = [inside(folder, path.relative_to(folder)) for path in (folder / 'runs').glob('*/run.json')]
        if not runs:
            return
        if len(runs) != 1:
            raise ValueError('Multiple audit runs in one stage; cannot select retained output')
        audit_run = runs[0].parent
        data = read_json(runs[0])
        entry.update(audit_run=str(audit_run), audit_stop=data.get('stop'))
        if data.get('reason'):
            entry['audit_reason'] = data['reason']
        if data.get('agents'):
            entry['agents'] = {**data['agents'], 'run_dir': str(audit_run)}
        last_completed = max((t['number'] for t in data['turns'] if t['status'] == 'completed'), default=0)
        has_supplement = any(t['number'] > last_completed for t in data['turns'])
        if entry['status'] in {'running', 'not_started'} or entry['status'] == 'returned' and not has_supplement:
            return
        index = 'review.json' if entry['kind'] == 'repair_verification' else 'findings.json'
        paths = {key: str(path) for key, name in (('report', 'report.md'), ('index', index))
                 if (path := inside(audit_run, 'work/' + name)).is_file()}
        if paths:
            source = read_json(inside(audit_run, 'inputs/source.json'))
            entry['pending_report'] = {
                'status': 'needs_review', 'candidate_commit': source['commit'],
                'last_completed_turn': last_completed,
                'audit_run': str(audit_run), **paths,
                'turns': str(inside(audit_run, 'turns')),
                'executions': str(inside(audit_run, 'executions')),
                'note': 'Unfinished or unimported agent output. Report and index may disagree; an empty index does not establish no findings. No issue is imported or closed from these files.',
            }
    except (OSError, ValueError, KeyError, TypeError) as exc:
        # Failure navigation must not hide the original failure or prevent final saving.
        entry['retained_output_error'] = str(exc)


def execute(root, runtime=None):
    root = Path(root).resolve()
    runtime = runtime or Runtime()
    with exclusive_run(root):
        record = read_json(root / 'experiment.json')
        if record['status'] != 'prepared':
            raise ValueError('Experiment already started; prepare a fresh experiment, never overwrite retained evidence')
        settings = from_dict(record['settings'] | {'audit_prompt': str(root / 'inputs/AUDIT.md'),
                                                   'review_prompt': str(root / 'inputs/VERIFY.md')}, root)
        issues = []
        catalog = []
        start = time.monotonic()
        deadline = start + settings.total_seconds
        record.update(status='running', started_at=utc_now(), evidence_index='evidence-index.json')

        def save():
            imports = [stage['finding_import'] for stage in record['stages'] if 'finding_import' in stage]
            state = ('not_started' if not imports else 'incomplete' if any(item['status'] == 'failed' for item in imports)
                     else 'pending' if any(item['status'] == 'pending' for item in imports) else 'imported')
            record['issue_index_status'] = state
            drafts = [stage['pending_report'] for stage in record['stages'] if 'pending_report' in stage]
            record['pending_audit_reports'] = drafts
            write_json(root / 'issues.json', {'import_status': state, 'imports': imports,
                                             'issues': issues, 'pending_reports': drafts})
            record['open_issues'] = [issue['id'] for issue in pending(issues)]
            record['awaiting_specification'] = [issue['id'] for issue in issues if issue['state'] == 'needs_specification']
            write_json(root / 'evidence-index.json', {
                'current_candidate_commit': record.get('current_candidate', {}).get('commit'),
                'scope': 'Agent-selected cases and open questions, not verdicts or repair assignments. Consult recorded versions and execution source contexts before reuse.',
                'entries': catalog})
            write_json(root / 'experiment.json', record)

        def remaining():
            value = deadline - time.monotonic()
            if value <= 0:
                raise StopWorkflow('budget_exhausted', 'Total experiment budget exhausted')
            return value

        def finish(reason):
            status = reason if reason in {'needs_specification', 'verification_incomplete',
                                         'verification_failed', 'environment_blocked'} else 'cycle_complete'
            record.update(status=status, stop_reason=reason,
                          reason=f'Stopped: {reason}; candidate, issue states and independent review evidence retained.')

        def phase(kind, path):
            entry = {'kind': kind, 'path': str(path), 'status': 'running', 'started_at': utc_now()}
            record['stages'].append(entry)
            record['phase'] = kind
            save()
            print(f'[{kind}] {path}', flush=True)
            return entry

        def run_agent(kind, seconds, candidate=None, feedback=None, reserve_seconds=0):
            stage = prepare_agent(agent_settings(settings, root, min(seconds, remaining())), kind)
            if candidate is not None:
                if candidate_commit(Path(candidate['path'])) != candidate['commit']:
                    raise ValueError('Candidate identity changed before repair')
                for name in candidate['files']:
                    copy_regular(Path(candidate['path']) / name, stage / 'workspace' / name)
                copy_tree(feedback, stage / 'workspace/.forge/feedback')
                (stage / 'prompt.txt').write_bytes((root / 'inputs/REPAIR.md').read_bytes())
            entry = phase(kind, stage)
            meta = read_json(stage / 'run.json')
            allocated = min(seconds, remaining() - reserve_seconds)
            if kind == 'repair' and allocated < settings.minimum_repair_seconds:
                entry.update(status='not_started', allocated_seconds=0, ended_at=utc_now(),
                             reason='Preparation left less than the minimum repair budget')
                meta.update(status='not_started', workflow_role=kind, candidate_commit=candidate['commit'],
                            reason=entry['reason'])
                write_json(stage / 'run.json', meta)
                save()
                return None
            if allocated <= 0:
                raise StopWorkflow('budget_exhausted', 'Preparation consumed the time available before the audit reserve')
            meta['settings']['timeout_seconds'] = allocated
            entry['allocated_seconds'] = allocated
            meta.update(workflow_role=kind, candidate_commit=candidate['commit'] if candidate else None,
                        candidate_path=candidate['path'] if candidate else None)
            write_json(stage / 'run.json', meta)
            result = runtime.agent(stage)
            entry.update(status=result['status'], ended_at=utc_now())
            if result.get('agents'):
                entry['agents'] = {**result['agents'], 'run_dir': str(stage)}
            save()
            if result['status'] != 'agent_finished':
                state = {'timed_out': 'stage_timed_out', 'interrupted': 'interrupted',
                         'environment_blocked': 'environment_blocked'}.get(result['status'], 'agent_failed')
                raise StopWorkflow(state, f'{kind}: {result["status"]}; partial output retained at {stage}')
            return stage

        def capture(stage, number):
            try:
                check_materials(stage / 'workspace', root / 'inputs', REQUIRED_INPUTS)
            except ValueError as exc:
                raise StopWorkflow('needs_specification', str(exc)) from exc
            candidate = runtime.export(settings, stage / 'workspace', root / 'candidates' / f'v{number:03d}',
                                       root / 'captures' / f'v{number:03d}', min(60, remaining()))
            candidate['version'] = number
            record['candidates'].append(candidate)
            record['current_candidate'] = candidate
            save()
            return candidate

        old_term = signal.getsignal(signal.SIGTERM)
        def cancel(*_):
            raise Terminated('SIGTERM')
        signal.signal(signal.SIGTERM, cancel)
        try:
            save()
            record['environment'] = runtime.check(settings)
            save()
            if not record['environment']['ready']:
                raise StopWorkflow('environment_blocked', 'Local tool/dependency checks failed; no generation started')
            # Generation leaves time for discovery. Repairs reserve review, not
            # another mandatory discovery round after the last modification.
            reserve = settings.verification_seconds + 10
            available = remaining() - reserve
            if available <= 0:
                raise StopWorkflow('budget_exhausted', 'Total budget cannot cover generation and discovery reserve')
            stage = run_agent('generation', min(settings.generation_seconds, available), reserve_seconds=reserve + 60)
            candidate = capture(stage, 0)
            repairs, number, forced_stop = 0, 0, None
            while True:
                audit_seconds = settings.initial_audit_seconds if number == 0 else settings.audit_seconds
                can_search_again = remaining() >= (audit_seconds + settings.minimum_repair_seconds
                    + settings.repair_verification_seconds + reserve + 60)
                final = repairs + 1 >= settings.max_repairs or not can_search_again
                folder = root / 'audits' / f'{number:03d}'
                entry = phase('final_audit' if final else 'audit', folder)
                imported = {'audit_number': number, 'candidate_commit': candidate['commit'],
                            'status': 'pending', 'issue_count': None}
                entry['finding_import'] = imported
                save()
                # The first audit keeps its own budget even in a generation-only run.
                if final and number > 0:
                    audit_seconds = settings.verification_seconds
                available = remaining() - 10
                repair_reserve = settings.minimum_repair_seconds + settings.repair_verification_seconds + 60
                if repairs < settings.max_repairs and available > repair_reserve:
                    available -= repair_reserve
                seconds = min(audit_seconds, available)
                entry['allocated_seconds'] = seconds
                if seconds <= 0:
                    raise StopWorkflow('budget_exhausted', 'Insufficient time to start another audit')
                if candidate_commit(Path(candidate['path'])) != candidate['commit']:
                    raise ValueError('Candidate changed before audit')
                audit_run = runtime.audit(settings, candidate, folder, seconds, min(seconds + 10, remaining()))
                if (audit_run / 'run.json').is_file():
                    agents = read_json(audit_run / 'run.json').get('agents')
                    if agents:
                        entry['agents'] = {**agents, 'run_dir': str(audit_run)}
                entry.update(status='returned', audit_run=str(audit_run), ended_at=utc_now())
                record['last_audit'] = str(audit_run)
                save()
                handoff_path = root / 'handoffs' / f'{number:03d}'
                try:
                    handoff = prepare_handoff(audit_run, candidate, handoff_path)
                    entry.update(handoff=str(handoff_path / 'handoff.json'),
                                 last_completed_turn=handoff['last_completed_turn'])
                    imported['findings_path'] = str(handoff_path / 'audit-work/findings.json')
                    coverage, discovered = findings(handoff_path, candidate, number)
                except (ValueError, OSError) as exc:
                    imported.update(status='failed', error=str(exc))
                    entry.update(status='incomplete', reason=str(exc))
                    save()
                    raise StopWorkflow('audit_incomplete', str(exc)) from exc
                issues.extend(discovered)
                note = catalog_entry(handoff_path, candidate, f'a{number:03d}', 'findings.json')
                if note:
                    catalog.append(note)
                imported.update(status='imported', issue_count=len(discovered))
                entry.update(handoff=str(handoff_path / 'handoff.json'),
                             last_completed_turn=handoff['last_completed_turn'], coverage=coverage,
                             discovered_issues=[issue['id'] for issue in discovered], final_discovery=final)
                save()
                if not repairable(issues) or repairs >= settings.max_repairs:
                    entry['final_discovery'] = True
                    reason = ('no_open_findings' if not pending(issues) else
                              'needs_specification' if not repairable(issues) else
                              'repair_limit')
                    finish(reason)
                    break
                # Recompute after actual audit/archival time, not its original nominal allocation.
                seconds = min(settings.repair_seconds, remaining() - settings.repair_verification_seconds - 60)
                if seconds < settings.minimum_repair_seconds:
                    finish('insufficient_repair_budget')
                    break
                feedback = root / 'feedback' / f'{repairs:03d}'
                feedback_bundle(feedback, handoff_path, candidate, issues, catalog)
                expected_ids = [issue['id'] for issue in repairable(issues)]
                stage = run_agent('repair', seconds, candidate, feedback,
                                  reserve_seconds=settings.repair_verification_seconds + 60)
                if stage is None:
                    finish('insufficient_repair_budget')
                    break
                repair = read_repair_result(stage / 'workspace', candidate['commit'], expected_ids)
                record['stages'][-1]['repair_claim'] = repair
                save()
                # Legacy global claims remain readable; neither form bypasses review.
                specification_claim = repair['action'] == 'needs_specification' or any(
                    item['disposition'] == 'needs_specification' for item in repair['issues'])
                previous = candidate
                candidate = capture(stage, repairs + 1)
                candidate['changes'] = delta(previous, candidate)
                record['stages'][-1]['actual_changes'] = candidate['changes']
                changed = any(candidate['changes'].values())
                if (repair['action'] == 'no_change' and changed) or (repair['action'] == 'repaired' and not changed):
                    record['stages'][-1]['action_mismatch'] = 'Declared action differs from the captured file changes.'
                repairs += 1
                record['repairs_completed'] = repairs
                # This session sees original evidence and both versions. Fresh discovery never does.
                context = root / 'reviews' / f'{repairs:03d}' / 'context'
                copy_tree(Path(previous['path']), context / 'before', excluded={'.git'})
                copy_tree(feedback, context / 'feedback')
                if (stage / 'executions').is_dir():
                    copy_tree(stage / 'executions', context / 'repair-executions', excluded={'replay-work'})
                write_json(context / 'request.json', {'before_commit': previous['commit'], 'after_commit': candidate['commit'],
                           'issue_ids': expected_ids, 'repair_claim': repair, 'actual_changes': candidate['changes'],
                           'before_source': 'before/', 'feedback': 'feedback/',
                           'repair_executions': 'repair-executions/' if (context/'repair-executions').is_dir() else None})
                review_folder = root / 'reviews' / f'{repairs:03d}' / 'audit'
                entry = phase('repair_verification', review_folder)
                seconds = min(settings.repair_verification_seconds, remaining() - 10)
                entry['allocated_seconds'] = max(0, seconds)
                if seconds <= 0:
                    forced_stop = 'verification_incomplete'
                    entry.update(status='not_started', reason='No review budget remains', ended_at=utc_now())
                else:
                    bundle = root / 'reviews' / f'{repairs:03d}' / 'handoff'
                    try:
                        review_run = runtime.verify(settings, candidate, review_folder, context, seconds,
                                                    min(seconds + 10, remaining()))
                        agents = read_json(review_run / 'run.json').get('agents')
                        if agents:
                            entry['agents'] = {**agents, 'run_dir': str(review_run)}
                        entry.update(status='returned', audit_run=str(review_run), ended_at=utc_now())
                        prepare_handoff(review_run, candidate, bundle)
                        result = review_result(bundle, previous, candidate, expected_ids)
                    except StopWorkflow as exc:
                        if exc.status == 'interrupted':
                            raise
                        forced_stop = 'verification_incomplete' if exc.status == 'budget_exhausted' else 'verification_failed'
                        entry.update(status='failed', reason=str(exc), ended_at=utc_now())
                    except (OSError, ValueError) as exc:
                        forced_stop = 'verification_incomplete'
                        entry.update(status='incomplete', reason=str(exc))
                    else:
                        apply_review(issues, result, bundle, candidate)
                        note = catalog_entry(bundle, candidate, f'r{repairs:03d}', 'review.json')
                        if note:
                            catalog.append(note)
                        entry['review_result'] = result
                        entry['discovered_issues'] = [item['id'] for item in result['new_issues']]
                        states = {issue['state'] for issue in pending(issues)}
                        if 'environment_blocked' in states:
                            forced_stop = 'environment_blocked'
                if (not changed and not specification_claim and not forced_stop
                        and not any(issue['id'] in expected_ids and issue['state'] == 'needs_specification' for issue in issues)):
                    forced_stop = 'no_change'
                save()
                # The final discovery may be repaired. Its independent review
                # ends the run, including any unresolved or newly found issues.
                if (forced_stop or final or repairs >= settings.max_repairs
                        or pending(issues) and not repairable(issues)
                        or remaining() < settings.audit_seconds + repair_reserve + 10):
                    finish(forced_stop or ('needs_specification' if pending(issues) and not repairable(issues) else
                           'repair_limit' if repairs >= settings.max_repairs else
                           'insufficient_repair_budget' if pending(issues) else 'final_review_complete'))
                    break
                number += 1
        except StopWorkflow as exc:
            record.update(status=exc.status, stop_reason=exc.status, reason=str(exc))
        except (KeyboardInterrupt, Terminated):
            record.update(status='interrupted', stop_reason='interrupted', reason='Controller interrupted between stages')
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            record.update(status='controller_step_failed', stop_reason='controller_step_failed', reason=str(exc))
        finally:
            old_int = signal.signal(signal.SIGINT, signal.SIG_IGN)
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            try:
                for entry in record['stages']:
                    if entry['status'] == 'running':
                        entry.update(status=record['status'], ended_at=utc_now())
                    if entry.get('finding_import', {}).get('status') == 'pending':
                        entry['finding_import'].update(status='failed', error=record.get('reason', 'No completed import'))
                    record_audit_progress(root, entry)
                record.update(ended_at=utc_now(), elapsed_seconds=time.monotonic() - start)
                save()
            finally:
                signal.signal(signal.SIGINT, old_int)
                signal.signal(signal.SIGTERM, old_term)
        return record


def inspect(root):
    root = Path(root).resolve()
    record = read_json(root / 'experiment.json')
    # Also expose old failed runs and unfinished supplements without rewriting archives.
    for entry in record['stages']:
        if entry['status'] not in {'running', 'not_started'}:
            record_audit_progress(root, entry)
    return {'experiment_dir': str(root), 'status': record['status'],
            'issue_index_status': record.get('issue_index_status',
                                             'incomplete' if record['status'] == 'audit_incomplete' else 'unknown'),
            'reason': record.get('reason'), 'stop_reason': record.get('stop_reason'), 'open_issues': record.get('open_issues', []), 'elapsed_seconds': record.get('elapsed_seconds'),
            'awaiting_specification': record.get('awaiting_specification', []),
            'evidence_index': str(root / record['evidence_index']) if record.get('evidence_index') else None,
            'pending_audit_reports': [stage['pending_report'] for stage in record['stages'] if 'pending_report' in stage],
            'models': {'generation_and_repair': [record['settings']['generator_model'], record['settings']['generator_reasoning_effort']],
                       'audit': [record['settings']['audit_model'], record['settings']['audit_reasoning_effort']]},
            'candidate': record.get('current_candidate'), 'last_audit': record.get('last_audit'),
            'stages': record['stages']}
