"""Private native configuration for generation and repair; no model calls here."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

from runtime.codex_support import common_settings, codex_options


class Client:
    def __init__(self, settings, stage, deadline):
        self.stage, self.deadline = stage, deadline
        self.executable = shutil.which(settings.codex)
        if not self.executable:
            raise FileNotFoundError('Codex CLI is unavailable: ' + settings.codex)
        if settings.profile:
            raise ValueError('Host Codex profiles are not supported by isolated generation')
        instructions = (stage / 'inputs/AGENTS.md').read_text()
        self.private = tempfile.TemporaryDirectory(prefix='.client-', dir=stage)
        self.home = Path(self.private.name)
        self.client_home = self.home / 'codex'
        self.client_home.mkdir()
        self.secrets = []
        self.environment = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': str(self.home),
                            'CODEX_HOME': str(self.client_home), 'LANG': 'C.UTF-8'}
        for key in ('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY',
                    'http_proxy', 'https_proxy', 'all_proxy', 'no_proxy', 'SSL_CERT_FILE', 'SSL_CERT_DIR'):
            if key in os.environ:
                self.environment[key] = os.environ[key]
        self.settings = {**common_settings(), 'web_search': settings.web_search,
                         'model': settings.model, 'sandbox_mode': 'workspace-write',
                         'projects': {str(stage / 'workspace'): {'trust_level': 'untrusted'}},
                         'developer_instructions': instructions,
                         'shell_environment_policy.inherit': 'none',
                         'shell_environment_policy.experimental_use_profile': False}
        if settings.reasoning_effort:
            self.settings['model_reasoning_effort'] = settings.reasoning_effort

    def prepare(self, tool_environment):
        self.settings['shell_environment_policy.set'] = tool_environment
        # Bundled skills are materialized on first prompt initialization, without a model call.
        self.probe()
        self.settings['skills.config'] = [{'path': str(path), 'enabled': False}
                                         for path in sorted(self.client_home.glob('skills/**/SKILL.md'))]
        items = self.probe()
        kinds = [kind for item in items for kind in item.get('internal_chat_message_metadata_passthrough', {})
                 .get('content_item_kinds', [])]
        if any(kind in {'host_skills.instructions', 'agents_md.instructions'} or 'memory' in kind or 'plugin' in kind
               for kind in kinds):
            raise ValueError('Unexpected automatic instructions in isolated generation prompt')
        for name, value in [('client-prompt.json', items), ('client-settings.json', self.settings)]:
            (self.stage / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

    def probe(self):
        result = subprocess.run([self.executable, '--no-daemon', 'debug', 'prompt-input',
                                 *codex_options(self.settings), 'Local configuration inspection only.'],
                                cwd=self.stage / 'workspace', env=self.environment,
                                capture_output=True, text=True,
                                timeout=max(.01, min(30, self.deadline - time.monotonic())) if self.deadline is not None else 30)
        if result.returncode:
            (self.stage / 'client-probe.stderr').write_text(result.stderr)
            raise ValueError('Native prompt isolation check failed; see client-probe.stderr')
        items = json.loads(result.stdout)
        if not isinstance(items, list) or not items:
            raise ValueError('Native prompt isolation check returned no usable context')
        return items

    def authenticate(self):
        key = os.environ.get('CODEX_API_KEY')
        if key:
            self.environment['CODEX_API_KEY'] = key
            self.settings['forced_login_method'] = 'api'
            self.secrets = [key]
            return
        original = Path(os.environ.get('CODEX_HOME', Path.home() / '.codex')) / 'auth.json'
        if not original.is_file() or original.is_symlink():
            raise ValueError('Generation requires file-backed ChatGPT login or CODEX_API_KEY; no automatic login')
        data = original.read_bytes()
        auth = json.loads(data)
        if auth.get('auth_mode') != 'chatgpt':
            raise ValueError('Generation requires ChatGPT file authentication or explicit CODEX_API_KEY')
        path = self.client_home / 'auth.json'
        path.write_bytes(data)
        path.chmod(0o600)
        self.settings['forced_login_method'] = 'chatgpt'
        self.secrets = [value for key, value in auth.get('tokens', {}).items()
                        if key in {'access_token', 'refresh_token', 'id_token'} and isinstance(value, str)]

    def close(self):
        try:
            for name in ('events.jsonl', 'stderr.log', 'final.txt'):
                path = self.stage / name
                if path.is_file():
                    data = path.read_bytes()
                    for secret in self.secrets:
                        if secret:
                            data = data.replace(secret.encode(), b'[REDACTED_CREDENTIAL]')
                    path.write_bytes(data)
        finally:
            self.private.cleanup()
