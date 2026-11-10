import fcntl
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

from generator.config import ROOT, Settings, settings_from_dict
from generator.runner import execute, prepare, read_json, summarize_events
from generator.client import Client


def process_alive(pid):
    try:
        stat = Path(f"/proc/{pid}/stat").read_text()
        return stat.split(")", 1)[1].split()[0] != "Z"
    except (FileNotFoundError, ProcessLookupError):
        return False


def await_process_exit(pid):
    # SIGKILL delivery is asynchronous for orphan descendants; allow the scheduler to run.
    deadline = time.monotonic() + 1
    while process_alive(pid) and time.monotonic() < deadline:
        time.sleep(0.01)
    return not process_alive(pid)


class RunnerTests(unittest.TestCase):
    def setUp(self):
        stub = patch('generator.execution.prepare', return_value={'options': ['-c', 'mcp_servers.forge_local.required=true']})
        stub.start()
        self.addCleanup(stub.stop)
        self.temporary = tempfile.TemporaryDirectory(prefix="forge-runner-tests-")
        self.root = Path(self.temporary.name)
        home = patch.dict(os.environ, {'CODEX_HOME': str(self.root / 'codex-home'), 'CODEX_API_KEY': '',
                                      'FORGE_HOST_SENTINEL': 'not-for-the-agent'})
        home.start()
        self.addCleanup(home.stop)
        private = self.root / 'codex-home'
        private.mkdir()
        (private / 'auth.json').write_text(json.dumps({'auth_mode': 'chatgpt', 'tokens': {'access_token': 'fixture-login'}}))
        self.inputs = self.root / "inputs"
        shutil.copytree(ROOT / "inputs", self.inputs)
        self.fake = self.root / "fake codex"
        shutil.copyfile(ROOT / "tests" / "fake_codex.py", self.fake)
        self.fake.chmod(0o755)
        self.settings = Settings(
            model="offline-fixture", codex=str(self.fake), timeout_seconds=10,
            inputs_dir=str(self.inputs), output_root=str(self.root / "stages"),
        )

    def tearDown(self):
        self.temporary.cleanup()

    def prepared(self, mode="complete", timeout=None):
        settings = self.settings
        if timeout is not None:
            settings = settings_from_dict(settings.to_dict() | {"timeout_seconds": timeout}, self.root)
        run = prepare(settings)
        (run / 'execution-control.json').write_text(json.dumps({'environment': {'PATH': '/usr/bin:/bin'}}))
        (run / "workspace" / "FAKE_MODE").write_text(mode)
        return run

    def test_preparation_is_offline_separate_and_retains_delivered_inputs(self):
        # Missing executable does not prevent preparing materials without a model call.
        settings = settings_from_dict(self.settings.to_dict() | {"codex": "nonexistent-offline-codex"}, self.root)
        first = prepare(settings)
        second = prepare(settings)
        self.assertNotEqual(first, second)
        self.assertTrue((first / "workspace" / ".git").is_dir())
        self.assertFalse((first / "events.jsonl").exists())
        self.assertFalse((first / "workspace" / "evaluation").exists())
        self.assertNotIn('trace_helper', read_json(first / 'run.json'))
        for folder in ('inputs', 'workspace'):
            self.assertEqual((first / folder / 'protocol.md').read_bytes(), (ROOT / 'inputs/protocol.md').read_bytes())
            self.assertFalse((first / folder / 'pseudocode.md').exists())
        self.assertEqual((first / 'inputs/schedule.py').read_bytes(), (ROOT / 'runtime/schedule.py').read_bytes())
        self.assertFalse((first / 'workspace/schedule.py').exists())
        self.assertEqual(read_json(first / 'run.json')['schedule_helper'], 'inputs/schedule.py')
        original = (first / "inputs" / "TASK.md").read_text()
        (self.inputs / "TASK.md").write_text("Changed for a later experiment")
        self.assertEqual((first / "prompt.txt").read_text(), original)
        self.assertEqual((first / "workspace" / "TASK.md").read_text(), original)

    def test_complete_process_records_events_without_claiming_correctness(self):
        run = self.prepared()
        result = execute(run)
        self.assertEqual(result["status"], "agent_finished")
        self.assertNotIn('assessment', result)
        self.assertFalse(result['agents']['usage_complete'])
        self.assertIsNone(result['agents']['usage'])
        self.assertTrue((run / 'agents.json').is_file())
        self.assertEqual(result["events"]["thread_ids"], ["offline-test-session"])
        self.assertEqual(result["events"]["usage_events"][0]["input_tokens"], 10)
        self.assertEqual((run / "workspace" / "received-prompt.txt").read_text(), (run / "prompt.txt").read_text())
        args = json.loads((run / "workspace" / "received-args.json").read_text())
        self.assertIn("workspace-write", args)
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", args)
        self.assertEqual(args[args.index("--ask-for-approval") + 1], "never")
        env = read_json(run / 'workspace/received-environment.json')
        self.assertNotEqual(env['CODEX_HOME'], os.environ['CODEX_HOME'])
        self.assertIsNone(env['FORGE_HOST_SENTINEL'])
        self.assertFalse(Path(env['CODEX_HOME']).exists())
        self.assertFalse(list(run.glob('.client-*')))
        config = read_json(run / 'client-settings.json')
        self.assertEqual(config['developer_instructions'], (self.inputs / 'IMPLEMENTATION.md').read_text())
        self.assertEqual(config['project_doc_max_bytes'], 0)

    def test_no_stage_deadline_completes_and_keeps_action_timeout(self):
        self.settings = settings_from_dict(self.settings.to_dict() | {'timeout_seconds': None}, self.root)
        run = self.prepared()
        result = execute(run)
        self.assertEqual(result['status'], 'agent_finished')
        self.assertIsNone(result['settings']['timeout_seconds'])
        self.assertEqual(result['settings']['action_seconds'], 300)
        self.assertFalse(list(run.glob('.client-*')))

    def test_private_client_copies_only_auth_and_cleans_secrets_on_failure(self):
        run = self.prepared()
        host = self.root / 'codex-home'
        (host / 'config.toml').write_text('developer_instructions="HOST"\n')
        (host / 'AGENTS.md').write_text('HOST')
        (host / 'skills').mkdir()
        original = (host / 'auth.json').read_bytes()
        client = Client(self.settings, run, time.monotonic() + 10)
        try:
            client.prepare({'PATH': '/usr/bin:/bin'})
            client.authenticate()
            private_auth = client.client_home / 'auth.json'
            self.assertEqual(private_auth.read_bytes(), original)
            self.assertEqual(private_auth.stat().st_mode & 0o777, 0o600)
            self.assertFalse((client.client_home / 'config.toml').exists())
            self.assertFalse((client.client_home / 'AGENTS.md').exists())
            (run / 'stderr.log').write_text('fixture-login')
        finally:
            client.close()
        self.assertEqual((host / 'auth.json').read_bytes(), original)
        self.assertEqual((run / 'stderr.log').read_text(), '[REDACTED_CREDENTIAL]')
        self.assertFalse(client.home.exists())

    def test_isolation_failure_stops_before_authentication_or_model_call(self):
        run = self.prepared()
        items = [{'internal_chat_message_metadata_passthrough': {'content_item_kinds': ['host_skills.instructions']}}]
        with patch.object(Client, 'probe', return_value=items), patch.object(Client, 'authenticate') as auth:
            result = execute(run)
        auth.assert_not_called()
        self.assertEqual(result['status'], 'launch_failed')
        self.assertFalse((run / 'workspace/received-prompt.txt').exists())
        self.assertFalse(list(run.glob('.client-*')))

    def test_explicit_api_key_is_not_in_shell_environment_or_saved_settings(self):
        run = self.prepared()
        client = Client(self.settings, run, time.monotonic() + 10)
        try:
            client.prepare({'PATH': '/usr/bin:/bin'})
            with patch.dict(os.environ, {'CODEX_API_KEY': 'fixture-api-key'}):
                client.authenticate()
            self.assertEqual(client.environment['CODEX_API_KEY'], 'fixture-api-key')
            self.assertNotIn('fixture-api-key', json.dumps(client.settings))
            self.assertFalse((client.client_home / 'auth.json').exists())
        finally:
            client.close()

    def test_missing_authentication_does_not_fall_back_to_host_configuration(self):
        run = self.prepared()
        (self.root / 'codex-home/auth.json').unlink()
        result = execute(run)
        self.assertEqual(result['status'], 'launch_failed')
        self.assertFalse((run / 'events.jsonl').exists())
        self.assertFalse(list(run.glob('.client-*')))

    def test_failed_execution_preflight_stops_before_any_native_model_invocation(self):
        run = self.prepared()
        with patch('generator.execution.prepare', side_effect=ValueError('fixture local execution unavailable')):
            result = execute(run)
        self.assertEqual(result['status'], 'environment_blocked')
        self.assertFalse((run / 'events.jsonl').exists())
        self.assertFalse((run / 'workspace/received-prompt.txt').exists())
        self.assertIn('fixture local execution unavailable', result['error'])

    def test_failure_and_truncation_are_not_success(self):
        for mode, expected in (("failed", "agent_failed"), ("zero_exit_failure", "agent_failed"), ("incomplete", "incomplete_output"), ("truncated", "incomplete_output")):
            with self.subTest(mode=mode):
                run = self.prepared(mode)
                self.assertEqual(execute(run)["status"], expected)
                self.assertTrue((run / "workspace" / "received-prompt.txt").exists())

    def test_launch_error_is_saved(self):
        settings = settings_from_dict(self.settings.to_dict() | {"codex": "nonexistent-offline-codex"}, self.root)
        run = prepare(settings)
        self.assertEqual(execute(run)["status"], "launch_failed")
        self.assertIn("error", read_json(run / "run.json"))

    def test_timeout_kills_descendant_even_if_it_ignores_term(self):
        run = self.prepared("timeout", timeout=0.6)
        result = execute(run)
        self.assertEqual(result["status"], "timed_out")
        child = int((run / "workspace" / "child.pid").read_text())
        self.assertTrue(await_process_exit(child))
        self.assertTrue((run / "events.jsonl").exists())
        self.assertLess(result["elapsed_seconds"], 8)

    def test_normal_exit_cleans_up_leftover_local_children(self):
        run = self.prepared("background")
        self.assertEqual(execute(run)["status"], "agent_finished")
        child = int((run / "workspace" / "child.pid").read_text())
        self.assertTrue(await_process_exit(child))

    def test_sigterm_saves_partial_run_and_stops_children(self):
        self.settings = settings_from_dict(self.settings.to_dict() | {'timeout_seconds': None}, self.root)
        run = self.prepared("interrupt")
        script = (
            "import sys; from pathlib import Path; from generator.runner import execute; "
            "from unittest.mock import patch; patch('generator.execution.prepare', return_value={'options': []}).start(); "
            "result = execute(Path(sys.argv[1])); "
            "sys.exit(130 if result['status'] == 'interrupted' else 1)"
        )
        process = subprocess.Popen(
            [sys.executable, "-c", script, str(run)],
            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        try:
            marker = run / "workspace" / "child.pid"
            deadline = time.monotonic() + 10
            while not marker.exists() and time.monotonic() < deadline:
                if process.poll() is not None:
                    self.fail(f"runner exited before cancellation: {process.communicate()}")
                time.sleep(0.02)
            self.assertTrue(marker.exists())
            process.send_signal(signal.SIGTERM)
            process.communicate(timeout=8)
            self.assertEqual(process.returncode, 130)
            self.assertEqual(read_json(run / "run.json")["status"], "interrupted")
            self.assertTrue(await_process_exit(int(marker.read_text())))
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()

    def test_reexecution_does_not_overwrite_prior_run(self):
        run = self.prepared()
        execute(run)
        events = (run / "events.jsonl").read_bytes()
        with self.assertRaisesRegex(ValueError, "fresh run"):
            execute(run)
        self.assertEqual((run / "events.jsonl").read_bytes(), events)

    def test_concurrent_ownership_is_rejected_without_modifying_state(self):
        run = self.prepared()
        with (run / ".runner.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(ValueError, "Another runner"):
                execute(run)
        self.assertEqual(read_json(run / "run.json")["status"], "prepared")

    def test_configuration_rejects_invalid_budget_and_unknown_fields(self):
        for value in (0, -1, True, float("inf"), "30"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                settings_from_dict({"timeout_seconds": value}, self.root)
        with self.assertRaises(ValueError):
            settings_from_dict({"unknown_setting": True}, self.root)
        settings = settings_from_dict({"output_root": "relative-stages"}, self.root)
        self.assertEqual(settings.output_root, str(self.root / "relative-stages"))

    def test_event_summary_tolerates_future_events_and_partial_lines(self):
        path = self.root / "events.jsonl"
        path.write_text('\n'.join([
            '{"type":"future.event"}', 'null', '{"type":"item.completed","item":null}',
            '{"type":"turn.completed","usage":{"input_tokens":1}}',
            '{"type":"turn.started"}', '{"unfinished":',
        ]))
        summary = summarize_events(path)
        self.assertEqual(summary["invalid_json_lines"], 2)
        self.assertEqual(summary["completed_turns"], 1)
        self.assertEqual(summary["last_turn_event"], "turn.started")


if __name__ == "__main__":
    unittest.main()
