"""Log redaction, submodule checks and atomic evidence records."""
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from uuid import uuid4


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def redact(text: str) -> str:
    text = re.sub(r"(?i)(authorization[\s:]+(?:bearer\s+)?)[^\s\"']+", r"\1[REDACTED]", text)
    text = re.sub(r"(?i)((?:api[_-]?key|access[_-]?token|password|secret)[\"']?\s*[:=]\s*[\"']?)[^\s\"',}]+", r"\1[REDACTED]", text)
    text = re.sub(r"\b(?:sk-[A-Za-z0-9_-]{12,}|gh[pousr]_[A-Za-z0-9_]{16,})\b", "[REDACTED]", text)
    return text


def write_json(path: Path, value):
    """Atomically replace a JSON record; callers serialize their own model types."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def read_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return data


EXCLUDED_DIRS = {".git", ".codex", ".agents", ".ssh", ".aws", ".venv", "runs", "__pycache__"}
MAX_SOURCE_BYTES = 16_000_000


def file_digest(path):
    """Return (digest, size) for incremental evidence records with bounded buffers."""
    hasher, size = hashlib.sha256(), 0
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            hasher.update(block)
            size += len(block)
    return hasher.hexdigest(), size


def git(repo: Path, *args):
    try:
        result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=5)
        return result.stdout.strip() if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def fixed_submodules(repo):
    """Validate initialized gitlinks without fetching or following branch tips."""
    records = {}
    def visit(root, prefix=Path('.')):
        tree = git(root, 'ls-tree', '-rz', 'HEAD')
        if tree is None:
            if (root/'.git').exists():raise ValueError(f'Cannot inspect fixed Git tree: {root}')
            return
        for entry in tree.split('\0'):
            if not entry:continue
            meta, name = entry.split('\t', 1)
            mode, kind, expected = meta.split()
            if mode != '160000':continue
            relative = prefix / name
            child = root / name
            if Path(name).is_absolute() or '..' in Path(name).parts or any(
                    p.is_symlink() for p in [child, *child.parents] if p.is_relative_to(repo)):
                raise ValueError(f'Unsafe submodule path: {relative}')
            actual = git(child, 'rev-parse', 'HEAD') if (child/'.git').exists() else None
            if actual != expected:
                raise ValueError(f'Submodule {relative}: expected {expected}; actual {actual or "missing/uninitialized"}')
            status = git(child, 'status', '--porcelain', '--untracked-files=all')
            if status != '':
                raise ValueError(f'Submodule {relative}: expected {expected}; actual dirty or unreadable working tree')
            records[str(relative)] = expected
            visit(child, relative)
    visit(repo)
    return records
