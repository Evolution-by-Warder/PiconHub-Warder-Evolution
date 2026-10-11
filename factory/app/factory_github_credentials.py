"""Windows-user-bound DPAPI storage for the optional Factory GitHub upload credential.

Never write a plaintext token or include it in diagnostics. No credential means
uploads remain queued locally. Windows only: other systems use environment variables.
"""
import ctypes
import os
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

def load_token(path):
    configured = os.environ.get('WARDER_DIAGNOSTICS_TOKEN', '').strip()
    if configured:
        return configured
    try:
        return _transform(Path(path).read_bytes(), False).decode('utf-8').strip()
    except (OSError, UnicodeError, ValueError):
        return ''

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
