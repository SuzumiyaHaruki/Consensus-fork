#!/usr/bin/env python3
"""Offline CLI fixture, never an implementation of the consensus protocol."""

import json
import os
from pathlib import Path
import subprocess
import sys
import time


if "--version" in sys.argv:
    print("fake-codex offline-fixture")
    raise SystemExit(0)
if "--help" in sys.argv:
    print("--json --output-last-message --sandbox --no-daemon --ask-for-approval")
    raise SystemExit(0)
if sys.argv[1:4] == ['--no-daemon', 'debug', 'prompt-input']:
    print(json.dumps([{'role': 'developer', 'content': [],
                      'internal_chat_message_metadata_passthrough': {'content_item_kinds': ['generic.developer_instructions']}}]))
    raise SystemExit(0)

arguments = sys.argv[1:]
workspace = Path(arguments[arguments.index("--cd") + 1])
final = Path(arguments[arguments.index("--output-last-message") + 1])
prompt = sys.stdin.read()
(workspace / "received-prompt.txt").write_text(prompt)
(workspace / "received-args.json").write_text(json.dumps(arguments))
(workspace / 'received-environment.json').write_text(json.dumps({key: os.environ.get(key)
    for key in ('HOME', 'CODEX_HOME', 'FORGE_HOST_SENTINEL')}))
mode_file = workspace / "FAKE_MODE"
mode = mode_file.read_text().strip() if mode_file.exists() else "complete"


def emit(event):
    print(json.dumps(event), flush=True)


emit({"type": "thread.started", "thread_id": "offline-test-session"})
emit({"type": "turn.started"})
if mode in ("timeout", "interrupt", "background"):
    child_code = (
        "import os, pathlib, signal, sys, time; "
        "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
        "pathlib.Path(sys.argv[1]).write_text(str(os.getpid())); time.sleep(120)"
    )
    subprocess.Popen([sys.executable, "-c", child_code, str(workspace / "child.pid")])
    deadline = time.monotonic() + 2
    while not (workspace / "child.pid").exists() and time.monotonic() < deadline:
        time.sleep(0.01)
    if mode != "background":
        time.sleep(120)
if mode == "failed":
    emit({"type": "turn.failed", "error": {"message": "simulated provider failure"}})
    raise SystemExit(7)
if mode == "zero_exit_failure":
    emit({"type": "turn.failed", "error": {"message": "failure despite exit zero"}})
    raise SystemExit(0)
if mode == "incomplete":
    raise SystemExit(0)
if mode == "truncated":
    print('{"type":', flush=True)
    raise SystemExit(0)
emit({"type": "item.completed", "item": {"type": "command_execution", "command": "offline fixture only"}})
emit({"type": "item.completed", "item": {"type": "file_change", "changes": []}})
emit({"type": "turn.completed", "usage": {"input_tokens": 10, "cached_input_tokens": 2, "output_tokens": 3}})
final.write_text("Offline fixture completed. This is not a protocol implementation.\n")
