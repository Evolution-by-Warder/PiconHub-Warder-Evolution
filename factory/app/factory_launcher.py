"""Windows launcher with GUI heartbeat and rollback of pending updates."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(os.environ.get('WARDER_PICON_FACTORY_ROOT', 'D:/WARDER-PICON-FACTORY' if os.name == 'nt' else str(Path.home() / 'WARDER-PICONS')))
APP = ROOT / '11-APP' / 'WARDER-PICON-FACTORY'
LOG = ROOT / '08-REPORTS' / 'factory-launch.log'


def app_command(app=APP, python=sys.executable):
    entry = Path(app) / 'engine.py'
    if not entry.is_file():
        raise FileNotFoundError('Factory engine.py not found: ' + str(entry))
    return [str(python), '-u', str(entry)]


def launch(app=APP, python=sys.executable, log=LOG, *, runner=subprocess.run):
    cmd = app_command(app, python)
    log = Path(log)
    log.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env['WARDER_PICON_FACTORY_ROOT'] = str(ROOT)
    with log.open('a', encoding='utf-8') as out:
        out.write('Launching Factory (no unverified update is installed)\n')
        out.flush()
        return runner(cmd, cwd=str(app), env=env, stdout=out, stderr=subprocess.STDOUT).returncode


def launch_with_recovery(app=APP, python=sys.executable, log=LOG, *, timeout=20):
    """A new GUI must report ready before previous application is deleted."""
    from factory_update_transaction import resolve
    app = Path(app).resolve()
    cmd = app_command(app, python)
    log = Path(log)
    log.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.factory-launch-', dir=log.parent) as temporary:
        marker = Path(temporary) / 'gui-ready'
        env = os.environ.copy()
        env['WARDER_PICON_FACTORY_ROOT'] = str(ROOT)
        env['WARDER_FACTORY_GUI_READY_FILE'] = str(marker)
        with log.open('a', encoding='utf-8') as out:
            proc = subprocess.Popen(cmd, cwd=str(app), env=env, stdout=out, stderr=subprocess.STDOUT)
            import time
            deadline = time.monotonic() + timeout
            ready = False
            while time.monotonic() < deadline:
                if marker.is_file() and marker.read_text(encoding='utf-8').strip() == 'GUI_READY':
                    ready = True
                    break
                if proc.poll() is not None:
                    break
                time.sleep(.1)
            if ready:
                resolve(app, gui_ready=True)
                return proc.wait()
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
            outcome = resolve(app, gui_ready=False)
            out.write('GUI did not report startup readiness; transaction: ' + outcome + '\n')
            out.flush()
        # The restored application must actually start, rather than leaving the user
        # with a rollback on disk but no running Factory window.
        if outcome == 'rolled_back':
            return launch(app=app, python=python, log=log)
        return 1


def main():
    from factory_single_instance import exclusive_launcher, AlreadyRunning
    try:
        with exclusive_launcher(ROOT / '11-APP' / '.factory-launch.lock'):
            from factory_persistent_data import migrate
            migrate(APP, ROOT / '11-APP' / '.factory-data')
            from factory_auto_update import attempt_update
            def log_update(message):
                LOG.parent.mkdir(parents=True, exist_ok=True)
                with LOG.open('a', encoding='utf-8') as stream:
                    stream.write(message + '\n')
            pending = APP.parent / '.factory-pending-update.json'
            if pending.is_file():
                # A previous run may have crashed before acknowledging GUI startup.
                # Never overwrite its rollback state with another update.
                log_update('Pending update recovered by GUI readiness check')
                return launch_with_recovery()
            attempt_update(APP, reporter=log_update)
            if pending.is_file():
                return launch_with_recovery()
            # An ordinary, already-installed GUI must not be killed because its
            # first scan takes longer than the update-specific readiness timeout.
            return launch()
    except (OSError, ValueError, AlreadyRunning) as exc:
        print('WARDER FACTORY launch failed:', exc, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
