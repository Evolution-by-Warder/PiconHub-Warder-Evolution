"""Windows-user-bound DPAPI storage for the optional Factory GitHub upload credential.

Never write a plaintext token or include it in diagnostics. No credential means
uploads remain queued locally. Windows only: other systems use environment variables.
"""
import ctypes
import os
import shutil
import subprocess
from pathlib import Path

class DATA_BLOB(ctypes.Structure):
    _fields_ = [('cbData', ctypes.c_ulong), ('pbData', ctypes.POINTER(ctypes.c_byte))]

def _blob(data):
    buf = ctypes.create_string_buffer(data)
    return DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte))), buf

def _transform(data, protect):
    if os.name != 'nt':
        raise OSError('Windows DPAPI required')
    crypt = ctypes.windll.crypt32
    kernel = ctypes.windll.kernel32
    src, keepalive = _blob(data)
    dst = DATA_BLOB()
    operation = crypt.CryptProtectData if protect else crypt.CryptUnprotectData
    if protect:
        ok = operation(ctypes.byref(src), None, None, None, None, 0x01, ctypes.byref(dst))
    else:
        ok = operation(ctypes.byref(src), None, None, None, None, 0x01, ctypes.byref(dst))
    if not ok:
        raise ctypes.WinError()
    try:
        return ctypes.string_at(dst.pbData, dst.cbData)
    finally:
        kernel.LocalFree(dst.pbData)

def github_cli_token():
    """Reuse persistent GitHub CLI login, if available, without saving a second token."""
    gh = shutil.which('gh')
    if not gh:
        return ''
    try:
        result = subprocess.run([gh, 'auth', 'token', '--hostname', 'github.com'],
                                capture_output=True, text=True, timeout=12, check=False)
        if result.returncode == 0:
            token = result.stdout.strip()
            if token and not any(char.isspace() for char in token):
                return token
    except (OSError, subprocess.TimeoutExpired):
        pass
    return ''

def load_token(path):
    configured = os.environ.get('WARDER_DIAGNOSTICS_TOKEN', '').strip()
    if configured:
        return configured
    try:
        return _transform(Path(path).read_bytes(), False).decode('utf-8').strip()
    except (OSError, UnicodeError, ValueError):
        return github_cli_token()

def load_master_write_token(path):
    """Read the distinct Master-write credential, never the diagnostics token."""
    configured = os.environ.get('WARDER_MASTER_WRITE_TOKEN', '').strip()
    if configured and not any(char.isspace() for char in configured):
        return configured
    try:
        stored = _transform(Path(path).read_bytes(), False).decode('utf-8').strip()
        if stored and not any(char.isspace() for char in stored):
            return stored
    except (OSError, UnicodeError, ValueError):
        pass
    return github_cli_token()

def save_master_write_token(path, token):
    """Persist an optional Master-write token using the same user-bound DPAPI."""
    save_token(path, token)

def save_token(path, token):
    token = str(token).strip()
    if not token or any(c.isspace() for c in token) or len(token) > 512:
        raise ValueError('Invalid GitHub token')
    encrypted = _transform(token.encode('utf-8'), True)
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_suffix('.tmp')
    try:
        temp.write_bytes(encrypted)
        os.replace(temp, destination)
    finally:
        if temp.exists():
            temp.unlink()
