"""Crash-recoverable activation state for a launcher-owned Factory update.

A staged update is never activated merely because it exists: the caller must
explicitly authorize activation after independently checking its release hash.
"""
import json
import os
from pathlib import Path
import shutil
import time

from factory_update_activate import activate_staged, ActivationError

STATE = '.factory-pending-update.json'


def _write_state(path, payload):
    path = Path(path)
    tmp = path.with_name(path.name + '.tmp')
    with tmp.open('w', encoding='utf-8') as f:
        json.dump(payload, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def begin(stage, app, *, authorized=False, validate=None):
    """Explicitly authorized local transaction; caller holds single-instance lock."""
    if not authorized:
        raise ActivationError('Explicit update authorization missing')
    app = Path(app).resolve()
    state = app.parent / STATE
    if state.exists():
        raise ActivationError('Unresolved update transaction')
    previous = activate_staged(stage, app, validate=validate)
    try:
        _write_state(state, {'app': str(app), 'previous': str(previous) if previous else None,
                             'started': False, 'created': time.time()})
    except Exception:
        # Do not leave an untracked replacement active.
        if app.is_dir():
            shutil.rmtree(app)
        if previous and previous.exists():
            os.replace(previous, app)
        raise
    return state


def resolve(app, *, gui_ready=False):
    """Confirm after a genuine GUI heartbeat; otherwise restore prior version."""
    app = Path(app).resolve()
    state = app.parent / STATE
    if not state.is_file():
        return 'no_pending_update'
    record = json.loads(state.read_text(encoding='utf-8'))
    if record.get('app') != str(app):
        raise ActivationError('Transaction application mismatch')
    prev_raw = record.get('previous')
    previous = Path(prev_raw) if prev_raw else None
    if previous and (previous.parent != app.parent or not previous.name.startswith(app.name + '.previous-')):
        raise ActivationError('Unsafe rollback location')
    if gui_ready:
        if previous and previous.is_dir():
            shutil.rmtree(previous)
        state.unlink()
        return 'confirmed'
    if previous and previous.is_dir():
        if app.exists():
            shutil.rmtree(app)
        os.replace(previous, app)
        state.unlink()
        return 'rolled_back'
    if previous:
        raise ActivationError('Previous application missing; refusing destructive rollback')
    # Fresh install has no prior version; do not erase it on a failed start.
    state.unlink()
    return 'failed_first_install_preserved'
