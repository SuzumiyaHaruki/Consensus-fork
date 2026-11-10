"""Configuration for the finite generation/audit/repair experiment."""
from dataclasses import asdict, dataclass, fields
import json
import math
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT = ROOT / 'configs/workflow.json'


@dataclass(frozen=True)
class WorkflowSettings:
    generator_model: str = 'gpt-6.1-sol'
    generator_reasoning_effort: str = 'high'
    audit_model: str = 'gpt-6.1-sol'
    audit_reasoning_effort: str = 'high'
    codex: str = 'codex'
    audit_python: str = str(ROOT / '.venv/bin/python')
    audit_prompt: str = str(ROOT / 'inputs/AUDIT.md')
    inputs_dir: str = str(ROOT / 'inputs')
    repair_prompt: str = str(ROOT / 'inputs/REPAIR.md')
    review_prompt: str = str(ROOT / 'inputs/VERIFY.md')
    output_root: str = str(ROOT / 'experiments')
    audit_seconds: float = 3600
    repair_verification_seconds: float = 1800
    audit_turn_seconds: float = 900
    action_seconds: float = 300
    audit_calls: int = 20
    max_repairs: int = 3

    def to_dict(self):
        return asdict(self)


def from_dict(values, base):
    if not isinstance(values, dict):
        raise ValueError('Workflow configuration must be an object')
    unknown = set(values) - {f.name for f in fields(WorkflowSettings)}
    if unknown:
        raise ValueError('Unknown workflow settings: ' + ', '.join(sorted(unknown)))
    merged = WorkflowSettings().to_dict() | values
    for key, value in merged.items():
        if key.endswith('_seconds'):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f'{key} must be finite and positive')
        elif key in {'audit_calls', 'max_repairs'}:
            if type(value) is not int or value < (0 if key == 'max_repairs' else 1):
                raise ValueError(f'Invalid {key}')
        elif not isinstance(value, str) or not value.strip():
            raise ValueError(f'{key} must be a nonempty string')
    for key in ('generator_reasoning_effort', 'audit_reasoning_effort'):
        if merged[key] not in {'low', 'medium', 'high', 'xhigh', 'max', 'ultra'}:
            raise ValueError(f'Invalid {key}')
    for key in ('audit_python', 'audit_prompt', 'inputs_dir', 'repair_prompt', 'review_prompt', 'output_root'):
        path = Path(merged[key]).expanduser()
        # Do not resolve the virtualenv executable's symlink to the system Python.
        merged[key] = os.path.abspath(base / path if not path.is_absolute() else path)
    if '/' in merged['codex']:
        merged['codex'] = os.path.abspath(base / Path(merged['codex']).expanduser())
    return WorkflowSettings(**merged)


def load(path=DEFAULT, overrides=None):
    path = Path(path).resolve()
    settings = from_dict(json.loads(path.read_text()), path.parent)
    return from_dict(settings.to_dict() | (overrides or {}), Path.cwd())
