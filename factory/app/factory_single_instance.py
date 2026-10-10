"""OS-backed exclusive launcher lock; held for the whole GUI lifetime."""
from contextlib import contextmanager
from pathlib import Path
import os

class AlreadyRunning(RuntimeError):
    pass

@contextmanager
def exclusive_launcher(lock_path):
    path = Path(lock_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as handle:
        # Lock byte zero, not the whole file; Windows msvcrt.locking requires a byte.
        handle.seek(0)
        if handle.read(1) == b'':
            handle.write(b'\0')
            handle.flush()
        handle.seek(0)
        if os.name == 'nt':
            import msvcrt
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise AlreadyRunning('Factory is already running') from exc
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise AlreadyRunning('Factory is already running') from exc
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
