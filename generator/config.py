"""Internal settings for one generation or repair stage."""

from dataclasses import asdict, dataclass, fields
import math
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    model: str | None = "gpt-6.1-sol"
    reasoning_effort: str | None = "high"
    timeout_seconds: float = 3600
    codex: str = "codex"
    profile: str | None = None
    web_search: str = "disabled"
    output_root: str = str(ROOT / "experiments")
    inputs_dir: str = str(ROOT / "inputs")
    execution_python: str = str(ROOT / ".venv/bin/python")
    action_seconds: float = 300

    def to_dict(self) -> dict:
        return asdict(self)


def settings_from_dict(values: dict, base: Path) -> Settings:
    if not isinstance(values, dict):
        raise ValueError("Configuration must be a JSON object")
    unknown = set(values) - {field.name for field in fields(Settings)}
    if unknown:
        raise ValueError(f"Unknown configuration fields: {', '.join(sorted(unknown))}")
    merged = Settings().to_dict() | values
    for name in ("model", "reasoning_effort", "profile"):
        value = merged[name]
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError(f"{name} must be a nonempty string or null")
    for name in ("codex", "web_search", "output_root", "inputs_dir", "execution_python"):
        if not isinstance(merged[name], str) or not merged[name].strip():
            raise ValueError(f"{name} must be a nonempty string")
    if merged["reasoning_effort"] not in (None, "minimal", "low", "medium", "high", "xhigh", "max", "ultra"):
        raise ValueError("Unrecognized reasoning_effort; use a level supported by your model")
    if merged["web_search"] not in ("disabled", "cached", "live"):
        raise ValueError("web_search must be disabled, cached, or live")
    for name in ('timeout_seconds', 'action_seconds'):
        seconds = merged[name]
        if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or seconds <= 0:
            raise ValueError(f'{name} must be finite and positive')
    merged['execution_python'] = os.path.abspath(base / Path(merged['execution_python']).expanduser())
    for name in ("output_root", "inputs_dir"):
        path = Path(merged[name]).expanduser()
        merged[name] = str((base / path).resolve() if not path.is_absolute() else path.resolve())
    # A bare name uses PATH; an explicit relative executable path is config-relative.
    if "/" in merged["codex"]:
        path = Path(merged["codex"]).expanduser()
        merged["codex"] = str((base / path).resolve())
    return Settings(**merged)
