"""Short-lived updater process; never replace an app while another Factory owns it."""
from factory_auto_update import attempt_update
from factory_single_instance import exclusive_launcher, AlreadyRunning
from workspace_paths import resolve_root, workspace_paths


def run(*, updater=attempt_update, reporter=print):
    root = resolve_root()
    app = workspace_paths(root)['app']
    lock = root / '11-APP' / '.factory-launch.lock'
    # The pending state is checked under the launcher lock below.
    pending = app.parent / '.factory-pending-update.json'
    try:
        with exclusive_launcher(lock):
            if pending.exists():
                reporter('FACTORY UPDATE: pending GUI confirmation; no second update')
                return 'pending_gui_confirmation'
            result = updater(app, reporter=reporter)
            reporter('FACTORY UPDATE: ' + result)
            return result
    except AlreadyRunning:
        reporter('FACTORY UPDATE: application already running; update deferred')
        return 'already_running'
    except (OSError, ValueError) as exc:
        reporter('FACTORY UPDATE: skipped (' + type(exc).__name__ + '); installed application preserved')
        return 'skipped'


if __name__ == '__main__':
    run()
