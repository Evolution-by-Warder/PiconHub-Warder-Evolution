"""Activate a verified staged Factory release while the GUI is stopped.

Caller must hold the launcher-level single-instance lock. The stage must be
created by factory_update_stage.stage_verified_zip. No user data is touched.
"""
from pathlib import Path
import os
import shutil
import uuid

class ActivationError(RuntimeError):
    pass

def activate_staged(stage, app_dir, *, validate=None):
    stage, app = Path(stage).resolve(), Path(app_dir).resolve()
    if not stage.is_dir() or not (stage / '.verified-sha256').is_file():
        raise ActivationError('Stage has not been verified')
    if not (stage / 'engine.py').is_file():
        raise ActivationError('Factory entrypoint missing')
    if stage == app or stage in app.parents or app in stage.parents:
        raise ActivationError('Overlapping stage/application directories')
    if validate is not None and not validate(stage):
        raise ActivationError('Staged application validation failed')
    app.parent.mkdir(parents=True, exist_ok=True)
    previous = app.with_name(app.name + '.previous-' + uuid.uuid4().hex)
    had_old = app.exists()
    try:
        if had_old:
            os.replace(app, previous)
        try:
            os.replace(stage, app)
        except OSError:
            # Cross-volume staging is not atomic: copy to a sibling first.
            sibling = app.with_name(app.name + '.incoming-' + uuid.uuid4().hex)
            try:
                shutil.copytree(stage, sibling, symlinks=False)
                os.replace(sibling, app)
            finally:
                if sibling.exists():
                    shutil.rmtree(sibling)
    except Exception as exc:
        if app.exists() and had_old:
            shutil.rmtree(app)
        if had_old and previous.exists():
            os.replace(previous, app)
        raise ActivationError('Activation failed; previous version restored') from exc
    # The previous version is retained until the launcher confirms startup.
    return previous if had_old else None

def confirm_started(previous):
    """Call only after the new GUI has actually reported successful startup."""
    if previous is not None:
        previous = Path(previous)
        if previous.is_dir() and '.previous-' in previous.name:
            shutil.rmtree(previous)
