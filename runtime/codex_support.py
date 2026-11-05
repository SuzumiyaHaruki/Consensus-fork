"""Neutral Codex options and top-level failure interpretation from CA."""
import json
import re


DISABLED_FEATURES = (
    "apps", "plugins", "remote_plugin", "hooks", "memories", "multi_agent_v2",
    "skill_search", "skill_mcp_dependency_install", "shell_snapshot", "browser_use",
    "browser_use_external", "computer_use", "image_generation", "external_agent_memory_import",
    "unbounded_connection_retries", "workspace_dependencies", "in_app_local_automation",
)


def toml(value):
    if isinstance(value, dict):
        return "{" + ",".join(json.dumps(k) + "=" + toml(v) for k, v in value.items()) + "}"
    if isinstance(value, list):
        return "[" + ",".join(toml(v) for v in value) + "]"
    return json.dumps(value)


def codex_options(settings):
    return [arg for key, value in settings.items() for arg in ("-c", key + "=" + toml(value))]


def common_settings(provider=None):
    """Isolated capabilities; native subagents inherit the parent permissions."""
    settings = {"project_doc_max_bytes": 0, "web_search": "disabled", "mcp_servers": {}, "approval_policy": "never",
                "allow_login_shell": False, "memories.use_memories": False, "memories.generate_memories": False,
                "features.skip_host_skill_discovery": True,
                "features.multi_agent": True,
                **{"features." + name: False for name in DISABLED_FEATURES}}
    if provider:
        settings.update({f"model_providers.{provider.id}.{key}": value for key, value in {
            "request_max_retries": 4, "stream_max_retries": 5, "stream_idle_timeout_ms": 300000}.items()})
    return settings


def classify_failure(text: str) -> str:
    low = text.lower()
    if any(s in low for s in ["insufficient_quota", "quota exceeded", "usage limit", "rate limit", "quota exhausted", "credits exhausted"]):
        return 'quota_exhausted'
    if (any(s in low for s in ["login required", "not logged in", "please log in", "authentication required", "unauthorized", "run codex login"])
            or re.search(r"\b(?:http(?:/\d(?:\.\d)?)?|status(?: code)?)\s*[:=]?\s*401\b", low)):
        return 'login_required'
    return 'error'


def codex_diagnostic(events):
    """Retain top-level failures, without interpreting tool output as a native error."""
    from .storage import redact
    errors = [e.get('error') if e.get('type') == 'turn.failed' else e.get('message')
        for e in events if e.get('type') in {'turn.failed','error'}]
    messages = [' '.join(str(error[k]) for k in ('code','message') if error.get(k))
        if isinstance(error,dict) else str(error or '') for error in errors]
    messages = [m if m.strip() else 'Unspecified Codex failure' for m in messages]
    return {'message': redact('\n'.join(messages))}
