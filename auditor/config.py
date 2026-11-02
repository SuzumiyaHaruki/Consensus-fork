"""Strict configuration and CLI for the local Codex auditor."""
import argparse
import json
import re
import sys
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

class TargetConfig(Record):
    '''Configuration for the target environment.'''
    expected_module: str | None = None
    variant: str = ""
    analysis_roots: list[str] = []
    execution_package: str = "."
    harness_path: str | None = None

    @model_validator(mode="after")
    def relative_paths(self):
        paths=self.analysis_roots+[self.execution_package]+([self.harness_path] if self.harness_path else [])
        if any(not p or p.startswith('-') or Path(p).is_absolute() or '..' in Path(p).parts for p in paths):
            raise ValueError("Target paths must stay within the relative repository namespace")
        return self


class CodexProvider(Record):
    id: str
    base_url: str
    env_key: str
    model_catalog_path: str | None = None

    @model_validator(mode="after")
    def connection(self):
        if not re.fullmatch(r'[a-z][a-z0-9_-]{0,63}',self.id) or self.id in {'openai','ollama','lmstudio','amazon-bedrock'}:
            raise ValueError('Custom provider id must be a nonreserved simple identifier')
        url=urlsplit(self.base_url)
        if (url.scheme!='https' or not url.hostname or url.username is not None or url.password is not None
                or '?' in self.base_url or '#' in self.base_url or any(c.isspace() or c=='\\' for c in self.base_url)):
            raise ValueError('Provider base_url must be HTTPS without credentials, query, fragment or whitespace')
        _ = url.port
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',self.env_key) or self.env_key.upper() in {
                'PATH','HOME','CODEX_HOME','TMPDIR','LANG','LC_ALL','JAVA_HOME','JAVA_TOOL_OPTIONS','MAVEN_ARGS','MAVEN_OPTS','RUSTC','RUSTDOC','CARGO_HOME',
                'GOCACHE','GOMODCACHE','GOPROXY','GOSUMDB','GOTOOLCHAIN','GOFLAGS','SSL_CERT_FILE','SSL_CERT_DIR',
                'HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','NO_PROXY'}:
            raise ValueError('Provider env_key must name a dedicated credential variable, not a runtime setting')
        return self

def read_yaml(path):
    class UniqueLoader(yaml.SafeLoader):
        pass

    def mapping(loader, node):
        result = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node)
            if key in result:
                raise ValueError(f"Duplicate configuration key: {key}")
            result[key] = loader.construct_object(value_node)
        return result

    UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)
    value = yaml.load(Path(path).read_text(), Loader=UniqueLoader)
    if not isinstance(value, dict):
        raise ValueError("Configuration must be a mapping")
    return value


def relative_path(value, directory, *, resolve=True):
    path = Path(directory) / Path(value).expanduser()
    return str(path.resolve() if resolve else path.absolute())


def read_target(path):
    raw = read_yaml(path)
    backend = raw.get('execution_backend')
    if backend not in {'go_module', 'cargo', 'maven', 'python', 'none'}:
        raise ValueError('Unknown target execution_backend')
    target = TargetConfig.model_validate(raw.get('target', {}))
    return {'execution_backend': backend, 'target': target.model_dump()}



class Budget(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)
    total_seconds: float = Field(default=7200, gt=0)
    agent_calls: int = Field(default=120, gt=0)
    agent_turn_timeout: float = Field(default=900, gt=0)
    action_timeout: float = Field(default=600, gt=0)


class Config(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    baseline_id: Literal["codex_plain"] = "codex_plain"
    target_config: str
    task_path: str = str(Path(__file__).resolve().parents[1] / "inputs/AUDIT.md")
    task_mode: Literal['audit', 'review'] = 'audit'
    review_context: str | None = None
    repo_path: str | None = None
    agent_model: str
    agent_reasoning_effort: str | None
    codex_provider: CodexProvider | None = None
    auth_mode: Literal["codex_login", "api_key"]
    api_key_env: str | None = None
    runs_dir: str = "runs"
    allow_agent_materials: bool = False
    allow_experiments: bool = False
    go_mod_cache_dir: str | None = None
    cargo_dependency_cache_dir: str | None = None
    maven_dependency_cache_dir: str | None = None
    budget: Budget = Field(default_factory=Budget)

    @model_validator(mode="after")
    def validate_connection(self):
        if (self.task_mode == 'review') != bool(self.review_context):
            raise ValueError('Only repair verification requires review_context; fresh audits must not receive it')
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]*", self.agent_model):
            raise ValueError("agent_model must be one explicit identifier")
        if self.agent_reasoning_effort is not None and not re.fullmatch(r"[a-z]+", self.agent_reasoning_effort):
            raise ValueError("agent_reasoning_effort must be an explicit level or null")
        if self.codex_provider:
            if self.auth_mode != "api_key" or self.api_key_env is not None:
                raise ValueError("Custom providers use api_key and codex_provider.env_key only")
        elif self.auth_mode == "api_key":
            if not self.api_key_env:
                raise ValueError("Native API authentication requires api_key_env")
            CodexProvider(id="validation", base_url="https://example.org", env_key=self.api_key_env)
        elif self.api_key_env is not None:
            raise ValueError("codex_login must not configure an API credential")
        return self

    @property
    def credential_name(self):
        return self.codex_provider.env_key if self.codex_provider else self.api_key_env


def load_config(path):
    path = Path(path).expanduser().resolve()
    raw = read_yaml(path)
    config = Config.model_validate(raw)
    for name in ("target_config", "task_path", "review_context", "repo_path", "runs_dir", "go_mod_cache_dir", "cargo_dependency_cache_dir", "maven_dependency_cache_dir"):
        value = getattr(config, name)
        if value is not None:
            setattr(config, name, relative_path(value, path.parent))
    if config.codex_provider and config.codex_provider.model_catalog_path:
        config.codex_provider.model_catalog_path = relative_path(config.codex_provider.model_catalog_path, path.parent)
    return config


def load_target(config):
    raw = read_target(config.target_config)
    if raw.get("execution_backend") not in {"go_module", "cargo", "maven"}:
        raise ValueError("Only go_module, cargo and maven targets are supported")
    fields = {k: v for k, v in raw.get("target", {}).items()
              if k in {"variant", "expected_module", "execution_package", "analysis_roots"}}
    target = TargetConfig.model_validate(fields)
    return {"execution_backend": raw["execution_backend"], **target.model_dump(exclude={"harness_path"})}


def validate_selection(config):
    values = [config.agent_model]
    if config.codex_provider:
        values += [config.codex_provider.id, config.codex_provider.base_url]
    if any(re.search(r"(?i)(replace[_-]?me|fill[_-]?me|\.invalid\b|<|>)", v) for v in values):
        raise ValueError("Replace placeholder endpoint/model before invoking Codex")
    if not config.repo_path or not Path(config.repo_path).is_dir():
        raise ValueError("repo_path must identify an explicitly selected local repository")
    repo, runs = Path(config.repo_path), Path(config.runs_dir)
    if runs.is_relative_to(repo) or repo.is_relative_to(runs):
        raise ValueError("runs_dir and source repository must be disjoint")
    project = Path(__file__).resolve().parent.parent
    if repo == project or project.is_relative_to(repo):
        raise ValueError("The framework repository cannot be the audit target")
    return load_target(config)


def main(argv=None):
    parser = argparse.ArgumentParser(description="本地 Codex 审计；check-env 不调用模型")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("check-env", "run"):
        command = sub.add_parser(name)
        command.add_argument("--config", required=True)
        command.add_argument("--target-config", help="Neutral target definition; relative to the current directory")
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        if args.target_config:
            config.target_config = relative_path(args.target_config, Path.cwd())
        target = validate_selection(config)
        if args.command != "check-env" and not (config.allow_agent_materials and config.allow_experiments):
            raise ValueError("Set allow_agent_materials and allow_experiments explicitly before model use")
        from .runner import check_environment, run
        result = check_environment(config, target) if args.command == "check-env" else run(config, target)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 1
    except ValidationError as exc:
        problems = [".".join(map(str, e["loc"])) + ": " + e["msg"] for e in exc.errors(include_input=False)]
        print("配置无效：" + "; ".join(problems), file=sys.stderr)
        return 2
    except (ValueError, OSError, yaml.YAMLError) as exc:
        print(f"审计未启动：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
