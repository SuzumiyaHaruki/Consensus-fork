"""Optional execution from a captured candidate, with retained caller-selected files."""
import os
from pathlib import Path
import shutil
import stat

from .storage import EXCLUDED_DIRS, MAX_SOURCE_BYTES, sensitive_file

MAX_OUTPUT_BYTES = 64 * 1024 * 1024
MAX_OUTPUT_FILES = 1024


def regular_file(root, name):
    relative = Path(name)
    if not relative.parts or relative.is_absolute() or '..' in relative.parts or set(relative.parts) & (EXCLUDED_DIRS | {'.runtime', '.forge'}):
        raise ValueError('Replay input must be a relative file within the working copy')
    path = root / relative
    if any(p.is_symlink() for p in (path, *path.parents) if p.is_relative_to(root)):
        raise ValueError('Replay inputs must not traverse symbolic links')
    # Resolve through directory descriptors so concurrent test edits cannot swap
    # an already-checked parent for a symlink and make this host-side copy escape.
    directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in relative.parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = child
        descriptor = os.open(relative.parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        with os.fdopen(descriptor, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > MAX_SOURCE_BYTES:
                raise ValueError('Replay input must be a bounded regular file, not a hardlink')
            data = stream.read(MAX_SOURCE_BYTES + 1)
    finally:
        os.close(directory)
    if len(data) > MAX_SOURCE_BYTES:
        raise ValueError('Replay input grew beyond its size limit while reading')
    if sensitive_file(path, data) or data.startswith(b'\x7fELF'):
        raise ValueError('Replay input contains private data or a compiled executable')
    return data, stat.S_IMODE(info.st_mode) & 0o111


def prepare(control, source, overlays, folder):
    work = Path(control['work'])
    environment = dict(control['environment'])
    if source is None:
        if overlays:
            raise ValueError('overlays require a captured source selection')
        return work, environment, {'kind': 'mutable_workspace', **control.get('source_context', {}),
                                  'scope': 'Base version is context only; this command uses a mutable working copy.'}
    selected = control.get('replay_sources', {}).get(source)
    if not selected:
        raise ValueError('Unknown captured source; available: ' + ', '.join(control.get('replay_sources', {})))
    original, replay = Path(selected['path']), folder / 'replay-work'
    if original.is_symlink() or not original.is_dir():
        raise ValueError('Captured source must be an existing regular directory')
    # Sources come from trusted capture/context, not an agent-supplied host path.
    for directory, dirs, files in os.walk(original, followlinks=False):
        dirs[:] = [name for name in dirs if name not in EXCLUDED_DIRS and not (Path(directory)/name).is_symlink()]
        for name in files:
            relative = (Path(directory) / name).relative_to(original)
            data, executable = regular_file(original, str(relative))
            target = replay / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            target.chmod(0o644 | executable)
    replay.mkdir(exist_ok=True)
    retained = []
    for name in dict.fromkeys(overlays):
        data, executable = regular_file(work, name)
        target = replay / name
        replaces = target.exists()
        for path in (folder / 'inputs' / name, target):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            path.chmod(0o644 | executable)
        retained.append({'path': name, 'replaces_source': replaces, 'retained_path': str(Path('inputs') / name)})
    for key, value in environment.items():
        environment[key] = value.replace(str(work), str(replay))
    for key in ('HOME', 'TMPDIR', 'GOCACHE', 'GOMODCACHE'):
        path = Path(environment.get(key, '/'))
        if path.is_relative_to(replay):
            path.mkdir(parents=True, exist_ok=True)
    return replay, environment, {'kind': 'candidate_copy', 'label': source, 'commit': selected['commit'],
                                'overlays': retained,
                                'scope': 'Captured starting source plus retained overlays; commands may change their private copy. No assertion verdict.'}


def cleanup(folder):
    # Preserve overlays and logs, not build caches or the disposable candidate copy.
    path = folder / 'replay-work'
    if path.is_dir():
        shutil.rmtree(path)


def retain_outputs(work, requested, folder):
    """Copy selected outputs before cleanup; exclusions do not change test results."""
    result = {'files': [], 'excluded': []}
    seen, total = set(), 0

    def exclude(name, reason):
        result['excluded'].append({'path': name, 'reason': reason})

    for name in dict.fromkeys(requested):
        relative = Path(name)
        if (not relative.parts or relative.is_absolute() or '..' in relative.parts
                or set(relative.parts) & (EXCLUDED_DIRS | {'.runtime', '.forge'})):
            exclude(name, 'Select relative files or subdirectories outside private/cache directories')
            continue
        path = work / relative
        if any(p.is_symlink() for p in (path, *path.parents) if p.is_relative_to(work)):
            exclude(name, 'Symbolic links are not retained')
            continue
        if not path.exists():
            exclude(name, 'Requested output is missing')
            continue
        paths = [path]
        while paths:
            current = paths.pop()
            item = str(current.relative_to(work))
            if item in seen:
                continue
            seen.add(item)
            if len(seen) > MAX_OUTPUT_FILES:
                exclude(item, 'Output entry limit reached; remaining outputs were not collected')
                return result
            try:
                if current.is_symlink():
                    raise ValueError('Symbolic links are not retained')
                if set(Path(item).parts) & (EXCLUDED_DIRS | {'.runtime', '.forge'}):
                    raise ValueError('Private/cache directory is excluded')
                if current.is_dir():
                    # Bound enumeration as well as copying; no unbounded directory listing.
                    with os.scandir(current) as entries:
                        for entry in entries:
                            if len(paths) + len(seen) >= MAX_OUTPUT_FILES:
                                exclude(item, 'Output entry limit reached; directory listing is partial')
                                break
                            paths.append(Path(entry.path))
                    continue
                data, _ = regular_file(work, item)
                if total + len(data) > MAX_OUTPUT_BYTES:
                    raise ValueError('Total retained output byte limit exceeded')
                target = folder / 'artifacts' / item
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                total += len(data)
                result['files'].append({'path': item, 'retained_path': 'artifacts/' + item, 'bytes': len(data)})
            except (OSError, ValueError) as exc:
                exclude(item, str(exc))
    return result
