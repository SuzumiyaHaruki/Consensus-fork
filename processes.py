"""Bounded subprocesses for trusted controller helpers, not target test execution."""
import signal
import subprocess
import time

from generator.runner import Terminated, terminate_group, utc_now, write_json


def invoke(argv, folder, timeout, cwd):
    folder.mkdir(parents=True, exist_ok=False)
    record = {'argv': argv, 'cwd': str(cwd), 'started_at': utc_now(), 'status': 'running', 'timeout_seconds': timeout}
    write_json(folder / 'process.json', record)
    started, process = time.monotonic(), None
    old_term = signal.getsignal(signal.SIGTERM)
    def cancel(*_):
        raise Terminated('SIGTERM')
    signal.signal(signal.SIGTERM, cancel)
    try:
        with (folder / 'stdout.log').open('w') as out, (folder / 'stderr.log').open('w') as err:
            process = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.DEVNULL, stdout=out, stderr=err, start_new_session=True)
            record['pid'] = process.pid
            write_json(folder / 'process.json', record)
            try:
                process.wait(timeout=timeout)
                record['status'] = 'completed'
            except subprocess.TimeoutExpired:
                record['status'] = 'timed_out'
    except (KeyboardInterrupt, Terminated):
        record['status'] = 'interrupted'
    except OSError as exc:
        record.update(status='launch_failed', error=str(exc))
    finally:
        old_int = signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        try:
            if process is not None:
                if process.poll() is None:
                    # CA handles TERM itself and needs time to save its last completed report.
                    try:
                        process.send_signal(signal.SIGTERM)
                        process.wait(timeout=5)
                    except (ProcessLookupError, subprocess.TimeoutExpired):
                        pass
                terminate_group(process)
                record['returncode'] = process.returncode
            record.update(ended_at=utc_now(), elapsed_seconds=time.monotonic() - started)
            write_json(folder / 'process.json', record)
        finally:
            signal.signal(signal.SIGINT, old_int)
            signal.signal(signal.SIGTERM, old_term)
    return record
