"""Neutral tool and offline dependency environments shared with the plain baseline."""
import os
from pathlib import Path
import shutil
import subprocess
import re


def executable(name):
    path = shutil.which(name)
    if not path:
        raise ValueError(f"{name} is required; add its installation bin directory to PATH")
    return Path(path).resolve()


def cargo_tool():
    cargo = executable('cargo')
    if cargo.name == 'rustup':
        cargo = Path(subprocess.check_output([str(cargo), 'which', 'cargo'], text=True, timeout=10).strip()).resolve()
    return cargo


def cargo_environment(scratch, cargo, cache):
    home = scratch / 'cargo-home'
    if any(p.is_symlink() for p in [home, scratch]):
        raise ValueError('Cargo scratch directory traverses a symlink')
    home.mkdir(parents=True, exist_ok=True)
    for name in ('registry', 'git'):
        source, dest = cache / name, home / name
        if not source.is_dir():
            continue
        if source.is_symlink():
            raise ValueError('Cargo dependency roots must not be symlinks')
        if dest.is_symlink() and dest.resolve() == source.resolve():
            continue
        if dest.exists() or dest.is_symlink():
            raise ValueError('Cargo scratch cache differs from the configured dependency cache')
        dest.symlink_to(source, target_is_directory=True)
    return {'CARGO_HOME': str(home), 'CARGO_TARGET_DIR': str(scratch / 'cargo-target'),
            'CARGO_NET_OFFLINE': 'true', 'CARGO_TERM_COLOR': 'never', 'CARGO_BUILD_JOBS': '2',
            'RUSTC': str(cargo.parent / 'rustc'), 'RUSTDOC': str(cargo.parent / 'rustdoc')}


def maven_tools():
    java_home = Path(os.environ['JAVA_HOME']).expanduser().resolve() if os.environ.get('JAVA_HOME') else executable('javac').parent.parent
    if not (java_home / 'bin/javac').is_file():
        raise ValueError('Maven requires a JDK, including javac')
    maven = executable('mvn')
    version = subprocess.check_output([str(maven), '--version'], text=True, stderr=subprocess.STDOUT, timeout=10,
        env={'PATH': os.environ.get('PATH','/usr/bin:/bin'), 'JAVA_HOME': str(java_home), 'MAVEN_SKIP_RC': 'true'})
    match = re.search(r'Apache Maven (\d+)\.(\d+)', version)
    if not match or tuple(map(int, match.groups())) < (3,9):
        raise ValueError('Maven 3.9+ is required for the controlled MAVEN_ARGS environment')
    return maven, java_home


def maven_environment(scratch, maven, java_home, cache):
    scratch.mkdir(parents=True, exist_ok=True)
    settings = scratch / 'maven-settings.xml'
    if settings.is_symlink():
        raise ValueError('Maven settings must be a private regular file')
    settings.write_text('<settings xmlns="http://maven.apache.org/SETTINGS/1.2.0"/>\n')
    # Maven 3.9+ reads these arguments before project arguments. No personal settings or RC scripts.
    args = ['-o', '-B', '-ntp', '-s', str(settings), '-gs', str(settings), '-Dmaven.repo.local=' + str(cache)]
    if any(any(c.isspace() for c in value) for value in args):
        raise ValueError('Maven environment paths must not contain whitespace (MAVEN_ARGS uses shell word splitting)')
    return {'JAVA_HOME': str(java_home), 'MAVEN_SKIP_RC': 'true', 'MAVEN_ARGS': ' '.join(args),
            'JAVA_TOOL_OPTIONS': '-Djava.io.tmpdir=' + str(scratch),
            'PATH': str(java_home / 'bin') + ':' + str(maven.parent) + ':' + os.environ.get('PATH', '/usr/bin:/bin')}


def go_environment(workspace):
    return {"GOCACHE": str(workspace / ".execution/go-build"), "GOPROXY": "off", "GOSUMDB": "off",
        "GOTOOLCHAIN": "local", "GOFLAGS": "-mod=readonly", "GOWORK": "off", "GOMODCACHE": str(Path.home() / "go/pkg/mod")}
