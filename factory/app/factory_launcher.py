"""Windows launcher with GUI heartbeat and rollback of pending updates."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from workspace_paths import resolve_root, workspace_paths, verify_required_directories

ROOT = resolve_root()
_PATHS = workspace_paths(ROOT)
APP = _PATHS['app']
LOG = _PATHS['logs'] / 'factory-launch.log'


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
    if os.name != 'nt':
        env['WARDER_PICON_FACTORY_ROOT'] = str(ROOT)
    with log.open('a', encoding='utf-8') as out:
        out.write('Launching Factory (no unverified update is installed)\n')
        out.flush()
        return runner(cmd, cwd=str(app), env=env, stdout=out, stderr=subprocess.STDOUT).returncode


def launch_with_recovery(app=APP, python=sys.executable, log=LOG, *, timeout=90):
    """A new GUI must report ready before previous application is deleted."""
    from factory_update_transaction import resolve
    app = Path(app).resolve()
    log = Path(log)
    log.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.factory-launch-', dir=log.parent) as temporary:
        marker = Path(temporary) / 'gui-ready'
        env = os.environ.copy()
        if os.name != 'nt':
            env['WARDER_PICON_FACTORY_ROOT'] = str(ROOT)
        env['WARDER_FACTORY_GUI_READY_FILE'] = str(marker)
        with log.open('a', encoding='utf-8') as out:
            if not (app / 'engine.py').is_file():
                outcome = resolve(app, gui_ready=False)
                out.write('Missing engine before launch; transaction: ' + outcome + '\n')
                out.flush()
                if outcome == 'rolled_back':
                    return launch(app=app, python=python, log=log)
                return 1
            cmd = app_command(app, python)
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
    structure_ok, findings = verify_required_directories(ROOT)
    if not structure_ok:
        print('WARDER FACTORY read-only preflight blocked writes: ' + '; '.join(findings), file=sys.stderr)
        return 1
    try:
        with exclusive_launcher(ROOT / '11-APP' / '.factory-launch.lock'):
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
            if not (APP / 'engine.py').is_file():
                from factory_update_transaction import resolve
                previous = sorted(APP.parent.glob(APP.name + '.previous-*'), reverse=True)
                log_update('Factory engine missing; automatic update suspended; recovery candidates: ' + str(len(previous)))
                if previous:
                    log_update('Previous application found; manual inspection required before restoring')
                return 1
            # The update check runs in a separate bootstrap BEFORE this launcher
            # starts (SPUSTI-WARDER.cmd). Do not modify APP from its own process.
            # A successful update leaves a pending transaction which must be
            # acknowledged by a real GUI heartbeat or rolled back.
            return launch()
    except (OSError, ValueError, AlreadyRunning) as exc:
        print('WARDER FACTORY launch failed:', exc, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
